"""An unmeasured value's `note` is not decoration; the engine only functions as
"transparent, not blocking" if the reason a gate reports actually carries the
note a human or agent wrote explaining the gap. These pin that behaviour so it
cannot regress silently - see ai/skills/dave-r/references/evidence.md for why
a guardrail (not just a measured quantity) legitimately ends up unmeasured.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from daver.expr import evaluate  # noqa: E402
from daver.model import Context  # noqa: E402


def _ctx(cycle):
    return Context(cycle=cycle, adapter={})


# --- exists ------------------------------------------------------------

def test_exists_surfaces_note_on_unmeasured_guardrail():
    cycle = {"definition_brief": {"guardrails": {
        "latency_budget_ms": {
            "provenance": "unmeasured",
            "note": "Owner could not commit to a number as of 2026-08-29.",
        },
    }}}
    r = evaluate({"exists": "definition_brief.guardrails.latency_budget_ms"}, _ctx(cycle))
    assert not r.ok
    assert "is explicitly unmeasured" in r.reason
    assert "Owner could not commit to a number as of 2026-08-29." in r.reason


def test_exists_unmeasured_without_note_is_unchanged():
    cycle = {"definition_brief": {"guardrails": {
        "latency_budget_ms": {"provenance": "unmeasured"},
    }}}
    r = evaluate({"exists": "definition_brief.guardrails.latency_budget_ms"}, _ctx(cycle))
    assert not r.ok
    assert r.reason == "definition_brief.guardrails.latency_budget_ms is explicitly unmeasured"


# --- comparison (the V-5 shape: a measured value against a guardrail) --

def test_lte_surfaces_note_when_guardrail_side_is_unmeasured():
    cycle = {
        "definition_brief": {"guardrails": {"latency_budget_ms": {
            "provenance": "unmeasured",
            "note": "Owner declined to set a number; proposed 150ms, no response yet.",
        }}},
        "validation_plan": {"measured": {"latency_delta_ms": {
            "value": 80, "provenance": "observed",
            "source": {"system": "x", "ref": "y"}, "observed_at": "2026-08-29T00:00:00Z",
        }}},
    }
    r = evaluate({"lte": ["validation_plan.measured.latency_delta_ms",
                          "definition_brief.guardrails.latency_budget_ms"]}, _ctx(cycle))
    assert not r.ok
    assert "proposed 150ms, no response yet." in r.reason


def test_lte_surfaces_note_when_measured_side_is_unmeasured():
    cycle = {
        "definition_brief": {"guardrails": {"latency_budget_ms": {
            "value": 150, "provenance": "asserted",
            "asserted_by": "d@example.com", "asserted_at": "2026-08-29T00:00:00Z",
        }}},
        "validation_plan": {"measured": {"latency_delta_ms": {
            "provenance": "unmeasured", "note": "No p95 instrumentation on this path yet.",
        }}},
    }
    r = evaluate({"lte": ["validation_plan.measured.latency_delta_ms",
                          "definition_brief.guardrails.latency_budget_ms"]}, _ctx(cycle))
    assert not r.ok
    assert "No p95 instrumentation on this path yet." in r.reason


# --- provenance_in (what V-1/V-3/V-5/V-6/R-1 actually assert) ----------

def test_provenance_in_surfaces_note_on_unmeasured():
    cycle = {"validation_plan": {"measured": {"false_positive_rate": {
        "provenance": "unmeasured", "note": "Shadow mode has not started yet.",
    }}}}
    r = evaluate({"provenance_in": ["validation_plan.measured.false_positive_rate",
                                    ["observed", "derived"]]}, _ctx(cycle))
    assert not r.ok
    assert "is unmeasured. The gate blocks rather than estimating." in r.reason
    assert "Shadow mode has not started yet." in r.reason


def test_provenance_in_unmeasured_without_note_is_unchanged():
    cycle = {"validation_plan": {"measured": {"false_positive_rate": {
        "provenance": "unmeasured",
    }}}}
    r = evaluate({"provenance_in": ["validation_plan.measured.false_positive_rate",
                                    ["observed", "derived"]]}, _ctx(cycle))
    assert not r.ok
    assert r.reason == ("validation_plan.measured.false_positive_rate is unmeasured. "
                         "The gate blocks rather than estimating.")


def test_note_on_a_non_unmeasured_value_is_not_echoed_into_unrelated_failures():
    """A note is not a general-purpose message field; it only surfaces on the
    unmeasured/missing path it documents. An asserted value's note (e.g. why a
    number was picked) must not bleed into an unrelated comparison failure."""
    cycle = {"definition_brief": {"guardrails": {
        "false_positive_tolerance": {
            "value": 0, "provenance": "asserted", "asserted_by": "d@example.com",
            "asserted_at": "2026-08-29T00:00:00Z", "note": "Unrelated note text.",
        },
    }}}
    r = evaluate({"gt": ["definition_brief.guardrails.false_positive_tolerance", 0]}, _ctx(cycle))
    assert not r.ok
    assert "Unrelated note text." not in r.reason
