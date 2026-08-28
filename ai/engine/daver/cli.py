"""daver command line. Same spec, same gates, no MCP client required."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import integrity, resolvers
from .gates import STAGES, Spec
from .model import load_cycle
from .report import render


def _spec(args) -> Spec:
    return Spec(getattr(args, "spec", None), profile=getattr(args, "profile", None) or "baseline")


def _dump(path: str, cycle: dict) -> None:
    import yaml
    with open(path, "w") as fh:
        yaml.safe_dump(cycle, fh, sort_keys=False, width=100, allow_unicode=True)


def cmd_check(args) -> int:
    rep = _spec(args).run(load_cycle(args.cycle), stage=args.stage, cumulative=not args.only)
    if args.json:
        print(json.dumps(rep.to_dict(), indent=2))
    else:
        print(render(rep, verbose=args.verbose))
    return 0 if rep.can_advance else 1


def cmd_gates(args) -> int:
    s = _spec(args)
    if args.gate:
        for stage, gs in s.gates.items():
            for g in gs:
                if g["id"].lower() == args.gate.lower():
                    print(json.dumps({"stage": stage, **g}, indent=2, default=str))
                    return 0
        for a in s.adapters.values():
            for g in a.get("gates", []):
                if g["id"].lower() == args.gate.lower():
                    print(json.dumps({"adapter": a["id"], **g}, indent=2, default=str))
                    return 0
        print(f"unknown gate {args.gate}", file=sys.stderr)
        return 2
    for stage in STAGES:
        print(f"\n{stage.upper()}")
        for g in s.gates[stage]:
            new = f"  [new in {g['added_in']}]" if g.get("added_in") else ""
            print(f"  {g['id']:6} {g['name']:42} {g.get('severity','blocking'):9}{new}")
    for a in s.adapters.values():
        if a.get("gates"):
            print(f"\n{a['id'].upper()} (adapter)")
            for g in a["gates"]:
                new = f"  [new in {g['added_in']}]" if g.get("added_in") else ""
                print(f"  {g['id']:6} {g['name']:42} {g.get('severity','blocking'):9}{new}")
    return 0


def cmd_adapters(args) -> int:
    s = _spec(args)
    for a in s.adapters.values():
        print(f"{a['id']:24} {a['name']}")
        print(f"{'':24} planes: {', '.join(a.get('planes', []))}")
        print(f"{'':24} min shadow days: {a.get('min_shadow_days', {})}")
        print(f"{'':24} extra gates: {len(a.get('gates', []))}")
        print()
    return 0


def cmd_questions(args) -> int:
    a = _spec(args).adapter(args.adapter)
    print(f"Ask a human these, for {a['id']}. Everything else, discover.\n")
    fixed = [
        "Which flows must not break? Name them.",
        "What false positive rate on those flows is acceptable? A number, not zero.",
        "How much added latency can you accept, and at which percentile?",
        "Who personally owns this risk? One name, not a team.",
        "Is damage happening right now? If yes, what does a day of not acting cost?",
        "What is explicitly out of scope for this cycle?",
    ]
    for i, q in enumerate(fixed, 1):
        print(f"  {i}. {q}")
    extra = [q for q in a.get("discovery", {}).get("must_ask_human", []) if " " in str(q)]
    for i, q in enumerate(extra, len(fixed) + 1):
        print(f"  {i}. {q}")
    print("\nRead these instead of asking:")
    for src in a.get("discovery", {}).get("sources", []):
        detail = src.get("globs") or src.get("calls") or src.get("system") or ""
        print(f"  - {src.get('kind')}: {detail}")
    return 0


def cmd_scaffold(args) -> int:
    s = _spec(args)
    a = s.adapter(args.adapter)
    skeleton = {
        "spec_version": "1.0.0",
        "cycle_id": args.cycle_id,
        "adapter": a["id"],
        "stage": "define",
        "definition_brief": {
            "name": args.cycle_id, "status": "draft",
            "asset": {"target": "TODO: exact host and path", "traffic_scope": "TODO",
                      "critical_flows": []},
            "threat_scenarios": [],
            "guardrails": {
                "false_positive_tolerance": {"provenance": "unmeasured"},
                "latency_budget_ms": {"provenance": "unmeasured"},
            },
            "success_metrics": [], "non_goals": [],
            "triage": {"track": "planned",
                       "justification": {"provenance": "unmeasured"},
                       "harm_accruing": {"provenance": "unmeasured"}},
            "alternatives_considered": [],
            # Deliberately a placeholder that D-0 rejects. An unedited scaffold must
            # never read as a cycle with a named accountable owner.
            "raci": {"accountable": {"name": "TODO: one named person",
                                     "identity": "TODO: their email or SSO subject"},
                     "responsible": []},
        },
        "audit": [],
    }
    import yaml
    text = yaml.safe_dump(skeleton, sort_keys=False, width=100)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"wrote {args.out}")
        print("Every TODO must be replaced before any gate can pass; gate D-0 rejects "
              "placeholders so a scaffold cannot be mistaken for a completed brief.")
    else:
        print(text)
    return 0


def cmd_lint(args) -> int:
    problems = _spec(args).lint()
    if problems:
        for p in problems:
            print(p)
        return 1
    print("spec lint clean")
    return 0


def cmd_verify(args) -> int:
    """Re-run every observed value's source and compare. Closes the evidence loop."""
    import os
    if args.evidence_root:
        os.environ["DAVER_EVIDENCE_ROOT"] = args.evidence_root
    r = resolvers.verify(load_cycle(args.cycle), tolerance=args.tolerance, strict=args.strict)
    if args.json:
        print(json.dumps(r, indent=2, default=str))
        return 0 if r["ok"] else 1
    c = r["counts"]
    verdict = "OK" if r["ok"] else "FAILED"
    if r["ok"] and c["skipped"] and not c["match"]:
        verdict = "INCONCLUSIVE"
    print(f"evidence verification: {verdict}")
    if verdict == "INCONCLUSIVE":
        print(f"  nothing was actually re-verified: {c['skipped']} value(s) use telemetry "
              f"systems with no registered resolver.")
        print("  register resolvers, or run --strict to treat this as a failure.")
    print(f"  match {c['match']}, drift {c['drift']}, unresolvable {c['unresolvable']}, "
          f"error {c['error']}, skipped {c['skipped']}")
    print(f"  resolvers registered: {', '.join(r['registered_resolvers'])}")
    for f in r["findings"]:
        print(f"\n  [{f['status']}] {f['path']}")
        print(f"      {f.get('detail','')}")
    return 0 if r["ok"] else 1


def cmd_chain(args) -> int:
    """Stamp the audit log with a hash chain so later edits are detectable."""
    cycle = load_cycle(args.cycle)
    integrity.chain_audit(cycle)
    _dump(args.cycle, cycle)
    r = integrity.verify_audit(cycle)
    print(f"chained {r.get('entries', 0)} audit entries, head {r.get('head','')[:16]}...")
    return 0


def cmd_audit(args) -> int:
    r = integrity.verify_audit(load_cycle(args.cycle))
    print(json.dumps(r, indent=2))
    return 0 if r["ok"] else 1


def cmd_sign_request(args) -> int:
    """Print what a human must sign. This command cannot sign anything."""
    r = integrity.sign_request(load_cycle(args.cycle), args.subject, args.key)
    print(f"cycle:    {r['cycle_id']}")
    print(f"subject:  {r['subject']}")
    print(f"signer:   {r['must_be_signed_by']}")
    print(f"digest:   {r['digest']}")
    print("\nThe accountable owner runs, on their own machine:\n")
    for line in r["how"]:
        print(f"  {line}")
    print(f"\n{r['note']}")
    return 0


def cmd_verify_signatures(args) -> int:
    import os
    if args.evidence_root:
        os.environ["DAVER_EVIDENCE_ROOT"] = args.evidence_root
    r = integrity.verify_all_signatures(load_cycle(args.cycle), args.allowed_signers)
    print(json.dumps(r, indent=2))
    return 0 if r["ok"] else 1


def cmd_sweep(args) -> int:
    """Portfolio-wide exception hygiene. The job worth running on a schedule."""
    import datetime as dt
    import glob as _glob
    now = dt.date.today()
    weak = {"ip", "asn", "user-agent", "path"}
    paths = sorted(_glob.glob(os.path.join(args.dir, "**", "*.cycle.yaml"), recursive=True)) \
        if os.path.isdir(args.dir) else [args.dir]
    rows, cycles = [], 0
    for p in paths:
        try:
            cycle = load_cycle(p)
        except Exception as e:
            rows.append({"cycle": os.path.basename(p), "id": "-", "flags": [f"unreadable: {e}"]})
            continue
        cycles += 1
        for e in (cycle.get("exception_register") or {}).get("exceptions", []):
            if e.get("status") in {"retired", "expired"} and not args.all:
                continue
            flags = []
            closed = e.get("status") in {"retired", "expired"}
            exp = e.get("expiry")
            try:
                d = dt.date.fromisoformat(str(exp)) if exp else None
            except ValueError:
                d = None
            if closed:
                flags.append(f"closed ({e.get('status')})")
            elif d is None:
                flags.append("no expiry")
            elif (d - now).days < 0:
                flags.append(f"OVERDUE {abs((d - now).days)}d past expiry, not retired")
            elif (d - now).days <= args.window:
                flags.append(f"expires in {(d - now).days}d")
            if not closed and not e.get("expiry_action"):
                flags.append("no expiry action")
            if (e.get("mechanism") or {}).get("kind") in weak:
                flags.append(f"weak mechanism: {e['mechanism']['kind']}")
            cc = e.get("compensating_control") or {}
            if not cc.get("description") and not cc.get("none_because"):
                flags.append("no compensating control")
            br = (e.get("blast_radius") or {}).get("severity")
            if br in {"high", "critical"}:
                flags.append(f"blast radius {br}")
            u = e.get("usage")
            if isinstance(u, dict) and u.get("value") == 0:
                flags.append("never used")
            if flags:
                rows.append({"cycle": cycle.get("cycle_id", os.path.basename(p)),
                             "id": e.get("id"), "scope": e.get("scope"), "flags": flags})
    if args.json:
        print(json.dumps({"cycles_scanned": cycles, "findings": rows}, indent=2))
    else:
        print(f"swept {cycles} cycle(s), {len(rows)} exception(s) need attention\n")
        for r in rows:
            print(f"  {r['cycle']} / {r['id']}: {r.get('scope','')}")
            for f in r["flags"]:
                print(f"      - {f}")
    return 1 if rows else 0


def cmd_profiles(args) -> int:
    import yaml as _y
    pdir = os.path.join(_spec(args).root, "profiles")
    for fn in sorted(os.listdir(pdir)):
        if fn.endswith(".yaml"):
            d = _y.safe_load(open(os.path.join(pdir, fn)))
            print(f"{d['id']:18} {d.get('name','')}")
            print(f"{'':18} {' '.join((d.get('description') or '').split())[:150]}")
            ov = d.get("severity_overrides") or {}
            if ov:
                print(f"{'':18} promotes: {', '.join(f'{k}->{v}' for k, v in ov.items())}")
            print()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="daver", description="DAVE+R lifecycle gates")
    ap.add_argument("--spec", help="path to spec/ (default: bundled, or $DAVER_SPEC)")
    ap.add_argument("--profile", default="baseline",
                    help="gate profile: baseline, agent-operated, regulated")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="run gates against a cycle document")
    c.add_argument("cycle")
    c.add_argument("--stage", choices=STAGES, help="default: the cycle's own stage")
    c.add_argument("--only", action="store_true", help="this stage only, not cumulative")
    c.add_argument("--json", action="store_true")
    c.add_argument("-v", "--verbose", action="store_true", help="also list passing gates")
    c.add_argument("--profile", help="baseline (default), agent-operated, regulated")
    c.set_defaults(func=cmd_check)

    g = sub.add_parser("gates", help="list gates, or explain one")
    g.add_argument("gate", nargs="?")
    g.set_defaults(func=cmd_gates)

    a = sub.add_parser("adapters", help="list modules")
    a.set_defaults(func=cmd_adapters)

    q = sub.add_parser("questions", help="the short human question set for a module")
    q.add_argument("adapter")
    q.set_defaults(func=cmd_questions)

    s = sub.add_parser("scaffold", help="create an empty cycle document")
    s.add_argument("adapter")
    s.add_argument("cycle_id")
    s.add_argument("-o", "--out")
    s.set_defaults(func=cmd_scaffold)

    ln = sub.add_parser("lint", help="check the spec against itself")
    ln.set_defaults(func=cmd_lint)

    v = sub.add_parser("verify", help="re-run every observed source and compare")
    v.add_argument("cycle")
    v.add_argument("--evidence-root", help="root for file/exec resolvers")
    v.add_argument("--tolerance", type=float, default=0.02)
    v.add_argument("--strict", action="store_true", help="unregistered systems fail rather than skip")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_verify)

    ch = sub.add_parser("chain", help="hash-chain the audit log (writes in place)")
    ch.add_argument("cycle")
    ch.set_defaults(func=cmd_chain)

    au = sub.add_parser("audit", help="verify the audit hash chain")
    au.add_argument("cycle")
    au.set_defaults(func=cmd_audit)

    sr = sub.add_parser("sign-request", help="print the digest a human must sign")
    sr.add_argument("cycle")
    sr.add_argument("--subject", default="go_no_go", choices=sorted(integrity.SIGNED_SUBJECTS))
    sr.add_argument("--key", default="~/.ssh/id_ed25519")
    sr.set_defaults(func=cmd_sign_request)

    vs = sub.add_parser("verify-signatures", help="verify detached human signatures")
    vs.add_argument("cycle")
    vs.add_argument("--allowed-signers")
    vs.add_argument("--evidence-root")
    vs.set_defaults(func=cmd_verify_signatures)

    sw = sub.add_parser("sweep", help="portfolio-wide exception hygiene")
    sw.add_argument("dir", nargs="?", default=".")
    sw.add_argument("--window", type=int, default=30, help="warn this many days before expiry")
    sw.add_argument("--all", action="store_true", help="include retired and expired")
    sw.add_argument("--json", action="store_true")
    sw.set_defaults(func=cmd_sweep)

    pf = sub.add_parser("profiles", help="list gate profiles")
    pf.set_defaults(func=cmd_profiles)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
