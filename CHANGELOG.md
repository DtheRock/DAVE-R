# Changelog

All notable changes to the DAVE+R Framework. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project uses [semantic versioning](https://semver.org/) as defined in the framework's
own Versioning section.

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

[1.1.0]: https://github.com/DtheRock/DAVE-R/releases/tag/v1.1.0
[1.0.0]: https://github.com/DtheRock/DAVE-R/releases/tag/v1.0.0
