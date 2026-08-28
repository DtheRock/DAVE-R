# Discovery: read first, ask second

The difference between an agent and a form.

## Principle

A fixed questionnaire produces generic answers, and DAVE+R's own Define stage warns
against defining threats "in the abstract." So do not open with questions. Read the
project, draft the artifact, show your work, and ask the human to correct it.

Target: six human questions instead of forty, and they are the six only a human can
answer.

## What you can almost always infer

| Field | Where it comes from |
| :--- | :--- |
| `asset.target` | OpenAPI specs, route definitions, ingress config, existing WAF rule scopes |
| `asset.critical_flows` | Auth routes, checkout paths, endpoints with the highest revenue attribution, anything with an SLA in the repo |
| Existing controls | Terraform, ruleset JSON, provider API listings |
| `telemetry.source` | Dashboard definitions, monitor config, existing alert routes |
| `rollback.procedure` | Terraform variables, feature flags, CI pipeline revert paths |
| `rollback.target_seconds` | Git history: how long past reverts actually took |
| `complexity_trend.*` | Count live rules and exceptions via the provider API |
| Prior incidents | Git revert history, incident tickets, postmortems in the repo |

Cite every inference. `source: {system: terraform, ref: "modules/waf/main.tf:L42"}`
makes your draft checkable; an uncited claim makes it a guess with good posture.

## What you must never infer

Judgement, risk acceptance and business context. Specifically:

- False positive tolerance and latency budget. These are business decisions about
  acceptable harm, not technical facts.
- Who is accountable. You can find who commits to a repo. You cannot find who is
  willing to own an outage.
- Whether harm is currently tolerable.
- Non-goals.
- Any signature.

If a human is unavailable and you need one of these, stop and say so. Do not proceed
with a placeholder, and do not pick a "reasonable default" for a risk tolerance.

## Per adapter

Run `daver questions <adapter>` for the machine-readable list. Summary:

**a-edge-waf** - Terraform and WAF config for existing rules, limits and rollback
toggles; provider API for live rules, current enforcement mode and block volume;
OpenAPI or route files for the endpoint inventory and which paths are unauthenticated;
git history for rule change history and revert timings.

**b-cloud-posture** - IaC for network zones, security groups, IAM roles and public
resources; provider API for live topology, effective permissions and audit log
coverage; policy files for guardrails and existing exceptions. Effective permissions
matter more than declared ones and must be read, not assumed.

**c-bot-fraud** - bot management API for the current score distribution, live
thresholds, challenge and solve rates; the warehouse for label history and the
confirmed abuse base rate; risk and scoring code for signal weights and threshold
config. The base rate is the single most important thing to find, and it is almost
always available in the warehouse.

**d-governance-delivery** - VCS for change history, revert rate and review coverage;
ticketing for change records and approval chains; on-call config for escalation paths.

## When discovery is impossible

No repo access, no API credentials, a greenfield project. Then you do fall back to
asking - but ask concretely, one artifact at a time, and say why you are asking rather
than reading. Never present a long form up front.
