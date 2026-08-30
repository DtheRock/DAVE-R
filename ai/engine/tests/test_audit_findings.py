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
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from daver import Spec, integrity, load_cycle, resolvers  # noqa: E402
from daver.expr import MATCH_TIMEOUT_SECONDS, MAX_MATCH_SUBJECT, evaluate  # noqa: E402
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


# =============================================================================
# Full audit, 2026-08-30 (dave-r-full-audit.md) - 8 findings, one section each.
# Finding 8 (exec-resolver argv allowlist comments overstating the safety
# boundary) has no test here: it changed only docstrings/comments, no
# behavior, and there is nothing computable to regress-test in prose.
# =============================================================================

# --- Finding 1 (High): X-1/X-2/X-3 must fire no later than validate --------

def test_x_gates_evaluate_no_later_than_validate(ref_cycle):
    """integrity.yaml declared `stage: execute` at the file level, so X-1
    (audit chain), X-2 (signature verification) and X-3 (source
    re-verification) were all bucketed into execute even though V-11's
    go/no-go decision is a Validate-stage gate. An operator checking
    `--stage validate` got a clean structural pass on the signature fields
    without X-2 ever running the real cryptographic check."""
    ids_at_validate = {r.id for r in Spec().run(ref_cycle, stage="validate").results}
    assert {"X-1", "X-2", "X-3"} <= ids_at_validate


def test_x_gates_fire_on_the_cli_default_stage_too(ref_cycle):
    """No --stage flag means the CLI reads the cycle document's own `stage:`
    field - written by the agent, not a fixed default. That path must pick up
    the X-gates identically, or the fix only covers the flag nobody was told
    to pass."""
    cycle = copy.deepcopy(ref_cycle)
    cycle["stage"] = "validate"
    ids = {r.id for r in Spec().run(cycle).results}
    assert {"X-1", "X-2", "X-3"} <= ids


# --- Finding 2 (Medium): D-3 must check latency_budget_ms's sign too -------

@pytest.mark.parametrize("bad_value", [0, -50])
def test_d3_rejects_a_non_positive_latency_budget(ref_cycle, bad_value):
    """D-3 already refused a zero-or-negative false_positive_tolerance because
    a declared-zero guardrail is a hollow guarantee no statistical control can
    honor. latency_budget_ms is the exact same shape of guardrail and was only
    checked for existence, not sign - 0 and -50 both silently passed."""
    cycle = copy.deepcopy(ref_cycle)
    cycle["definition_brief"]["guardrails"]["latency_budget_ms"]["value"] = bad_value
    d3 = next(r for r in Spec().run(cycle, stage="define").results if r.id == "D-3")
    assert not d3.passed


def test_d3_still_passes_a_real_positive_latency_budget(ref_cycle):
    d3 = next(r for r in Spec().run(ref_cycle, stage="define").results if r.id == "D-3")
    assert d3.passed


# --- Finding 3 (Medium): omitting --evidence-root must not disable F-1 -----

def test_omitted_workspace_defaults_to_cwd_not_to_skipping_the_check(tmp_path, monkeypatch):
    """--evidence-root has no argparse default, so omitting it left
    workspace=None all the way down to resolve_trust_anchor - which treated
    None as "skip the containment check" rather than "not told, so assume
    cwd", unlike resolvers.evidence_root()'s own self-healing default. Same
    anchor, same file, used to flip from refused to trusted purely because a
    flag was left off the command line."""
    monkeypatch.chdir(tmp_path)
    anchor = tmp_path / "allowed_signers"
    anchor.write_text("attacker@evil ssh-ed25519 AAAAfake\n")
    path, why = integrity.resolve_trust_anchor(str(anchor), workspace=None)
    assert path is None and "inside the audited workspace" in why


def test_omitted_workspace_still_trusts_a_genuinely_outside_anchor(tmp_path, monkeypatch):
    """The default must be a real default, not a blanket refusal: an anchor
    that is genuinely outside the (defaulted-to-cwd) workspace still
    resolves normally."""
    workdir = tmp_path / "workspace"; workdir.mkdir()
    operator_space = tmp_path / "operator"; operator_space.mkdir()
    monkeypatch.chdir(workdir)
    anchor = operator_space / "allowed_signers"
    anchor.write_text("owner@acme.example ssh-ed25519 AAAAfake\n")
    path, _ = integrity.resolve_trust_anchor(str(anchor), workspace=None)
    assert path == str(anchor)


# --- Finding 4 (Low-Medium): matches must bound wall-clock time, not length -

def test_matches_bounds_wall_clock_time_against_catastrophic_backtracking():
    """MAX_MATCH_SUBJECT only bounds a huge but well-behaved input; it does
    nothing for a pattern whose cost is exponential in the match rather than
    the input size. `(a+)+$` against a non-matching subject measured
    0.03s/0.43s/6.90s at 18/22/26 characters - a ~30-40 character
    adapter-authored pattern could hang the run indefinitely. A worker
    subprocess with subprocess.run's own `timeout=` gives a genuine
    OS-enforced bound regardless of input length; a thread does not, because
    CPython's `re` holds the GIL for the whole match and a
    `Thread.join(timeout)` cannot reclaim control either - measured 7+
    seconds against a 1.0s budget when tried."""
    cycle = {"module": {"s": "a" * 40 + "!"}}
    t0 = time.perf_counter()
    r = evaluate({"matches": ["module.s", "(a+)+$"]}, Context(cycle=cycle))
    elapsed = time.perf_counter() - t0
    assert not r.ok
    assert elapsed < MATCH_TIMEOUT_SECONDS + 1.5, (
        f"took {elapsed:.2f}s; a catastrophic pattern must be bounded near "
        f"{MATCH_TIMEOUT_SECONDS}s regardless of input length")


def test_matches_still_matches_normally():
    assert evaluate({"matches": ["module.s", "^[a-z]+$"]}, Context(cycle={"module": {"s": "hello"}})).ok
    assert not evaluate({"matches": ["module.s", "^[a-z]+$"]}, Context(cycle={"module": {"s": "HELLO"}})).ok


# --- Finding 5 (Low): lint() must catch capitalized dangling references ----

def test_lint_catches_a_capitalized_dangling_reference():
    """_unresolvable_refs used to skip any ref whose root wasn't all-lowercase,
    to dodge false positives on enum-like literals - which meant a root
    mistyped with a capital letter (Definition_brief instead of
    definition_brief) escaped detection entirely and became a silent runtime
    string literal, exactly the failure mode this check exists to catch."""
    s = Spec()
    assert s._unresolvable_refs({"assert": {"exists": "Definition_brief.asset.target"}})


def test_lint_still_ignores_non_reference_strings():
    """Enum values and prose must not become false positives just because the
    case-sensitivity blind spot closed."""
    s = Spec()
    assert not s._unresolvable_refs({"assert": {"in": ["module.x", ["LOW", "HIGH"]]}})
    assert not s._unresolvable_refs({"assert": {"matches": ["module.x", "an Execution. of the plan"]}})


# --- Finding 6 (Low): adapter gate stage-inference must be structural ------

def test_adapter_stage_inference_ignores_an_incidental_substring():
    """_adapter_gate_stage used to yaml.safe_dump the gate's assert block and
    substring-search it for artifact names like 'execution' or 'audit' -
    matching even inside an unrelated regex pattern or prose string, not just
    a real reference, and silently filing the gate under the wrong stage."""
    g = {"id": "T-1", "assert": {"matches": ["module.x", "an execution. of the plan"]}}
    assert Spec._adapter_gate_stage(g) == "define"


def test_adapter_stage_inference_still_detects_real_references():
    assert Spec._adapter_gate_stage(
        {"id": "T-2", "assert": {"exists": "execution.enforcement_authorization"}}) == "execute"
    assert Spec._adapter_gate_stage(
        {"id": "T-3", "assert": {"exists": "validation_plan.go_no_go"}}) == "validate"


def test_adapter_stage_inference_explicit_stage_still_wins():
    assert Spec._adapter_gate_stage({"id": "T-4", "stage": "refine", "assert": {}}) == "refine"


# --- Finding 7 (Low): schemas must reject undeclared keys ------------------

def _cycle_schema_validator():
    """Build a Draft202012Validator for cycle.schema.json from the shipped
    schemas. jsonschema/referencing are optional (ai/mcp/requirements.txt, not
    the core engine's ai/requirements-ci.txt), so this skips where they aren't
    installed - same as the rest of the MCP-adjacent surface. Importing the
    specific names, not just the packages: an old system-wide jsonschema can be
    present but predate Draft202012Validator, which imports fine at the package
    level and then fails on the class - importorskip alone would not catch that."""
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as e:
        pytest.skip(f"jsonschema/referencing with Draft202012Validator support not available: {e}")

    sdir = os.path.join(os.path.dirname(__file__), "..", "..", "spec", "schemas")
    registry = Registry()
    for fn in os.listdir(sdir):
        if fn.endswith(".json"):
            with open(os.path.join(sdir, fn)) as fh:
                registry = registry.with_resource(fn, Resource.from_contents(json.load(fh)))
    with open(os.path.join(sdir, "cycle.schema.json")) as fh:
        cyc_schema = json.load(fh)
    return Draft202012Validator(cyc_schema, registry=registry)


def test_schemas_still_validate_the_real_reference_cycle(ref_cycle):
    """5 of 8 schemas didn't set additionalProperties: false; the fix must not
    make the schema stricter than the real documents it's supposed to accept."""
    validator = _cycle_schema_validator()
    errs = list(validator.iter_errors(ref_cycle))
    assert not errs, [e.message for e in errs[:3]]


def test_schemas_reject_a_typo_d_key(ref_cycle):
    """adapter/common/definition-brief/exception-register/refinement-log all
    allowed undeclared extra fields, so a typo'd key (provenence instead of
    provenance, say) silently passed schema validation."""
    validator = _cycle_schema_validator()
    typo_cycle = copy.deepcopy(ref_cycle)
    typo_cycle["definition_brief"]["raci"]["accountable"]["provenence_typo"] = "oops"
    assert list(validator.iter_errors(typo_cycle)), \
        "a typo'd/undeclared key should now be rejected by additionalProperties: false"
