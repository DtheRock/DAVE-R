# DAVE+R Exception Register

*Principle: Exceptions are a normal part of reality, but they must be governed, time-bounded, and reviewed.*

| Exception ID | Scope (IP, UA, Path) | Rationale | Approver | Expiry Date | Review Cadence | Reduction Plan |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `EXC-001` | IP: `198.51.100.14` | Legacy B2B partner (BetaCorp) cannot support SNI / Cookies. | J. Smith | 2026-06-01 | Monthly | BetaCorp is migrating to new API Gateway by May 15th. |
| `EXC-002` | Path: `/api/v1/webhooks` | Strict WAF limits break payment provider callbacks. | A. Wong | 2026-12-31 | Quarterly | Move webhook validation to mTLS mutual authentication in Q4. |
