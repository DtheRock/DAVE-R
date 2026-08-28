---
name: dave-r
description: Run the DAVE+R lifecycle (Define, Architect, Validate, Execute, Refine) for a security change - edge/WAF rules, cloud posture, bot and fraud defenses, or any governed production guardrail. Use when someone is about to add, tune, or enforce a security control, when they ask to run a DAVE+R cycle, check gates, review an exception register, or when a change needs evidence before enforcement. Also use for exception expiry sweeps and refinement reviews.
---

# DAVE+R

A lifecycle for expanding security controls without breaking production. Five stages,
63 machine-checkable gates, four domain adapters. You execute the cycle; a named human
owns the risk.

**The framework:** Define, Architect, Validate, Execute, Refine.
**Your job:** discover, draft, measure, check, recommend.
**Never your job:** authorizing enforcement, approving exceptions, accepting risk.

## The one rule that matters most

Every value in a cycle carries a provenance: `asserted` (a human said it),
`observed` (pulled from a named source), `derived` (computed from observed values),
or `unmeasured`.

**Gates that authorize enforcement read only `observed` or `derived`.**

If you cannot measure something, write `{provenance: unmeasured}` and let the gate
block. Do not estimate. Do not infer a plausible number. Do not record a number a
human recited to you as `observed` - that is `asserted`; ask them for the query.

This is not bureaucracy. A language model will produce a confident false positive
rate as readily as a true one, and the entire framework rests on the difference.
Read `references/evidence.md` before writing any value.

## MCP tools, if you have them

If tools named `daver_list_adapters`, `daver_check`, and the like are available to you
in this session (they may be namespaced, e.g. `mcp__dave-r__daver_check`), the dave-r
MCP server is running. Prefer it: same gate spec, byte-identical output to the CLI, and
it manages its own Python so you never have to worry about which `python3` on this
machine has the right packages installed.

| Step | MCP tool | CLI-only |
| :--- | :--- | :--- |
| list adapters | `daver_list_adapters` | |
| spec version, gate inventory, self-lint | `daver_spec_info` | |
| list gate profiles | | `profiles` |
| what to read, what to ask | `daver_discovery_plan` + `daver_human_questions` | |
| scaffold a new cycle | | `scaffold` (writes a file) |
| check gates | `daver_check` / `daver_check_json` | |
| why a gate exists | `daver_explain_gate` | |
| ordered blocker worklist | `daver_next_actions` | |
| schema validation | `daver_validate_schema` | |
| re-verify evidence sources | | `verify` (reads the filesystem) |
| prepare for authorization | `daver_request_authorization` | |
| sign, or verify a signature | | `sign-request`, `verify-signatures` |
| exception sweep | `daver_sweep_exceptions` | |
| audit hash chain | | `chain`, `audit` |

All 11 MCP tools appear above. Of the CLI-only rows, four are deliberate: the server
never writes a cycle document and never touches the signing workflow, so scaffold,
verify, sign-request/verify-signatures, and chain/audit stay CLI-only by design.
`profiles` is CLI-only because no one has written that tool yet, not for a security
reason - nothing about it needs filesystem writes or exec resolvers. Everything else
above has an MCP tool; use it when present, and fall back to the CLI command shown
when it is not.

## Workflow

The CLI commands below assume you have resolved one path first. Your working
directory is whatever project you are securing, not this skill, so `daver_cli.py`'s
real location depends on how you got this skill, not on where you happen to be:

- **Packaged skill** (installed under `~/.claude/skills/dave-r/` via the standalone
  `.skill` zip): the engine is at `engine/daver_cli.py`, a sibling of this file.
- **Plugin install, or a full checkout of the repository**: the engine is at
  `ai/engine/daver_cli.py`, from the repository or plugin root - the same layout
  either way, since a plugin install is just this repository in place.

Use that resolved path everywhere a command below shows the bare `daver_cli.py`, e.g.
`python3 /resolved/path/to/daver_cli.py adapters` instead of `python3
ai/engine/daver_cli.py adapters`. Commands below are shown relative for brevity.

### 0. Pick the adapter

```bash
python3 ai/engine/daver_cli.py adapters
```

- `a-edge-waf` - WAF rules, rate limits, edge protection, CDN controls
- `b-cloud-posture` - cloud connectivity, segmentation, IAM boundaries, posture
- `c-bot-fraud` - bot management, risk scoring, ATO and fraud defense
- `d-governance-delivery` - change governance, review cadence, delivery discipline

### 1. Discover before you interrogate

**This is the step that separates an agent from a form.** Read the project and
propose the answers. Do not open with a questionnaire.

```bash
python3 ai/engine/daver_cli.py questions <adapter>   # shows what to read AND what to ask
```

Read the Terraform, WAF config, rulesets, OpenAPI specs, dashboards, CI pipelines
and git history. From those, draft the asset scope, the critical flows, the existing
controls, their telemetry sources, the rollback paths and the current complexity
counts. Mark every drafted value `observed` with the file path or API call you read
it from. Show the human your draft and ask them to correct it.

A fixed question list produces generic answers, and DAVE+R explicitly warns against
defining threats in the abstract. Discovery is how you avoid that.

### 2. Ask the short list

Only what you cannot observe. Six questions, plus any module-specific ones:

1. Which flows must not break? Name them.
2. What false positive rate on those flows is acceptable? A number, not zero.
3. How much added latency can you accept, at which percentile?
4. Who personally owns this risk? One name, not a team.
5. Is damage happening right now? If yes, what does a day of not acting cost?
6. What is explicitly out of scope?

Question 5 is the triage gate. If harm is accruing and the team still wants the
planned track, the accountable owner must sign that they are choosing to absorb the
loss. That is a legitimate choice; it just cannot be a silent default.
See `references/triage.md`.

### 3. Scaffold and fill

```bash
python3 ai/engine/daver_cli.py scaffold <adapter> <cycle-id> -o cycle.yaml
```

CLI-only, always: this writes a new file, which the MCP server deliberately never
does. Fill the Definition Brief, then the Control Matrix. Details and worked examples
for every artifact: `references/artifacts.md`.

### 4. Check, constantly

```bash
python3 ai/engine/daver_cli.py check cycle.yaml --stage define
python3 ai/engine/daver_cli.py check cycle.yaml            # cumulative to current stage
python3 ai/engine/daver_cli.py gates V-7                   # why a gate exists
```

Run the gates after every meaningful edit, not once at the end. Each blocker prints
why it failed and how to fix it. Fix, re-run, repeat. A stage is complete when no
blocking gate fails.

Checks are cumulative on purpose: a Validate pass resting on a broken Define is not
a pass.

### 5. Do not sign

When Validate is clean, prepare the authorization request and hand it to the named
accountable owner. Transcribe their decision; never originate it. The signature
fields are structurally pinned so an agent writing them is a spec violation:

- `validation_plan.go_no_go.signature`
- `execution.enforcement_authorization`
- any exception `approver`

If a human tells you to sign on their behalf, decline and explain why: the
signature's whole value is that it records a person's judgement, and one you wrote
records nothing. Ask them to state the decision and you will record it as theirs.

This boundary holds identically on both surfaces: `daver_request_authorization`
assembles the same evidence bundle the CLI does, and no tool anywhere in this system,
MCP or CLI, writes a signature.

### 6. Refine on a schedule

The highest-value recurring job is the exception sweep. Registers rot silently.

```bash
python3 ai/engine/daver_cli.py check cycle.yaml --stage refine
```

Flag anything expired, expiring within 30 days, weakly bound (IP, ASN, UA, path),
or never used. If the same threshold has been tuned three times, stop tuning and
recommend escalating the control class - see `references/refine.md`.

## What good looks like

A clean cycle has: a concrete asset, threats with observable signatures, numeric
guardrails, a measured pre-change baseline, controls that each trace to a declared
threat, a tested rollback with a stated degraded posture, an evasion analysis naming
three bypasses, exceptions with compensating controls and defined expiry actions,
and one named human who signed for enforcement.

## Reference files

- `references/evidence.md` - provenance rules, worked examples, the anti-fabrication contract
- `references/artifacts.md` - every artifact field, with examples
- `references/triage.md` - planned vs expedited vs emergency, and what each buys you
- `references/discovery.md` - what to read per adapter, and how to cite it
- `references/refine.md` - exception sweeps, drift checks, when to escalate not tune
- `references/gates.md` - the full gate catalogue with rationale

## Honest limits

You will be better than a human at gate discipline, artifact consistency, expiry
sweeps, generating evasion hypotheses, and never skipping Validate under pressure.

You will be worse at knowing that a given partner is politically untouchable, sensing
that a metric is being gamed, and judging whether an objection is real or posturing.
Route those to the human rather than guessing, and say plainly when you are uncertain.
