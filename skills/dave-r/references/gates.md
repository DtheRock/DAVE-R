# Gate catalogue

Generated from `spec/gates/` and `spec/adapters/`. Do not edit by hand.

44 core gates across five stages, plus 19 adapter gates.

## Define

### D-0 - no-unfilled-placeholders
`blocking` · define  **(new in spec 1.0.0)**

Found by pointing a live agent at a fresh scaffold. `raci.accountable.identity` of
"TODO" satisfied D-5: it exists, and it does not match the team/group pattern. A cycle
that claims a named accountable human when there is none is the most dangerous false
pass this system can produce, because every later signature gate compares against that
identity. Placeholder text is now rejected wherever it can reach a gate.

**Fix:** Replace every TODO, TBD, [bracketed] and <angled> placeholder with a real value, or with an explicit {provenance: unmeasured} marker so the relevant gate blocks honestly rather than passing on a stub.

### D-1 - scope-is-concrete
`blocking` · define

A control scoped to "the API" cannot be validated. Everything downstream binds to this.

**Fix:** Name the exact host, path or resource, the traffic scope, and enumerate the flows that must not break.

### D-2 - threats-are-observable
`blocking` · define

DAVE+R says define threats "for the asset, not in the abstract". A threat with no
observable signature cannot be measured in shadow mode, so the control protecting
against it can never earn enforcement.

**Fix:** For each threat, state how it appears in telemetry. If you cannot name the signal, you cannot validate the control.

### D-3 - guardrails-are-numeric
`blocking` · define

Prose guardrails are unenforceable. A tolerance of exactly zero is also rejected: no
statistical control can guarantee it, so declaring it guarantees a later argument
instead of a later measurement.

**Fix:** Declare a false positive budget as a fraction (e.g. 0.001) and a latency budget in ms at a stated percentile.

### D-4 - metrics-have-baselines
`blocking` · define

Without a pre-change baseline you cannot separate your control's false positives from
pre-existing failures. Every post-rollout number becomes unfalsifiable.

**Fix:** For each success metric, record the current value and how it was measured, before any change ships.

### D-5 - one-named-accountable-human
`blocking` · define

An agent can draft a rationale, a risk assessment, telemetry links and a rollback plan.
It cannot own the risk. Teams cannot either: shared accountability is no accountability.

**Fix:** Name one person with an identity that resolves to an individual, not a distribution list.

### D-6 - urgency-triaged
`blocking` · define  **(new in spec 1.0.0)**

The lifecycle had no path for an attack already causing damage. Both published DAVE+R
scenarios open mid-incident and then sit in shadow mode for 5 and 7 days, which in the
credential-stuffing case means knowingly absorbing a week of account takeovers. That may
be the right call, but it must be a signed decision rather than a default.

**Fix:** Set the track. If harm is accruing now and you still choose the planned track, the accountable owner must sign that they are accepting the ongoing loss, and you must state the cost per day of not acting.

### D-7 - alternatives-considered
`blocking` · define  **(new in spec 1.0.0)**

Define previously started from "we are adding a control" and never asked whether a
control was the right response. The scraping scenario is the clean illustration: origin
DB CPU spikes on a pricing endpoint, and caching, per-key quotas and requiring auth are
never considered. Without this gate the framework quietly nudges every problem toward
the edge, which undercuts the vendor-neutral claim.

**Fix:** List at least one alternative on a different plane, including any root-cause fix, and say why it was rejected.

### D-8 - non-goals-declared
`advisory` · define

Scope creep during Execute is the most common cause of a blown latency budget.

**Fix:** State what this cycle explicitly does not attempt.

## Architect

### A-1 - every-control-complete
`blocking` · architect

The framework's own minimum. A control missing any of these cannot be operated, only
deployed.

**Fix:** Give every control a named owner, a resolvable telemetry source with at least one metric, and a rollback procedure.

### A-2 - controls-trace-to-threats
`blocking` · architect

A control that addresses no declared threat is either solving a problem nobody wrote
down or is cargo cult. This is the cross-artifact check a human reviewer never does
reliably and an agent does in milliseconds.

**Fix:** Point each control at the threat scenario IDs it mitigates. Add the threat to the brief, or drop the control.

### A-3 - rollback-granularity-declared
`blocking` · architect  **(new in spec 1.0.0)**

Rollback was always described as disabling the control. The scraping scenario rolls back
a global Terraform toggle in 45 seconds for a problem that only needed one partner
exempted. Granularity makes blast radius an explicit design decision.

**Fix:** State whether rollback is global, per-segment, per-rule, or graduated (block -> challenge -> log), and the target time.

### A-4 - degraded-posture-declared
`blocking` · architect  **(new in spec 1.0.0)**

Rollback restores availability and simultaneously restores the abuse. The attack does
not pause while you are rolled back. "Nothing protects us" is an acceptable answer; not
having thought about it is not.

**Fix:** For each control, state what protects the asset during the rollback window.

### A-5 - telemetry-is-resolvable
`blocking` · architect

"Datadog" is not a telemetry source. A gate later has to read this value and prove a
number came from somewhere re-runnable.

**Fix:** Record the system plus the query, dashboard ID or API path. It must be re-runnable by someone else.

### A-6 - trust-boundary-documented
`blocking` · architect

Enforcement plane decisions are only defensible against a stated boundary map. Diagrams
must be committed assets, not external attachment URLs, or a fork of a CC BY licensed
framework inherits broken images and unversioned evidence.

**Fix:** Document zones and flows. Commit any diagram into the repo and reference it relatively.

### A-7 - incremental-rollout-supported
`advisory` · architect

A control that can only ship globally cannot be canaried, which forecloses the Execute
stage's core discipline.

**Fix:** Prefer controls that can be scoped to a segment or stepped down to challenge, rather than binary global toggles.

## Validate

### V-1 - baseline-measured-before-shadow
`blocking` · validate  **(new in spec 1.0.0)**

The original Validate stage measured false positives during shadow but never required a
pre-change baseline. Without one you cannot attribute failures to your control, and the
go/no-go decision rests on an unfalsifiable number.

**Fix:** Measure the current false positive and latency profile before shadow mode starts, from a named source.

### V-2 - shadow-duration-sufficient
`blocking` · validate

Traffic mix differs on weekends, at month end, and during campaigns. A three day shadow
on a consumer flow measures one slice of reality. Adapters set the minimum; the
expedited and emergency tracks may shorten it, which is exactly why D-6 requires that
choice to be signed.

**Fix:** Extend shadow mode to the adapter minimum, or change the triage track and have the accountable owner sign for the shortened window.

### V-3 - false-positives-within-tolerance
`blocking` · validate

The framework's central promise. Enforceable only because D-3 forced a numeric tolerance
and V-1 forced a baseline.

**Fix:** Tune thresholds or add exceptions until the measured rate is inside the declared budget. Do not widen the budget to fit the result without a signed change to the brief.

### V-4 - critical-flows-individually-measured
`blocking` · validate

An aggregate false positive rate hides a flow that is completely broken. If login is 2
percent of traffic and 100 percent broken, the aggregate looks like 2 percent.

**Fix:** Break the false positive measurement down by each critical flow enumerated in the brief.

### V-5 - latency-within-budget
`blocking` · validate

**Fix:** Measure the processing delta at the declared percentile and bring it inside budget.

### V-6 - rollback-tested
`blocking` · validate

An untested rollback is a hope. This is one of the framework's genuinely strong original
ideas; the only change is requiring evidence rather than a checkbox.

**Fix:** Actually execute the rollback in a non-production or canary scope and record the result and elapsed time.

### V-7 - evasion-analysis-complete
`blocking` · validate  **(new in spec 1.0.0)**

Validate measured false positives, latency and rollback, but never whether the control
survives an adversary who adapts. Both published scenarios were then bitten in Refine by
evasion that was obvious at design time: scrapers dropping to 290 under a 300 req/min
limit, attackers spoofing app tokens with emulators. One design-time question would have
caught both.

**Fix:** Name at least three ways to defeat this control, test at least one, and give every bypass a disposition. An accepted bypass needs a named human signature.

### V-8 - threshold-not-on-a-treadmill
`advisory` · validate  **(new in spec 1.0.0)**

If an attacker can operate just under your threshold and still achieve their goal, you
have bought time, not a fix. The scraping scenario ratchets 300 to 200 after observing
evasion at 290; nothing stops a move to 190. Escalate control class instead of tuning.

**Fix:** If an attacker retains more than 75 percent of their throughput just under the threshold, consider a different control class (authentication, per-key quota, cost-based challenge) rather than a lower number.

### V-9 - exceptions-governed
`blocking` · validate  **(new in spec 1.0.0)**

The original register had no compensating control and no blast radius field, which is
how a twelve month WAF bypass on an unauthenticated webhook path gets approved with
quarterly review and nobody notices. It also never defined what happens at expiry, which
is how every register drifts into permanent exceptions.

**Fix:** Every exception needs a compensating control (or an explicit statement that none exists), a blast radius, an expiry with a defined expiry action, a named approver, and it must reference a control that actually exists.

### V-10 - weak-bypass-mechanisms-justified
`blocking` · validate  **(new in spec 1.0.0)**

The bypass mechanism is itself an attack surface. IP allowlists are spoofable where the
origin trusts client IP; an ASN can contain thousands of unrelated hosts on shared cloud
ranges. The credential-stuffing scenario bypasses an aggregator by ASN without flagging
it.

**Fix:** Prefer cryptographic identity, mTLS or a signed header. If you must use IP, ASN, UA or path, justify it and cap the expiry at 180 days.

### V-11 - go-no-go-signed-by-accountable-owner
`blocking` · validate

The single most important guardrail for agent operation. An agent may draft, measure,
check and recommend. Authorising enforcement is a human act, and the signer must be the
person who took accountability in Define.

**Fix:** The accountable owner named in the Definition Brief must personally sign the go decision.

## Execute

### E-1 - staged-rollout-with-abort-criteria
`blocking` · execute

A rollout stage with no abort criterion is not staged, it is just slow. The abort
trigger must be decided before the pressure starts.

**Fix:** Define at least two rollout stages, each with the scope and the metric threshold that halts the rollout.

### E-2 - observability-live-before-enforcement
`blocking` · execute

Enforcing before dashboards and alert routing exist means the first signal of a problem
is a customer. Evidence typing matters here: an agent asserting "dashboards are live" is
worthless, an agent that queried the dashboard API is not.

**Fix:** Confirm dashboards render and alerts route to a live destination, by querying them, before flipping enforcement.

### E-3 - runbook-published
`blocking` · execute

The safe-disable path has to be findable by someone who was not in this cycle, at 3am.

**Fix:** Publish a runbook including the safe-disable path and link it here.

### E-4 - change-record-linked
`blocking` · execute

Auditability end to end is the framework's claim. A change with no record breaks the
chain.

**Fix:** Link the change record, PR or ticket that carries this cycle into production.

### E-5 - rollback-rehearsed
`blocking` · execute

V-6 tested that rollback works. E-5 tests that the people on call have done it recently
enough to do it under pressure. These are different failures.

**Fix:** Rehearse the rollback with the on-call rotation and record the result.

### E-6 - enforcement-authorized-by-human
`blocking` · execute

The hard stop. An agent may prepare everything in this artifact. Flipping enforcement is
a risk-acceptance act reserved to the accountable human, and the signature is
structurally pinned so an agent cannot author it.

**Fix:** The accountable owner must authorize enforcement personally. No agent may write this field.

### E-7 - emergency-changes-backfilled
`blocking` · execute  **(new in spec 1.0.0)**

Module D said emergency changes are documented post-hoc and folded back into the
governed path, in one line, with no mechanism. This gate is that mechanism: an emergency
cycle cannot close until it has been backfilled to the standard of a planned one.

**Fix:** Emergency track buys you a shortened shadow window, not an exemption from evidence. Backfill the baseline, evasion analysis and change record within the adapter's backfill window.

### X-1 - audit-chain-intact
`advisory` · execute  **(new in spec 1.0.0)**

The audit log records what the agent did, and the agent writes it. An agent that skipped
a step could simply not record skipping it. Chaining each entry to its predecessor makes
deletion, reordering and editing detectable after the fact.

**Fix:** Run 'daver chain <cycle>' after each agent action. A broken chain names the entry where it broke.

### X-2 - decisions-cryptographically-signed
`advisory` · execute  **(new in spec 1.0.0)**

'authored_by_agent: false' is a field the agent writes. That is a promise, not a
control. A detached signature over a canonical digest of the decision AND the evidence
it rests on is a control: the agent has no private key, so it cannot produce one. The
digest deliberately covers the guardrails, the baseline and the measured results, so
widening a tolerance or editing a number after the fact invalidates the signature rather
than silently riding on it.

**Fix:** Run 'daver sign-request <cycle> --subject go_no_go', have the accountable owner sign the digest with their own key, and paste the detached signature into the decision block. Add their public key to .daver/allowed_signers.

### X-3 - observed-values-reverifiable
`advisory` · execute  **(new in spec 1.0.0)**

Evidence typing says an observed value must carry a re-runnable source. Nothing re-ran
it. A source string that resolves to nothing looked identical to a real measurement,
which made the whole evidence contract an honour system. This gate re-executes each
source and compares.

**Fix:** Register a resolver for each telemetry system in use, then run 'daver verify <cycle>'. Drift means the world changed or the number was wrong; unresolvable means the source was never real.

## Refine

### R-1 - refinements-are-evidence-backed
`blocking` · refine

"Measurable outcomes over vibes" applied to the stage most prone to vibes. A tuning
change with no cited observation is someone's hunch entering production.

**Fix:** Cite the observation that motivated each refinement, from a named source, and record the impact after.

### R-2 - no-expired-unactioned-exceptions
`blocking` · refine  **(new in spec 1.0.0)**

The register exists to prevent permanent exceptions. Without an expiry sweep it becomes
the thing that documents them instead. This is the check an agent should run on a
schedule, unprompted, forever.

**Fix:** Every exception past its expiry must be retired, or explicitly re-approved with a new expiry and a fresh signature. Silence is not renewal.

### R-3 - complexity-trend-recorded
`blocking` · refine  **(new in spec 1.0.0)**

"The system becomes simpler and/or stronger over time" was an exit criterion with no
measurement. Counting is cheap and makes the claim falsifiable.

**Fix:** Record control count, exception count and mean exception age each review cycle.

### R-4 - evasion-drift-rechecked
`blocking` · refine  **(new in spec 1.0.0)**

Adversaries adapt between cycles. Re-running the evasion analysis on cadence is what
turns Refine from cleanup into defence.

**Fix:** Re-run the evasion analysis at least quarterly and record the date.

### R-5 - escalate-rather-than-ratchet
`blocking` · refine  **(new in spec 1.0.0)**

Three adjustments to the same threshold is the signature of a losing control class. The
published scraping scenario presents ratcheting 300 to 200 as a success; it is a
treadmill, and teaching it as a win teaches the wrong lesson.

**Fix:** After three tunes of the same threshold, stop tuning. Escalate control class: authentication, per-key quota, cost-based challenge, or a different plane entirely.

### R-6 - version-bumped
`blocking` · refine

The framework mandates semver and says changes should be intentional and documented. A
cycle that changed production without a version bump is exactly the drift the framework
warns about, applied to itself.

**Fix:** Bump the version and record the change against it.

### R-7 - dead-controls-retired
`advisory` · refine

Rule bloat is a maintainability tax and an incident risk. Controls and exceptions with
zero observed usage should be candidates for removal.

**Fix:** An exception with no observed usage is dead weight. Retire it.

## Adapter: Module A - Edge and WAF Expansion

### A-A1 - critical-flows-explicitly-exempted-or-tested
`blocking` · a-edge-waf

The most common self-inflicted outage in edge work is a broad rule that catches a
checkout or login path nobody mapped. Enumerating them in Define is only useful if
Validate proves each one was exercised.

**Fix:** Add a safety test per critical flow that exercises the real path end to end.

### A-A2 - rule-naming-convention
`advisory` · a-edge-waf

Modular, named, explainable units scale; mega-rules do not. Naming is what makes a rule
retirable two years later.

**Fix:** Adopt a stable rule ID convention such as WAF-RL-01, BOT-CH-02.

### A-A3 - log-first-progression
`blocking` · a-edge-waf

The module's core discipline, made checkable. Enforcement is reached through log and
simulate, not jumped to.

**Fix:** Run the control in log-only or simulate mode before any enforcing mode.

## Adapter: Module B - Cloud Posture and Connectivity

### B-B1 - least-privilege-verified-not-assumed
`blocking` · b-cloud-posture

Declared least privilege and effective least privilege diverge constantly. The check
must read effective permissions, not the policy document's intent.

**Fix:** Enumerate effective permissions from the provider API and confirm they match intent.

### B-B2 - audit-logging-centralized
`blocking` · b-cloud-posture

Centralized audit logging is a stated default of this module. A control whose plane has
no audit trail cannot be refined, only guessed at.

**Fix:** Confirm control plane audit logs are enabled and shipped to central storage, by querying, before enforcing.

### B-B3 - connectivity-failure-mode-tested
`blocking` · b-cloud-posture

"Connectivity designed for failure and rollback, not optimism." Untested failure modes
in connectivity are how a security change becomes a regional outage.

**Fix:** Test what happens when the new connectivity path fails, not only when it works.

### B-B4 - blast-radius-bounded-by-zone
`advisory` · b-cloud-posture

A posture control that spans every zone has no canary path.

**Fix:** Scope posture controls per zone or account so they can be rolled out and back incrementally.

## Adapter: Module C - Bot and Fraud Defense (Bayesian Extension)

### C-C1 - base-rate-declared
`blocking` · c-bot-fraud  **(new in spec 1.0.0)**

The single most important thing to tell a team building risk scores. If 0.1 percent of
logins are account takeover, a signal that is 95 percent accurate still produces mostly
false positives. Module C described posterior updating without ever requiring the prior,
which is the base rate fallacy waiting to happen at production scale.

**Fix:** Measure the actual prevalence of the abuse in your traffic before choosing thresholds. Derive the expected false positive volume at your candidate threshold and check it against the guardrail.

### C-C2 - signal-independence-assessed
`blocking` · c-bot-fraud  **(new in spec 1.0.0)**

Naive Bayes assumes conditional independence. Bot signals violate it badly: headless
user agent, missing attestation, datacenter ASN and absent cookie almost always travel
together. Multiplying their likelihood ratios produces wildly overconfident scores,
which is the direct cause of the false positive blowups this framework exists to
prevent.

**Fix:** Assign each signal to a correlation group or justify treating it as independent. Down-weight or combine within-group signals rather than summing them.

### C-C3 - calibration-measured-with-named-metric
`blocking` · c-bot-fraud  **(new in spec 1.0.0)**

The framework says "calibrate" repeatedly but never defines what calibrated means or how
you would know. A score is calibrated when items scored 0.9 are abusive 90 percent of
the time. That is measurable; assert it with a number.

**Fix:** Report a Brier score, expected calibration error, or reliability curve from shadow data.

### C-C4 - thresholds-derived-from-distribution
`blocking` · c-bot-fraud  **(new in spec 1.0.0)**

Bands like "under 50 allow, 50 to 89 challenge, over 90 block" appear in the published
scenario with no derivation. Thresholds picked rather than derived encode someone's
intuition about a distribution they have not looked at.

**Fix:** Choose each threshold from the observed shadow score distribution and record the percentile it sits at.

### C-C5 - adverse-action-path-exists
`blocking` · c-bot-fraud  **(new in spec 1.0.0)**

Some legitimate users will be blocked; the guardrail is a budget, not zero. They need a
route back. Beyond the obvious UX harm, automated decisions with legal or significant
effect on EU data subjects carry obligations under GDPR Article 22 including a right to
human review, and the original module was silent on this.

**Fix:** Define how a blocked legitimate user reaches a human, who that human is, and what evidence about the decision is retained so the review can be meaningful.

### C-C6 - feedback-loop-not-self-confirming
`blocking` · c-bot-fraud  **(new in spec 1.0.0)**

The model trains on outcomes the model itself gated. Blocked traffic generates no
labels, so the model becomes progressively more confident about a world it created. An
unGated holdout is the standard defence and it must be deliberate.

**Fix:** Hold out a small unGated or challenge-only sample so you keep observing what the model would have blocked, and use it to detect drift.

### C-C7 - decisions-explainable
`blocking` · c-bot-fraud

The module's own rule, record the strongest evidence factors for each action. Without
it, appeals and incident review are both impossible.

**Fix:** Record the strongest contributing signals alongside every enforcement decision.

### C-C8 - recalibrate-on-traffic-shift
`advisory` · c-bot-fraud

Seasonality, launches and campaigns change the traffic mix, and a threshold calibrated
in October is wrong on Black Friday.

**Fix:** Define the events that force recalibration, not just a fixed schedule.

## Adapter: Module D - Governance and Delivery

### D-D1 - change-has-all-five
`blocking` · d-governance-delivery

The module's own minimum governance requirement, made executable. An agent can produce
four of these five. It can never produce the risk owner.

**Fix:** Every change needs an owner, rationale, risk assessment, telemetry links and a rollback plan.

### D-D2 - emergency-ratio-monitored
`advisory` · d-governance-delivery  **(new in spec 1.0.0)**

An emergency lane is necessary, and it is also the lane that eats governance if nobody
watches its share. A rising emergency ratio means the planned path is too slow, which is
a process defect, not a series of unlucky incidents.

**Fix:** Track the fraction of changes taking the emergency track and review it monthly.

### D-D3 - review-cadence-adhered
`blocking` · d-governance-delivery

Weekly telemetry review, monthly exception review, quarterly architecture review.
Cadence that is not measured does not happen.

**Fix:** Record each review when it happens. A cadence with no evidence of adherence is a plan, not a practice.

### D-D4 - agent-actions-audited
`blocking` · d-governance-delivery  **(new in spec 1.0.0)**

Once an agent participates in the lifecycle, "auditable end to end" has to cover what
the agent did, not only what the humans approved. Every gate run and every artifact
write is appended to the cycle audit trail.

**Fix:** Append every agent action and gate run to the cycle audit log.
