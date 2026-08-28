"""Regression suite.

The two fixtures are faithful encodings of the published DAVE+R scenarios. They are
the sharpest available test of the gate set: if the machine layer adds real rigor,
it must find, unprompted, the same gaps a careful human reviewer finds by hand.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from daver import Spec, load_cycle  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="module")
def spec():
    return Spec()


def _report(spec, name, stage="execute"):
    return spec.run(load_cycle(os.path.join(FIX, f"{name}.cycle.yaml")), stage=stage)


def _blocked(rep):
    return {r.id for r in rep.blockers}


# --- spec integrity --------------------------------------------------------

def test_spec_lints_clean(spec):
    assert spec.lint() == []


def test_every_gate_has_rationale_or_remediation(spec):
    for stage, gates in spec.gates.items():
        for g in gates:
            assert g.get("remediation"), f"{g['id']} has no remediation"


def test_all_four_modules_present(spec):
    assert set(spec.adapters) == {
        "a-edge-waf", "b-cloud-posture", "c-bot-fraud", "d-governance-delivery",
    }


# --- scenario 1: AI scrapers on a pricing API ------------------------------

def test_s1_blocks_overall(spec):
    assert not _report(spec, "scenario1").can_advance


@pytest.mark.parametrize("gate,because", [
    ("D-3", "0% false positive tolerance is not achievable for a statistical control"),
    ("D-6", "harm was accruing during a 5-day shadow with no signed acceptance"),
    ("D-7", "caching, per-key quota and requiring auth were never considered"),
    ("A-4", "no degraded posture for the rollback window"),
    ("V-1", "no pre-change baseline was ever measured"),
    ("V-7", "no evasion analysis; scrapers evaded at 290 under a 300 limit"),
    ("V-9", "BetaCorp exception has no compensating control or blast radius"),
    ("V-10", "IP-based bypass with no justification"),
    ("V-11", "no signed go/no-go from the accountable owner"),
    ("A-A1", "the one critical flow was never individually tested"),
])
def test_s1_catches_known_gap(spec, gate, because):
    assert gate in _blocked(_report(spec, "scenario1")), because


def test_s1_evidence_typing_rejects_asserted_rollback(spec):
    r = next(x for x in _report(spec, "scenario1").results if x.id == "V-6")
    assert not r.passed
    assert "asserted" in r.reason and "observed" in r.reason


def test_s1_credits_what_the_scenario_did_well(spec):
    """The scenario genuinely did several things right. A gate set that fails
    everything is useless as a signal."""
    passed = {r.id for r in _report(spec, "scenario1").results if r.passed}
    assert "D-1" in passed          # scope was concrete
    assert "D-2" in passed          # threat had an observable signature
    assert "A-2" in passed          # control traced to a declared threat
    assert "A-1" in passed          # control had owner, telemetry, rollback
    # R-1 lives in the Refine stage, so it is only exercised in a refine-stage run.
    refine_passed = {r.id for r in _report(spec, "scenario1", stage="refine").results if r.passed}
    assert "R-1" in refine_passed   # both refinements cited observed evidence


# --- scenario 2: credential stuffing on login ------------------------------

def test_s2_blocks_overall(spec):
    assert not _report(spec, "scenario2").can_advance


@pytest.mark.parametrize("gate,because", [
    ("C-C1", "posterior updating described without ever stating the prior"),
    ("C-C2", "correlated bot signals treated as independent evidence"),
    ("C-C3", "'calibrate' used repeatedly, never defined or measured"),
    ("C-C4", "score bands 50/90 picked, not derived from the distribution"),
    ("C-C5", "no appeal path for wrongly blocked users"),
    ("C-C6", "no holdout; the model trains on outcomes it gated"),
])
def test_s2_catches_bayesian_gap(spec, gate, because):
    assert gate in _blocked(_report(spec, "scenario2")), because


def test_s2_asn_bypass_flagged(spec):
    r = next(x for x in _report(spec, "scenario2").results if x.id == "V-10")
    assert not r.passed, "an ASN can hold thousands of unrelated hosts"


def test_s2_measured_fp_rate_passes(spec):
    """0.04% observed against a 0.1% budget. The scenario did measure this one,
    from a named source, so the gate must pass."""
    r = next(x for x in _report(spec, "scenario2").results if x.id == "V-3")
    assert r.passed


# --- engine semantics ------------------------------------------------------

def test_cumulative_run_includes_earlier_stages(spec):
    rep = _report(spec, "scenario1", stage="execute")
    assert {r.stage for r in rep.results} >= {"define", "architect", "validate", "execute"}


def test_single_stage_run_is_narrower(spec):
    rep = spec.run(load_cycle(os.path.join(FIX, "scenario1.cycle.yaml")),
                   stage="define", cumulative=False)
    assert {r.stage for r in rep.results} == {"define"}


def test_unknown_adapter_raises(spec):
    with pytest.raises(KeyError):
        spec.run({"adapter": "nope", "stage": "define"})


def test_malformed_gate_never_passes(spec):
    from daver.expr import evaluate
    from daver.model import Context
    assert not evaluate({"bogus_op": [1, 2]}, Context(cycle={}))
    assert not evaluate({"all": [{"nope": 1}]}, Context(cycle={}))


def test_derived_from_asserted_is_rejected(spec):
    """Evidence laundering: a derived value rooted in an assertion must not pass
    a gate that requires observation."""
    from daver.expr import evaluate
    from daver.model import Context
    cycle = {
        "module": {
            "guess": {"value": 0.5, "provenance": "asserted", "asserted_by": "someone"},
            "rate": {"value": 0.5, "provenance": "derived",
                     "derived_from": ["module.guess"], "method": "passthrough"},
        }
    }
    r = evaluate({"provenance_in": ["module.rate", ["observed", "derived"]]}, Context(cycle=cycle))
    assert not r
    assert "laundering" in r.reason


# --- reference cycle: the gate set must be satisfiable ---------------------

def test_reference_cycle_passes_every_blocking_gate(spec):
    """A gate set nothing can pass is useless. The reference cycle is the proof
    that a real, complete DAVE+R run clears all 42 blocking gates."""
    rep = _report(spec, "reference", stage="refine")
    assert rep.can_advance, [f"{r.id}: {r.reason}" for r in rep.blockers]


def test_reference_cycle_still_raises_an_honest_advisory(spec):
    """It is not a fantasy. The rate limit still leaks 97% of attacker throughput
    just under the threshold, and V-8 says so. Advisories are signal, not noise."""
    rep = _report(spec, "reference", stage="refine")
    assert "V-8" in {r.id for r in rep.advisories}


def test_reference_cycle_signatures_are_human(spec):
    cycle = load_cycle(os.path.join(FIX, "reference.cycle.yaml"))
    for path in (
        cycle["validation_plan"]["go_no_go"]["signature"],
        cycle["execution"]["enforcement_authorization"],
        cycle["exception_register"]["exceptions"][0]["approver"],
    ):
        assert path["authored_by_agent"] is False
        assert "@" in path["by"]["identity"]


def test_every_stage_of_reference_cycle_is_clean(spec):
    for stage in ("define", "architect", "validate", "execute", "refine"):
        rep = _report(spec, "reference", stage=stage)
        assert rep.can_advance, f"{stage}: {[r.id for r in rep.blockers]}"
