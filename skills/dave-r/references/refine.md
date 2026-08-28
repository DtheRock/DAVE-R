# Refine: sweeps, drift, and knowing when to stop tuning

The stage most likely to be skipped and most likely to pay off.

## The exception sweep

Run it on a schedule, unprompted. A register without a sweep becomes the thing that
documents permanent exceptions rather than the thing that prevents them.

Flag every exception that is:

- **Expired and unactioned.** Gate R-2 blocks on this. Expiry with no action is not
  renewal; it is drift with a date stamp on it.
- **Expiring within 30 days.** Warn early so the reduction plan has time to run.
- **Weakly bound.** Mechanism is `ip`, `asn`, `user-agent` or `path`. These are
  spoofable or over-broad. An ASN can hold thousands of unrelated hosts on shared
  cloud ranges - "the aggregator's backend ASNs" may trust far more than intended.
- **Missing a compensating control.** What covers the risk while the bypass is live?
- **High blast radius.** Especially unauthenticated paths reaching confidential or
  regulated data.
- **Never used.** Zero observed hits means dead weight. Retire it.

## Escalate, do not ratchet

Gate R-5. If the same threshold has been adjusted three times, the control class is
losing and tuning it again buys days, not a fix.

The published scraping scenario is the clean illustration: scrapers evade a 300
req/min limit by dropping to 290, so the team lowers it to 200. Nothing stops a move
to 190. The scenario presents this as a success; it is a treadmill.

When you spot the pattern, recommend a class change rather than a number change:

| Losing | Escalate to |
| :--- | :--- |
| Rate limit on an unauthenticated endpoint | Require authentication, then per-key quota |
| Static threshold on a single signal | Multi-signal risk score with graduated response |
| IP or ASN allowlist | Cryptographic identity, mTLS, or signed request |
| Volume-based bot detection | Cost-based challenge (proof of work, attestation) |
| Blocking scrapers by pattern | Cache aggressively, or price the data and sell it |

Say the quiet part: a control that only works while the attacker is unsophisticated
is a control with an expiry date. Better to know the date.

## Drift checks

Re-run the evasion analysis at least quarterly (gate R-4). Adversaries adapt between
cycles; an evasion analysis from nine months ago describes a different opponent.

Ask, each time: what changed in the traffic mix, what new bypasses are cheap now, and
has anything in `accepted` disposition become unacceptable?

## Complexity trend

Gate R-3 requires counting controls, exceptions and mean exception age each cycle.
The framework claims the system gets simpler over time. Counting is what turns that
from aspiration into a falsifiable claim - and a rising exception count with a rising
mean age is the earliest signal that governance is slipping.

## Feeding back into Define

Every refinement is evidence for the next cycle's Define stage. A bypass you accepted
under time pressure is a threat scenario for next quarter. Carry it forward explicitly
rather than rediscovering it after an incident.
