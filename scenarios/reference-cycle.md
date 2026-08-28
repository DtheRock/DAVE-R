# Reference cycle: the same problem, run to the v1.1.0 standard

[`ai/engine/tests/fixtures/reference.cycle.yaml`](../ai/engine/tests/fixtures/reference.cycle.yaml)

The scraping scenario, run properly. Every artifact filled in, every cross-reference
resolving, all 43 blocking gates passing. It exists for two reasons: as the worked example
this repo previously lacked, and as proof that the gate set is satisfiable. A gate set
nothing can pass is useless.

```bash
python3 ai/engine/daver_cli.py check ai/engine/tests/fixtures/reference.cycle.yaml --stage refine
```

## What it does differently

| | scraping-pricing-api (v1.0.0) | reference cycle (v1.1.0) |
| :--- | :--- | :--- |
| Triage | none; 5-day shadow by default while 503s continued | expedited track, signed, daily harm cost stated |
| Baseline | never measured | FP rate, latency, error rate and attack volume, 14d window, before shadow |
| Alternatives | none considered | edge cache, require auth, per-key quota — each with why it was rejected |
| FP tolerance | "0%", never measured | 0.001 declared, 0.0006 measured, and broken out per critical flow |
| Evasion | discovered 30 days later in production | three bypasses named, two tested, one accepted with a signature |
| Threshold | 300, then 200 after evasion at 290 | 200 = p99.9 of legitimate session rate, derived from the shadow distribution |
| Exception | static IP, no cover, no expiry action | signed header scoped to one path, rate-capped, alerted, weekly rotation, auto-revoke |
| Rollback | global toggle, 45s | graduated block → challenge → log, 90s, with the degraded posture written down |
| Rollout | single flip | canary → region → full, each with an abort criterion |
| Sign-off | not recorded | named individual, on both go/no-go and enforcement |

## It is not a fantasy

The reference cycle still raises advisories, and deliberately so:

```
WARN V-8 threshold-not-on-a-treadmill
      threshold_evasion_margin (0.03) >= 0.25 is false
```

An attacker operating just under 200 req/min still retains 97% of their throughput. The
rate limit is genuinely weak against a patient adversary. The cycle documents that,
mitigates it by pairing the threshold with a challenge rather than a pass, and carries the
residual risk forward explicitly.

That advisory is the most useful line in the file. A framework that let this cycle report
all-clear would be lying to you about a control that a determined scraper walks straight
around.
