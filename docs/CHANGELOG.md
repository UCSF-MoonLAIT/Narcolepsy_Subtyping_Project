# Analysis and repository change history

This log records meaningful analytical states. Frozen raw runs and historical reports remain preserved; old metrics are not silently replaced.

| Stage | Recorded change |
| --- | --- |
| Historical A, October 2026 | Saved v2 prefix run later used as a retrospective baseline. An earlier imported-output snapshot has unverified provenance and is excluded. |
| Full-source B, completed November 13 | Completed source-preserving classification/reconciliation with eight unusable outputs. Earlier five-label release remains historical. |
| Combined v3, completed November 15 | Fresh four-label inference on all 128 patients; 80 final quote flags and one unusable output. |
| November 17 evaluation policy | Primary includes otherwise eligible quote-only flagged predictions; strict source-quote sensitivity reported separately. Policy was adopted post-run. |
| November 18 retries | Eight B and one combined failures retried with frozen parent versions; zero recoveries. |
| November 18 A inclusion | Re-evaluated saved historical A under current four-label checks; added three-way comparisons, actual-prefix quote sensitivity, tables and figures. No A inference. |
| November 18 review scope | No new specialist adjudication in the current computational scope. Optional specialist handoff remains separate. |
| November 18 agreed conclusion | Lead with separate-versus-combined labeling; historical A supports discussion of source coverage without a causal coverage-only claim. |
| November 18 freeze-readiness audit | Saved-output results, all seven tables, 36 matrices, four figures and 23 data-free tests verified. Content ready; formal Git commit remains pending. |
| November 18 repository navigation | Aggregate results promoted to `review/`; reviewer guidance placed in `docs/`; superseded root documents archived; original execution/data paths retained. |

The current [report](../review/REPORT.md), [experiment registry](EXPERIMENTS.md), and [aggregate manifest](../review/manifest.json) are authoritative for this snapshot. Dated local archives retain prior documents and a move/hash record for the navigation change. New analyses should use a new run destination and record the policy, source versions, and eligible denominator.
