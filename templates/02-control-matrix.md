# DAVE+R Control Matrix

**System/Domain:** [e.g., Edge WAF Profiles]  
**Last Updated:** YYYY-MM-DD  

| Control ID | Intent / Description | Enforcement Plane | Owner | Telemetry Source | Rollback Procedure |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `WAF-RL-01` | Cap unauth API requests to 100/min. | Edge (CDN WAF) | @secops | Datadog Dashboard `WAF-01` | Toggle Terraform flag `waf_rl_enforce` to `false`. |
| `BOT-CH-02` | Challenge requests missing standard browser headers. | Edge (Bot Mgmt) | @fraud | Splunk Index `edge_sec` | Set action from `Managed Challenge` to `Log Only`. |
| `IAM-MFA-01`| Require MFA for anomalous geos. | Identity (Okta) | @iam | Okta System Logs | Move user to `Break-Glass-NoMFA` group. |
