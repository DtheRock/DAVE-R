"""Declarative assertion evaluator.

Gates are data, not code. This module is the only place that knows how to execute
them, which is what lets the skill and the MCP server run identical logic
without duplicating it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .model import MISSING, Context, is_evidence, parse_time, provenance_of, unwrap


@dataclass
class Result:
    ok: bool
    reason: str = ""
    vacuous: bool = False   # held only because there was nothing to check

    def __bool__(self) -> bool:
        return self.ok


OK = Result(True)
VACUOUS = Result(True, vacuous=True)


def _fail(msg: str) -> Result:
    return Result(False, msg)


def _num(v: Any):
    if isinstance(v, bool):
        return None
    return v if isinstance(v, (int, float)) else None


def _compare(ctx: Context, a_ref: Any, b_ref: Any, op: str) -> Result:
    a, b = ctx.resolve(a_ref), ctx.resolve(b_ref)
    if a is MISSING:
        return _fail(f"{a_ref} is missing or unmeasured")
    if b is MISSING:
        return _fail(f"{b_ref} is missing or unmeasured")

    ta, tb = parse_time(a), parse_time(b)
    if ta and tb and not (_num(a) is not None and _num(b) is not None):
        a, b = ta, tb
    else:
        na, nb = _num(a), _num(b)
        if na is not None and nb is not None:
            a, b = na, nb

    try:
        res = {
            "lt": a < b, "lte": a <= b, "gt": a > b, "gte": a >= b,
            "eq": a == b, "ne": a != b,
        }[op]
    except TypeError:
        return _fail(f"cannot compare {a_ref} ({a!r}) with {b_ref} ({b!r})")

    if res:
        return OK
    sym = {"lt": "<", "lte": "<=", "gt": ">", "gte": ">=", "eq": "==", "ne": "!="}[op]
    return _fail(f"{a_ref} ({a}) {sym} {b_ref} ({b}) is false")


def evaluate(expr: Any, ctx: Context) -> Result:
    if expr is True:
        return OK
    if expr is False:
        return _fail("literal false")
    if not isinstance(expr, dict) or len(expr) != 1:
        return _fail(f"malformed assertion: {expr!r}")

    (op, arg), = expr.items()

    # --- boolean combinators -------------------------------------------------
    if op == "all":
        results = []
        for sub in arg:
            r = evaluate(sub, ctx)
            if not r:
                return r
            results.append(r)
        return VACUOUS if results and all(x.vacuous for x in results) else OK

    if op == "any":
        reasons = []
        for sub in arg:
            r = evaluate(sub, ctx)
            if r:
                return r
            reasons.append(r.reason)
        return _fail("no alternative held: " + "; ".join(reasons))

    if op == "not":
        if not evaluate(arg, ctx):
            return OK
        # Render the negated form legibly rather than dumping the raw expression.
        if isinstance(arg, dict) and len(arg) == 1:
            (inner_op, inner_arg), = arg.items()
            if inner_op == "matches":
                v = ctx.resolve(inner_arg[0])
                return _fail(f"{inner_arg[0]} ('{v}') matches disallowed pattern /{inner_arg[1]}/")
            if inner_op in {"eq", "in", "exists"}:
                return _fail(f"{inner_arg if inner_op != 'exists' else inner_arg} unexpectedly satisfied '{inner_op}'")
        return _fail(f"condition held but should not: {arg!r}")

    if op == "implies":
        cond, then = arg
        if not evaluate(cond, ctx):
            return VACUOUS  # precondition never fired; nothing was checked
        r = evaluate(then, ctx)
        return OK if r else _fail(f"precondition held but {r.reason}")

    # --- existence -----------------------------------------------------------
    if op == "exists":
        node = ctx.resolve_node(arg)
        if node is MISSING or node is None:
            return _fail(f"{arg} is not set")
        if is_evidence(node) and provenance_of(node) == "unmeasured":
            return _fail(f"{arg} is explicitly unmeasured")
        if unwrap(node) is MISSING:
            return _fail(f"{arg} has no value")
        if isinstance(node, (list, dict, str)) and len(node) == 0:
            return _fail(f"{arg} is empty")
        return OK

    if op == "min_items":
        ref, n = arg
        node = ctx.resolve(ref)
        if not isinstance(node, list):
            return _fail(f"{ref} is not a list (got {type(node).__name__})")
        return OK if len(node) >= n else _fail(f"{ref} has {len(node)} item(s), needs {n}")

    if op == "lookup_exists":
        map_ref, key_ref = arg
        m = ctx.resolve(map_ref)
        k = ctx.resolve(key_ref)
        if not isinstance(m, dict):
            return _fail(f"{map_ref} is not a map")
        if k not in m:
            return _fail(f"{map_ref} has no entry for '{k}'")
        return OK

    # --- comparison ----------------------------------------------------------
    if op in {"lt", "lte", "gt", "gte", "eq", "ne"}:
        return _compare(ctx, arg[0], arg[1], op)

    if op == "same":
        a, b = ctx.resolve(arg[0]), ctx.resolve(arg[1])
        if a is MISSING or b is MISSING:
            return _fail(f"cannot compare, one of {arg} is missing")
        return OK if a == b else _fail(f"{arg[0]} ({a}) != {arg[1]} ({b})")

    if op == "before":
        a, b = parse_time(ctx.resolve(arg[0])), parse_time(ctx.resolve(arg[1]))
        if not a or not b:
            return _fail(f"{arg} are not both timestamps")
        return OK if a < b else _fail(f"{arg[0]} ({a.date()}) is not before {arg[1]} ({b.date()})")

    if op == "in":
        ref, allowed = arg
        v = ctx.resolve(ref)
        if v is MISSING:
            return _fail(f"{ref} is missing")
        return OK if v in allowed else _fail(f"{ref} is '{v}', expected one of {allowed}")

    if op == "matches":
        ref, pattern = arg
        v = ctx.resolve(ref)
        if not isinstance(v, str):
            return _fail(f"{ref} is not a string")
        return OK if re.search(pattern, v) else _fail(f"{ref} ('{v}') does not match /{pattern}/")

    # --- evidence typing (the spec's central rule) ---------------------------
    if op == "provenance_in":
        ref, allowed = arg
        node = ctx.resolve_node(ref)
        if node is MISSING or node is None:
            return _fail(f"{ref} is missing (evidence required: {'/'.join(allowed)})")
        p = provenance_of(node)
        if p is None:
            return _fail(f"{ref} carries no provenance; evidence-typed value required")
        if p not in allowed:
            if p == "asserted":
                who = node.get("asserted_by", "someone")
                return _fail(
                    f"{ref} is asserted by {who}, but this gate authorizes enforcement "
                    f"and requires {'/'.join(allowed)}. Measure it, do not state it."
                )
            if p == "unmeasured":
                return _fail(f"{ref} is unmeasured. The gate blocks rather than estimating.")
            return _fail(f"{ref} provenance is '{p}', requires {'/'.join(allowed)}")
        if p == "observed":
            src = node.get("source") or {}
            if not src.get("system") or not src.get("ref"):
                return _fail(f"{ref} claims observed but has no re-runnable source")
        if p == "derived":
            for parent in node.get("derived_from", []):
                pn = ctx.resolve_node(parent)
                if provenance_of(pn) == "asserted":
                    return _fail(f"{ref} is derived from asserted value {parent}; evidence laundering")
        return OK

    # --- iteration -----------------------------------------------------------
    if op in {"each", "each_any"}:
        coll = ctx.resolve(arg["in"])
        if coll is MISSING or coll is None:
            return _fail(f"{arg['in']} is missing")
        if not isinstance(coll, list):
            return _fail(f"{arg['in']} is not a list")
        if not coll:
            return _fail(f"{arg['in']} is empty") if op == "each_any" else VACUOUS

        failures = []
        for i, item in enumerate(coll):
            label = item.get("id") if isinstance(item, dict) and item.get("id") else f"[{i}]"
            sub = ctx.bind(item=item, outer=ctx.bindings.get("item"))
            r = evaluate(arg["satisfies"], sub)
            if op == "each_any" and r:
                return OK
            if op == "each" and not r:
                failures.append(f"{label}: {r.reason}")
        if op == "each_any":
            return _fail(f"no item in {arg['in']} satisfied the condition")
        return OK if not failures else _fail("; ".join(failures))

    if op == "any_in":
        coll = ctx.resolve(arg["collection"])
        if not isinstance(coll, list):
            return _fail(f"{arg['collection']} is not a list")
        for item in coll:
            sub = ctx.bind(item=item, outer=ctx.bindings.get("item"))
            if evaluate(arg["where"], sub):
                return OK
        outer = ctx.bindings.get("item")
        who = outer.get("id") if isinstance(outer, dict) else ""
        return _fail(f"nothing in {arg['collection']} matched{' for ' + str(who) if who else ''}")

    # --- cross-artifact integrity -------------------------------------------
    if op == "refs_resolve":
        list_ref, coll_ref, id_field = arg
        ids = ctx.resolve(list_ref)
        coll = ctx.resolve(coll_ref)
        if not isinstance(ids, list):
            return _fail(f"{list_ref} is not a list")
        if not isinstance(coll, list):
            return _fail(f"{coll_ref} is missing; cannot verify references")
        known = {c.get(id_field) for c in coll if isinstance(c, dict)}
        dangling = [i for i in ids if i not in known]
        if dangling:
            return _fail(f"{list_ref} references unknown {coll_ref} {id_field}(s): {dangling}")
        return OK

    return _fail(f"unknown operator '{op}'")
