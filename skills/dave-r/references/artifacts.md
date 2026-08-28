# The five artifacts

Every artifact is a section of one `cycle.yaml`. They cross-reference by ID, and
that is what makes the chain machine-checkable: a control that addresses no declared
threat, or an exception bypassing a control that does not exist, fails a gate.

A complete worked example lives at `engine/tests/fixtures/reference.cycle.yaml`.
It passes all 43 blocking gates. Read it alongside this file.

## 1. Definition Brief

Turns ambiguity into an executable target.

| Field | Notes |
| :--- | :--- |
| `asset.target` | Concrete. A host and path, not "the API". |
| `asset.critical_flows` | Enumerate them. Validate tests each one individually (V-4). |
| `threat_scenarios[].observable_signature` | How the threat appears in telemetry. If you cannot name the signal, you cannot validate the control. Gate D-2 rejects "bots" and "attackers". |
| `guardrails.false_positive_tolerance` | A fraction. Never zero: no statistical control can guarantee it, and D-3 blocks it. |
| `success_metrics[].baseline` | Measured **before** shadow mode. This is the field teams skip and the reason their results are unfalsifiable. |
| `triage` | Track, whether harm is accruing now, and what a day of inaction costs. See `triage.md`. |
| `alternatives_considered` | At least one, on a different plane, with why it was rejected. Stop the framework nudging every problem toward the edge. |
| `raci.accountable` | One person. D-5 rejects anything matching team, group, ops, oncall. |

## 2. Control Matrix

Design that can be operated, not just deployed.

Each control needs `id`, `intent`, `plane`, `owner`, `addresses` (threat IDs from the
brief), `telemetry.source` (re-runnable), and a `rollback` block with four parts:

- `procedure` - how
- `granularity` - `global`, `segment`, `rule`, or `graduated` (block to challenge to log)
- `target_seconds` - how fast
- `degraded_posture` - **what protects the asset while rolled back.** Rollback restores
  availability and simultaneously restores the abuse. "Nothing" is a valid answer that
  must be written down.

Also required: `trust_boundary` with at least two zones and one flow. Any diagram must
be a committed relative path, not an external URL (A-6).

## 3. Validation Plan

Where enforcement is earned. Every measured field here is read by an enforcement gate,
so none of them may be `asserted`.

- `baseline` - FP rate and latency measured before `shadow.start`. Gate V-1.
- `shadow` - mode, start, end, duration. Adapter sets the minimum by triage track.
- `tests` - at least abuse, safety, bypass, rollback. One safety test per critical flow.
- `evasion_analysis` - **at least three named bypasses, at least one tested, every one
  with a disposition.** An `accepted` bypass needs a named human signature. Gate V-7.
- `measured` - FP rate overall and per critical flow, latency delta, rollback tested.
- `go_no_go.signature` - the accountable owner from Define, personally. Never you.

`threshold_evasion_margin` is worth computing for any threshold control: how much of
their goal can an attacker still reach just under the limit? Below 0.25 and you are on
a treadmill, not a fix.

## 4. Exception Register

Exceptions are normal. Ungoverned exceptions are not.

Beyond the obvious fields, four that the original template lacked:

- `mechanism.kind` - preference order: `cryptographic-identity`, `mtls`,
  `signed-header`, `api-key`, then the weak ones: `ip`, `asn`, `user-agent`, `path`.
  Weak mechanisms need a written justification and a maximum 180-day expiry (V-10).
  Remember an ASN can hold thousands of unrelated hosts.
- `compensating_control` - what covers the risk while the bypass is live. If genuinely
  nothing, say so in `none_because`. Silence is not permitted.
- `blast_radius` - severity, whether the bypassed path is unauthenticated, what data is
  reachable. A twelve-month bypass on an unauthenticated webhook path should be visibly
  alarming, and this is the field that makes it so.
- `expiry_action` - `auto-revoke`, `escalate`, `block-change`, or `review-required`.
  There is deliberately no `auto-extend`. Undefined expiry behaviour is how every
  register drifts into permanent exceptions.

## 5. Refinement Log

Each entry needs an observed `evidence` value, an `impact`, and a semver `version`.
Plus two standing sections:

- `complexity_trend` - control count, exception count, mean exception age. The framework
  claims the system gets simpler; counting makes that falsifiable.
- `drift_check` - when the evasion analysis was last re-run, how many times this
  threshold has been adjusted, and whether escalation is now recommended. Three
  adjustments to the same number means the control class is losing (R-5).

## Cross-artifact rules the gates enforce

- Every control `addresses` at least one threat ID that exists in the brief (A-2).
- Every exception `applies_to` at least one control ID that exists (V-9).
- Every critical flow in the brief has a matching test (A-A1) and its own measured FP
  rate (V-4).
- The go/no-go signer and the enforcement authorizer are both the accountable owner
  named in the brief (V-11, E-6).
- A `derived` value rooted in an `asserted` one fails any gate requiring observation.
