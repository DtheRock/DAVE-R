"""Source resolvers: re-execute a recorded observation and check it still holds.

The gap this closes. Before this module, `provenance: observed` was an honour
system - an agent could write a plausible `source` that resolves to nothing, and
every downstream gate would treat the number as measured. The evidence contract
was only as strong as the agent's willingness to obey it.

A resolver takes a source descriptor and returns the live value. `daver verify`
re-runs every observed value in a cycle and reports drift, unresolvable sources,
and fabrications.

Resolvers are deliberately conservative:
  * Only allowlisted systems resolve. An unknown system is UNRESOLVABLE, never a pass.
  * `exec` runs a command from a config file the operator controls, never a command
    string taken from the cycle document, because a cycle document is agent-written
    and may be influenced by discovered content.
  * Network resolvers are not shipped enabled. Wire your own and register it.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from .model import is_evidence, provenance_of


@dataclass
class Resolution:
    status: str          # "match" | "drift" | "unresolvable" | "skipped" | "error"
    live_value: Any = None
    detail: str = ""


Resolver = Callable[[dict], Resolution]
_REGISTRY: dict[str, Resolver] = {}


def register(system: str, fn: Resolver) -> None:
    _REGISTRY[system] = fn


def registered() -> list[str]:
    return sorted(_REGISTRY)


# --- shipped resolvers -----------------------------------------------------

def _file_resolver(source: dict) -> Resolution:
    """ref is a path, optionally 'path#jsonpointer'. Root-relative to DAVER_EVIDENCE_ROOT."""
    root = os.path.abspath(os.environ.get("DAVER_EVIDENCE_ROOT", os.getcwd()))
    ref = str(source.get("ref", ""))
    path, _, pointer = ref.partition("#")
    full = os.path.abspath(os.path.join(root, path))
    if not (full == root or full.startswith(root + os.sep)):
        return Resolution("error", detail=f"path escapes evidence root: {path}")
    if not os.path.isfile(full):
        return Resolution("unresolvable", detail=f"no such file: {path}")
    try:
        with open(full) as fh:
            data = json.load(fh) if full.endswith(".json") else fh.read().strip()
    except Exception as e:
        return Resolution("error", detail=f"cannot read {path}: {e}")
    if pointer and isinstance(data, dict):
        node: Any = data
        for part in pointer.strip("/").split("/"):
            if not isinstance(node, dict) or part not in node:
                return Resolution("unresolvable", detail=f"pointer {pointer} not found in {path}")
            node = node[part]
        data = node
    return Resolution("match", live_value=data)


def _exec_resolver(source: dict) -> Resolution:
    """Runs a named command from .daver/resolvers.json.

    The cycle document supplies a KEY, never a command. A cycle is agent-written and
    its contents may be influenced by material the agent discovered, so allowing it to
    name an arbitrary command would be a command-injection path straight through the
    evidence layer.
    """
    root = os.path.abspath(os.environ.get("DAVER_EVIDENCE_ROOT", os.getcwd()))
    cfg_path = os.path.join(root, ".daver", "resolvers.json")
    if not os.path.isfile(cfg_path):
        return Resolution("unresolvable", detail="no .daver/resolvers.json in evidence root")
    try:
        with open(cfg_path) as fh:
            cfg = json.load(fh)
    except Exception as e:
        return Resolution("error", detail=f"bad resolvers.json: {e}")
    key = str(source.get("ref", ""))
    entry = (cfg.get("exec") or {}).get(key)
    if not entry:
        return Resolution("unresolvable", detail=f"'{key}' is not a declared exec resolver")
    argv = entry if isinstance(entry, list) else None
    if argv is None:
        return Resolution("error", detail=f"resolver '{key}' must be an argv list, not a shell string")
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=30, cwd=root, shell=False)
    except subprocess.TimeoutExpired:
        return Resolution("error", detail=f"resolver '{key}' timed out")
    except Exception as e:
        return Resolution("error", detail=f"resolver '{key}' failed: {e}")
    if out.returncode != 0:
        return Resolution("error", detail=f"resolver '{key}' exit {out.returncode}: {out.stderr[:200]}")
    text = out.stdout.strip()
    try:
        return Resolution("match", live_value=json.loads(text))
    except json.JSONDecodeError:
        return Resolution("match", live_value=text)


register("file", _file_resolver)
register("exec", _exec_resolver)


# --- verification ----------------------------------------------------------

def _walk_values(node: Any, path: str = ""):
    if is_evidence(node):
        yield path, node
        return
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_values(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_values(v, f"{path}[{i}]")


def _close_enough(recorded: Any, live: Any, tol: float = 0.02) -> bool:
    if isinstance(recorded, bool) or isinstance(live, bool):
        return recorded == live
    if isinstance(recorded, (int, float)) and isinstance(live, (int, float)):
        if recorded == 0:
            return abs(live) < 1e-9
        return abs(recorded - live) / abs(recorded) <= tol
    return str(recorded).strip() == str(live).strip()


def verify(cycle: dict, tolerance: float = 0.02, strict: bool = False) -> dict:
    """Re-run every observed value's source and compare.

    strict=True treats an unresolvable source as a failure. Use strict in CI where
    every telemetry system has a registered resolver; use lenient locally where some
    do not.
    """
    findings, counts = [], {"match": 0, "drift": 0, "unresolvable": 0, "error": 0, "skipped": 0}
    for path, node in _walk_values(cycle):
        if provenance_of(node) != "observed":
            continue
        src = node.get("source") or {}
        system = src.get("system")
        if not system or not src.get("ref"):
            findings.append({"path": path, "status": "error",
                             "detail": "claims observed but has no re-runnable source"})
            counts["error"] += 1
            continue
        fn = _REGISTRY.get(system)
        if fn is None:
            counts["unresolvable" if strict else "skipped"] += 1
            findings.append({"path": path, "status": "unresolvable" if strict else "skipped",
                             "system": system,
                             "detail": f"no resolver registered for '{system}'"})
            continue
        try:
            res = fn(src)
        except Exception as e:
            res = Resolution("error", detail=str(e))
        recorded = node.get("value")
        if res.status == "match" and not _close_enough(recorded, res.live_value, tolerance):
            res = Resolution("drift", live_value=res.live_value,
                             detail=f"recorded {recorded!r}, source now returns {res.live_value!r}")
        counts[res.status] = counts.get(res.status, 0) + 1
        if res.status != "match":
            findings.append({"path": path, "status": res.status, "system": system,
                             "ref": src.get("ref"), "detail": res.detail})
    ok = counts["drift"] == 0 and counts["error"] == 0 and counts["unresolvable"] == 0
    return {"ok": ok, "counts": counts, "findings": findings,
            "registered_resolvers": registered()}
