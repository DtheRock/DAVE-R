# DAVE+R Refinement Log

*A chronological record of tuning, cleanups, and system hardening.*

| Date | Version | Change / Refinement | Evidence & Rationale | Impact Observed |
| :--- | :--- | :--- | :--- | :--- |
| 2026-02-14 | `v1.1` | Tightened rate limit from 150/min to 100/min. | 30 days of telemetry showed 99th percentile of legitimate users never exceed 80/min. | Caught an additional 15% of low-and-slow scrapers. |
| 2026-03-01 | `v1.2` | Retired Exception `EXC-001`. | BetaCorp successfully migrated to authenticated API keys. | Cleaned up WAF rule bloat. Edge latency dropped by 2ms. |
