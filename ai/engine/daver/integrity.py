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


# --- signatures ------------------------------------------------------------

def signature_subject(cycle: dict, subject: str) -> dict:
    """The exact material a signature covers.

    Deliberately includes the EVIDENCE, not just the decision. Signing "approved"
    alone would let the evidence change afterwards while the approval still looked
    valid. The signer is attesting to a decision on a specific body of measurement.
    """
    if subject not in SIGNED_SUBJECTS:
        raise KeyError(f"unknown subject '{subject}'. Known: {sorted(SIGNED_SUBJECTS)}")
    brief = cycle.get("definition_brief") or {}
    vp = cycle.get("validation_plan") or {}
    return {
        "cycle_id": cycle.get("cycle_id"),
        "spec_version": cycle.get("spec_version"),
        "subject": subject,
        "accountable": ((brief.get("raci") or {}).get("accountable") or {}).get("identity"),
        "guardrails": brief.get("guardrails"),
        "triage_track": (brief.get("triage") or {}).get("track"),
        "measured": vp.get("measured"),
        "baseline": vp.get("baseline"),
        "shadow": {k: vp.get("shadow", {}).get(k) for k in ("start", "end", "mode", "duration_days")},
        "evasion_bypass_count": len((vp.get("evasion_analysis") or {}).get("bypasses") or []),
        "exception_ids": [e.get("id") for e in (cycle.get("exception_register") or {}).get("exceptions", [])],
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


def verify_signature(cycle: dict, subject: str, allowed_signers: str | None = None) -> dict:
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
    allowed = allowed_signers or os.environ.get(
        "DAVER_ALLOWED_SIGNERS",
        os.path.join(os.environ.get("DAVER_EVIDENCE_ROOT", os.getcwd()), ".daver", "allowed_signers"))
    if not os.path.isfile(allowed):
        return {"ok": False, "subject": subject, "detail": f"no allowed_signers file at {allowed}"}

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


def verify_all_signatures(cycle: dict, allowed_signers: str | None = None) -> dict:
    results = {}
    for subject, path in SIGNED_SUBJECTS.items():
        node = cycle
        for k in path:
            node = (node or {}).get(k) or {}
        if node:
            results[subject] = verify_signature(cycle, subject, allowed_signers)
    return {"ok": all(r.get("ok") for r in results.values()) if results else False,
            "subjects": results or "no signature blocks present"}
