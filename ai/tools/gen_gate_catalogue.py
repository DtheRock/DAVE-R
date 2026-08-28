#!/usr/bin/env python3
"""Generate the gate catalogue from the spec, so docs can never drift from gates."""
import os, sys, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from daver import Spec, STAGES

def wrap(t, indent="  "):
    t = " ".join((t or "").split())
    return textwrap.fill(t, 88, initial_indent=indent, subsequent_indent=indent) if t else ""

def emit(g, stage_label):
    new = f"  **(new in spec 1.0.0)**" if g.get("added_in") else ""
    sev = g.get("severity", "blocking")
    out = [f"### {g['id']} - {g['name']}", f"`{sev}` · {stage_label}{new}", ""]
    if g.get("rationale"):
        out += [wrap(g["rationale"], ""), ""]
    out += [f"**Fix:** {' '.join(g.get('remediation','').split())}", ""]
    return "\n".join(out)

def main():
    s = Spec()
    L = ["# Gate catalogue", "",
         "Generated from `spec/gates/` and `spec/adapters/`. Do not edit by hand.", "",
         f"{sum(len(v) for v in s.gates.values())} core gates across five stages, plus "
         f"{sum(len(a.get('gates',[])) for a in s.adapters.values())} adapter gates.", ""]
    for st in STAGES:
        L += [f"## {st.capitalize()}", ""]
        for g in s.gates[st]:
            L.append(emit(g, st))
    for a in s.adapters.values():
        if not a.get("gates"):
            continue
        L += [f"## Adapter: {a['name']}", ""]
        for g in a["gates"]:
            L.append(emit(g, a["id"]))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "skills", "dave-r", "references", "gates.md")
    with open(out, "w") as fh:
        fh.write("\n".join(L).rstrip() + "\n")
    print(f"wrote {os.path.normpath(out)}")

main()
