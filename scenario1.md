📖 DAVE+R In Action: Mitigating AI Scrapers Without Breaking the Business
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
