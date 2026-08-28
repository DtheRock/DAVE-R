# DAVE+R Control Matrix

**System/Domain:** [e.g., Edge WAF Profiles]  
**Last Updated:** YYYY-MM-DD  

## Trust boundary
* **Zones:** [e.g., internet → edge → api-gateway → origin → pricing-db]
* **Where authentication begins:** [e.g., at the API gateway]
* **Diagram:** [relative path to a committed asset, e.g. `assets/trust-boundary.svg`]

## Controls

| Control ID | Intent | Addresses | Plane | Owner | Telemetry | Enforcement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `WAF-RL-01` | Cap unauth requests to the pricing endpoint | THR-001 | Edge (WAF) | @m.silva | Datadog `dashboard/waf-pricing-01` | graduated |
| `API-QT-01` | Enforce contracted per-partner ceiling | THR-002 | Application | @m.silva | Datadog `dashboard/api-quota-01` | block |

> Every control must trace to at least one threat scenario in the Definition Brief.
> A control that addresses nothing written down is solving an unrecorded problem.

## Rollback
*New fields in v1.1: granularity and degraded posture.*

| Control ID | Procedure | Granularity | Target | Degraded posture *(what defends the asset while rolled back)* |
| :--- | :--- | :--- | :--- | :--- |
| `WAF-RL-01` | Terraform `waf_pricing_mode`: block → challenge → log | graduated | 90s | Per-key quota `API-QT-01` remains; emergency 60s edge cache engages above 90% origin CPU |
| `API-QT-01` | Set quota enforcement flag false per partner key | rule | 30s | Contractual limits unenforced; overage billed retroactively per contract 7.3 |

> Rollback restores availability and restores the abuse. The attack does not pause.
> "Nothing protects us" is an acceptable answer. Not having considered it is not.

## Policy tiers
* **Baseline:** [controls applied everywhere]
* **Overlays:** [name] applies to [scope] → [controls]
