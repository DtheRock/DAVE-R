📖 DAVE+R In Action: Defeating Credential Stuffing Without Killing Conversion
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
