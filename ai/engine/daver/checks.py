"""Builtin checks: gates that need to run code, not just evaluate an expression.

Most gates are pure declarative assertions over the cycle document, which is what
keeps them portable across executors. Three cannot be: verifying a hash chain,
verifying a detached signature, and re-running a telemetry source all require
computation and I/O. They are registered here by name and referenced from a gate's
`check:` key instead of `assert:`.

An executor that does not implement a named check MUST fail the gate, never skip it.
"""
from __future__ import annotations

import re
from typing import Callable

from . import integrity, resolvers

_CHECKS: dict[str, Callable[[dict, dict], tuple[bool, str]]] = {}


def register(name: str):
    def deco(fn):
        _CHECKS[name] = fn
        return fn
    return deco


def get(name: str):
    return _CHECKS.get(name)


def registered() -> list[str]:
    return sorted(_CHECKS)


# Placeholder detection, deliberately split into two shapes.
#
# Word shapes must appear at the start and end on a word boundary, so "Nathalie" is not
# an "n/a" and "examples/" is not "example".
_PLACEHOLDER_WORD = re.compile(
    r"^\s*(todo|tbd|tba|fixme|xxx+|change ?me|fill ?in|placeholder|your[ _-]\w+)\b", re.I)

# Filler shapes must be the ENTIRE value. An early version matched any string starting
# with a dash, which flagged every "-----BEGIN SSH SIGNATURE-----" block as unfilled.
# A signature is the opposite of a placeholder.
_PLACEHOLDER_WHOLE = re.compile(
    r"^\s*(n/?a|-+|\?+|\.{3,}|\[[^\]]*\]|<[^>]*>)\s*$", re.I)

# Fields whose contents are opaque blobs and can never be placeholders.
_OPAQUE_KEYS = {"detached_signature", "hash", "prev", "sha", "digest"}
_ARMOURED = re.compile(r"-----BEGIN [A-Z0-9 ]+-----")


def _is_placeholder(key: str, value: str) -> bool:
    if key.rsplit(".", 1)[-1] in _OPAQUE_KEYS:
        return False
    if _ARMOURED.search(value):
        return False
    return bool(_PLACEHOLDER_WORD.match(value) or _PLACEHOLDER_WHOLE.match(value))


@register("no_placeholder_values")
def _no_placeholders(cycle: dict, opts: dict) -> tuple[bool, str]:
    """Scaffolds and half-finished briefs must not read as complete.

    Found by pointing a live agent at a fresh scaffold: `raci.accountable.identity`
    of "TODO" passed D-5, because it exists and does not match the team/group
    pattern. A cycle that claims a named accountable human when there is none is
    the most dangerous possible false pass, because every later signature gate
    compares against that identity.
    """
    hits = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str) and _is_placeholder(path, node):
            hits.append(f"{path} = {node!r}")

    for section in ("definition_brief", "control_matrix", "validation_plan",
                    "exception_register", "execution"):
        if cycle.get(section):
            walk(cycle[section], section)
    if not hits:
        return True, ""
    return False, f"{len(hits)} unfilled placeholder(s): " + "; ".join(hits[:6])


@register("audit_chain_intact")
def _audit_chain(cycle: dict, opts: dict) -> tuple[bool, str]:
    if not (cycle.get("audit") or []):
        return False, "audit log is empty; agent actions are unrecorded"
    r = integrity.verify_audit(cycle)
    return bool(r.get("ok")), "" if r.get("ok") else r.get("detail", "chain broken")


@register("decisions_cryptographically_signed")
def _signed(cycle: dict, opts: dict) -> tuple[bool, str]:
    subjects, problems = [], []
    for subject, path in integrity.SIGNED_SUBJECTS.items():
        node = cycle
        for k in path:
            node = (node or {}).get(k) or {}
        if not node:
            continue
        subjects.append(subject)
        r = integrity.verify_signature(cycle, subject, opts.get("allowed_signers"))
        if not r.get("ok"):
            problems.append(f"{subject}: {r.get('detail', 'unverified')}")
    if not subjects:
        return False, "no decision blocks present to sign"
    return (not problems), "; ".join(problems)


@register("observed_values_reverifiable")
def _reverify(cycle: dict, opts: dict) -> tuple[bool, str]:
    r = resolvers.verify(cycle, tolerance=opts.get("tolerance", 0.02),
                         strict=opts.get("strict_resolvers", False))
    if r["ok"]:
        return True, ""
    bad = [f"{f['path']} ({f['status']})" for f in r["findings"]][:6]
    return False, f"{r['counts']['drift']} drifted, {r['counts']['error']} unresolvable: " + "; ".join(bad)
