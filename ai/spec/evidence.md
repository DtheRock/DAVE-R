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
   loop. See the skill's `references/evidence.md` for the full protocol and a
   worked example.
