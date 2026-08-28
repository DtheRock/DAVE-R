"""Cycle loading, reference resolution, and evidence-typing rules.

The evidence rules here are the spec's central guarantee: a gate that authorizes
enforcement may only read values whose provenance is observed or derived. See
spec/evidence.md (normative).
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Any

MISSING = object()

EVIDENCE_KEYS = {"provenance"}
STRONG_PROVENANCE = {"observed", "derived"}
ALL_PROVENANCE = {"asserted", "observed", "derived", "unmeasured"}

_DUR = re.compile(r"^\$now(?:([+-])(\d+)([dhm]))?$")
_DATE_FMTS = ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def is_evidence(node: Any) -> bool:
    return isinstance(node, dict) and "provenance" in node


def unwrap(node: Any) -> Any:
    """Return the comparable payload of a node, transparently for evidence values."""
    if is_evidence(node):
        if node.get("provenance") == "unmeasured":
            return MISSING
        return node.get("value", MISSING)
    return node


def provenance_of(node: Any) -> str | None:
    return node.get("provenance") if is_evidence(node) else None


def parse_time(v: Any) -> _dt.datetime | None:
    if isinstance(v, _dt.datetime):
        return v if v.tzinfo else v.replace(tzinfo=_dt.timezone.utc)
    if isinstance(v, _dt.date):
        return _dt.datetime(v.year, v.month, v.day, tzinfo=_dt.timezone.utc)
    if not isinstance(v, str):
        return None
    s = v.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+0000"
    for fmt in _DATE_FMTS:
        try:
            d = _dt.datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
        except ValueError:
            continue
    return None


class UnresolvedRef(Exception):
    """A reference whose root is not a known artifact. Only raised in strict mode."""


@dataclass
class Context:
    """One evaluation context: the cycle plus whatever loop bindings are active."""
    cycle: dict
    adapter: dict = field(default_factory=dict)
    bindings: dict = field(default_factory=dict)
    now: _dt.datetime = field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
    strict: bool = False

    def bind(self, **kw) -> "Context":
        b = dict(self.bindings)
        b.update(kw)
        return Context(self.cycle, self.adapter, b, self.now, self.strict)

    # ---- reference resolution -------------------------------------------------

    def resolve_node(self, ref: Any) -> Any:
        """Resolve a ref to its raw node (evidence wrapper intact). Non-refs pass through."""
        if not isinstance(ref, str):
            return ref

        if ref.startswith("$"):
            return self._resolve_special(ref)

        head, _, rest = ref.partition(".")
        if head in self.bindings:
            root = self.bindings[head]
            path = rest
        elif head in self.cycle or head in {
            "definition_brief", "control_matrix", "validation_plan",
            "exception_register", "refinement_log", "execution", "module", "audit",
        }:
            root = self.cycle.get(head, MISSING)
            path = rest
        else:
            # Not a ref shape we recognise. Under strict resolution this is an
            # authoring error and must surface; at runtime it is a literal.
            #
            # Returning the ref as a string was a silent fail-open: a misspelled
            # root ("validatoin_plan.x") became a non-empty string, so `exists`
            # passed and `ne` passed, and a broken gate reported as a passing one.
            if self.strict:
                raise UnresolvedRef(ref)
            return ref

        return self._walk(root, path)

    def _walk(self, node: Any, path: str) -> Any:
        if node is MISSING or not path:
            return node
        for part in path.split("."):
            if node is MISSING or node is None:
                return MISSING
            m = re.match(r"^([A-Za-z0-9_-]+)\[(\d+)\]$", part)
            if m:
                key, idx = m.group(1), int(m.group(2))
                node = node.get(key, MISSING) if isinstance(node, dict) else MISSING
                if isinstance(node, list) and idx < len(node):
                    node = node[idx]
                else:
                    return MISSING
                continue
            if isinstance(node, dict):
                node = node.get(part, MISSING)
            elif is_evidence(node):
                node = node.get(part, MISSING)
            else:
                return MISSING
        return node

    def _resolve_special(self, ref: str) -> Any:
        m = _DUR.match(ref)
        if m:
            if not m.group(1):
                return self.now
            sign, qty, unit = m.group(1), int(m.group(2)), m.group(3)
            delta = {"d": _dt.timedelta(days=qty), "h": _dt.timedelta(hours=qty), "m": _dt.timedelta(minutes=qty)}[unit]
            return self.now + delta if sign == "+" else self.now - delta

        if ref.startswith("$adapter."):
            key = ref[len("$adapter."):]
            val = self.adapter.get(key, MISSING)
            # min_shadow_days is a per-track map; select by the cycle's declared track.
            if isinstance(val, dict):
                track = unwrap(self._walk(self.cycle.get("definition_brief", {}), "triage.track"))
                if track in val:
                    return val[track]
                return MISSING
            return val

        return ref

    def resolve(self, ref: Any) -> Any:
        """Resolve a ref to its comparable value (evidence unwrapped)."""
        return unwrap(self.resolve_node(ref))


def load_cycle(path: str) -> dict:
    import json
    import yaml
    with open(path) as fh:
        text = fh.read()
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)
