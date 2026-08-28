# 📖 DAVE+R In Action: Mitigating AI Scrapers Without Breaking the Business

**Module A (Edge and WAF Expansion).** Written against framework v1.0.0,
and reproduced here exactly as published.

---

The Scenario: Acme Corp’s core product relies on a live pricing API (/v2/pricing/live). Recently, aggressive AI data-crawlers began scraping the endpoint. This caused origin database CPU spikes, resulting in intermittent 503 Service Unavailable timeouts for paying enterprise customers.

The Security team wanted to instantly deploy a strict WAF rule to block all high-volume, automated traffic. However, in the past, rushed deployments had accidentally blocked Acme's VIP B2B partners, violating SLAs and destroying trust between Security and Product.

Instead of guessing, the team used the DAVE+R lifecycle.

1) Define
The Security and Platform teams didn't touch the WAF console yet. They spent 20 minutes writing a Definition Brief.

Target Asset: /v2/pricing/live endpoint.

The Guardrail (Critical): They must not block requests from their top 5 enterprise partners. WAF processing must add < 15ms of latency.

Success Metric: Reduce unauthenticated scraping volume by 80% while maintaining a 0% false-positive rate for known partners.

2) Architect
The team designed the solution and documented it in the Control Matrix.

Enforcement Plane: Edge WAF.

The Rule: A baseline strict Rate Limit (300 requests/minute) for all traffic, overlaid with a bypass rule for VIP Partners.

Telemetry: WAF logs routed to a specific Datadog dashboard.

Rollback Plan: A single Terraform variable toggle (waf_pricing_protect = false) that disables the rule globally within 45 seconds.

3) Validate (The "Save Your Job" Phase)
Because DAVE+R requires "Earned Enforcement," the team deployed the rule strictly in Log-Only (Shadow) Mode for 5 days.

The Discovery: On day 3, log analysis revealed a major issue. One of their biggest partners (BetaCorp) had a misconfigured integration and wasn't sending the required partner headers. If the rule had been enforced immediately, BetaCorp would have been blocked, causing a massive SLA violation.

The Calibration: Because they were in Validate mode, there was no outage. The team contacted BetaCorp to fix their header. In the meantime, they explicitly bypassed BetaCorp's static IP and logged it in the Exception Register with a 30-day expiration date.

4) Execute
With the false positive identified and mitigated, the team had earned the right to enforce the rule.

Controlled Rollout: They flipped the WAF rule from Log-Only to Block Mode via their CI/CD pipeline during a low-traffic window.

The Result: Scraping dropped by 92% immediately. Origin server CPU utilization stabilized. Zero support tickets were filed by legitimate partners because the exception handled the false positives gracefully.

5) Refine
DAVE+R assumes adversaries adapt and systems accrue technical debt. 30 days later, the team executed a routine Refinement sync:

Cleanup: BetaCorp confirmed they had fixed their API headers. The team successfully deleted BetaCorp's IP from the Exception Register, removing technical debt from the WAF.

Tuning: Reviewing the telemetry, the team noticed scrapers had slowed down to 290 requests/minute to evade the 300 req/min rule. Backed by this evidence, the team updated the threshold to 200 requests/minute, logging the data-backed decision in the Refinement Log.

The Outcome: By using DAVE+R, Acme Corp stopped the attack, proved the safety of their changes with telemetry, prevented a self-inflicted outage, and kept their security posture continuously tuned.

---

## What it cost

*Added in v1.1.0. A story that only goes right teaches less than one that shows the price.*

- **Five days of continued 503s to paying enterprise customers** while shadow mode ran. The
  attack did not pause for the validation window. This was almost certainly the right call,
  but v1.0.0 gave the team no way to make it deliberately, which is why v1.1.0 added the
  Triage gate.
- Roughly 20 minutes on the brief, 5 days of daily log review, and a partner conversation
  with BetaCorp that a security team had to own end to end.
- One exception carried for 30 days, and the coordination to actually close it.

## What v1.0.0 did not ask for

Replayed through the v1.1.0 gates, this cycle clears 13 of 40 gates. It was not
badly run. These are things the framework did not require:

- **No triage decision.** 503s were reaching paying customers throughout a 5-day shadow
  window, chosen by default rather than by a signed decision with the daily cost stated.
- **No baseline.** The pre-change scraping volume was never recorded, so "92% reduction"
  cannot be verified against anything.
- **No alternatives considered.** The origin database was the thing falling over. Caching
  the endpoint, requiring authentication, or a per-key quota at the gateway would each have
  addressed the cause rather than the symptom. None appear in the brief, because Define
  started from "which WAF rule".
- **A 0% false positive target.** Not achievable by any statistical control, and never
  actually measured. "Zero support tickets" is a proxy, not a false positive rate.
- **No evasion analysis.** The scrapers dropping to 290 under a 300 limit was entirely
  predictable at design time. One question in Validate would have caught it 30 days earlier.
- **The refinement is a treadmill, not a fix.** Lowering 300 to 200 after observing evasion
  at 290 invites a move to 190. This scenario presents ratcheting as a success, which
  teaches the wrong lesson. The v1.1.0 answer is to escalate the control class: require
  authentication, add a per-key quota, or make the request cost something.
- **The exception is weakly bound and uncovered.** A static IP bypass, with no compensating
  control, no blast radius assessment, and no defined action at expiry.
- **Rollback blast radius.** A single global Terraform toggle, for a problem that only ever
  needed one partner exempted, with nothing stated about what protects the endpoint during
  the rollback window.

See [reference-cycle.md](reference-cycle.md) for this same problem run to the v1.1.0
standard.
