# DAVE+R Refinement Log

*A chronological record of tuning, cleanups, and system hardening.*

## Entries

| Date | Version | Kind | Change | Evidence *(observed, with a source)* | Impact observed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-06-23 | `v1.1.0` | threshold-tune | Raised challenge threshold 200 → 220 req/min | Post-enforcement p99.9 of legitimate sessions rose to 168 after the pricing page added a live-refresh widget (Datadog, 14d) | Challenge rate on the page fell 31%, scraping volume unchanged |
| 2026-07-14 | `v1.2.0` | exception-retired | `EXC-001` auto-revoked on schedule | Zero exception hits in the 9 days before expiry; partner signature verified in production 06-28 | Exception count 1 → 0; one bypass path removed |

**Kinds:** `threshold-tune`, `control-escalation`, `exception-retired`, `rule-retired`,
`signal-added`, `rollback`, `simplification`.

> Every refinement cites an observation. "It felt noisy" is not a refinement, it is a hunch
> entering production.

## Complexity trend
*New in v1.1. The framework claims the system gets simpler over time. Counting is what makes
that claim falsifiable rather than aspirational.*

| Date | Controls | Exceptions | Mean exception age (days) | Past expiry, unactioned |
| :--- | :--- | :--- | :--- | :--- |
| 2026-06-01 | 2 | 1 | 12 | 0 |
| 2026-08-01 | 2 | 0 | 0 | 0 |

A rising exception count with a rising mean age is the earliest signal that governance is
slipping.

## Drift check
*New in v1.1. Adversaries adapt between cycles. An evasion analysis from three quarters ago
describes a different opponent.*

* **Last evasion re-analysis:** [date — at least quarterly]
* **Adjustments to this threshold, cumulative:** [count]
* **Escalation recommended?** [Yes / No]
* **New bypasses observed:** [...]

> **The ratchet trap.** Three adjustments to the same threshold is the signature of a control
> class that is losing. Each tune buys less time than the last while the rule set gets harder
> to reason about. Change the class of control, not the number:
>
> | Losing | Escalate to |
> | :--- | :--- |
> | Rate limit on an unauthenticated endpoint | Require authentication, then per-key quota |
> | Static threshold on a single signal | Multi-signal risk score with graduated response |
> | IP or ASN allowlist | Cryptographic identity, mTLS, or signed request |
> | Volume-based bot detection | Cost-based challenge (proof of work, attestation) |
