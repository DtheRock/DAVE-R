# 📖 DAVE+R In Action: Defeating Credential Stuffing Without Killing Conversion

**Module C (Bot and Fraud Defense, Bayesian Extension).** Written against framework v1.0.0,
and reproduced here exactly as published.

---

The Scenario:
GlobalRetail Corp is facing a massive "credential stuffing" Account Takeover (ATO) attack on their /api/v2/login endpoint just weeks before a major holiday sale. Attackers are using millions of rotating residential proxies to test stolen passwords, successfully draining customer loyalty accounts.

The Conflict:
The Security team wants to deploy a strict WAF rule to hard-block any IP with failed login spikes. The VP of E-Commerce vetoes the change immediately: "Millions of our legitimate mobile customers share those exact same IP addresses via CGNAT, and others use Apple iCloud Private Relay. If you block those IPs, you kill our daily active users (DAU) and flood our call center."

Trapped between an active attack and a business freeze, the teams use the DAVE+R lifecycle to break the deadlock using data.

1) Define (Aligning Security and Business)
Instead of arguing over WAF rules, Security and E-Commerce co-author a Definition Brief.

Target Asset: /api/v2/login (Web and Mobile).

The Guardrail (Critical): The baseline login conversion rate must not drop. Legitimate users on shared IPs or privacy relays must not be hard-blocked.

Success Metric: 95% reduction in successful ATOs, with a false-positive rate under 0.1% on critical flows.

2) Architect (Designing for Nuance)
Because a blunt binary rule ("Block bad IPs") violates the guardrails, the team leverages Module C (Bot and Fraud Defense) to design a Bayesian probabilistic control.

The Logic: Instead of a single decisive signal, they calculate a Risk Score. The prior baseline (a residential IP) is updated with observed signals (missing mobile app attestation token, impossible travel velocity, headless browser user-agent).

Graduated Mitigations:

Low Risk (< 50): Allow cleanly.

Medium Risk (50-89): Step-up to Email/SMS MFA challenge.

High Risk (> 90): Hard block at the Edge WAF.

3) Validate (The "Save the Business" Phase)
DAVE+R mandates "Earned Enforcement." The team deploys the new Bayesian scoring engine strictly in Log-Only (Shadow) Mode for 7 days to gather production evidence.

The Discovery: On Day 3, the telemetry reveals a hidden disaster. A major personal finance aggregator (like Mint/Plaid) is programmatically logging into the platform thousands of times an hour on behalf of real users. They lack the mobile app token and look exactly like the attackers. If Security had rushed to enforce their initial rule, they would have completely severed integrations for 250,000 customers.

The Calibration: Because they caught this in Validate mode, there is no outage. The team identifies the aggregator's backend ASNs, adds them to the Exception Register with a 6-month expiration date, and recalibrates the Bayesian weights. The shadow false-positive rate drops to a safe 0.04%.

4) Execute (Governed Deployment)
With the B2B FinTech false positive safely bypassed and the E-Commerce team reassured by the shadow telemetry, Security has mathematically earned the right to enforce the rule.

Controlled Rollout: They switch the policy from Log-Only to Enforce Mode, starting with 5% of traffic and monitoring conversion metrics closely before scaling to 100%.

The Result: The ATO attack hits a brick wall of MFA challenges and blocks. ATOs drop by 98%. Most importantly, because mobile users and the B2B aggregator were accounted for, the customer support queue remains completely quiet. Product and Security celebrate a joint win.

5) Refine (Adapting to the Adversary)
DAVE+R assumes attackers will adapt and technical debt must be managed.

The Pivot: Two weeks later, attackers realize they are blocked and switch to a "low-and-slow" attack using outdated mobile emulators to spoof the missing app tokens.

The Tuning: During a routine telemetry review, the team spots the drift. They don't panic or rewrite the system. They simply add a new signal (Emulator Screen Resolution Profiling) to the Bayesian risk engine, log the tweak in the Refinement Log, and seamlessly push v1.1.

Retiring Debt: Six months later, the aggregator exception in the register expires. Because it was tracked and governed, the team successfully migrates the aggregator to secure OAuth API keys and deletes the legacy IP exception, making the system simpler and more secure than before.

---

## What it cost

*Added in v1.1.0.*

- **Seven days of continued account takeovers** while shadow mode ran. Customer loyalty
  balances were being drained throughout. Protecting conversion was a defensible priority,
  but the cost was real and nobody wrote it down.
- Two weeks later, a successful adversary pivot that required a further engineering cycle.
- Six months of an ASN-scoped bypass, plus the commercial work to migrate the aggregator
  to OAuth.
- A cross-functional negotiation between Security and E-Commerce that only worked because
  someone senior forced both into the same document.

## What v1.0.0 did not ask for

Replayed through the v1.1.0 gates, this cycle clears 16 of 45 gates. Seven of
the eight Module C gates block, which is why v1.1.0 rewrote that module's statistical
requirements.

- **No triage decision.** Accounts were being drained for seven days by default. With the
  daily loss quantified, the team might still have chosen the same window, or might have
  enforced the top risk band immediately while calibrating the rest. v1.0.0 offered no way
  to have that conversation.
- **The prior is never stated.** The whole module is posterior updating, and the base rate
  of ATO in the login population appears nowhere. At a 0.1% base rate, a 95%-accurate
  signal still produces overwhelmingly more false positives than true ones. That arithmetic
  decides whether the thresholds are safe, and it was never done.
- **Correlated signals treated as independent.** Missing app attestation, headless
  user-agent and emulator profile almost always travel together. Combining them as
  independent evidence produces a score far more confident than the data supports, which is
  precisely the mechanism that generates the false positive blowups the cycle was trying to
  avoid.
- **"Calibrate" is never defined or measured.** The word appears repeatedly. No Brier score,
  no reliability curve, no expected calibration error. A score is calibrated when sessions
  scored 0.9 are abusive about 90% of the time, and that is a number you can report.
- **Thresholds picked, not derived.** 50 and 90 arrive with no explanation of what
  percentile of the observed distribution they sit at.
- **No adverse action path.** Users blocked at score > 90 have no described route to a
  human. With a 0.1% false positive budget on a login endpoint at retail scale, that is a
  large number of real customers locked out with nowhere to go, and in several jurisdictions
  it carries review obligations besides.
- **No holdout.** The model trains on outcomes the model gated. Blocked traffic generates no
  labels, so confidence rises about a world the model created. The emulator pivot was found
  by a human noticing drift; a holdout would have surfaced it sooner.
- **No evasion analysis.** Spoofing a missing app token was foreseeable. It was found in
  production, two weeks after enforcement.
- **The exception is ASN-scoped.** An ASN can cover thousands of unrelated hosts on shared
  cloud ranges. Nothing in the scenario acknowledges the breadth of what was trusted, and
  there is no compensating control.

To be clear about what went right: the shadow window caught the aggregator, the graduated
response was the correct architecture, and the exception was actually retired on schedule
with the underlying integration fixed. That last part is rarer than it should be.
