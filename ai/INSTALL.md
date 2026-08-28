# Install and run

Three independent ways to use this. **You do not need all of them.** They share the spec
in `spec/`; none of them depends on the others.

| You want | Use | Needs |
| :--- | :--- | :--- |
| Run gates from a terminal or CI | the CLI | Python 3.9+, `pyyaml` |
| An agent to run the lifecycle in Claude Code or Cowork | the skill | same as CLI |
| Any MCP client to call the lifecycle as tools | the MCP server | CLI deps + `mcp` |

## Dependencies, precisely

The engine imports only the standard library plus **PyYAML**. That is the whole
requirement for gates, evidence typing, the audit chain, signatures, resolvers and the
evals.

```bash
pip install pyyaml
python3 ai/engine/daver_cli.py check my-cycle.yaml
```

Optional, and only for the feature named:

| Package | Needed for | Without it |
| :--- | :--- | :--- |
| `mcp` | the MCP server | server will not start; CLI and skill unaffected |
| `jsonschema` + `referencing` | `daver_validate_schema` (MCP) | that one tool reports it is unavailable; gates unaffected |
| `pytest` | running the test suite | tests do not run; nothing else affected |
| `ssh-keygen` | detached signatures (gate X-2) | X-2 reports unsigned. Ships with macOS and Linux. |

There are no network calls anywhere in the engine, the CLI or the skill. The MCP server
speaks stdio to its client and reaches nothing else. The shipped resolvers read local
files and run operator-declared commands; no telemetry resolver ships enabled.

## 1. CLI only

```bash
pip install pyyaml
python3 ai/engine/daver_cli.py adapters
python3 ai/engine/daver_cli.py questions a-edge-waf
python3 ai/engine/daver_cli.py scaffold a-edge-waf my-change -o cycle.yaml
python3 ai/engine/daver_cli.py check cycle.yaml
```

Exit code 0 means no blocking gate failed; 1 means blocked. That is what CI uses.

## 2. As a skill (Claude Code, Cowork)

Build a self-contained skill package. It bundles its own copy of `spec/` and the engine,
so it runs with no checkout of this repo:

```bash
bash ai/skills/package.sh          # writes dist/dave-r.skill
```

Install `dist/dave-r.skill` in Claude Code or Cowork, then ask for a DAVE+R cycle in
plain language. The skill shells out to the bundled CLI, so `pyyaml` still needs to be
importable by whatever Python the environment uses.

Using it in place from a checkout works too: point the agent at `ai/skills/dave-r/SKILL.md`.

## 3. As an MCP server

```bash
pip install mcp pyyaml            # add jsonschema referencing for schema validation
```

```json
{
  "mcpServers": {
    "dave-r": {
      "command": "python3",
      "args": ["/absolute/path/to/DAVE-R/ai/mcp/server.py"],
      "env": {
        "DAVER_WORKSPACE": "/absolute/path/to/your/cycles",
        "DAVER_SPEC": "/absolute/path/to/DAVE-R/ai/spec"
      }
    }
  }
}
```

Works with any MCP client. `DAVER_WORKSPACE` is an allowlist root: cycle paths arrive as
untrusted tool input, so they are resolved inside it and traversal is rejected.

## Skill or MCP server, which?

Neither requires the other, and running both is fine but redundant.

- **Skill**: the agent reads your project, drafts the artifacts, and runs the gates by
  calling the CLI. Best when the agent has filesystem access to the repo you are securing.
  This is the richer experience, because discovery is most of the value.
- **MCP server**: exposes the lifecycle as 11 typed tools to any MCP client. Best when the
  client has no shell, when several clients or people share one cycle store, or when you
  want the tool boundary to be the security boundary.

Both execute the same gate files from `spec/`, so a cycle checked by one is checked
identically by the other.

## Environment variables

| Variable | Used by | Meaning |
| :--- | :--- | :--- |
| `DAVER_SPEC` | all | path to `spec/`; defaults to the copy next to the engine |
| `DAVER_WORKSPACE` | MCP server | allowlist root for cycle documents |
| `DAVER_EVIDENCE_ROOT` | resolvers, signatures | root for `file`/`exec` resolvers and `.daver/allowed_signers` |

## Verify your install

```bash
python3 ai/engine/daver_cli.py lint                                    # spec self-check
python3 ai/engine/daver_cli.py check ai/engine/tests/fixtures/reference.cycle.yaml --stage refine
pip install pytest && python3 -m pytest ai/engine/tests -q             # 84 tests
bash ai/examples/signing/demo.sh                                       # needs ssh-keygen
```

The reference cycle should report `CAN ADVANCE`. The two scenario fixtures should report
`BLOCKED`; that is intentional, they are the published v1.0.0 examples replayed against
v1.1.0 gates.
