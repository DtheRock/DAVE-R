# DAVE+R AI layer

Makes the [DAVE+R framework](https://github.com/DtheRock/DAVE-R) executable by an agent
without letting the agent decide anything it should not.

**Define → Architect → Validate → Execute → Refine**, expressed as 63 machine-checkable
gates over five typed artifacts, with four domain adapters.

## Why this exists

The framework was written for humans and is good. Handing it to an agent unchanged
fails in a specific way: a language model will produce a confident false positive rate
as readily as a true one, and DAVE+R's entire premise is "measurable outcomes over
vibes." So the central mechanism here is not the gates. It is **evidence typing**.

Every value carries a provenance: `asserted` (a human said it), `observed` (pulled from
a named, re-runnable source), `derived` (computed from observed values), or
`unmeasured`. Gates that authorize enforcement read only `observed` or `derived`. An
agent that cannot measure must block, not estimate.

## Layout

```
spec/              vendor-neutral, the normative layer
  AGENTS.md          the contract any agent framework implements
  evidence.md        provenance rules (normative)
  schemas/           JSON Schema for the 5 artifacts + cycle container
  gates/             44 core gates, declarative YAML
  adapters/          Modules A-D, 19 additional gates
engine/            reference executor + CLI (pyyaml only)
  daver/             ~700 lines: refs, evidence, evaluator, runner
  tests/             84 tests, incl. both published scenarios as fixtures
mcp/               MCP server, 11 tools, read-only, cannot authorize
skills/dave-r/     agent skill: discovery-first orchestration
```

Gates live in `spec/` as **data**. The skill and the MCP server both execute the same
files, so the two consumers cannot drift apart.

## Quick start

Dependencies: Python 3.9+ and **PyYAML**. That is all the engine, CLI and skill
need. See [INSTALL.md](INSTALL.md) for the MCP server and the optional extras.

```bash
python3 engine/daver_cli.py adapters                      # what modules exist
python3 engine/daver_cli.py questions a-edge-waf          # what to read, what to ask
python3 engine/daver_cli.py scaffold a-edge-waf my-change -o cycle.yaml
python3 engine/daver_cli.py check cycle.yaml              # gates, with fixes
python3 engine/daver_cli.py gates V-7                     # why a gate exists
```

## The three hard boundaries

An agent may draft, discover, measure, check and recommend. It may never:

1. Write `validation_plan.go_no_go.signature`
2. Write `execution.enforcement_authorization`
3. Approve, extend, or widen any exception or guardrail

These are risk-acceptance acts. The signature's whole value is that it records a
person's judgement; one an agent wrote records nothing.

## What the gates found in the published scenarios

Both scenarios from the DAVE+R repo are encoded as test fixtures, faithfully: only what
the published text states, with silence encoded as absence.

| | scenario1 (AI scrapers) | scenario2 (credential stuffing) |
| :--- | :--- | :--- |
| Gates passed | 13 / 40 | 16 / 45 |
| Blocking | 21 | 23 |

Caught unprompted, among others: no pre-change baseline, no evasion analysis (both
scenarios are then bitten by evasion in Refine that was predictable at design time), an
exception with no compensating control, an IP and an ASN bypass with no justification,
a 0% false positive target that no statistical control can meet, and in scenario2 the
whole Bayesian rigor set - posterior updating described without ever stating the prior,
correlated bot signals treated as independent, "calibrate" used repeatedly but never
defined or measured, score bands picked rather than derived, no appeal path, no holdout.

`engine/tests/fixtures/reference.cycle.yaml` is the same scraping problem run properly.
It clears all 43 blocking gates and still raises two honest advisories: the rate limit
really does leak 97% of attacker throughput just under the threshold (V-8), and the
decisions are recorded but not cryptographically signed (X-2).

## Relationship to the framework

The AI layer requires things framework v1.0.0 does not, because a machine-checkable gate
forces them:

- A triage track (planned / expedited / emergency), closing the gap where the lifecycle
  had no path for an attack already causing damage
- A measured pre-change baseline
- An evasion analysis in Validate
- Compensating control, blast radius and expiry action on every exception
- Rollback granularity and a degraded posture
- Alternatives considered, so the framework stops nudging every problem toward the edge
- Base rate, signal independence, calibration metric, appeal path and holdout for Module C

These are proposed as framework v1.1.0, not just spec details. The spec and the
framework should move together.

## License

Inherits CC BY 4.0 from the DAVE+R framework. Attribution: DAVE+R Framework by
Demetrios Petropoulos.
