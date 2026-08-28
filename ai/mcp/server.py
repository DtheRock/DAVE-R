#!/usr/bin/env python3
"""DAVE+R MCP server.

Exposes the lifecycle as tools any MCP client can call. This server and the agent
skill are two consumers of ONE spec: every gate executed here is loaded from
spec/gates/*.yaml at runtime, so the two can never drift apart.

Security posture, deliberate:
  * The server executes NO commands. Exec resolvers are never enabled here, and
    the server refuses to run if the environment tries to turn them on. A tool
    surface driven by a language model is the last place to accept a
    config-file-to-subprocess path.
  * It cannot authorize enforcement. There is no tool that writes an approval
    signature. `daver_request_authorization` prepares the artifact a named human
    must sign out-of-band, and says so.
  * DAVER_WORKSPACE is ONE boundary, applied everywhere. Cycle paths, resolver
    file reads and the signature trust anchor are all confined to it. An earlier
    version confined only the cycle path while the resolver layer read a second
    variable defaulting to the process cwd, so pinning the documented boundary
    bought nothing. It is now required: the server refuses to start rather than
    silently adopting whatever directory the MCP client happened to launch it in.
  * Paths resolve through realpath and symlinks are refused, so a link inside the
    workspace cannot read files outside it.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from daver import Spec, load_cycle, render, resolvers  # noqa: E402

_workspace_env = os.environ.get("DAVER_WORKSPACE")
if not _workspace_env:
    raise SystemExit(
        "dave-r MCP server refuses to start without an explicit DAVER_WORKSPACE. "
        "This is the one boundary confining cycle paths, resolver reads and the "
        "signature trust anchor; defaulting it to the process's working directory "
        "would make that boundary whatever directory the MCP client happened to "
        "launch from, which is not something this server's own security posture "
        "should depend on silently. Set DAVER_WORKSPACE to the directory containing "
        "the cycle documents this server should operate on.")
WORKSPACE = os.path.realpath(_workspace_env)

# Refuse to start with exec resolvers on. An operator may legitimately enable them
# for the CLI; over MCP the caller is a language model acting on content it
# discovered, and that is not a caller we hand subprocess to.
if resolvers.exec_enabled():
    raise SystemExit(
        "dave-r MCP server refuses to start with exec resolvers enabled. "
        f"Unset {resolvers.EXEC_ENV} for this process. Exec resolvers run commands "
        "declared in the repository under examination; that is not a capability an "
        "MCP tool surface should expose.")

# One boundary, applied to gates, resolvers and the trust anchor alike.
SPEC = Spec(os.environ.get("DAVER_SPEC"), evidence_root=WORKSPACE)
mcp = FastMCP("dave-r")


def _safe_path(p: str) -> str:
    """Resolve a caller-supplied path inside the workspace.

    realpath, not abspath: abspath normalises `..` but follows a symlink straight
    out of the root, and a cloned repository brings its symlinks with it.
    """
    full = os.path.realpath(os.path.join(WORKSPACE, p))
    if not (full == WORKSPACE or full.startswith(WORKSPACE + os.sep)):
        raise ValueError(f"path escapes workspace root: {p}")
    if not os.path.isfile(full):
        raise FileNotFoundError(f"no cycle document at {p}")
    return full


def _load(cycle_path: str) -> dict:
    return load_cycle(_safe_path(cycle_path))


# --- orientation -----------------------------------------------------------

@mcp.tool()
def daver_list_adapters() -> str:
    """List the DAVE+R modules (adapters) available and what each covers.

    The lifecycle and gates are constant; an adapter supplies the control planes,
    telemetry systems, signal vocabulary and minimum shadow duration for a domain.
    """
    out = []
    for a in SPEC.adapters.values():
        out.append({
            "id": a["id"],
            "name": a["name"],
            "purpose": a.get("purpose", "").strip(),
            "planes": a.get("planes", []),
            "min_shadow_days": a.get("min_shadow_days", {}),
            "extra_gates": [g["id"] for g in a.get("gates", [])],
        })
    return json.dumps(out, indent=2)


@mcp.tool()
def daver_discovery_plan(adapter: str) -> str:
    """What an agent should READ before asking a human anything, for this module.

    Discovery-first is the design: infer the answers from the project's own
    configuration, then ask the human only for what cannot be observed.
    """
    a = SPEC.adapter(adapter)
    d = a.get("discovery", {})
    return json.dumps({
        "adapter": a["id"],
        "read_these": d.get("sources", []),
        "agent_can_infer": d.get("infers", []),
        "must_ask_a_human": d.get("must_ask_human", []),
        "note": "Anything under must_ask_a_human is judgement, risk acceptance or "
                "business context. An agent must never author these on a human's behalf.",
    }, indent=2)


@mcp.tool()
def daver_human_questions(adapter: str) -> str:
    """The irreducible question set for a human, for this module.

    Everything else is discoverable. Keep this list short: a long form produces
    generic answers, which is the failure mode DAVE+R was designed against.
    """
    a = SPEC.adapter(adapter)
    base = [
        {"field": "definition_brief.asset.critical_flows",
         "ask": "Which flows must not break? Name them."},
        {"field": "definition_brief.guardrails.false_positive_tolerance",
         "ask": "What false positive rate on those flows is acceptable? A number, not zero."},
        {"field": "definition_brief.guardrails.latency_budget_ms",
         "ask": "How much added latency can you accept, at which percentile?"},
        {"field": "definition_brief.raci.accountable",
         "ask": "Who personally owns this risk? One name, not a team."},
        {"field": "definition_brief.triage.track",
         "ask": "Is damage happening right now? If yes, what does a day of not acting cost?"},
        {"field": "definition_brief.non_goals",
         "ask": "What is explicitly out of scope for this cycle?"},
    ]
    extra = [q for q in a.get("discovery", {}).get("must_ask_human", []) if isinstance(q, str) and " " in q]
    return json.dumps({"adapter": a["id"], "questions": base,
                       "module_specific": extra}, indent=2)


# --- the lifecycle ---------------------------------------------------------

@mcp.tool()
def daver_check(cycle_path: str, stage: str = "", cumulative: bool = True) -> str:
    """Run the DAVE+R gates against a cycle document and report pass/block.

    Cumulative by default: a Validate pass resting on a broken Define is not a pass.
    Returns the rendered report. Use daver_next_actions for an ordered worklist.
    """
    cycle = _load(cycle_path)
    rep = SPEC.run(cycle, stage=stage or None, cumulative=cumulative)
    return render(rep)


@mcp.tool()
def daver_check_json(cycle_path: str, stage: str = "", cumulative: bool = True) -> str:
    """Machine-readable form of daver_check, for chaining or CI."""
    rep = SPEC.run(_load(cycle_path), stage=stage or None, cumulative=cumulative)
    return json.dumps(rep.to_dict(), indent=2)


@mcp.tool()
def daver_next_actions(cycle_path: str, stage: str = "") -> str:
    """The ordered worklist to unblock this cycle: what is failing and how to fix it."""
    rep = SPEC.run(_load(cycle_path), stage=stage or None)
    if rep.can_advance:
        return json.dumps({
            "can_advance": True,
            "stage": rep.stage,
            "advisories": [{"id": r.id, "why": r.reason} for r in rep.advisories],
            "next": "All blocking gates pass. Advance the stage.",
        }, indent=2)
    return json.dumps({
        "can_advance": False,
        "stage": rep.stage,
        "blockers": [
            {"gate": r.id, "name": r.name, "stage": r.stage, "why": r.reason,
             "fix": r.remediation.strip(), "new_in_spec": r.added_in}
            for r in rep.blockers
        ],
    }, indent=2)


@mcp.tool()
def daver_explain_gate(gate_id: str) -> str:
    """Why a gate exists, what it checks, and how to satisfy it.

    Most gates carry the specific failure they were written to prevent.
    """
    for stage, gates in SPEC.gates.items():
        for g in gates:
            if g["id"].lower() == gate_id.lower():
                return json.dumps({"stage": stage, "source": "core", **g}, indent=2, default=str)
    for a in SPEC.adapters.values():
        for g in a.get("gates", []):
            if g["id"].lower() == gate_id.lower():
                return json.dumps({"adapter": a["id"], "source": a["id"], **g}, indent=2, default=str)
    known = [g["id"] for gs in SPEC.gates.values() for g in gs]
    return f"Unknown gate '{gate_id}'. Known core gates: {', '.join(known)}"


@mcp.tool()
def daver_validate_schema(cycle_path: str) -> str:
    """Validate a cycle document against the DAVE+R JSON Schemas (structure, not gates)."""
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:
        return "jsonschema and referencing are required for schema validation."

    sdir = os.path.join(SPEC.root, "schemas")
    registry = Registry()
    for fn in os.listdir(sdir):
        if fn.endswith(".json"):
            with open(os.path.join(sdir, fn)) as fh:
                registry = registry.with_resource(fn, Resource.from_contents(json.load(fh)))
    with open(os.path.join(sdir, "cycle.schema.json")) as fh:
        schema = json.load(fh)
    v = Draft202012Validator(schema, registry=registry)
    errs = sorted(v.iter_errors(_load(cycle_path)), key=lambda e: list(e.path))
    if not errs:
        return "Schema valid."
    return json.dumps([{"path": "/".join(str(p) for p in e.path), "error": e.message}
                       for e in errs[:40]], indent=2)


# --- standing hygiene ------------------------------------------------------

@mcp.tool()
def daver_sweep_exceptions(cycle_path: str) -> str:
    """Report exceptions that are expired, expiring soon, weakly bound, or unused.

    This is the check worth running on a schedule, unprompted. An exception register
    without an expiry sweep becomes the thing that documents permanent exceptions
    rather than the thing that prevents them.
    """
    cycle = _load(cycle_path)
    now = dt.datetime.now(dt.timezone.utc).date()
    weak = {"ip", "asn", "user-agent", "path"}
    rows = []
    for e in (cycle.get("exception_register") or {}).get("exceptions", []):
        exp = e.get("expiry")
        try:
            expd = dt.date.fromisoformat(str(exp)) if exp else None
        except ValueError:
            expd = None
        days = (expd - now).days if expd else None
        flags = []
        if e.get("status") in {"retired", "expired"}:
            flags.append("closed")
        else:
            if days is not None and days < 0:
                flags.append(f"EXPIRED {abs(days)}d ago")
            elif days is not None and days <= 30:
                flags.append(f"expires in {days}d")
            if not expd:
                flags.append("no expiry")
            if not e.get("expiry_action"):
                flags.append("no expiry action")
        if (e.get("mechanism") or {}).get("kind") in weak:
            flags.append(f"weak mechanism: {e['mechanism']['kind']}")
        cc = e.get("compensating_control") or {}
        if not cc.get("description") and not cc.get("none_because"):
            flags.append("no compensating control")
        br = (e.get("blast_radius") or {}).get("severity")
        if br in {"high", "critical"}:
            flags.append(f"blast radius {br}")
        usage = e.get("usage")
        if isinstance(usage, dict) and usage.get("value") == 0:
            flags.append("never used, candidate for removal")
        if flags:
            rows.append({"id": e.get("id"), "scope": e.get("scope"),
                         "expiry": exp, "flags": flags,
                         "approver": ((e.get("approver") or {}).get("by") or {}).get("name")})
    return json.dumps({"cycle": cycle.get("cycle_id"), "checked": now.isoformat(),
                       "findings": rows or "no exceptions need attention"}, indent=2)


@mcp.tool()
def daver_request_authorization(cycle_path: str) -> str:
    """Prepare the authorization request a named human must sign to enable enforcement.

    This tool deliberately CANNOT approve anything. It assembles the evidence and
    identifies the one person entitled to decide. Flipping enforcement is a
    risk-acceptance act reserved to that human, and no agent may write the
    signature on their behalf.
    """
    cycle = _load(cycle_path)
    rep = SPEC.run(cycle, stage="validate")
    brief = cycle.get("definition_brief", {})
    acct = (brief.get("raci") or {}).get("accountable") or {}
    vp = cycle.get("validation_plan") or {}

    def val(node):
        return node.get("value") if isinstance(node, dict) else node

    return json.dumps({
        "cycle_id": cycle.get("cycle_id"),
        "gates_currently_blocking": [r.id for r in rep.blockers],
        "ready_for_authorization": rep.can_advance,
        "must_be_signed_by": {"name": acct.get("name"), "identity": acct.get("identity")},
        "evidence_summary": {
            "baseline_fp_rate": val((vp.get("baseline") or {}).get("false_positive_rate")),
            "measured_fp_rate": val((vp.get("measured") or {}).get("false_positive_rate")),
            "declared_tolerance": val((brief.get("guardrails") or {}).get("false_positive_tolerance")),
            "latency_delta_ms": val((vp.get("measured") or {}).get("latency_delta_ms")),
            "rollback_tested": val((vp.get("measured") or {}).get("rollback_tested")),
            "shadow_days": val((vp.get("shadow") or {}).get("duration_days")),
            "evasion_bypasses_analysed": len((vp.get("evasion_analysis") or {}).get("bypasses") or []),
        },
        "agent_may_not": [
            "write execution.enforcement_authorization",
            "write validation_plan.go_no_go.signature",
            "approve or extend any exception",
            "widen a guardrail to fit a measured result",
        ],
        "instruction": "Present this to the accountable owner. They record the decision "
                       "out-of-band. The agent transcribes their answer; it never originates it.",
    }, indent=2)


@mcp.tool()
def daver_spec_info() -> str:
    """Spec version, gate inventory, and self-lint status."""
    core = {s: [g["id"] for g in gs] for s, gs in SPEC.gates.items()}
    return json.dumps({
        "spec_version": open(os.path.join(SPEC.root, "VERSION")).read().strip(),
        "spec_root": SPEC.root,
        "workspace": WORKSPACE,
        "exec_resolvers": "disabled (this server never enables them)",
        "registered_resolvers": resolvers.registered(),
        "core_gates": core,
        "core_gate_count": sum(len(v) for v in core.values()),
        "adapter_gates": {a["id"]: [g["id"] for g in a.get("gates", [])] for a in SPEC.adapters.values()},
        "lint": SPEC.lint() or "clean",
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
