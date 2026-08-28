# DAVE+R Exception Register

*Principle: Exceptions are a normal part of reality, but they must be governed,
time-bounded, reviewed, and covered by something while they are open.*

## Bypass mechanism strength
*New in v1.1. The bypass mechanism is itself an attack surface. Prefer, in order:*

1. Cryptographic identity
2. mTLS
3. Signed header
4. API key
5. **IP address** — requires written justification, expiry capped at 180 days
6. **ASN** — requires written justification, expiry capped at 180 days

An IP allowlist is trivially defeated wherever the origin trusts a client-supplied address.
An ASN can contain thousands of unrelated hosts on shared cloud ranges, so "allow the
partner's ASN" often means "allow that cloud region".

## Register

| Exception ID | Applies to | Scope | Mechanism | Rationale | Approver |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `EXC-001` | `WAF-RL-01` | BetaCorp integration during signature migration | signed-header (HMAC, scoped to one path) | Their May migration dropped the partner signature; blocking breaches an active SLA | J. Okonkwo |
| `EXC-002` | `WAF-RL-02` | `/api/v1/webhooks` | path | Strict WAF limits break payment provider callbacks | A. Wong |

## Governance
*New columns in v1.1: compensating control, blast radius, expiry action.*

| Exception ID | Compensating control | Blast radius | Expiry | Expiry action | Review | Reduction plan |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `EXC-001` | Rate-capped to contracted 10 req/s, bound to their signature, every hit alerted, credential rotates weekly | low — read-only pricing, authenticated, one party | 2026-07-14 | auto-revoke | weekly | Restore production partner signature by 06-30 |
| `EXC-002` | **[REQUIRED]** what covers this while open? If genuinely nothing, say so explicitly | **high — unauthenticated path, payment callbacks** | 2026-12-31 | review-required | quarterly | Move to mTLS in Q4 |

> `EXC-002` is what a dangerous exception looks like: an unauthenticated path held open for
> twelve months on quarterly review. The compensating control and blast radius columns exist
> so that is visible rather than buried in a rationale nobody rereads.

**Expiry actions:** `auto-revoke`, `escalate`, `block-change`, `review-required`.
There is deliberately no `auto-extend`. An exception past its expiry with no recorded
decision is not renewed; it is drift with a date stamp on it.

**Usage:** track hit counts. An exception with zero observed usage is dead weight. Retire it.
