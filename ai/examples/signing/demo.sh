#!/usr/bin/env bash
# Demonstrate X-2 end to end with an ephemeral key.
#
# No private key is committed to this repo, and none should be. This script makes a
# throwaway one in a temp dir so you can see the control work, then throws it away.
# In real use the signing key lives on the accountable owner's machine, ideally in a
# hardware token, and never anywhere an agent can read it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/.daver"
cp "$ROOT/engine/tests/fixtures/reference.cycle.yaml" "$WORK/cycle.yaml"

echo "==> the accountable owner generates a key (normally: already has one)"
ssh-keygen -t ed25519 -f "$WORK/owner" -N "" -C "j.okonkwo@acme.example" -q
printf 'j.okonkwo@acme.example %s\n' "$(cut -d' ' -f1,2 "$WORK/owner.pub")" > "$WORK/.daver/allowed_signers"

echo
echo "==> before signing, under the agent-operated profile"
python3 "$ROOT/engine/daver_cli.py" check "$WORK/cycle.yaml" --stage refine \
  --profile agent-operated 2>&1 | sed -n '1,8p' || true

echo
echo "==> what the human is asked to sign"
python3 "$ROOT/engine/daver_cli.py" sign-request "$WORK/cycle.yaml" --subject go_no_go \
  | sed -n '1,6p'

echo
echo "==> the human signs, out of band, with their own key"
for SUBJ in go_no_go enforcement; do
  D=$(ROOT="$ROOT" python3 - "$WORK/cycle.yaml" "$SUBJ" <<'PY'
import sys, os
sys.path.insert(0, os.path.join(os.environ["ROOT"], "engine"))
from daver import integrity, load_cycle
print(integrity.signature_digest(load_cycle(sys.argv[1]), sys.argv[2]))
PY
)
  printf '%s' "$D" > "$WORK/$SUBJ.digest"
  ssh-keygen -Y sign -f "$WORK/owner" -n dave-r "$WORK/$SUBJ.digest" >/dev/null 2>&1
done

ROOT="$ROOT" python3 - "$WORK" <<'PY'
import os, sys, yaml
sys.path.insert(0, os.path.join(os.environ["ROOT"], "engine"))
from daver import load_cycle
w = sys.argv[1]
c = load_cycle(f"{w}/cycle.yaml")
c["validation_plan"]["go_no_go"]["signature"]["detached_signature"] = open(f"{w}/go_no_go.digest.sig").read()
c["execution"]["enforcement_authorization"]["detached_signature"] = open(f"{w}/enforcement.digest.sig").read()
yaml.safe_dump(c, open(f"{w}/cycle.yaml", "w"), sort_keys=False, width=100)
PY

echo
echo "==> after signing"
DAVER_EVIDENCE_ROOT="$WORK" python3 "$ROOT/engine/daver_cli.py" check "$WORK/cycle.yaml" \
  --stage refine --profile agent-operated 2>&1 | sed -n '1,4p'

echo
echo "==> now tamper: widen the guardrail after the owner signed"
python3 - "$WORK/cycle.yaml" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1]))
c["definition_brief"]["guardrails"]["false_positive_tolerance"]["value"] = 0.5
yaml.safe_dump(c, open(sys.argv[1], "w"), sort_keys=False, width=100)
PY
# verify-signatures exits non-zero when signatures are invalid, which is the expected
# outcome here, so do not let pipefail treat the demo's success as a failure.
set +e
DAVER_EVIDENCE_ROOT="$WORK" python3 "$ROOT/engine/daver_cli.py" verify-signatures "$WORK/cycle.yaml" \
  > "$WORK/sigcheck.json"
set -e
python3 -c "import json; print('signatures valid:', json.load(open('$WORK/sigcheck.json'))['ok'])"
echo
echo "The signature covers the guardrails and the evidence, not just the word 'approved'."
