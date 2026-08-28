# DAVE+R Validation Plan

**Initiative / Change Name:** [Name]  
**Validation Window:** [Start Date] to [End Date]  
**Triage Track:** [Planned | Expedited | Emergency] → shadow minimum [from module]

## 0. Baseline
*New in v1.1. Measured BEFORE shadow mode starts. Without it, every post-rollout number is unfalsifiable.*

| Measure | Value | Source | Measured at |
| :--- | :--- | :--- | :--- |
| False positive rate | [e.g., 0.0004] | [query] | [timestamp, before shadow.start] |
| Latency p95 | [e.g., 42ms] | [query] | [...] |
| Error rate | [...] | [...] | [...] |
| Attack volume | [...] | [...] | [...] |

## 1. Shadow / Log-Only Mode Plan
* **Duration:** [module minimum for this track; note if it spans a full weekly cycle]
* **Monitoring Focus:** Identify legitimate user-agents, IPs, or partner flows caught by the proposed rule.
* **Review Cadence:** [Daily / twice daily during an expedited window] by [Owner].
* **Findings:** [what shadow mode caught, and what you did about each]

## 2. Testing Scenarios
*One safety test per critical flow enumerated in the Definition Brief.*

| Scenario | Kind | Method | Expected Outcome | Covers flow | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Abuse | abuse | [e.g., Replay captured crawler traffic at 400 req/min] | Challenge at 200, block at 400 | | [ ] |
| Safety | safety | [e.g., Signed partner request, all 5 partners] | Passes cleanly | partner-pull | [ ] |
| Safety | safety | [e.g., Anonymous page load, 500 concurrent] | Passes cleanly | web-page | [ ] |
| Bypass | bypass | [e.g., Request with exception credential] | Bypasses, logged as exception hit | | [ ] |
| Rollback | rollback | [e.g., graduated rollback in canary scope] | Each step within target | | [ ] |

## 3. Evasion Analysis
*New in v1.1. Name at least three ways to defeat this control. Test at least one.*

| # | Bypass | Cost to attacker | Tested? | Disposition | Rationale / who accepted |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | [e.g., Slow the crawl to just under the threshold] | trivial | Yes | mitigated | [e.g., paired with challenge at threshold, not a pass] |
| 2 | [e.g., Distribute across many residential IPs] | moderate | Yes | mitigated | [e.g., catalogue-coverage-per-session signal added] |
| 3 | [e.g., Obtain a legitimate partner signature] | high | No | accepted | [Named signature required for any accepted bypass] |

* **Threshold evasion margin:** [how much of their goal does an attacker retain just under the
  threshold? If most of it, you have bought time, not built a fix — consider escalating the
  control class instead of lowering the number.]

## 4. Threshold Calibration
* **Initial Hypothesis:** [e.g., Cap at 300 req/min based on a prior incident]
* **Shadow Mode Finding:** [e.g., p99.5 of legitimate sessions peaks at 140 req/min]
* **Adjusted Threshold:** [e.g., Challenge at 200, block at 400]
* **Derived from:** [the percentile this sits at in the observed distribution — not picked]

## 5. Measured Results
| Measure | Value | Guardrail | Within? |
| :--- | :--- | :--- | :--- |
| False positive rate, overall | [...] | [...] | [ ] |
| FP rate, [critical flow 1] | [...] | [...] | [ ] |
| FP rate, [critical flow 2] | [...] | [...] | [ ] |
| Latency delta | [...] | [...] | [ ] |
| Rollback tested | [...] | | [ ] |

> An aggregate FP rate hides a broken flow. If login is 2% of traffic and 100% broken,
> the aggregate reads 2%.

## 6. Go / No-Go Decision
* [ ] Baseline was measured before shadow mode began.
* [ ] False positive rate is within tolerance, per critical flow.
* [ ] Performance impact is measured and acceptable.
* [ ] Rollback was successfully tested.
* [ ] Evasion analysis complete; known trivial bypasses mitigated or accepted in writing.
* [ ] Required exceptions documented and approved.
* [ ] Support team briefed and runbook published.
* **Approval to Execute:** [Signed by the accountable individual named in the Definition Brief]
