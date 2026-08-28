"""Regression tests for the v1.1.0 adversarial review.

One test per finding, each written to fail on the original code. The threat model
these encode: the tool is installed by people who point it at repositories they
did not write, so the document under examination and anything travelling beside it
are attacker-controlled.
"""
import copy
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from daver import Spec, integrity, load_cycle, resolvers  # noqa: E402
from daver.expr import MAX_MATCH_SUBJECT, evaluate  # noqa: E402
from daver.model import Context  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
HAS_SSH = shutil.which("ssh-keygen") is not None


@pytest.fixture
def ref_cycle():
    return load_cycle(os.path.join(FIX, "reference.cycle.yaml"))


# --- F-2: no code execution in a default install ---------------------------

def test_exec_resolver_not_registered_by_default():
    """The single most important property. Anything that must be configured to be
    safe is unsafe in practice."""
    assert "exec" not in resolvers.registered()
    assert not resolvers.exec_enabled()


def test_argv_list_starting_with_a_shell_is_refused():
    """An argv list whose first element is a shell is still a shell."""
    for argv in (["/bin/sh", "-c", "id"], ["bash", "-c", "id"], ["/usr/bin/python3", "-c", "1"],
                 ["node", "-e", "1"], ["env", "id"], ["perl", "-e", "1"]):
        assert resolvers._reject_argv(argv), f"{argv} should be refused"


def test_inline_code_flags_refused_even_for_allowed_binaries():
    assert resolvers._reject_argv(["/opt/telemetry/fetch", "-c", "whatever"])


def test_a_real_telemetry_binary_is_allowed():
    assert resolvers._reject_argv(["/opt/telemetry/fetch", "--metric", "fp_rate"]) is None


def test_shell_string_still_refused():
    assert resolvers._reject_argv("echo pwned; rm -rf /")


def test_exec_config_in_audited_tree_does_not_run_by_default(tmp_path):
    """End-to-end: the exact shape a hostile pull request would carry."""
    (tmp_path / ".daver").mkdir()
    probe = tmp_path / "probe.txt"
    (tmp_path / ".daver" / "resolvers.json").write_text(json.dumps(
        {"exec": {"pwn": ["/bin/sh", "-c", f"touch {probe}; echo 0.99"]}}))
    cycle = {"module": {"v": {"value": 0.99, "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "exec", "ref": "pwn"}}}}
    r = resolvers.verify(cycle, root=str(tmp_path))
    assert not probe.exists(), "running the gates executed code from the audited tree"
    assert r["counts"]["match"] == 0


# --- F-11: one boundary, and it is the caller's ----------------------------

def test_resolver_root_comes_from_the_caller_not_a_second_env_var(tmp_path, monkeypatch):
    """DAVER_WORKSPACE must bound the layer that does the work, or it is decoration."""
    safe = tmp_path / "safe"; safe.mkdir()
    hostile = tmp_path / "hostile"; (hostile / ".daver").mkdir(parents=True)
    (hostile / "secret.json").write_text('{"fp": 0.5}')
    monkeypatch.setenv("DAVER_EVIDENCE_ROOT", str(hostile))
    cycle = {"module": {"v": {"value": 0.5, "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "file", "ref": "secret.json#/fp"}}}}
    r = resolvers.verify(cycle, root=str(safe))
    assert r["root"] == os.path.realpath(str(safe))
    assert r["counts"]["match"] == 0, "caller root was ignored in favour of the env var"


# --- F-7: symlinks -------------------------------------------------------

def test_symlink_inside_the_root_is_refused(tmp_path):
    root = tmp_path / "ev"; root.mkdir()
    outside = tmp_path / "outside.txt"; outside.write_text("secret")
    os.symlink(outside, root / "leak.txt")
    res = resolvers._file_resolver({"system": "file", "ref": "leak.txt"}, str(root))
    assert res.status != "match", "a symlink walked out of the evidence root"


@pytest.mark.parametrize("ref", ["/etc/hostname", "../../../etc/hostname"])
def test_traversal_still_refused(tmp_path, ref):
    root = tmp_path / "ev"; root.mkdir()
    assert resolvers._file_resolver({"system": "file", "ref": ref}, str(root)).status == "error"


# --- F-3: derivation is a graph, not one hop -------------------------------

@pytest.mark.parametrize("hops", [1, 2, 3, 6])
def test_laundering_blocked_at_any_depth(hops):
    module = {"root": {"value": 1, "provenance": "asserted", "asserted_by": "x"}}
    prev = "module.root"
    for i in range(hops):
        name = f"h{i}"
        module[name] = {"value": 1, "provenance": "derived", "derived_from": [prev], "method": "p"}
        prev = f"module.{name}"
    r = evaluate({"provenance_in": [prev, ["observed", "derived"]]}, Context(cycle={"module": module}))
    assert not r.ok, f"{hops}-hop derivation laundered an assertion"


def test_unresolvable_parent_fails():
    cycle = {"module": {"d": {"value": 1, "provenance": "derived",
                              "derived_from": ["totally.made.up"], "method": "p"}}}
    assert not evaluate({"provenance_in": ["module.d", ["observed", "derived"]]}, Context(cycle=cycle))


def test_circular_derivation_terminates():
    cycle = {"module": {
        "a": {"value": 1, "provenance": "derived", "derived_from": ["module.b"], "method": "p"},
        "b": {"value": 1, "provenance": "derived", "derived_from": ["module.a"], "method": "p"}}}
    r = evaluate({"provenance_in": ["module.a", ["observed", "derived"]]}, Context(cycle=cycle))
    assert not r.ok and "circular" in r.reason


def test_legitimate_derivation_still_passes():
    cycle = {"module": {
        "o": {"value": 1, "provenance": "observed", "observed_at": "2026-01-01T00:00:00Z",
              "source": {"system": "file", "ref": "x"}},
        "d": {"value": 2, "provenance": "derived", "derived_from": ["module.o"], "method": "x2"}}}
    assert evaluate({"provenance_in": ["module.d", ["observed", "derived"]]}, Context(cycle=cycle))


# --- F-5: a misspelled root must not become a passing gate -----------------

def test_lint_catches_unresolvable_reference():
    s = Spec()
    assert s._unresolvable_refs({"assert": {"exists": "validatoin_plan.x"}})
    assert not s._unresolvable_refs({"assert": {"exists": "validation_plan.x"}})


def test_shipped_spec_has_no_unresolvable_references():
    assert Spec().lint() == []


# --- F-4: a check gate must be able to say "nothing to check" --------------

def test_x3_reports_not_applicable_when_it_verified_nothing():
    cycle = {"spec_version": "1.0.0", "cycle_id": "x", "adapter": "a-edge-waf", "stage": "execute",
             "module": {"m": {"value": 1, "provenance": "observed",
                              "observed_at": "2026-01-01T00:00:00Z",
                              "source": {"system": "datadog", "ref": "q"}}}, "audit": []}
    x3 = next(g for g in Spec(profile="baseline").run(cycle, stage="execute").results if g.id == "X-3")
    assert x3.passed and not x3.applicable, "X-3 reported a pass having verified nothing"
    assert "nothing was re-verified" in x3.reason


def _cycle_with_source(system, ref):
    return {"spec_version": "1.0.0", "cycle_id": "x", "adapter": "a-edge-waf", "stage": "execute",
            "module": {"m": {"value": 1, "provenance": "observed",
                             "observed_at": "2026-01-01T00:00:00Z",
                             "source": {"system": system, "ref": ref}}}, "audit": []}


def _x3(profile, cycle, root=None):
    return next(g for g in Spec(profile=profile, evidence_root=root).run(cycle, stage="execute").results
                if g.id == "X-3")


def test_agent_operated_blocks_a_fabricated_source(tmp_path):
    """A resolver RAN and the source does not exist. That is the fabrication case
    the gate exists for, and it blocks."""
    x3 = _x3("agent-operated", _cycle_with_source("file", "does-not-exist.json"), str(tmp_path))
    assert not x3.passed


def test_agent_operated_does_not_demand_a_telemetry_backend(tmp_path):
    """An unwired telemetry system is an operator gap, not a lie. Blocking on it
    would make the profile unusable until the team stands up a logging backend,
    which punishes the wrong party: you cannot detect a fabricated source for a
    system you have no way to reach."""
    x3 = _x3("agent-operated", _cycle_with_source("datadog", "sum:x"), str(tmp_path))
    assert x3.passed and not x3.applicable, "unwired system must report n/a, not block"
    assert "no registered resolver" in x3.reason


def test_regulated_does_demand_one(tmp_path):
    x3 = _x3("regulated", _cycle_with_source("datadog", "sum:x"), str(tmp_path))
    assert not x3.passed, "regulated requires every observed value to be re-runnable"


def test_a_verifiable_source_passes_cleanly(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({"fp": 1}))
    x3 = _x3("agent-operated", _cycle_with_source("file", "m.json#/fp"), str(tmp_path))
    assert x3.passed and x3.applicable and not x3.reason


def test_partial_verification_is_reported_not_hidden(tmp_path):
    """Some values checked, some unwired. The reason must say so rather than
    reporting a clean pass."""
    (tmp_path / "m.json").write_text(json.dumps({"fp": 1}))
    cycle = _cycle_with_source("file", "m.json#/fp")
    cycle["module"]["n"] = {"value": 2, "provenance": "observed",
                            "observed_at": "2026-01-01T00:00:00Z",
                            "source": {"system": "datadog", "ref": "sum:x"}}
    x3 = _x3("agent-operated", cycle, str(tmp_path))
    assert x3.passed and x3.applicable
    assert "1 value(s) verified" in x3.reason and "no registered resolver" in x3.reason


def test_operator_gap_and_fabrication_are_distinguishable(tmp_path):
    """The distinction the first fix missed: both used to count as 'unresolvable'."""
    gap = resolvers.verify(_cycle_with_source("datadog", "sum:x"), root=str(tmp_path))
    fake = resolvers.verify(_cycle_with_source("file", "nope.json"), root=str(tmp_path))
    assert gap["counts"]["no_resolver"] == 1 and gap["failure_count"] == 0
    assert fake["counts"]["unresolvable"] == 1 and fake["failure_count"] == 1


# --- F-1: the trust anchor is not the agent's to write ---------------------

def test_anchor_inside_the_workspace_is_refused(tmp_path):
    ws = tmp_path / "ws"; (ws / ".daver").mkdir(parents=True)
    anchor = ws / ".daver" / "allowed_signers"
    anchor.write_text("j.okonkwo@acme.example ssh-ed25519 AAAAfake\n")
    path, why = integrity.resolve_trust_anchor(str(anchor), workspace=str(ws))
    assert path is None and "inside the audited workspace" in why


@pytest.mark.skipif(not HAS_SSH, reason="ssh-keygen not available")
def test_agent_cannot_forge_signoff_with_a_self_written_anchor(tmp_path, ref_cycle):
    """The original break: generate a key, write it into allowed_signers under the
    accountable human's identity, sign, and X-2 accepted the forgery."""
    ws = tmp_path / "ws"; (ws / ".daver").mkdir(parents=True)
    key = ws / ".daver" / "agent_key"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(key), "-N", "", "-q"], check=True)
    pub = (ws / ".daver" / "agent_key.pub").read_text().split()
    (ws / ".daver" / "allowed_signers").write_text(
        f"j.okonkwo@acme.example {pub[0]} {pub[1]}\n")

    for subject, path in integrity.SIGNED_SUBJECTS.items():
        d = integrity.signature_digest(ref_cycle, subject)
        f = ws / f"{subject}.txt"; f.write_text(d)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key),
                        "-n", integrity.NAMESPACE, str(f)], check=True, capture_output=True)
        node = ref_cycle
        for k in path:
            node = node[k]
        node["detached_signature"] = (ws / f"{subject}.txt.sig").read_text()

    r = integrity.verify_signature(ref_cycle, "go_no_go",
                                   str(ws / ".daver" / "allowed_signers"), workspace=str(ws))
    assert not r["ok"], "an agent forged a human sign-off using its own key"


# --- F-6: the signature covers the whole decision --------------------------

@pytest.mark.parametrize("label,mutate", [
    ("bypass disposition", lambda c: c["validation_plan"]["evasion_analysis"]["bypasses"][0]
        .__setitem__("disposition", "accepted")),
    ("exception scope", lambda c: c["exception_register"]["exceptions"][0]
        .__setitem__("scope", "0.0.0.0/0")),
    ("exception expiry", lambda c: c["exception_register"]["exceptions"][0]
        .__setitem__("expiry", "2099-01-01")),
    ("control enforcement mode", lambda c: c["control_matrix"]["controls"][0]
        .__setitem__("enforcement_mode", "log")),
    ("audit log deleted", lambda c: c.__setitem__("audit", [])),
    ("audit entry edited", lambda c: c["audit"][1].__setitem__("detail", "tampered")),
    ("guardrail widened", lambda c: c["definition_brief"]["guardrails"]
        ["false_positive_tolerance"].__setitem__("value", 0.5)),
    ("measured value changed", lambda c: c["validation_plan"]["measured"]
        ["false_positive_rate"].__setitem__("value", 0.9)),
])
def test_signature_covers(label, mutate, ref_cycle):
    before = integrity.signature_digest(ref_cycle, "go_no_go")
    mutated = copy.deepcopy(ref_cycle)
    mutate(mutated)
    assert integrity.signature_digest(mutated, "go_no_go") != before, \
        f"a signed cycle could be rewritten: {label}"


def test_subject_is_versioned(ref_cycle):
    """Old signatures must fail loudly rather than be reinterpreted."""
    assert integrity.signature_subject(ref_cycle, "go_no_go")["subject_version"] == integrity.SUBJECT_VERSION


# --- F-10: bounded regex ---------------------------------------------------

def test_matches_subject_is_bounded():
    cycle = {"module": {"s": "a" * (MAX_MATCH_SUBJECT * 4)}}
    r = evaluate({"matches": ["module.s", "^a+$"]}, Context(cycle=cycle))
    assert r.ok  # still works, just on a bounded prefix
    assert MAX_MATCH_SUBJECT <= 65536


# --- visitor-path audit F-D: MCP server WORKSPACE must not fail open -------

def test_mcp_server_refuses_to_start_without_explicit_workspace(tmp_path):
    """A silent default to cwd makes DAVER_WORKSPACE decoration, not a boundary.

    Requires the optional `mcp` package; skipped where it is not installed, same
    as the rest of the MCP surface, which has no other coverage in this suite.
    """
    pytest.importorskip("mcp")
    server_py = os.path.join(os.path.dirname(__file__), "..", "..", "mcp", "server.py")
    env = {k: v for k, v in os.environ.items() if k != "DAVER_WORKSPACE"}
    result = subprocess.run([sys.executable, server_py], cwd=str(tmp_path), env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0, "server started with no explicit DAVER_WORKSPACE"
    assert "DAVER_WORKSPACE" in result.stderr
