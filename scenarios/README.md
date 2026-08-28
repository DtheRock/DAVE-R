# Worked examples

| | |
| :--- | :--- |
| [scraping-pricing-api.md](scraping-pricing-api.md) | AI scrapers on a live pricing API. Module A. |
| [credential-stuffing-login.md](credential-stuffing-login.md) | Credential stuffing on a login endpoint. Module C. |
| [reference-cycle.md](reference-cycle.md) | The same scraping problem, run to the v1.1.0 standard, with every artifact filled in. |

The first two were written against v1.0.0 and are kept as published, with two sections
added to each: what the cycle actually cost, and what v1.0.0 did not require that v1.1.0
now does.

That second section is the more useful one. Both scenarios end in a clear win, and a
story that only goes right teaches less than one that shows where the framework was thin.
Each was replayed through the v1.1.0 gates, and the results are reported honestly:
scenario one clears 13 of 40 gates, scenario two clears 16 of 45. Neither was
badly run. The framework simply did not ask for things it should have.
