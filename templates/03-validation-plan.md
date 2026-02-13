# DAVE+R Validation Plan

**Initiative / Change Name:** [Name]  
**Validation Window:** [Start Date] to [End Date]  

## 1. Shadow / Log-Only Mode Plan
* **Duration:** [e.g., minimum 7 days to capture weekend/weekday traffic patterns]
* **Monitoring Focus:** Identify legitimate user-agents, IPs, or partner flows caught by the proposed rule.
* **Review Cadence:** Daily review of shadow logs by [Owner].

## 2. Testing Scenarios (Active Validation)
| Scenario | Test Method | Expected Outcome | Pass/Fail |
| :--- | :--- | :--- | :--- |
| **Abuse Test** | Scripted curl barrage (200 req/sec) from AWS test node. | Rule triggers, flags IP as 'Would Block'. | [ ] |
| **Safety Test** | Normal browser flow via staging environment. | Passes cleanly, no challenge logged. | [ ] |
| **Bypass Test** | Hit endpoint with known Partner IP. | Request bypasses rate limit (Exception works). | [ ] |
| **Rollback Test** | Revert rule via CI/CD pipeline. | Rule disables within 3 minutes. | [ ] |

## 3. Threshold Calibration
* **Initial Hypothesis:** [e.g., Block if bot score > 80]
* **Shadow Mode Finding:** [e.g., Score > 80 catches 5% of legitimate mobile users due to carrier CGNAT]
* **Adjusted Threshold:** [e.g., Enforce block at score > 90, send silent CAPTCHA for 80-89]

## 4. Go / No-Go Decision
* [ ] False positive rate is measured and within tolerance.
* [ ] Required exceptions have been documented and approved.
* [ ] Support team is briefed and runbook is published.
* [ ] Rollback was successfully tested.
* **Approval to Execute:** [Sign-off from Accountable Owner]
