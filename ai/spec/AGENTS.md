# Running DAVE+R as an agent

Vendor-neutral contract. Any agent framework can implement this; the skill and the MCP
server in this repo are two reference implementations of exactly these rules.

## What this spec provides

| Layer | File | Purpose |
| :--- | :--- | :--- |
| Artifact structure | `schemas/*.json` | JSON Schema for the five DAVE+R artifacts and the cycle container |
| Evidence contract | `evidence.md` | Provenance typing. Normative. The anti-fabrication rule. |
| Gates | `gates/*.yaml` | 40 declarative pass/fail assertions across the five stages |
| Adapters | `adapters/*.yaml` | Per-domain planes, telemetry, signals, shadow minimums, 19 extra gates |

Gates are **data, not code**. Any executor that implements the operator set below runs
the identical gate set, which is what stops two consumers from drifting apart.

## The agent contract

**1. Discover before you interrogate.** Read the project's own configuration and
propose the artifact. Ask a human only what cannot be observed. Each adapter's
`discovery` block lists what to read (`sources`), what you may infer (`infers`), and
what you must ask (`must_ask_human`).

**2. Evidence typing is absolute.** Gates that authorize enforcement read only
`observed` or `derived`. If you cannot measure, write `unmeasured` and let the gate
block. Never estimate, never launder an assertion through `derived`.

**3. You may not sign.** Three fields are reserved to a named human:
`validation_plan.go_no_go.signature`, `execution.enforcement_authorization`, and every
exception `approver`. Each carries `authored_by_agent: false`, pinned by schema. An
agent writing `true` is a spec violation; an agent writing the field at all is a
governance failure.

**4. Gates are cumulative.** A Validate pass resting on a broken Define is not a pass.
Run every stage up to and including the current one.

**5. Everything is audited.** Append each agent action and gate run to `cycle.audit`.
"Auditable end to end" has to cover what the agent did, not only what humans approved.

## Operator set

An executor must implement these to run the gate files.

| Operator | Form | Meaning |
| :--- | :--- | :--- |
| `exists` | `ref` | Resolves, is non-empty, and is not `unmeasured` |
| `min_items` | `[ref, n]` | List has at least n entries |
| `lookup_exists` | `[map_ref, key_ref]` | Map contains the key |
| `eq` `ne` `lt` `lte` `gt` `gte` | `[a, b]` | Compare, with numeric and date coercion |
| `same` | `[a, b]` | Resolved values are identical |
| `before` | `[a, b]` | a is a timestamp strictly before b |
| `in` | `[ref, [values]]` | Value is a member |
| `matches` | `[ref, regex]` | String matches |
| `provenance_in` | `[ref, [provenances]]` | Evidence rule. Also verifies `observed` has a re-runnable source, and that `derived` does not root in an assertion. |
| `all` `any` | `[exprs]` | Conjunction, disjunction |
| `not` | `expr` | Negation |
| `implies` | `[cond, then]` | Vacuously true when cond is false |
| `each` | `{in, satisfies}` | Every item satisfies; `item.` binds the element |
| `each_any` | `{in, satisfies}` | At least one item satisfies |
| `any_in` | `{collection, where}` | At least one element matches; `outer.` binds the enclosing item |
| `refs_resolve` | `[list_ref, collection_ref, id_field]` | Cross-artifact integrity |

Special references: `$now`, `$now+Nd`, `$now-Nd`, and `$adapter.<key>` (where
`min_shadow_days` resolves through the cycle's declared triage track).

**A malformed or unknown expression must evaluate to FAIL, never to pass.** A gate that
errors open is worse than no gate, because it reports safety it did not check.

## Minimum viable executor

Roughly 300 lines. `engine/daver/expr.py` is a complete reference implementation under
a permissive license, dependency-light (pyyaml only for loading).

## Interop

The Control Matrix maps onto OSCAL component definitions and the Exception Register
onto POA&M items, for anyone needing to feed a federal or regulated compliance pipeline.
DAVE+R is a change lifecycle rather than a control catalogue, so it sits alongside
OSCAL rather than on top of it.

## Conformance

An implementation conforms if it: executes all gate files unmodified, enforces the
evidence contract, refuses to author the three signature fields, runs cumulatively, and
fails closed on malformed expressions. Verify against
`engine/tests/fixtures/reference.cycle.yaml`, which must pass every blocking gate, and
the two scenario fixtures, which must not.
