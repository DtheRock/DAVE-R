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
