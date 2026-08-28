# DAVE+R Definition Brief

**Initiative / Change Name:** [e.g., Block AI Scrapers on Pricing API]  
**Date:** YYYY-MM-DD  |  **Primary Owner:** [Name/Team]  
**Status:** [Draft | Approved | Active | Closed]  

## 0. Triage
*New in v1.1. Decide how much evidence this change can afford to wait for, before gathering it.*
* **Harm accruing right now?** [Yes / No — from telemetry, not from the room's mood]
* **Cost of a day of not acting:** [e.g., ~$6,500/day in SLA credits] *(required if harm is accruing)*
* **Track:** [Planned | Expedited | Emergency]
* **Justification:** [Why this track]
* **If harm is accruing and you chose Planned:** the accountable owner signs below that they
  are accepting the ongoing loss.
  * Accepted by: [Name] on [Date]

## 1. Asset(s) & Scope
*What are we protecting? Be specific.*
* **Target Asset:** [e.g., `api.example.com/v2/pricing/live`]
* **Traffic Scope:** [e.g., Global edge traffic, unauthenticated endpoints only]
* **Critical Flows** *(enumerate them; Validate tests and measures each one individually)*
  1. [ID] [Description] — impact if broken: [e.g., SLA breach across 5 contracts]
  2. [ID] [Description] — impact if broken: [...]

## 2. Threat & Abuse Scenarios
*What specific behaviors are we trying to stop? Avoid abstract threats.*

| ID | Behaviour | Observable signature *(v1.1: how it appears in telemetry)* |
| :--- | :--- | :--- |
| THR-001 | [e.g., Distributed volumetric scraping from residential proxies] | [e.g., >5 req/s unauthenticated, near-uniform inter-arrival, no Referer, full catalogue coverage in <1h] |
| THR-002 | [...] | [...] |

> If you cannot name the signal, you cannot validate the control.

## 3. Constraints & Guardrails
*What MUST NOT break? Express as numbers.*
* **False Positive Tolerance:** [e.g., 0.001] — *not zero; no statistical control can guarantee it*
* **Latency Limit:** [e.g., +15ms at p95]
* **Business Guardrail:** [e.g., Legitimate B2B partners on legacy integrations must not be blocked]
  * Measured by: [system + query/dashboard reference]

## 4. Alternatives Considered
*New in v1.1. Is a control the right response, or should the underlying cause be fixed?*

| Option | Plane | Addresses root cause? | Rejected because |
| :--- | :--- | :--- | :--- |
| [e.g., Cache the endpoint at edge, 30s TTL] | edge | Yes | [e.g., Partners contractually require <5s freshness] |
| [e.g., Require authentication] | identity | Yes | [e.g., Public pricing page depends on anonymous access; tracked as PLAT-4412] |

## 5. Success Metrics & Non-Goals
*How do we know this worked?*

| ID | Metric | Baseline *(measured BEFORE anything ships)* | Target | Measured by |
| :--- | :--- | :--- | :--- | :--- |
| SM-1 | [e.g., Unauthenticated scraping volume] | [e.g., 4.2M req/day, 14d window] | [e.g., 840k req/day] | [source] |
| SM-2 | [...] | [...] | [...] | [...] |

* **Non-Goals:** [e.g., We are not attempting to stop manual, human copy-pasting in this iteration.]

## 6. RACI & Escalation
* **Accountable (owns the risk):** [ONE named individual. A team is not an owner.]
* **Responsible (builds it):** [Engineer/Team doing the work]
* **Consulted:** [e.g., Partner Integration Team, App Dev]
* **Informed:** [e.g., Customer Support, NOC]
* **Emergency Escalation Path:** [Slack channel / PagerDuty service]
