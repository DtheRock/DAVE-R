"""Source resolvers: re-execute a recorded observation and check it still holds.

Before this module, `provenance: observed` was an honour system - an agent could
write a plausible `source` that resolves to nothing, and every downstream gate
would treat the number as measured. `daver verify` re-runs every observed value
and reports drift, unresolvable sources, and fabrications.

SECURITY MODEL (revised in 1.1.1 after an adversarial review)
-------------------------------------------------------------
This tool is installed by people who point it at repositories they did not write.
The document under examination, and any config that travels beside it, are
ATTACKER-CONTROLLED. Three rules follow:

  1. No resolver that executes a command is registered by default. `exec` must be
     turned on explicitly by the operator (DAVER_ENABLE_EXEC=1 or
     --allow-exec-resolvers). Anything that must be configured to be safe is
     unsafe in practice, so the safe state is the one you get for free.
  2. Containment is passed in by the caller, not read from a second environment
     variable. A tool boundary that does not bound the layer doing the work is
     decoration.
  3. Paths are resolved with realpath and symlinks are refused. abspath
     normalises `..` but happily follows a symlink out of the root.

Even with exec enabled, argv[0] is allowlisted against interpreters: an argv list
whose first element is a shell is a shell, so ["/bin/sh","-c",...] is not a
mitigation over a shell string.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from .model import is_evidence, provenance_of

# Interpreters that turn an "argv list" back into arbitrary code execution.
_INTERPRETERS = {
    "sh", "bash", "zsh", "dash", "ksh", "csh", "tcsh", "fish", "ash",
    "python", "python2", "python3", "pypy", "pypy3",
    "node", "nodejs", "deno", "bun", "perl", "ruby", "php", "lua", "tclsh",
    "awk", "gawk", "mawk", "sed", "env", "xargs", "eval", "exec", "nohup",
    "osascript", "powershell", "pwsh", "cmd", "wine", "docker", "kubectl",
    "ssh", "scp", "rsync", "curl", "wget", "nc", "ncat", "socat", "telnet",
    "make", "cmake", "git", "npm", "npx", "pip", "pip3", "uv", "gem", "cargo",
}

EXEC_ENV = "DAVER_ENABLE_EXEC"


@dataclass
class Resolution:
    status: str
    # match         verified against the live source
    # drift         source resolved, value differs from what was recorded
    # unresolvable  a resolver RAN and the source does not exist. Fabrication signal.
    # no_resolver   no resolver registered for that system. An operator gap, NOT a
    #               fabrication signal: you cannot detect a lie about a system you
    #               have no way to reach, and blocking on it punishes the wrong party.
    # error         something broke

    live_value: Any = None
    detail: str = ""


Resolver = Callable[[dict, str], Resolution]
_REGISTRY: dict[str, Resolver] = {}


def register(system: str, fn: Resolver) -> None:
    _REGISTRY[system] = fn


def registered() -> list[str]:
    return sorted(_REGISTRY)


def exec_enabled() -> bool:
    return "exec" in _REGISTRY


def enable_exec(announce: bool = True) -> None:
    """Turn on the exec resolver. Deliberately not called at import.

    The operator is telling us they trust the resolver config. Say what that
    means, once, so the decision is visible in the log rather than implicit.
    """
    if "exec" in _REGISTRY:
        return
    register("exec", _exec_resolver)
    if announce:
        print("daver: exec resolvers ENABLED. Commands declared in "
              ".daver/resolvers.json under the evidence root will be executed. "
              "Do not enable this against a repository you do not trust.")


def _maybe_enable_exec_from_env() -> None:
    if os.environ.get(EXEC_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        enable_exec(announce=False)


# --- containment -----------------------------------------------------------

def _confine(root: str, candidate: str) -> str:
    """Resolve `candidate` under `root`, refusing traversal AND symlink escape."""
    real_root = os.path.realpath(root)
    full = os.path.realpath(os.path.join(real_root, candidate))
    if not (full == real_root or full.startswith(real_root + os.sep)):
        raise ValueError(f"path escapes evidence root: {candidate}")
    # Refuse a symlink anywhere along the path, even one that lands inside the
    # root: following it is how a cloned repo reads files the operator never
    # offered. realpath above already resolved it; compare to catch the case.
    lexical = os.path.abspath(os.path.join(real_root, candidate))
    if lexical != full and os.path.islink(lexical):
        raise ValueError(f"refusing to follow symlink: {candidate}")
    parts = candidate.split(os.sep)
    probe = real_root
    for part in parts:
        if not part or part == ".":
            continue
        probe = os.path.join(probe, part)
        if os.path.islink(probe):
            raise ValueError(f"refusing to follow symlink: {candidate}")
    return full


def evidence_root(root: str | None = None) -> str:
    """Containment root. Callers pass it in; the env var is only the fallback."""
    return os.path.realpath(root or os.environ.get("DAVER_EVIDENCE_ROOT", os.getcwd()))


# --- shipped resolvers -----------------------------------------------------

def _file_resolver(source: dict, root: str) -> Resolution:
    """ref is a path, optionally 'path#jsonpointer', confined to the root."""
    ref = str(source.get("ref", ""))
    path, _, pointer = ref.partition("#")
    try:
        full = _confine(root, path)
    except ValueError as e:
        return Resolution("error", detail=str(e))
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


def _reject_argv(argv: list) -> str | None:
    """Why this argv must not run, or None if it is acceptable."""
    if not isinstance(argv, list) or not argv:
        return "resolver must be a non-empty argv list, not a shell string"
    if not all(isinstance(a, str) for a in argv):
        return "every argv element must be a string"
    prog = os.path.basename(argv[0]).lower()
    if prog.endswith(".exe"):
        prog = prog[:-4]
    if prog in _INTERPRETERS:
        return (f"argv[0] is '{prog}', an interpreter. An argv list whose first element "
                f"is a shell is still a shell. Point the resolver at a purpose-built "
                f"binary or a committed script instead of an inline -c.")
    if any(a in {"-c", "-e", "--eval", "--command"} for a in argv[1:]):
        return f"inline code flag {[a for a in argv[1:] if a in {'-c','-e','--eval','--command'}][0]!r} is not permitted"
    return None


def _exec_resolver(source: dict, root: str) -> Resolution:
    """Runs a named command from .daver/resolvers.json under the evidence root.

    The cycle document supplies a KEY, never a command, and the command it names
    must still survive the argv allowlist. Only reachable when the operator has
    explicitly enabled exec resolvers.
    """
    try:
        cfg_path = _confine(root, os.path.join(".daver", "resolvers.json"))
    except ValueError as e:
        return Resolution("error", detail=str(e))
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
    why = _reject_argv(entry)
    if why:
        return Resolution("error", detail=f"resolver '{key}' refused: {why}")
    try:
        out = subprocess.run(entry, capture_output=True, text=True, timeout=30,
                             cwd=root, shell=False)
    except subprocess.TimeoutExpired:
        return Resolution("error", detail=f"resolver '{key}' timed out")
    except FileNotFoundError:
        return Resolution("unresolvable", detail=f"resolver '{key}': {shlex.quote(entry[0])} not found")
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
_maybe_enable_exec_from_env()


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


def verify(cycle: dict, tolerance: float = 0.02, strict: bool = False,
           root: str | None = None) -> dict:
    """Re-run every observed value's source and compare.

    strict=True treats an unresolvable source as a failure. `root` is the
    containment boundary; callers that have one (the MCP server, the CLI) pass
    it so that boundary actually bounds this layer.
    """
    r = evidence_root(root)
    findings = []
    counts = {"match": 0, "drift": 0, "unresolvable": 0, "no_resolver": 0, "error": 0}
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
            counts["no_resolver"] += 1
            detail = (f"no resolver registered for '{system}', so this value could not be "
                      f"checked either way")
            if system == "exec" and not exec_enabled():
                detail += f" (exec resolvers are disabled; set {EXEC_ENV}=1 to enable)"
            findings.append({"path": path, "status": "no_resolver", "system": system,
                             "detail": detail})
            continue
        try:
            res = fn(src, r)
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
    # A verification failure is drift, an error, or a source that a working resolver
    # could not find. An unwired telemetry system is none of those: it is a gap in
    # the operator's setup, and it becomes a failure only under strict.
    failed = counts["drift"] + counts["error"] + counts["unresolvable"]
    ok = failed == 0 and not (strict and counts["no_resolver"])
    return {"ok": ok, "counts": counts, "findings": findings,
            "registered_resolvers": registered(), "root": r,
            "verified_count": counts["match"],
            "unverifiable_count": counts["no_resolver"],
            "failure_count": failed}
