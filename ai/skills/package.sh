#!/usr/bin/env bash
# Build a self-contained dave-r.skill for Cowork / Claude Code.
# The repo shares one copy of spec/ and engine/; the packaged skill bundles its own
# so it runs anywhere with no repo checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/dist/dave-r.skill}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/dave-r"
cp "$ROOT/ai/skills/dave-r/SKILL.md" "$TMP/dave-r/"
cp -r "$ROOT/ai/skills/dave-r/references" "$TMP/dave-r/"
cp -r "$ROOT/ai/spec" "$TMP/dave-r/spec"
mkdir -p "$TMP/dave-r/engine/tests/fixtures"
cp -r "$ROOT/ai/engine/daver" "$TMP/dave-r/engine/daver"
cp "$ROOT/ai/engine/daver_cli.py" "$TMP/dave-r/engine/"
cp "$ROOT/ai/engine/tests/fixtures/reference.cycle.yaml" "$TMP/dave-r/engine/tests/fixtures/"

# bundled layout: paths are relative to the skill root
python3 - "$TMP/dave-r/SKILL.md" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
s = s.replace("python3 ai/engine/daver_cli.py", "python3 engine/daver_cli.py")
s = s.replace("`ai/skills/dave-r/references/", "`references/")
s = s.replace("`ai/engine/tests/fixtures/", "`engine/tests/fixtures/")
open(p, "w").write(s)
PY

find "$TMP" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$TMP" && zip -qr "$OUT" dave-r -x '*__pycache__*' '*.pyc')
echo "wrote $OUT"
