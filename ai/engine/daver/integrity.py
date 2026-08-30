"""Tamper evidence: audit hash chaining and real human signatures.

Two self-report problems this fixes.

1. `cycle.audit` recorded what the agent did, but the agent wrote it, so an agent
   that skipped a step could simply not record skipping it. Chaining each entry to
   its predecessor makes deletion and edits detectable.

2. `authored_by_agent: false` was a field the agent could write. That is not a
   control, it is a promise. Binding each signature to a detached cryptographic
   signature over a canonical digest makes it one: the agent has no private key,
   so it cannot produce a valid signature no matter what it writes in the document.

The reference signer is `ssh-keygen -Y`, which ships on macOS and Linux and needs no
new dependency or key infrastructure. Any detached-signature scheme works; the
digest is what matters.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from typing import Any

NAMESPACE = "dave-r"

SIGNED_SUBJECTS = {
    "go_no_go": ("validation_plan", "go_no_go", "signature"),
    "enforcement": ("execution", "enforcement_authorization"),
}


def canonical(obj: Any) -> bytes:
    """Deterministic serialization. Same document, same bytes, any platform."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


# --- audit chain -----------------------------------------------------------

def _entry_core(e: dict) -> dict:
    return {k: v for k, v in e.items() if k not in {"hash", "prev"}}


def chain_audit(cycle: dict) -> dict:
    """Stamp each audit entry with prev + hash. Idempotent."""
    prev = "0" * 64
    for e in cycle.get("audit") or []:
        e["prev"] = prev
        e["hash"] = hashlib.sha256(canonical({"prev": prev, **_entry_core(e)})).hexdigest()
        prev = e["hash"]
    return cycle


def verify_audit(cycle: dict) -> dict:
    """Walk the chain. Any edit, reorder or deletion breaks it at a nameable point."""
    entries = cycle.get("audit") or []
    if not entries:
        return {"ok": True, "entries": 0, "detail": "no audit entries"}
    prev = "0" * 64
    for i, e in enumerate(entries):
        if "hash" not in e or "prev" not in e:
            return {"ok": False, "broken_at": i, "detail": f"entry {i} is not chained; run 'daver chain'"}
        if e["prev"] != prev:
            return {"ok": False, "broken_at": i,
                    "detail": f"entry {i} does not follow entry {i-1}: an entry was edited, "
                              f"reordered or removed"}
        expect = hashlib.sha256(canonical({"prev": prev, **_entry_core(e)})).hexdigest()
        if e["hash"] != expect:
            return {"ok": False, "broken_at": i,
                    "detail": f"entry {i} content does not match its hash: it was edited after recording"}
        prev = e["hash"]
    return {"ok": True, "entries": len(entries), "head": prev}



# --- trust anchor ----------------------------------------------------------

OPERATOR_ANCHORS = (
    os.path.join(os.path.expanduser("~"), ".config", "daver", "allowed_signers"),
    os.path.join(os.path.expanduser("~"), ".daver", "allowed_signers"),
)


def resolve_trust_anchor(explicit: str | None = None,
                         workspace: str | None = None) -> tuple[str | None, str]:
    """Locate allowed_signers, refusing any anchor inside the audited workspace.

    X-2's whole claim is that the agent cannot produce a valid signature because
    it has no private key. That held only until you noticed the agent could write
    its OWN key into the trust anchor: the anchor lived at
    $DAVER_EVIDENCE_ROOT/.daver/allowed_signers, inside the workspace the agent
    operates in, and .gitignore excluded it so no committed copy existed to diff
    against. Generate a keypair, add it under the accountable human's identity,
    sign, and the forgery verifies.

    So the anchor now comes from operator space by default, and an anchor located
    inside the workspace is refused rather than trusted. Public keys are not
    secrets: the right pattern is to commit your own allowed_signers to your own
    repository and verify against that.

    workspace=None does NOT mean "skip the containment check" - it means the
    caller didn't say, so this defaults to the current directory, the same
    self-healing fallback resolvers.evidence_root() already uses for the file
    resolver's own boundary. A caller that genuinely wants no containment has no
    way to ask for that here, on purpose: the whole point of this function is
    that the check cannot be silently switched off by omitting a flag.
    """
    ws = os.path.realpath(workspace) if workspace else os.path.realpath(os.getcwd())

    def inside_workspace(path: str) -> bool:
        rp = os.path.realpath(path)
        return rp == ws or rp.startswith(ws + os.sep)

    candidates: list[tuple[str, str]] = []
    if explicit:
        candidates.append((explicit, "explicit argument"))
    env = os.environ.get("DAVER_ALLOWED_SIGNERS")
    if env:
        candidates.append((env, "DAVER_ALLOWED_SIGNERS"))
    candidates.extend((p, "operator config") for p in OPERATOR_ANCHORS)

    refused = []
    for path, origin in candidates:
        if inside_workspace(path):
            refused.append(f"{path} ({origin}) is inside the workspace under examination")
            continue
        if os.path.isfile(path):
            return path, origin
    if refused:
        return None, ("refusing to trust an allowed_signers file inside the audited "
                      "workspace: " + "; ".join(refused) + ". Keep the trust anchor in "
                      "operator space (~/.config/daver/allowed_signers) or commit it to "
                      "your own repository.")
    return None, (f"no allowed_signers file found. Looked in: "
                  f"{', '.join(p for p, _ in candidates)}")


# --- signatures ------------------------------------------------------------

SUBJECT_VERSION = 2


def signature_subject(cycle: dict, subject: str) -> dict:
    """The exact material a signature covers.

    Deliberately includes the EVIDENCE, not just the decision. Signing "approved"
    alone would let the evidence change afterwards while the approval still looked
    valid. The signer is attesting to a decision on a specific body of measurement.

    Version 2 (1.1.1) signs DIGESTS OF WHOLE SUB-DOCUMENTS rather than summaries.
    Version 1 took only len(bypasses) and a list of exception ids, so a signed
    cycle could be materially rewritten while the signature stayed valid: bypass
    dispositions flipped, exception scope and expiry changed, control enforcement
    modes altered, and the entire audit log deleted.

    It also pins the audit chain head. The threat model documents that an agent
    can tamper and re-chain; a human signature over the head is exactly the
    external anchor the chain otherwise lacks.
    """
    if subject not in SIGNED_SUBJECTS:
        raise KeyError(f"unknown subject '{subject}'. Known: {sorted(SIGNED_SUBJECTS)}")
    brief = cycle.get("definition_brief") or {}
    vp = cycle.get("validation_plan") or {}
    audit = verify_audit(cycle)
    return {
        "subject_version": SUBJECT_VERSION,
        "cycle_id": cycle.get("cycle_id"),
        "spec_version": cycle.get("spec_version"),
        "adapter": cycle.get("adapter"),
        "subject": subject,
        "accountable": ((brief.get("raci") or {}).get("accountable") or {}).get("identity"),
        "guardrails": brief.get("guardrails"),
        "triage_track": (brief.get("triage") or {}).get("track"),
        "critical_flows": digest(brief.get("asset", {}).get("critical_flows")),
        "threat_scenarios": digest(brief.get("threat_scenarios")),
        "measured": vp.get("measured"),
        "baseline": vp.get("baseline"),
        "shadow": {k: vp.get("shadow", {}).get(k) for k in ("start", "end", "mode", "duration_days")},
        "evasion_analysis": digest(vp.get("evasion_analysis")),
        "exception_register": digest(cycle.get("exception_register")),
        "control_matrix": digest(cycle.get("control_matrix")),
        "execution_rollout": digest((cycle.get("execution") or {}).get("rollout_stages")),
        "audit_head": audit.get("head") if audit.get("ok") else "UNCHAINED",
        "audit_entries": len(cycle.get("audit") or []),
    }


def signature_digest(cycle: dict, subject: str) -> str:
    return digest(signature_subject(cycle, subject))


def sign_request(cycle: dict, subject: str, key_hint: str = "~/.ssh/id_ed25519") -> dict:
    """What a human needs in order to sign. This function cannot sign anything."""
    d = signature_digest(cycle, subject)
    node = cycle
    for k in SIGNED_SUBJECTS[subject]:
        node = (node or {}).get(k) or {}
    who = (node.get("by") or {}).get("identity") or \
          (((cycle.get("definition_brief") or {}).get("raci") or {}).get("accountable") or {}).get("identity")
    return {
        "cycle_id": cycle.get("cycle_id"),
        "subject": subject,
        "digest": d,
        "must_be_signed_by": who,
        "namespace": NAMESPACE,
        "how": [
            f"echo -n {d} > /tmp/{subject}.digest",
            f"ssh-keygen -Y sign -f {key_hint} -n {NAMESPACE} /tmp/{subject}.digest",
            f"# then paste the contents of /tmp/{subject}.digest.sig into",
            f"# {'.'.join(SIGNED_SUBJECTS[subject])}.detached_signature",
        ],
        "note": "The agent has no private key. It cannot produce this signature, which "
                "is the point: the signature is what makes authored_by_agent:false real.",
    }


def verify_signature(cycle: dict, subject: str, allowed_signers: str | None = None,
                     workspace: str | None = None) -> dict:
    """Verify a detached signature over the canonical digest, via ssh-keygen -Y verify."""
    node = cycle
    for k in SIGNED_SUBJECTS[subject]:
        node = (node or {}).get(k) or {}
    if not node:
        return {"ok": False, "subject": subject, "detail": "no signature block present"}

    sig = node.get("detached_signature")
    if not sig:
        return {"ok": False, "subject": subject, "signed": False,
                "detail": "decision recorded but not cryptographically signed. "
                          "authored_by_agent:false is self-reported here."}

    signer = (node.get("by") or {}).get("identity")
    if not signer:
        return {"ok": False, "subject": subject,
                "detail": "signature block names no signer identity"}

    allowed, why = resolve_trust_anchor(allowed_signers, workspace)
    if allowed is None:
        return {"ok": False, "subject": subject, "detail": why}

    d = signature_digest(cycle, subject)
    with tempfile.TemporaryDirectory() as td:
        sig_path = os.path.join(td, "s.sig")
        with open(sig_path, "w") as fh:
            fh.write(sig if sig.endswith("\n") else sig + "\n")
        try:
            out = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", allowed, "-I", signer,
                 "-n", NAMESPACE, "-s", sig_path],
                input=d, capture_output=True, text=True, timeout=20, shell=False)
        except FileNotFoundError:
            return {"ok": False, "subject": subject, "detail": "ssh-keygen not available"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "subject": subject, "detail": "ssh-keygen verify timed out"}

    if out.returncode == 0:
        return {"ok": True, "subject": subject, "signer": signer, "digest": d}
    return {"ok": False, "subject": subject, "signer": signer, "digest": d,
            "detail": (out.stderr or out.stdout).strip()[:300]}


def verify_all_signatures(cycle: dict, allowed_signers: str | None = None,
                          workspace: str | None = None) -> dict:
    results = {}
    for subject, path in SIGNED_SUBJECTS.items():
        node = cycle
        for k in path:
            node = (node or {}).get(k) or {}
        if node:
            results[subject] = verify_signature(cycle, subject, allowed_signers, workspace)
    return {"ok": all(r.get("ok") for r in results.values()) if results else False,
            "subjects": results or "no signature blocks present"}
