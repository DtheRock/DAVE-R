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
speaks stdio to its client and reaches nothing else.

### Resolvers that run commands

Only the `file` resolver is registered by default. The `exec` resolver runs commands
declared in `.daver/resolvers.json` **inside the evidence root**, which means inside the
repository you are examining. It is therefore **off unless you turn it on**:

```bash
python3 ai/engine/daver_cli.py verify cycle.yaml --allow-exec-resolvers   # or DAVER_ENABLE_EXEC=1
```

Do not enable it against a repository you have not vetted. Even enabled, `argv[0]` is
allowlisted against interpreters, so `["/bin/sh","-c", …]` and `["python3","-c", …]` are
refused: an argv list whose first element is a shell is still a shell. Point a resolver at
a purpose-built binary or a committed script. The MCP server refuses to start with exec
resolvers enabled at all.

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

`dist/dave-r.skill` is a zip, not something either product opens directly. In Claude
Code, unpack it into the skills directory it reads from:

```bash
mkdir -p ~/.claude/skills && unzip -o dist/dave-r.skill -d ~/.claude/skills/
```

That gives you `~/.claude/skills/dave-r/`, picked up on the next session. The skill
shells out to the bundled CLI, so `pyyaml` still needs to be importable by whatever
Python the environment uses.

Cowork does not read `~/.claude/skills/`. Cowork sessions load skills enabled on the
claude.ai account, synced at session start and managed from Customize in the desktop
sidebar or skills settings on claude.ai, not from a file you unpack yourself. Until this
skill ships as a Cowork plugin, the packaged-skill path above is for Claude Code only.

Using it in place from a checkout works too, in either product: point the agent at
`ai/skills/dave-r/SKILL.md`.

## 3. As an MCP server

```bash
pip install pyyaml "mcp<2" jsonschema referencing
```

`mcp<2` matters: mcp 2.x renamed `FastMCP` to `MCPServer`, `ai/mcp/server.py` has not
been migrated, and a bare `pip install mcp` installs 2.x today. `jsonschema` and
`referencing` are for `daver_validate_schema`.

CI installs the same packages hash-pinned for reproducibility, the way
`ai/requirements-ci.txt` is: `pip install --require-hashes -r ai/mcp/requirements.txt`.
That file is resolved for exactly one platform (linux/x86_64, CPython 3.11); it is not
a portable install command, which is why the command above doesn't use it - a
different platform or Python version legitimately needs different wheels, and
`--require-hashes` (correctly) refuses to substitute them.

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
  client has no shell, or when several clients or people share one cycle store. It never
  enables exec resolvers, and `DAVER_WORKSPACE` confines cycle paths, resolver reads and
  the trust anchor alike.

Both execute the same gate files from `spec/`, so a cycle checked by one is checked
identically by the other.

## Environment variables

| Variable | Used by | Meaning |
| :--- | :--- | :--- |
| `DAVER_SPEC` | all | path to `spec/`; defaults to the copy next to the engine |
| `DAVER_WORKSPACE` | MCP server | allowlist root for cycle documents |
| `DAVER_EVIDENCE_ROOT` | resolvers | fallback containment root when a caller passes none. Prefer `--evidence-root`. |
| `DAVER_ENABLE_EXEC` | resolvers | set to `1` to enable command-running resolvers. Off by default. |
| `DAVER_ALLOWED_SIGNERS` | signatures | trust anchor path. Refused if it resolves inside the audited workspace. |

## Where the trust anchor lives

Signature verification (gate X-2) needs an `allowed_signers` file. It must live **outside**
the workspace being examined, because an agent that can write the anchor can add its own
key and forge a human sign-off. Default search order:

1. `--allowed-signers` / `DAVER_ALLOWED_SIGNERS`
2. `~/.config/daver/allowed_signers`
3. `~/.daver/allowed_signers`

Any candidate inside the audited workspace is refused. Public keys are not secrets, so the
recommended pattern is to commit your own `allowed_signers` to your own repository and
verify against that committed copy in CI.

## Do I need a logging or telemetry backend?

**No, not to use DAVE+R.** Evidence typing, the gates, signatures and the audit chain all
work with no telemetry integration at all.

What a resolver buys you is the ability to *re-run* a recorded measurement and confirm it
still holds. Without one, a value marked `observed` is taken at its word.

| Profile | Unwired telemetry system | Source a resolver ran and could not find |
| :--- | :--- | :--- |
| `baseline` | not applicable | blocks |
| `agent-operated` | not applicable | blocks |
| `regulated` | **blocks** | blocks |

So `agent-operated` still catches the case the gate exists for — an agent citing a source
that does not exist on a system you *can* reach — without demanding you stand up a backend
first. A system with no registered resolver is a gap in your setup, not evidence of a lie,
and blocking on it would punish the wrong party.

Be clear-eyed about the residual: you cannot detect a fabricated source for a system you
have no way to reach, and an agent could in principle cite an unwired system to dodge
verification. X-3 names the unverified values and their systems in its reason for exactly
that reason, so the gap is visible rather than silent. Wire up resolvers for the systems
you actually use, then move to `regulated`, which requires every observed value to be
re-runnable.

Writing one is small: a resolver is a function taking `(source, root)` and returning a
value. See `ai/engine/daver/resolvers.py`; `file` is about thirty lines.

## Verify your install

```bash
python3 ai/engine/daver_cli.py lint                                    # spec self-check
python3 ai/engine/daver_cli.py check ai/engine/tests/fixtures/reference.cycle.yaml --stage refine
pip install pytest && python3 -m pytest ai/engine/tests -q             # 123 tests
bash ai/examples/signing/demo.sh                                       # needs ssh-keygen
```

The reference cycle should report `CAN ADVANCE`. The two scenario fixtures should report
`BLOCKED`; that is intentional, they are the published v1.0.0 examples replayed against
v1.1.0 gates.
