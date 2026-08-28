# Changelog

All notable changes to the DAVE+R Framework. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project uses [semantic versioning](https://semver.org/) as defined in the framework's
own Versioning section.

---

## [1.1.3] - 2026-08-28

A second-round audit of 1.1.2 itself (re-verifying the visitor-path fixes rather than
trusting them) found that one of them was wrong. Fixed here; no other changes.

### Fixed

- **The 1.1.2 fix for the MCP install broke it a different way (high).** Pointing
  `ai/INSTALL.md` and `ai/mcp/README.md` at `pip install --require-hashes -r
  ai/mcp/requirements.txt` does install cleanly - but only on the one platform that
  file's hashes were resolved for (linux/x86_64, CPython 3.11, matching CI). On any
  other Python version or OS - a real Mac included - `--require-hashes` correctly
  refuses the install, because a different platform legitimately needs different
  wheels for `cffi`, `pydantic-core`, `rpds-py` and others, with different hashes. Pip
  reports this the same way it would report actual tampering, which is worse than the
  1.1.2 bug it replaced: that one failed everywhere and looked broken, this one fails
  on most platforms and, because the new CI step runs exactly ubuntu-latest + CPython
  3.11, looks green regardless. Both docs now give the portable, unpinned command
  (`pip install pyyaml "mcp<2" jsonschema referencing`); the hash-pinned file stays
  CI-only, with a header explaining why it must not be used as a human install command.
- **`ai/INSTALL.md` and `ai/README.md` said 122 tests (low).** The 1.1.2 commit that
  corrected the prior "84 tests" also added a test, without updating the number again.
  Actual is 123 (122 pass, 1 skips without `mcp` installed).

### Verification

The portable command installs clean, and the server it produces enumerates all 11
tools, on real Python 3.11, 3.12 and 3.13 (previously only 3.11 was ever exercised).
The hash-pinned CI file is unchanged apart from its header comment and still installs
identically under `--require-hashes`. 123 tests collected, 122 pass + 1 skip; spec
lint clean; no regressions.

## [1.1.2] - 2026-08-28

Fixes from a visitor-path audit: a fresh clone, in a clean container, with no prior
knowledge, walking the CLI, the skill and the MCP server exactly as documented. The
engine itself was sound; everything found was packaging or documentation that breaks
the experience described in `ai/INSTALL.md`. No spec, gate, schema or lifecycle changes:
every 1.1.1 cycle document remains valid.

### Fixed

- **The documented MCP server install cannot start (critical).** `pip install mcp
  pyyaml` resolves to mcp 2.x today, which renamed `FastMCP` to `MCPServer`; `server.py`
  imports the old name and the process dies before serving anything. The MCP server had
  no CI coverage at all, which is why this went unseen. Added `ai/mcp/requirements.txt`,
  hash-pinned like `ai/requirements-ci.txt`, pinning `mcp` below 2.0, and a CI step that
  installs it and asserts the server enumerates its 11 tools.
- **The skill's own commands assume a working directory it will never have (high).**
  Every command in `SKILL.md`, packaged and in-place alike, was a bare relative path to
  `daver_cli.py`. An installed skill runs with the agent's working directory set to
  whatever project it is securing, not this repository, so every command failed. `SKILL.md`
  now opens the Workflow section by having the agent resolve the real path first.
- **The packaged `.skill` names an install mechanism that does not exist (high).**
  `ai/INSTALL.md` said "Install `dist/dave-r.skill` in Claude Code or Cowork"; neither
  product installs a zip that way, and Cowork does not read the directory the fix below
  writes to. Corrected to the actual unpack step for Claude Code, and scoped the claim:
  Cowork is not supported until this ships as a plugin.
- **`DAVER_WORKSPACE` failed open (medium).** Unset, the MCP server silently adopted the
  process's working directory as the boundary confining cycle paths, resolver reads and
  the trust anchor, contradicting this repo's own fail-closed posture. The server now
  refuses to start without an explicit `DAVER_WORKSPACE`.
- **Stale path in `ai/mcp/README.md` (low).** Its example config pointed at
  `dave-r-ai/mcp/server.py`, a directory that does not exist; `ai/INSTALL.md`'s copy was
  already correct. Also fixed a second, previously unnoticed stale relative path in the
  same file's CI example. Both now match.
- **Version and count drift (low).** `README.md` said v1.1.0 while the spec and
  `CHANGELOG.md` had already moved to 1.1.1; `ai/INSTALL.md` and `ai/README.md` both
  still said 84 tests against an actual 122. No git tags existed at all, so nothing could
  be pinned or checked out; this release is the first tagged one.

### Verification

Fresh-clone conditions, empirically: real `pip install --require-hashes` against the new
`ai/mcp/requirements.txt` on a clean venv; the real MCP server started, refused to start
without `DAVER_WORKSPACE`, and enumerated its 11 tools; the packaged skill, unpacked and
invoked from an unrelated project directory with the resolved path, ran correctly, and
the original bare-relative form was reconfirmed broken from the same directory first. 122
tests pass (123 including the new MCP-gated test, which skips without `mcp` installed);
spec lint clean.

## [1.1.1] - 2026-08-28

Security fixes from an adversarial review of v1.1.0. No lifecycle or artifact changes:
every v1.1.0 cycle document remains valid.

The review's central observation is the one that reorders everything else. v1.1.0's threat
model was written for one deployment (your agent, your gates, your workspace) and then
shipped as an open-source tool that strangers install and point at code they have not
vetted. That moves the victim, and it makes the **defaults** the security policy: you
cannot instruct every downstream user, and almost none will read the threat model.

### Fixed

- **Remote code execution in the default install (critical).** Running the gates on an
  untrusted document executed commands from that document's directory. `.daver/resolvers.json`
  was read from the working directory, so it travelled inside the repository under
  examination, and the "argv list, not a shell string" defence did not hold, because an
  argv list whose first element is a shell is a shell. `exec` resolvers are now **not
  registered by default** (`DAVER_ENABLE_EXEC=1` or `--allow-exec-resolvers` to opt in),
  `argv[0]` is allowlisted against interpreters, and inline-code flags are refused.
- **The documented MCP boundary did not bound the layer doing the work (critical).**
  `DAVER_WORKSPACE` confined cycle paths while the resolver layer read `DAVER_EVIDENCE_ROOT`,
  defaulting to the process working directory, so pinning the documented boundary bought
  nothing. There is now one boundary, supplied by the caller, applied to cycle paths,
  resolver reads and the trust anchor alike. The MCP server refuses to start with exec
  resolvers enabled.
- **An agent could forge a human sign-off (critical).** X-2 rests on the agent having no
  private key, but the trust anchor resolved inside the workspace the agent operates in,
  and `.gitignore` excluded it so no committed copy existed to compare against. The anchor
  now resolves from operator space and one inside the audited workspace is refused.
- **Evidence laundering at two hops (high).** `derived_from` was checked one hop deep, so
  `asserted → derived → derived` reached an enforcement gate as valid evidence. The
  derivation graph is now walked to its roots with a visited set; unresolvable and
  parentless derivations fail too.
- **X-3 reported a clean pass having verified nothing (high).** `check:` gates could not
  express "not applicable", so the evidence gate went green for every consumer with no
  telemetry resolvers registered, which is everyone on first run. Checks can now report
  applicability, and `agent-operated` promotes X-3 to blocking. It distinguishes a source
  a resolver ran and could not find (a fabrication signal, always blocking) from a
  telemetry system with no registered resolver (an operator gap, reported as not
  applicable). Only `regulated` treats the second as a failure, so adopting
  `agent-operated` does not require standing up a telemetry backend first.
- **A misspelled reference root became a passing gate (high).** An unrecognised root was
  returned as a string literal, so `exists` and `ne` both passed. `lint()` now dry-runs
  every gate's references and fails the build, which also gives third-party adapter
  authors a conformance check they did not have.
- **The signature covered less than claimed (medium).** The signed subject took only
  `len(bypasses)` and a list of exception ids, so a signed cycle could be rewritten while
  the signature stayed valid: bypass dispositions flipped, exception scope and expiry
  changed, control enforcement modes altered, the audit log deleted. It now signs digests
  of whole sub-documents plus the audit chain head, and carries a `subject_version` so old
  signatures fail loudly. Signing the chain head also closes, for signed cycles, the
  tamper-and-re-chain risk the threat model documented as residual.
- **Symlinks walked out of the containment root (medium).** Both checks used `abspath`,
  which normalises `..` but follows symlinks. Now `realpath`, with symlinks refused.
- **CI failed on every push to main (medium).** The gate loop skipped the scenario fixtures
  but not the fixtures directory, so it gated `reference.cycle.yaml` under `agent-operated`,
  which it can never satisfy. A permanently red required check teaches people to merge past
  red. The loop now skips the whole fixtures directory, and a separate step asserts the
  fixture still behaves as documented.
- **Unpinned CI dependencies (medium).** Actions are pinned to commit SHAs and Python
  dependencies to hashes in `ai/requirements-ci.txt`, since the job's output *is* the
  security control.
- **Unbounded regex over agent-written strings (medium).** `matches` truncates its subject.

### Changed

- The CI template ships with `DAVER_ENABLE_EXEC: '0'` set explicitly rather than merely
  absent, and a header explaining that the `pull_request` trigger is load-bearing, that
  `pull_request_target` and secrets are unsafe here, and why.
- `THREAT-MODEL.md` gains T-13 (consumers copy the CI template) and corrects four claims
  that were false under the distribution model, in place rather than by deletion.
- `ai/mcp/README.md` no longer claims a posture the code did not have.
- 33 regression tests added, one per finding, each written to fail on v1.1.0.

---

## [1.1.0] - 2026-08-28

The framework was written for humans and worked. Expressing it in a form an agent could
execute exposed nine places where a requirement was implicit, and an implicit requirement
is one a machine cannot check and a tired human skips at 2am. This release makes them
explicit. It also adds the machine-executable layer itself.

MINOR, not MAJOR: the five stages are unchanged, and Triage is a gate at the front of
Define rather than a sixth stage. Cycles run under v1.0.0 remain valid; they will simply
be missing artifacts that v1.1.0 requires.

### Added

- **Triage gate (stage 0).** Planned, expedited and emergency tracks, each with its own
  shadow window, approval level and backfill obligation. v1.0.0 had no path for an attack
  already causing damage: both published scenarios opened mid-incident and then ran 5 and
  7 day shadow windows, which in the credential-stuffing case meant absorbing a week of
  account takeovers by default rather than by decision.
- **Alternatives considered, in Define.** At least one option on a different enforcement
  plane, including any root-cause fix, with the reason it was rejected. Without this the
  framework quietly pushed every problem toward the edge, which undercut the vendor-neutral
  claim.
- **Measured baselines, in Define.** Every success metric carries a value measured before
  anything ships. Without a baseline you cannot separate a control's false positives from
  pre-existing failures, and every post-rollout number becomes unfalsifiable.
- **Observable signature, per threat scenario.** If you cannot say how a threat appears in
  telemetry, you cannot validate the control that addresses it.
- **Rollback granularity and degraded posture, in Architect.** Rollback restores
  availability and simultaneously restores the abuse. Every control now states what
  defends the asset during the rollback window.
- **Evasion analysis, in Validate.** Three named bypasses, one tested, each with a
  disposition. Both published scenarios were bitten in Refine by evasion that was
  predictable at design time: scrapers dropping to 290 under a 300 req/min limit, attackers
  spoofing app tokens with emulators.
- **Exception governance.** Compensating control, blast radius, and a defined expiry action
  (`auto-revoke`, `escalate`, `block-change`, `review-required`; deliberately no
  `auto-extend`). Undefined expiry behaviour is how every register drifts into permanent
  exceptions.
- **Bypass mechanism strength ordering, in Module A.** Cryptographic identity, mTLS, signed
  header, API key, IP, ASN. The last two require written justification and a shortened
  expiry: IP allowlists are spoofable wherever the origin trusts a client-supplied address,
  and an ASN can contain thousands of unrelated hosts.
- **Statistical obligations, in Module C.** State the prior, group correlated signals,
  define and measure calibration, derive thresholds from the observed distribution, provide
  an adverse action path, keep an unGated holdout. This was the most differentiated section
  of the framework and the thinnest.
- **Escalate rather than ratchet, in Refine.** Three adjustments to the same threshold
  signals a losing control class. Change the class, not the number.
- **Complexity trend, in Refine.** Control count, exception count, mean exception age. The
  framework claimed the system gets simpler over time; counting is what makes that
  falsifiable.
- **Abort criteria per rollout stage, in Execute.** A stage with no abort criterion is not
  staged, it is just slow.
- **The `ai/` layer.** Vendor-neutral spec (JSON schemas, 44 core gates, 4 adapters,
  19 adapter gates, an agent contract), a reference gate engine and CLI, an MCP server,
  an agent skill, conformance evals, and a threat model.
- **Committed diagram assets** under `assets/`, replacing external attachment URLs that a
  fork or clone could not carry.

### Changed

- Scenario files renamed from `scenario1.md` / `scenario2.md` to descriptive names and
  moved under `scenarios/`, with an index.
- Both scenarios gained a "what it cost" section and an honest account of what v1.0.0
  missed in each. They previously read as unqualified wins, which experienced practitioners
  correctly discount.
- README rewritten. It had claimed the core document was a PDF and that templates and
  worked examples were "planned for a future release", months after both shipped.
- Templates updated to match the stages, including the new required fields.

### Fixed

- **Placeholder values could satisfy gates.** A fresh `daver scaffold` emitted
  `raci.accountable.identity: "TODO"`, which passed D-5: it exists and does not match the
  team/group pattern. A cycle claiming a named accountable owner when there is none is the
  worst false pass the system can produce, since every signature gate compares against that
  identity. New gate D-0 rejects placeholder text anywhere it can reach a gate. Found by
  running a live agent against the eval workspace.
- **Gates that held vacuously were reported as passes.** A gate iterating an empty
  collection returned a pass, so an empty exception register read as "exceptions are
  governed". The engine now separates **passed** from **not applicable**, and the report
  lists the latter with the words "not evidence of safety". Also found by the live run.
- **Licensing contradiction.** The framework recommended reserving commercial repackaging
  for written permission, while the applied licence (CC BY 4.0) already grants it
  irrevocably. The recommendation was removed rather than left to create an expectation the
  licence does not support. The enforceable part, that attribution does not imply
  endorsement, is retained and stated plainly.
- Version drift. Templates and scenarios shipped in February 2026 without a version bump,
  in a framework whose own Versioning section requires changes to be intentional and
  documented. This changelog exists so that does not recur.

---

## [1.0.0] - 2025-12-14

Initial public reference.

### Added

- The five-stage lifecycle: Define, Architect, Validate, Execute, Refine, each with intent,
  key activities, core outputs and exit criteria.
- Core principles.
- Module A (Edge and WAF Expansion), Module B (Cloud Posture and Connectivity),
  Module C (Bot and Fraud Defense, Bayesian Extension), Module D (Governance and Delivery).
- Metrics that define success, across security effectiveness, business safety and
  operational quality.
- Five starter templates.
- CC BY 4.0 licence.

[1.1.1]: https://github.com/DtheRock/DAVE-R/releases/tag/v1.1.1
[1.1.0]: https://github.com/DtheRock/DAVE-R/releases/tag/v1.1.0
[1.0.0]: https://github.com/DtheRock/DAVE-R/releases/tag/v1.0.0
