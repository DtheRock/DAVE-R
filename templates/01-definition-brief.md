# DAVE+R Definition Brief

**Initiative / Change Name:** [e.g., Block AI Scrapers on Pricing API]  
**Date:** YYYY-MM-DD  |  **Primary Owner:** [Name/Team]  
**Status:** [Draft | Approved | Active | Closed]  

## 1. Asset(s) & Scope
*What are we protecting? Be specific.*
* **Target Asset:** [e.g., `api.example.com/v2/pricing`]
* **Traffic Scope:** [e.g., Global edge traffic, unauthenticated endpoints only]

## 2. Threat & Abuse Scenarios
*What specific behaviors are we trying to stop? (Avoid abstract threats)*
1. [e.g., Distributed volumetric scraping originating from residential proxies.]
2. [e.g., Competitors pulling real-time inventory faster than 10 req/second.]

## 3. Constraints & Guardrails
*What MUST NOT break? What are the hard operational limits?*
* **Business Guardrail:** [e.g., Legitimate B2B partners using legacy integrations must not be blocked.]
* **Latency Limit:** [e.g., Edge WAF processing time must not increase by more than 5ms at p95.]
* **False Positive Tolerance:** [e.g., < 0.1% on critical conversion flows.]

## 4. Success Metrics & Non-Goals
*How do we know this worked?*
* **Security KPI:** [e.g., 80% reduction in origin `HTTP 429` (Rate Limit) errors.]
* **Business KPI:** [e.g., 30% reduction in Edge bandwidth egress costs.]
* **Non-Goal:** [e.g., We are not attempting to stop manual, human copy-pasting in this iteration.]

## 5. RACI & Escalation
* **Responsible (Builds it):** [Engineer/Team doing the work]
* **Accountable (Owns the risk):** [Manager/Director approving the rollout]
* **Consulted:** [e.g., Partner Integration Team, App Dev]
* **Informed:** [e.g., Customer Support, NOC]
* **Emergency Escalation Path:** [Slack channel / PagerDuty service]
