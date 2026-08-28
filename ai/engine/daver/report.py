"""Human-readable rendering of a gate run."""
from __future__ import annotations

from .gates import CycleReport

TICK, CROSS, WARN = "PASS", "BLOCK", "WARN"


def render(rep: CycleReport, verbose: bool = False) -> str:
    out = []
    head = f"DAVE+R cycle {rep.cycle_id}  |  adapter {rep.adapter}  |  stage {rep.stage}"
    out.append(head)
    out.append("=" * len(head))
    c = rep.to_dict()["counts"]
    verdict = "CAN ADVANCE" if rep.can_advance else f"BLOCKED ({len(rep.blockers)} gate(s))"
    out.append(f"{verdict}   passed {c['passed']}/{c['total']}, blocking {c['blocking']}, "
               f"advisory {c['advisory']}, n/a {c['not_applicable']}")
    out.append("")
    if rep.not_applicable:
        out.append("NOT APPLICABLE (held only because there was nothing to check, "
                   "not evidence of safety)")
        out.append("-" * 14)
        out.append("  " + ", ".join(r.id for r in rep.not_applicable))
        out.append("")

    if rep.blockers:
        out.append("BLOCKING")
        out.append("-" * 8)
        for r in rep.blockers:
            tag = f" [new in spec {r.added_in}]" if r.added_in else ""
            src = "" if r.source == "core" else f" ({r.source})"
            out.append(f"{CROSS} {r.id} {r.name}{src}{tag}")
            out.append(f"      why: {r.reason}")
            out.append(f"      fix: {r.remediation.strip()}")
            out.append("")

    if rep.advisories:
        out.append("ADVISORY")
        out.append("-" * 8)
        for r in rep.advisories:
            out.append(f"{WARN} {r.id} {r.name}")
            out.append(f"      why: {r.reason}")
            out.append("")

    if verbose:
        out.append("PASSED")
        out.append("-" * 6)
        for r in rep.passed:
            out.append(f"{TICK} {r.id} {r.name}")
    return "\n".join(out)
