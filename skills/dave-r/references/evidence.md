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
of evidence, and it is always a gate blocker where evidence is required.

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
behalf.

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
