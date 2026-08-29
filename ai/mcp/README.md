# DAVE+R MCP server

11 tools, any MCP client.

## Install

The plugin at the repo root ([`.claude-plugin/`](../../.claude-plugin/), see
[`ai/INSTALL.md`](../INSTALL.md) §2) wires this server up automatically, picking a
`python3` with the right packages at launch time via `ai/mcp/launch.py`. What follows is
for wiring it up by hand instead.

```bash
pip install pyyaml "mcp<2" jsonschema referencing
```

`mcp<2` matters: mcp 2.x renamed `FastMCP` to `MCPServer` and this server has not been
migrated; a bare `pip install mcp` installs 2.x today. `jsonschema` and `referencing`
are for `daver_validate_schema`. `pyyaml` comes from the CLI requirement.

CI installs the same packages hash-pinned for reproducibility instead:
`pip install --require-hashes -r ai/mcp/requirements.txt`, resolved for exactly one
platform (linux/x86_64, CPython 3.11). That file is not a portable install command -
a different platform or Python version legitimately needs different wheels, and
`--require-hashes` correctly refuses to substitute them - which is why it isn't what's
given above.

Claude Desktop / Claude Code config:

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

`DAVER_WORKSPACE` is an allowlist root. Cycle paths arrive as untrusted tool input, so
they are resolved inside it and traversal is rejected.

## Tools

| Tool | Purpose |
| :--- | :--- |
| `daver_list_adapters` | Modules available and what each covers |
| `daver_discovery_plan` | What to read before asking a human |
| `daver_human_questions` | The short irreducible question set |
| `daver_check` | Run gates, rendered report |
| `daver_check_json` | Same, machine-readable, for CI |
| `daver_next_actions` | Ordered worklist of blockers with fixes |
| `daver_explain_gate` | Why a gate exists and how to satisfy it |
| `daver_validate_schema` | Structural validation against the JSON Schemas |
| `daver_sweep_exceptions` | Expiry, weak binding, missing compensating control, unused |
| `daver_request_authorization` | Assemble the evidence a human must sign. Cannot sign. |
| `daver_spec_info` | Version, gate inventory, self-lint |

## Security posture

- **Executes no commands.** Exec resolvers are never enabled here, and the server
  **refuses to start** if the environment tries to turn them on. A tool surface driven
  by a language model acting on content it discovered is the last place to accept a
  config-file-to-`subprocess` path.
- **Reaches no production system.** No WAF, no cloud API, no deployment pipeline. It
  reads and checks documents.
- **Cannot authorize enforcement.** No tool writes an approval signature.
  `daver_request_authorization` prepares what a named human must sign, out of band.
- **One boundary.** `DAVER_WORKSPACE` confines cycle paths, resolver file reads and the
  signature trust anchor alike, via `realpath`; traversal and symlinks are both refused.
- **Fails closed.** A malformed or unknown gate expression evaluates to FAIL. A gate
  that errors open is worse than no gate.

> **Corrected in 1.1.1.** Earlier versions of this file claimed the server was
> "read-only with respect to production" while `daver_check` could execute arbitrary
> local commands, and claimed `DAVER_WORKSPACE` confined the server while the resolver
> layer read a different variable defaulting to the process working directory. Both
> claims were false. The behaviour now matches the description.

## CI

```bash
python3 ai/engine/daver_cli.py check cycle.yaml --json
# exit 0 = no blocking gates, exit 1 = blocked
```
