# Experiment registry

This is the reviewer-facing index of saved experiments. Local run directories remain at their original paths. Raw predictions/calls contain patient-level information and are ignored by Git; the repository exposes aggregate results and provenance instead.

| Record | Local artifact directory | Role and status |
| --- | --- | --- |
| Historical A | `NT_LLM/runs/stanford_v2_20261022T003015723429Z/` | Completed v2 inference on first 7,000 characters; 8,192-token context. Current primary eligibility 126/128. Not rerun for this comparison. |
| Original B | `NT_LLM/runs/coverage_B_reference_20261109/` | Completed full-source v2 pipeline; current primary eligibility 120/128. |
| Combined NT2+IH | `NT_LLM/runs/stanford_v3_combined_20261114_quotecheck/full/` | Completed full-source v3 pipeline; 127/128 primary eligible, including 80 quote-only flagged outputs. |
| Authorized retry round | `NT_LLM/runs/retry_B_combined_20261118T062415Z/` | Eight B and one combined failures retried with respective frozen code/settings; zero recoveries. Includes regenerated comparison. |
| A-inclusive offline evaluation | `NT_LLM/runs/historical_A_three_pipeline_comparison_20261118/` | Current four-label structural checks, pairwise/three-way metrics, and actual-prefix quote sensitivity; no inference. |
| Earlier B-only comparison | `NT_LLM/submission_20261109/comparison_B_complete_20261113/` | Preserved historical five-label release. Do not mix its metrics/denominators with current results. |
| Imported-output A snapshot | `NT_LLM/runs/stanford_v2_20261022T001027851608Z/` | Imported predictions with unverified inference provenance; excluded from current comparison. |
| Initial combined smoke | `NT_LLM/runs/stanford_v3_combined_20261114/` | Preserved technical smoke history; subsequently revalidated offline. Not a performance cohort. |
| Extraction-first C | `NT_LLM/runs/staged_C_reference_20261109_v1/` and `..._v2/` | Stopped technical experiments; excluded from result comparisons. Historical code in `archive/20261113/staged_c/`. |
| Matched-settings truncated A | No completed run | Not started; distinct from historical A and not required for this work. |

## Denominators that must remain distinct

| Analysis | Shared eligible patients | 34-patient subgroup shared eligible |
| --- | ---: | ---: |
| B versus combined, primary | 119 | 31 |
| A/B/combined three-way, primary | 117 | 31 |
| B versus combined, strict | 28 | 5 |
| A/B/combined three-way, strict | 17 | 5 |

Historical A has 81 strict-eligible outputs against the full record and 80 against its actual prefix. The three-way strict intersection is unchanged; some pairwise strict denominators differ. See [A-inclusive results](../review/results/historical_A/comparison.json) and [input-scope sensitivity](../review/results/historical_A/input_scope_strict_comparison.json).

Historical A and B share the v2 prompt and source/reference hashes. A's exact model digest, think setting, generation limit, and frozen execution environment are not established as equivalent to the later runs. B and combined use matching model/settings but different prompts/label handling. Neither comparison is a controlled single-factor causal experiment.
