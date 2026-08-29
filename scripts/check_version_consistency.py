#!/usr/bin/env python3
"""Fail if the plugin's version has drifted across the files that name it.

daver.json, ai/spec/VERSION, CHANGELOG.md, and marketplace.json's metadata.version
are not read by `claude plugin tag` (which only cross-checks plugin.json against
marketplace.json's plugins[] entry for the plugin itself, and only at tag time).
A version bump that touches plugin.json but misses one of these leaves a stale
number sitting in a file with no CI signal at all - exactly the manual-edit drift
this script exists to catch. It duplicates the plugin.json/marketplace.json
entry check `claude plugin tag` also does, on purpose: this script has no
dependency on the `claude` CLI being installed, so it runs standalone in a fast
PR check, as a pre-commit hook, or by hand, without needing that CLI present.

Ground truth is .claude-plugin/plugin.json's own "version" field; every other
location must match it exactly, byte for byte, not just semver-equivalent.

Usage: python3 scripts/check_version_consistency.py
Exit 0 if every location agrees, 1 and a diff otherwise.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_json(rel_path):
    return json.loads((ROOT / rel_path).read_text())


def changelog_top_version(rel_path):
    text = (ROOT / rel_path).read_text()
    m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    return m.group(1) if m else None


def main():
    plugin = read_json(".claude-plugin/plugin.json")
    truth = plugin.get("version")
    if not truth:
        print('FAIL: .claude-plugin/plugin.json has no "version" field', file=sys.stderr)
        return 1

    marketplace = read_json(".claude-plugin/marketplace.json")
    entry = next(
        (p for p in marketplace.get("plugins", []) if p.get("name") == plugin.get("name")),
        None,
    )
    daver = read_json("daver.json")

    checks = [
        ("plugin.json .version", truth),
        ("marketplace.json .metadata.version", marketplace.get("metadata", {}).get("version")),
        (
            f"marketplace.json .plugins[name={plugin.get('name')!r}].version",
            entry.get("version") if entry else None,
        ),
        ("daver.json .framework_version", daver.get("framework_version")),
        ("daver.json .spec_version", daver.get("spec_version")),
        ("ai/spec/VERSION", (ROOT / "ai/spec/VERSION").read_text().strip()),
        ("CHANGELOG.md top entry", changelog_top_version("CHANGELOG.md")),
    ]

    mismatches = [(label, value) for label, value in checks if value != truth]
    print(f"ground truth (.claude-plugin/plugin.json): {truth}")
    for label, value in checks:
        mark = "OK " if value == truth else "!! "
        print(f"  {mark}{label}: {value!r}")

    if mismatches:
        print(
            f"\nFAIL: {len(mismatches)} location(s) disagree with plugin.json's "
            f"version {truth!r}.",
            file=sys.stderr,
        )
        return 1

    print("\nAll version locations agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
