# DAVE+R MCP server

11 tools, any MCP client.

## Install

```bash
pip install mcp pyyaml jsonschema referencing
```

Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "dave-r": {
      "command": "python3",
      "args": ["/absolute/path/to/dave-r-ai/mcp/server.py"],
      "env": {
        "DAVER_WORKSPACE": "/absolute/path/to/your/cycles",
        "DAVER_SPEC": "/absolute/path/to/dave-r-ai/spec"
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

- **Read-only with respect to production.** Never reaches a WAF, cloud API, or
  deployment pipeline. It reads and checks documents.
- **Cannot authorize enforcement.** No tool writes an approval signature.
  `daver_request_authorization` prepares what a named human must sign, out of band.
- **Path traversal rejected.** Cycle paths resolve inside `DAVER_WORKSPACE` only.
- **Fails closed.** A malformed or unknown gate expression evaluates to FAIL. A gate
  that errors open is worse than no gate.

## CI

```bash
python3 engine/daver_cli.py check cycle.yaml --json
# exit 0 = no blocking gates, exit 1 = blocked
```
