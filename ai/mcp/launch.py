#!/usr/bin/env python3
"""Portable launcher for the dave-r MCP server.

server.py needs pyyaml and mcp<2 importable. Nothing on this machine guarantees
that: not the interpreter that happens to run this script (a system python3 is
often externally managed under PEP 668 and refuses `pip install` outright, see
ai/INSTALL.md), and not any one fixed path (a venv at a hardcoded location breaks
the moment someone else installs this plugin on a different machine).

So this script does not assume, it checks. It tries a short list of interpreters
likely to exist, execs into the first one where both packages actually import, and
if none qualify, says exactly what to run rather than guessing, crashing on an
ImportError three frames deep, or silently degrading.

Stdlib only, deliberately: this file must run correctly under the interpreter that
has neither package, so it can deliver that diagnosis instead of failing on its own
import line before it gets the chance.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "server.py")
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))  # ai/mcp -> ai -> repo/plugin root

# mcp 2.x renamed FastMCP to MCPServer; server.py has not been migrated. Probing
# this exact module, not just `import mcp`, is what correctly disqualifies an
# interpreter that has mcp 2.x installed instead of the pinned <2 range.
PROBE = "import yaml, mcp.server.fastmcp"


def _venv_candidates():
    # A venv local to this checkout is the most likely place to find both packages
    # installed on purpose (and the standard answer to PEP 668), so it outranks
    # generic interpreter names below. Cover both common directory names and both
    # binary names, and an already-activated venv if the parent shell set one.
    if os.environ.get("VIRTUAL_ENV"):
        yield os.path.join(os.environ["VIRTUAL_ENV"], "bin", "python3")
    for dirname in (".venv", "venv"):
        for binname in ("python3", "python"):
            yield os.path.join(REPO_ROOT, dirname, "bin", binname)


CANDIDATES = [sys.executable, *_venv_candidates(),
    "python3", "python3.13", "python3.12", "python3.11", "python3.10", "python3.9",
    "/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3",
    "/opt/anaconda3/bin/python3",
]


def qualifies(python_path):
    try:
        return subprocess.run([python_path, "-c", PROBE],
                               capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def main():
    # Probe and exec the path as found, never its realpath. Two things depend on
    # that: a venv's bin/python3 only auto-activates its site-packages when invoked
    # through that symlink, not through the bare interpreter it points to - and
    # that bare interpreter is exactly what created the venv, so the two share a
    # realpath despite behaving differently. Deduping by realpath would make every
    # venv candidate look like a repeat of one already tried (and failed), and skip
    # it. Dedup by the literal resolved path instead: enough to skip a name that
    # trivially repeats an earlier one, without conflating the two cases above.
    tried = set()
    for candidate in CANDIDATES:
        resolved = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if not resolved or not os.path.exists(resolved) or resolved in tried:
            continue
        tried.add(resolved)
        if qualifies(resolved):
            os.execv(resolved, [resolved, SERVER])

    sys.stderr.write(
        "dave-r MCP server: checked {} Python interpreter(s), none has both "
        "pyyaml and mcp<2 importable.\n\n"
        "Fix:\n"
        "  python3 -m pip install pyyaml \"mcp<2\" jsonschema referencing\n\n"
        "If that fails with 'externally-managed-environment', your system Python "
        "is PEP 668 protected (stock on Homebrew macOS, Debian, Ubuntu) - add "
        "--break-system-packages to the command above, or run it inside a venv: "
        "`python3 -m venv .venv && .venv/bin/pip install ...` at the repo root - "
        "this launcher already looks for .venv/ and venv/ there. "
        "See ai/INSTALL.md.\n".format(len(tried)))
    sys.exit(1)


if __name__ == "__main__":
    main()
