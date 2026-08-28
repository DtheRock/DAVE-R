"""Gate loading and execution."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml

from .checks import get as _check_get
from .expr import evaluate
from .model import Context

STAGES = ["define", "architect", "validate", "execute", "refine"]


def _spec_root(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("DAVER_SPEC")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "spec"))


@dataclass
class GateResult:
    id: str
    name: str
    stage: str
    severity: str
    passed: bool
    applicable: bool = True
    reason: str = ""
    remediation: str = ""
    rationale: str = ""
    added_in: str | None = None
    source: str = "core"

    @property
    def blocking(self) -> bool:
        return self.severity == "blocking" and not self.passed


@dataclass
class CycleReport:
    cycle_id: str
    adapter: str
    stage: str
    profile: str = "baseline"
    results: list[GateResult] = field(default_factory=list)

    @property
    def blockers(self) -> list[GateResult]:
        return [r for r in self.results if r.blocking]

    @property
    def advisories(self) -> list[GateResult]:
        return [r for r in self.results if r.severity == "advisory" and not r.passed]

    @property
    def passed(self) -> list[GateResult]:
        return [r for r in self.results if r.passed and r.applicable]

    @property
    def not_applicable(self) -> list[GateResult]:
        """Held only because there was nothing to check. Not evidence of safety."""
        return [r for r in self.results if r.passed and not r.applicable]

    @property
    def can_advance(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "adapter": self.adapter,
            "stage": self.stage,
            "profile": self.profile,
            "can_advance": self.can_advance,
            "counts": {
                "passed": len(self.passed),
                "not_applicable": len(self.not_applicable),
                "blocking": len(self.blockers),
                "advisory": len(self.advisories),
                "total": len(self.results),
            },
            "results": [
                {
                    "id": r.id, "name": r.name, "stage": r.stage, "severity": r.severity,
                    "passed": r.passed, "applicable": r.applicable,
                    "reason": r.reason, "remediation": r.remediation,
                    "added_in": r.added_in, "source": r.source,
                }
                for r in self.results
            ],
        }


class Spec:
    def __init__(self, root: str | None = None, profile: str = "baseline",
                 evidence_root: str | None = None):
        self.root = _spec_root(root)
        # Containment for anything that touches the filesystem on behalf of a
        # gate. Passed down so a caller's boundary bounds the resolver layer too.
        self.root_for_evidence = evidence_root
        self.gates: dict[str, list[dict]] = {}
        gdir = os.path.join(self.root, "gates")
        for stage in STAGES:
            with open(os.path.join(gdir, f"{stage}.yaml")) as fh:
                self.gates[stage] = yaml.safe_load(fh)["gates"]
        # Extra gate files (e.g. integrity.yaml) attach to the stage they declare.
        for fn in sorted(os.listdir(gdir)):
            if not fn.endswith((".yaml", ".yml")) or fn[:-5] in STAGES:
                continue
            with open(os.path.join(gdir, fn)) as fh:
                doc = yaml.safe_load(fh)
            self.gates.setdefault(doc.get("stage", "execute"), []).extend(doc.get("gates", []))
        self.profile = self._load_profile(profile)
        self.adapters: dict[str, dict] = {}
        adir = os.path.join(self.root, "adapters")
        for fn in sorted(os.listdir(adir)):
            if fn.endswith((".yaml", ".yml")):
                with open(os.path.join(adir, fn)) as fh:
                    a = yaml.safe_load(fh)
                    self.adapters[a["id"]] = a

    def _load_profile(self, name: str) -> dict:
        pdir = os.path.join(self.root, "profiles")
        path = os.path.join(pdir, f"{name}.yaml")
        if not os.path.isfile(path):
            avail = [f[:-5] for f in os.listdir(pdir)] if os.path.isdir(pdir) else []
            raise KeyError(f"unknown profile '{name}'. Known: {sorted(avail)}")
        with open(path) as fh:
            return yaml.safe_load(fh) or {}

    def severity_for(self, g: dict) -> str:
        overrides = self.profile.get("severity_overrides") or {}
        return overrides.get(g["id"], g.get("severity", "blocking"))

    def adapter(self, aid: str) -> dict:
        if aid not in self.adapters:
            raise KeyError(f"unknown adapter '{aid}'. Known: {sorted(self.adapters)}")
        return self.adapters[aid]

    # -- execution ----------------------------------------------------------

    def _run_one(self, g: dict, ctx: Context, stage: str, source: str) -> GateResult:
        try:
            applicable = True
            if "check" in g:
                fn = _check_get(g["check"])
                if fn is None:
                    # An unimplemented check must FAIL, never silently skip: a gate
                    # that reports safety it did not verify is worse than no gate.
                    passed, reason = False, f"check '{g['check']}' is not implemented by this executor"
                else:
                    opts = dict(self.profile.get("options") or {})
                    opts.setdefault("root", self.root_for_evidence)
                    outcome = fn(ctx.cycle, opts)
                    if len(outcome) == 3:
                        passed, reason, applicable = outcome
                    else:
                        passed, reason = outcome
            else:
                r = evaluate(g["assert"], ctx)
                passed, reason = bool(r), r.reason
                # A gate that held only because there was nothing to check is not
                # evidence of safety. Reporting it as a pass overstates the result.
                applicable = not r.vacuous
                if r.vacuous and not reason:
                    reason = "nothing to check: the data this gate inspects is absent or empty"
        except Exception as e:  # a malformed gate must never look like a pass
            passed, reason, applicable = False, f"gate evaluation error: {e}", True
        return GateResult(
            id=g["id"], name=g["name"], stage=stage, applicable=applicable,
            severity=self.severity_for(g), passed=passed, reason=reason,
            remediation=g.get("remediation", ""), rationale=g.get("rationale", ""),
            added_in=g.get("added_in"), source=source,
        )

    def run(self, cycle: dict, stage: str | None = None, cumulative: bool = True) -> CycleReport:
        """Run gates for a stage. Cumulative runs every stage up to and including it,
        because a Validate pass that rests on a broken Define is not a pass."""
        adapter = self.adapter(cycle.get("adapter", ""))
        target = stage or cycle.get("stage", "define")
        if target == "closed":
            target = "refine"
        idx = STAGES.index(target)
        stages = STAGES[: idx + 1] if cumulative else [target]

        ctx = Context(cycle=cycle, adapter=adapter)
        report = CycleReport(cycle.get("cycle_id", "?"), adapter["id"], target,
                             profile=self.profile.get("id", "baseline"))

        for st in stages:
            for g in self.gates[st]:
                report.results.append(self._run_one(g, ctx, st, "core"))
            for g in adapter.get("gates", []):
                if self._adapter_gate_stage(g) == st:
                    report.results.append(self._run_one(g, ctx, st, adapter["id"]))
        return report

    @staticmethod
    def _adapter_gate_stage(g: dict) -> str:
        """Adapter gates declare a stage, or infer it from the artifacts they read."""
        if "stage" in g:
            return g["stage"]
        blob = yaml.safe_dump(g.get("assert", {}))
        for artifact, stage in (
            ("execution.", "execute"),
            ("refinement_log.", "refine"),
            ("validation_plan.", "validate"),
            ("exception_register.", "validate"),
            ("control_matrix.", "architect"),
            ("audit", "execute"),
        ):
            if artifact in blob:
                return stage
        return "define"

    # -- self-check ---------------------------------------------------------

    def lint(self) -> list[str]:
        """The spec checks itself: a gate claiming to require evidence must actually
        assert provenance, or the guarantee is decorative."""
        problems, seen = [], set()
        allg = [(s, g, "core") for s in STAGES for g in self.gates[s]]
        allg += [(self._adapter_gate_stage(g), g, a["id"]) for a in self.adapters.values() for g in a.get("gates", [])]
        for stage, g, src in allg:
            gid = g["id"]
            if gid in seen:
                problems.append(f"{gid}: duplicate gate id")
            seen.add(gid)
            for k in ("name", "severity", "remediation"):
                if k not in g:
                    problems.append(f"{gid}: missing '{k}'")
            if "assert" not in g and "check" not in g:
                problems.append(f"{gid}: has neither 'assert' nor 'check'")
            if "check" in g and _check_get(g["check"]) is None:
                problems.append(f"{gid}: names unimplemented check '{g['check']}'")
            if g.get("severity") not in {"blocking", "advisory"}:
                problems.append(f"{gid}: severity must be blocking or advisory")
            if g.get("requires_evidence") and "provenance_in" not in yaml.safe_dump(g.get("assert", {})):
                problems.append(f"{gid}: declares requires_evidence but never asserts provenance_in")
            if "assert" in g:
                for bad in self._unresolvable_refs(g):
                    problems.append(
                        f"{gid}: reference '{bad}' has no known root. A misspelled root "
                        f"silently becomes a string literal at runtime, so the gate "
                        f"passes without checking anything.")
        return problems

    # Every artifact root a reference may legitimately start from.
    _KNOWN_ROOTS = frozenset({
        "definition_brief", "control_matrix", "validation_plan", "exception_register",
        "refinement_log", "execution", "module", "audit", "adapter",
        "spec_version", "cycle_id", "stage",
        "item", "outer",          # loop bindings
    })

    def _unresolvable_refs(self, g: dict) -> list[str]:
        """Dry-run a gate's references against the known artifact roots.

        Converts a silent runtime pass into a build-time error, and gives
        third-party adapter authors a real conformance check: adapters are the
        declared extension point and get no other review.
        """
        bad, seen = [], set()

        def walk(node):
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
            elif isinstance(node, str):
                check(node)

        def check(ref: str):
            if not ref or ref in seen:
                return
            seen.add(ref)
            if ref.startswith("$") or "." not in ref or " " in ref:
                return                       # special ref, enum value, regex or prose
            head = ref.split(".", 1)[0].split("[", 1)[0]
            if not head or not head.replace("_", "").isalnum():
                return
            if head.islower() and head not in self._KNOWN_ROOTS:
                bad.append(ref)

        walk(g.get("assert"))
        return bad
