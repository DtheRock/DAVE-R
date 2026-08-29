# Evidence Typing (normative)

The single rule that keeps an agent-run DAVE+R cycle honest.

Every value in a DAVE+R artifact carries a `provenance`. Gates that authorize
enforcement may only read values whose provenance is `observed` or `derived`.
An agent that cannot observe a required value MUST emit `unmeasured` and block
the gate. It is never permitted to estimate, infer from priors, or fill a
plausible number.

## The three provenances

| Provenance | Meaning | Required companions |
| :--- | :--- | :--- |
| `asserted` | A human stated it. Judgement, policy, risk acceptance, business context. | `asserted_by` (a resolvable human identity), `asserted_at` |
| `observed` | Pulled from a named system. Measurement. | `source` (system + query/dashboard/file ref), `observed_at` |
| `derived` | Computed from other values in this cycle. | `derived_from` (list of refs), `method` (the expression used) |

A fourth marker, `unmeasured`, is not a provenance. It is the explicit absence
of a required value, and it always blocks the gate that needs it - whether the
missing value is evidence a gate could not observe, or a guardrail a human has
not yet committed to (D-3's `latency_budget_ms` and `false_positive_tolerance`
are the common case). Blocking on `unmeasured` is not a lesser failure than
blocking on a missing field; it is the honest version of the same block, and
the `note` companion is where the agent records what it tried.

## Why the split exists

DAVE+R's core principle is "measurable outcomes over vibes." Under human
operation that principle is enforced socially: a colleague asks where a number
came from. Under agent operation there is no colleague, and a language model
will produce a confident false positive rate as readily as a true one. The
provenance field moves that check from social to structural.

## What may be asserted

Judgement calls only. Guardrails, tolerances, risk acceptance, ownership,
non-goals, business impact, triage track, and sign-off. These are the things a
human is *supposed* to decide, and an agent must never author them on a human's
behalf. An agent may still draft a proposed value and ask the human to confirm,
adjust, or reject it, the same discover-then-confirm pattern used for observed
values - proposing is not authoring, provided what gets recorded is the human's
actual answer, `asserted_by` them.

## What may never be asserted

Anything a gate uses to decide whether enforcement is earned: baseline rates,
shadow-mode false positive rates, latency deltas, rollback test outcomes,
attack volumes, exception usage, calibration scores. If it appears in a
Validate or Execute gate as a measured quantity, `asserted` is rejected.

## Derived values

`derived` exists so that computed quantities (a rate from a numerator and
denominator, a delta from before and after) are not laundered into `observed`.
A derived value is only as good as its inputs: the engine walks `derived_from`
to its **roots**, with a visited set for cycles, and rejects any derived value that
roots in an `asserted` or `unmeasured` input where `observed` was required. A
`derived_from` naming a path that does not resolve is also rejected, because a
derivation that cannot name its parents is not a derivation.

*(Through 1.1.0 this walk went one hop only, so `asserted → derived → derived`
laundered cleanly. Fixed in 1.1.1.)*

## Agent obligations

1. Never write `observed` without a resolvable `source` and a real timestamp.
2. Never convert `unmeasured` to a value without re-querying the source.
3. When a human supplies a number verbally, record it `asserted`, not `observed`,
   even if they say they read it off a dashboard. Ask for the query.
4. Surface every `unmeasured` field in the cycle status before proposing to
   advance a stage.
5. A guardrail a human cannot yet commit to is not a reason to stall: draft a
   proposed value from whatever they do know and ask them to confirm it; if
   they still cannot, mark it `unmeasured` with a `note` on what was tried, say
   plainly which gates stay blocked because of it, and keep working on
   whatever the cycle does not need it for. Do not ask the same question on a
   loop. See the worked example below.

---

## Worked examples for an agent

**Wrong.** The human says "our false positive rate is about 0.1 percent."
```yaml
false_positive_rate: { value: 0.001, provenance: observed, source: { system: datadog, ref: "dashboard" } }
```
They recited a number. You did not observe it, and "dashboard" is not re-runnable.

**Right.**
```yaml
false_positive_rate: { value: 0.001, provenance: asserted, asserted_by: "d.petropoulos@example.com",
                       asserted_at: "2026-08-28T10:00:00Z",
                       note: "Recalled from memory. Needs measurement before V-3." }
```
Then go and measure it. An asserted value will block V-3, which is correct.

**Right, after measuring.**
```yaml
false_positive_rate:
  value: 0.0008
  provenance: observed
  observed_at: "2026-08-28T11:20:00Z"
  source:
    system: datadog
    ref: "sum:waf.blocked{flow:checkout,legitimate:true}/sum:waf.requests{flow:checkout}"
    window: 7d
```

**When you cannot measure at all.**
```yaml
latency_delta_ms: { provenance: unmeasured, note: "No p95 instrumentation on this path yet." }
```
V-5 blocks. That is the system working. Tell the human what instrumentation is
missing rather than producing a number.

**A guardrail the human cannot commit to.** They said "I am not sure," then
"calculate it yourself," when asked for a latency budget.

`latency_budget_ms` is a guardrail, not evidence (see "What may be asserted") -
so unlike a measured quantity, you are allowed to draft a number for them to
confirm. Anchor the draft on whatever they do know rather than picking one out
of the air:

1. Ask what they would notice: "if this got slower, at what point would you or
   your users notice or complain?"
2. Ask about their current baseline, even roughly: "how fast do these endpoints
   respond today?" If they do not know that either, say so - it changes what a
   responsible number even is.
3. Propose one, with the reasoning attached, and ask them to confirm, adjust,
   or reject it explicitly:
   ```yaml
   latency_budget_ms:
     value: 150
     provenance: asserted
     asserted_by: "d.petropoulos@example.com"
     asserted_at: "2026-08-29T09:00:00Z"
     note: "Proposed by the agent as roughly 15 percent of the site's typical
            ~1000ms page response (owner's rough recollection, unmeasured);
            owner confirmed 150ms as acceptable at p95 without independently
            verifying the baseline."
   ```
   The `note` is what makes this defensible later: a reviewer sees it was
   reasoned and confirmed, not invented.
4. If they still will not or cannot commit, do not keep asking:
   ```yaml
   latency_budget_ms:
     provenance: unmeasured
     note: "Owner has no latency baseline and declined to set a number as of
            2026-08-29 ('calculate it yourself'). Proposed 150ms (see above);
            no response yet. Revisit before Validate."
   ```
   Tell them plainly, once: D-3 blocks, which means V-5 and go/no-go block
   with it, until this is set. Then keep working on everything else the cycle
   does not need it for. That is the gate working honestly, not the cycle
   stalling.

**Evidence laundering, which the engine rejects.**
```yaml
guess:    { value: 0.5, provenance: asserted, asserted_by: someone }
fp_rate:  { value: 0.5, provenance: derived, derived_from: [module.guess], method: passthrough }
```
`derived` does not upgrade an assertion. The engine walks `derived_from` to its
roots and fails the gate with "evidence laundering", at any depth.

## The contract

You may draft anything. You may measure anything you have access to. You may
recommend anything. You may not manufacture evidence, and you may not sign.
