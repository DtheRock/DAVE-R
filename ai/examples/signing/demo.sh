#!/usr/bin/env bash
# Demonstrate X-2 end to end with an ephemeral key.
#
# No private key is committed to this repo, and none should be. This script makes a
# throwaway one in a temp dir so you can see the control work, then throws it away.
# In real use the signing key lives on the accountable owner's machine, ideally in a
# hardware token, and never anywhere an agent can read it.
#
# Note the TWO directories. The cycle lives in the workspace under examination; the
# key and the trust anchor live outside it, in operator space. That separation is the
# control: an agent that can write the anchor can add its own key and forge a human
# sign-off, so an anchor found inside the workspace is refused rather than trusted.
# The last section demonstrates exactly that refusal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"       # workspace under examination (agent-writable)
OPERATOR="$(mktemp -d)"   # operator space (agent must never write here)
trap 'rm -rf "$WORK" "$OPERATOR"' EXIT

cp "$ROOT/engine/tests/fixtures/reference.cycle.yaml" "$WORK/cycle.yaml"

digest() {  # digest <subject>
  ROOT="$ROOT" python3 - "$WORK/cycle.yaml" "$1" <<'PY'
import sys, os
sys.path.insert(0, os.path.join(os.environ["ROOT"], "engine"))
from daver import integrity, load_cycle
print(integrity.signature_digest(load_cycle(sys.argv[1]), sys.argv[2]))
PY
}

echo "==> the accountable owner generates a key, in operator space"
ssh-keygen -t ed25519 -f "$OPERATOR/owner" -N "" -C "j.okonkwo@acme.example" -q
printf 'j.okonkwo@acme.example %s\n' "$(cut -d' ' -f1,2 "$OPERATOR/owner.pub")" \
  > "$OPERATOR/allowed_signers"

echo
echo "==> before signing, under the agent-operated profile"
DAVER_ALLOWED_SIGNERS="$OPERATOR/allowed_signers" \
  python3 "$ROOT/engine/daver_cli.py" check "$WORK/cycle.yaml" --stage refine \
  --profile agent-operated --evidence-root "$WORK" 2>&1 \
  | grep -E "^BLOCKED|^CAN ADVANCE|^BLOCK X-" | sed 's/^/  /' || true

echo
echo "==> what the human is asked to sign"
python3 "$ROOT/engine/daver_cli.py" sign-request "$WORK/cycle.yaml" --subject go_no_go \
  | sed -n '1,4p'

echo
echo "==> the human signs, out of band, with their own key"
for SUBJ in go_no_go enforcement; do
  printf '%s' "$(digest "$SUBJ")" > "$WORK/$SUBJ.digest"
  ssh-keygen -Y sign -f "$OPERATOR/owner" -n dave-r "$WORK/$SUBJ.digest" >/dev/null 2>&1
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
echo "==> after signing (X-2 satisfied; X-3 still blocks, correctly, because this"
echo "    fixture's telemetry systems have no registered resolver to re-run)"
DAVER_ALLOWED_SIGNERS="$OPERATOR/allowed_signers" \
  python3 "$ROOT/engine/daver_cli.py" check "$WORK/cycle.yaml" --stage refine \
  --profile agent-operated --evidence-root "$WORK" 2>&1 \
  | grep -E "^BLOCKED|^CAN ADVANCE|^BLOCK X-" | sed 's/^/  /' || true

echo
echo "==> tamper: widen the guardrail after the owner signed"
python3 - "$WORK/cycle.yaml" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1]))
c["definition_brief"]["guardrails"]["false_positive_tolerance"]["value"] = 0.5
yaml.safe_dump(c, open(sys.argv[1], "w"), sort_keys=False, width=100)
PY
set +e
DAVER_ALLOWED_SIGNERS="$OPERATOR/allowed_signers" \
  python3 "$ROOT/engine/daver_cli.py" verify-signatures "$WORK/cycle.yaml" \
  --evidence-root "$WORK" > "$WORK/sigcheck.json" 2>&1
set -e
python3 -c "import json;print('  signatures valid:', json.load(open('$WORK/sigcheck.json'))['ok'])"
echo "  The digest covers the guardrails, the evidence, the control matrix, the"
echo "  exception register and the audit chain head, not just the word 'approved'."

echo
echo "==> the forgery that anchor separation prevents"
echo "    (an agent writes its own key into an allowed_signers inside the workspace)"
mkdir -p "$WORK/.daver"
ssh-keygen -t ed25519 -f "$WORK/.daver/agent_key" -N "" -C "j.okonkwo@acme.example" -q
printf 'j.okonkwo@acme.example %s\n' "$(cut -d' ' -f1,2 "$WORK/.daver/agent_key.pub")" \
  > "$WORK/.daver/allowed_signers"
set +e
python3 "$ROOT/engine/daver_cli.py" verify-signatures "$WORK/cycle.yaml" \
  --allowed-signers "$WORK/.daver/allowed_signers" --evidence-root "$WORK" \
  > "$WORK/forged.json" 2>&1
set -e
python3 - "$WORK/forged.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
subs = d.get("subjects")
detail = subs.get("go_no_go", {}).get("detail", "") if isinstance(subs, dict) else str(subs)
print("  agent-written anchor inside the workspace:", "REFUSED" if not d["ok"] else "ACCEPTED")
print("  ", " ".join(detail.split())[:110])
PY
