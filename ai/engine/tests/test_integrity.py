"""Tests for the controls that make agent compliance verifiable rather than promised."""
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from daver import Spec, integrity, load_cycle, resolvers  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
HAS_SSH = shutil.which("ssh-keygen") is not None


@pytest.fixture
def cycle():
    return load_cycle(os.path.join(FIX, "reference.cycle.yaml"))


# --- audit chain -----------------------------------------------------------

def test_chain_is_idempotent(cycle):
    a = integrity.chain_audit(cycle)["audit"][-1]["hash"]
    b = integrity.chain_audit(cycle)["audit"][-1]["hash"]
    assert a == b


def test_chain_detects_edit(cycle):
    integrity.chain_audit(cycle)
    assert integrity.verify_audit(cycle)["ok"]
    cycle["audit"][1]["detail"] = "tampered"
    r = integrity.verify_audit(cycle)
    assert not r["ok"] and r["broken_at"] == 1


def test_chain_detects_deletion(cycle):
    integrity.chain_audit(cycle)
    del cycle["audit"][1]
    assert not integrity.verify_audit(cycle)["ok"]


def test_chain_detects_reorder(cycle):
    integrity.chain_audit(cycle)
    cycle["audit"][1], cycle["audit"][2] = cycle["audit"][2], cycle["audit"][1]
    assert not integrity.verify_audit(cycle)["ok"]


def test_unchained_audit_is_not_ok(cycle):
    for e in cycle["audit"]:
        e.pop("hash", None)
        e.pop("prev", None)
    assert not integrity.verify_audit(cycle)["ok"]


# --- signature digest ------------------------------------------------------

def test_digest_is_stable_across_key_order(cycle):
    d1 = integrity.signature_digest(cycle, "go_no_go")
    cycle["definition_brief"] = dict(reversed(list(cycle["definition_brief"].items())))
    assert integrity.signature_digest(cycle, "go_no_go") == d1


def test_digest_covers_the_evidence_not_just_the_decision(cycle):
    """Signing 'approved' alone would let the evidence change afterwards while the
    approval still looked valid."""
    before = integrity.signature_digest(cycle, "go_no_go")
    cycle["validation_plan"]["measured"]["false_positive_rate"]["value"] = 0.05
    assert integrity.signature_digest(cycle, "go_no_go") != before


def test_digest_covers_the_guardrail(cycle):
    """Widening a tolerance after sign-off must invalidate the signature."""
    before = integrity.signature_digest(cycle, "go_no_go")
    cycle["definition_brief"]["guardrails"]["false_positive_tolerance"]["value"] = 0.5
    assert integrity.signature_digest(cycle, "go_no_go") != before


def test_unsigned_decision_is_reported_as_self_reported(cycle):
    r = integrity.verify_signature(cycle, "go_no_go")
    assert not r["ok"]
    assert "self-reported" in r["detail"]


# --- real signatures -------------------------------------------------------

@pytest.mark.skipif(not HAS_SSH, reason="ssh-keygen not available")
class TestDetachedSignatures:
    @staticmethod
    def _setup(tmp_path, cycle):
        d = tmp_path / ".daver"
        d.mkdir()
        for name, comment in (("owner", "j.okonkwo@acme.example"), ("rogue", "attacker@evil")):
            subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(tmp_path / name),
                            "-N", "", "-C", comment, "-q"], check=True)
        pub = (tmp_path / "owner.pub").read_text().split()
        (d / "allowed_signers").write_text(f"j.okonkwo@acme.example {pub[0]} {pub[1]}\n")
        os.environ["DAVER_EVIDENCE_ROOT"] = str(tmp_path)
        return str(d / "allowed_signers")

    @staticmethod
    def _sign(tmp_path, key, digest, tag):
        f = tmp_path / f"{tag}.txt"
        f.write_text(digest)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(tmp_path / key),
                        "-n", integrity.NAMESPACE, str(f)], check=True, capture_output=True)
        return (tmp_path / f"{tag}.txt.sig").read_text()

    def test_genuine_signature_verifies(self, tmp_path, cycle):
        allowed = self._setup(tmp_path, cycle)
        d = integrity.signature_digest(cycle, "go_no_go")
        cycle["validation_plan"]["go_no_go"]["signature"]["detached_signature"] = \
            self._sign(tmp_path, "owner", d, "a")
        assert integrity.verify_signature(cycle, "go_no_go", allowed)["ok"]

    def test_evidence_edited_after_signing_fails(self, tmp_path, cycle):
        allowed = self._setup(tmp_path, cycle)
        d = integrity.signature_digest(cycle, "go_no_go")
        cycle["validation_plan"]["go_no_go"]["signature"]["detached_signature"] = \
            self._sign(tmp_path, "owner", d, "a")
        cycle["validation_plan"]["measured"]["false_positive_rate"]["value"] = 0.05
        assert not integrity.verify_signature(cycle, "go_no_go", allowed)["ok"]

    def test_guardrail_widened_after_signing_fails(self, tmp_path, cycle):
        allowed = self._setup(tmp_path, cycle)
        d = integrity.signature_digest(cycle, "go_no_go")
        cycle["validation_plan"]["go_no_go"]["signature"]["detached_signature"] = \
            self._sign(tmp_path, "owner", d, "a")
        cycle["definition_brief"]["guardrails"]["false_positive_tolerance"]["value"] = 0.5
        assert not integrity.verify_signature(cycle, "go_no_go", allowed)["ok"]

    def test_unauthorized_key_fails(self, tmp_path, cycle):
        allowed = self._setup(tmp_path, cycle)
        d = integrity.signature_digest(cycle, "go_no_go")
        cycle["validation_plan"]["go_no_go"]["signature"]["detached_signature"] = \
            self._sign(tmp_path, "rogue", d, "b")
        assert not integrity.verify_signature(cycle, "go_no_go", allowed)["ok"]

    def test_agent_cannot_forge_by_writing_the_flag(self, tmp_path, cycle):
        """The whole point: an agent setting authored_by_agent:false proves nothing."""
        allowed = self._setup(tmp_path, cycle)
        cycle["validation_plan"]["go_no_go"]["signature"]["authored_by_agent"] = False
        assert not integrity.verify_signature(cycle, "go_no_go", allowed)["ok"]


# --- evidence resolvers ----------------------------------------------------

def test_file_resolver_matches(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({"fp": 0.0006}))
    os.environ["DAVER_EVIDENCE_ROOT"] = str(tmp_path)
    cycle = {"module": {"x": {"value": 0.0006, "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "file", "ref": "m.json#/fp"}}}}
    assert resolvers.verify(cycle, root=str(tmp_path))["ok"]


def test_file_resolver_detects_drift(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({"fp": 0.05}))
    os.environ["DAVER_EVIDENCE_ROOT"] = str(tmp_path)
    cycle = {"module": {"x": {"value": 0.0006, "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "file", "ref": "m.json#/fp"}}}}
    r = resolvers.verify(cycle, root=str(tmp_path))
    assert not r["ok"] and r["counts"]["drift"] == 1


def test_fabricated_source_is_caught(tmp_path):
    """An agent inventing a plausible source string must not look like a measurement."""
    os.environ["DAVER_EVIDENCE_ROOT"] = str(tmp_path)
    cycle = {"module": {"x": {"value": 0.0006, "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "file", "ref": "does-not-exist.json#/fp"}}}}
    r = resolvers.verify(cycle, root=str(tmp_path))
    assert not r["ok"]
    assert r["findings"][0]["status"] == "unresolvable"


def test_resolver_rejects_path_traversal(tmp_path):
    os.environ["DAVER_EVIDENCE_ROOT"] = str(tmp_path)
    cycle = {"module": {"x": {"value": "root:x:0:0", "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "file", "ref": "../../../etc/passwd"}}}}
    r = resolvers.verify(cycle, root=str(tmp_path))
    assert not r["ok"] and r["findings"][0]["status"] == "error"


def test_exec_resolver_refuses_shell_strings(tmp_path):
    """A cycle document is agent-written and may reflect discovered content. It names
    a resolver KEY; it must never be able to supply a command."""
    d = tmp_path / ".daver"
    d.mkdir()
    (d / "resolvers.json").write_text(json.dumps({"exec": {"bad": "echo pwned; rm -rf /"}}))
    os.environ["DAVER_EVIDENCE_ROOT"] = str(tmp_path)
    r = resolvers._exec_resolver({"system": "exec", "ref": "bad"}, str(tmp_path))
    assert r.status == "error" and "argv list" in r.detail


def test_exec_resolver_rejects_undeclared_key(tmp_path):
    d = tmp_path / ".daver"
    d.mkdir()
    (d / "resolvers.json").write_text(json.dumps({"exec": {}}))
    os.environ["DAVER_EVIDENCE_ROOT"] = str(tmp_path)
    r = resolvers._exec_resolver({"system": "exec", "ref": "whatever"}, str(tmp_path))
    assert r.status == "unresolvable"


def test_unknown_system_never_counts_as_verified():
    cycle = {"module": {"x": {"value": 1, "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "datadog", "ref": "q"}}}}
    assert resolvers.verify(cycle, strict=True)["ok"] is False


# --- profiles --------------------------------------------------------------

def test_baseline_lets_reference_cycle_advance():
    c = load_cycle(os.path.join(FIX, "reference.cycle.yaml"))
    assert Spec(profile="baseline").run(c, stage="refine").can_advance


def test_agent_operated_requires_signatures():
    c = load_cycle(os.path.join(FIX, "reference.cycle.yaml"))
    rep = Spec(profile="agent-operated").run(c, stage="refine")
    assert not rep.can_advance
    assert "X-2" in {r.id for r in rep.blockers}


def test_unimplemented_check_fails_closed():
    """A gate that reports safety it did not verify is worse than no gate."""
    s = Spec()
    from daver.model import Context
    g = {"id": "T-0", "name": "t", "severity": "blocking", "check": "no_such_check",
         "remediation": "n/a"}
    r = s._run_one(g, Context(cycle={}), "execute", "core")
    assert not r.passed and "not implemented" in r.reason


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        Spec(profile="does-not-exist")


# --- defects found by a live agent run (see ai/evals) ----------------------

def test_fresh_scaffold_cannot_look_complete():
    """A live agent run found that an unedited scaffold's raci.accountable.identity
    of 'TODO' satisfied D-5. A cycle claiming a named accountable human when there is
    none is the most dangerous false pass this system can produce."""
    from daver.checks import get
    scaffold = {"definition_brief": {
        "asset": {"target": "TODO: exact host and path"},
        "raci": {"accountable": {"name": "TODO: one named person",
                                 "identity": "TODO: their email or SSO subject"}}}}
    ok, reason = get("no_placeholder_values")(scaffold, {})
    assert not ok
    assert "accountable.identity" in reason


@pytest.mark.parametrize("bad", ["TODO", "tbd ", "FIXME", "[Name/Team]", "<your email>",
                                 "changeme", "n/a", "...", "---", "your team"])
def test_placeholder_shapes_are_caught(bad):
    from daver.checks import get
    cycle = {"definition_brief": {"raci": {"accountable": {"identity": bad}}}}
    assert not get("no_placeholder_values")(cycle, {})[0]


def test_example_is_deliberately_not_a_placeholder():
    """RFC 2606 reserves .example for documentation, and the reference cycle uses
    acme.example throughout. Flagging 'example' would fire constantly on legitimate
    values, and a gate that cries wolf gets switched off."""
    from daver.checks import get
    cycle = {"definition_brief": {"raci": {"accountable": {"identity": "j@acme.example"}}}}
    assert get("no_placeholder_values")(cycle, {})[0]


def test_real_values_are_not_flagged_as_placeholders():
    from daver.checks import get
    cycle = load_cycle(os.path.join(FIX, "reference.cycle.yaml"))
    ok, reason = get("no_placeholder_values")(cycle, {})
    assert ok, reason


# --- vacuous passes --------------------------------------------------------

def test_empty_collection_is_not_applicable_not_a_pass():
    """Also from the live run: gates iterating an empty list reported as passes,
    so an empty exception register read as 'exceptions are governed'."""
    from daver.expr import evaluate
    from daver.model import Context
    r = evaluate({"each": {"in": "exception_register.exceptions",
                           "satisfies": {"exists": "item.expiry"}}},
                 Context(cycle={"exception_register": {"exceptions": []}}))
    assert r.ok and r.vacuous


def test_unfired_precondition_is_not_applicable():
    from daver.expr import evaluate
    from daver.model import Context
    r = evaluate({"implies": [{"eq": ["module.x", 1]}, {"exists": "module.y"}]},
                 Context(cycle={"module": {"x": 2}}))
    assert r.ok and r.vacuous


def test_real_pass_is_not_marked_vacuous():
    from daver.expr import evaluate
    from daver.model import Context
    r = evaluate({"each": {"in": "exception_register.exceptions",
                           "satisfies": {"exists": "item.expiry"}}},
                 Context(cycle={"exception_register": {"exceptions": [{"expiry": "2027-01-01"}]}}))
    assert r.ok and not r.vacuous


def test_report_separates_passed_from_not_applicable():
    c = load_cycle(os.path.join(FIX, "reference.cycle.yaml"))
    rep = Spec().run(c, stage="refine")
    na = {r.id for r in rep.not_applicable}
    assert na, "reference cycle should have at least one n/a gate"
    assert not (na & {r.id for r in rep.passed}), "a gate cannot be both passed and n/a"
    assert rep.can_advance, "n/a gates must not block"


@pytest.mark.parametrize("ok_value", [
    "-----BEGIN SSH SIGNATURE-----\nU1NIU0lHAAAAAQ...\n-----END SSH SIGNATURE-----",
    "Nathalie Okonkwo",            # starts with "na"
    "na-prod-eu-west-1",           # starts with "na"
    "examples/signing/demo.sh",    # starts with "example"
    "j.okonkwo@acme.example",
    "Toll-free support line",      # starts with "to"
    "TBDex integration",           # starts with "tbd" but is a real word
])
def test_real_values_are_not_mistaken_for_placeholders(ok_value):
    """An early regex matched any string starting with a dash, which flagged every
    SSH signature block as an unfilled placeholder."""
    from daver.checks import get
    cycle = {"definition_brief": {"raci": {"accountable": {"identity": ok_value}}}}
    ok, reason = get("no_placeholder_values")(cycle, {})
    assert ok, reason


def test_signature_blocks_never_trip_the_placeholder_gate():
    from daver.checks import get
    cycle = {"validation_plan": {"go_no_go": {"signature": {
        "detached_signature": "-----BEGIN SSH SIGNATURE-----\nabc\n-----END SSH SIGNATURE-----"}}}}
    assert get("no_placeholder_values")(cycle, {})[0]
