# Code map

Live code stays at its original locations so module imports, data roots, and frozen-run compatibility remain stable. Start with the offline commands in [reproduction](REPRODUCING_RESULTS.md), not by executing every available runner.

| Live file | Role | Starts model inference? |
| --- | --- | --- |
| `compare_classification.py` | Primary/strict saved-output comparison and protected-artifact hashes | No |
| `compare_coverage.py` | Paired evaluation, cohort reconciliation, and exports | No |
| `coverage_audit.py` | Saved source coverage accounting | No |
| `submission_tools.py` | Legacy-named offline audit/export helper | No |
| `recover_checkpoint.py` | Explicit recovery into a new checkpoint file | No |
| `estimate_runtime.py` | Historical runtime-estimation utility | No |
| `coverage_pipeline.py` | Full-source or explicitly selected prefix inference, chunking, reconciliation, and call validation | Yes |
| `run_v3_cohort.py` | Preflight/smoke/full-run supervisor; `--prepare-only` is offline | Normally yes |
| `run_reference_comparison.py` | Historical pilot/B/matched-A execution supervisor | Yes; not a status command |
| `narcolepsy_stanford.py` | Shared helpers plus historical prefix CLI | Yes when its workflow is invoked |
| `NT_LLM/narcolepsy_analysis.py` | Shared reference loading and current eligibility/metrics | No |
| `NT_LLM/validation.py` | Structural and quote-support checks, evidence flags | No |
| `NT_LLM/label_schemes.py` | Five-label/four-label mappings | No |
| `NT_LLM/narcolepsy_report.py` | Historical report generation | No |

`prompts/` contains the live templates. Exact executed prompts and later-run inference snapshots are retained in [review/reproducibility](../review/reproducibility/README.md). Snapshots document versions; they are not the live import targets. The snapshot scripts `evaluate_historical_A.py`, `render_submission_figures.py`, and `render_historical_A_figures.py` provide the current offline reproduction helpers.

The historical exporter validates native labels when creating some handoff outputs; it must not be used to validate unmapped NT2/IH predictions against the combined schema. A's canonical eligibility comes from the current mapped evaluator; its local review records were derived from that table. See the verified aggregate denominators rather than treating a generic export status as authoritative.

The default tests use synthetic/mocked inputs and do not execute model inference. Archived C/legacy tests are historical, remain local, and are outside both default discovery and the final commit. Moving live Python files into a new package would require a separate functional refactor and revalidation, so this navigation change does not relocate them.
