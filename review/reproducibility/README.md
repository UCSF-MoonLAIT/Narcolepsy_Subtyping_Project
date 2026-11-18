# Reproducibility and provenance

This folder distinguishes executed inference versions, the saved-output evaluation, and current portable figure helpers. Start with the repository [reproduction guide](../../docs/REPRODUCING_RESULTS.md).

| Material | Meaning |
| --- | --- |
| `prompts/` | Exact historical A, original B, and combined prompt snapshots. A/B share v2. |
| `inference_snapshots/original_B/` and `.../combined_NT2_IH/` | Hash-verified frozen parent inference code and configurations. These are audit snapshots, not live import roots. |
| `historical_A_run_manifest.json` | Historical A's recorded configuration. It does not establish the exact weights/think/output limit or the same frozen-code provenance as later runs. |
| `code/` | Evaluation/source snapshots plus offline A-inclusive evaluation and figure-generation helpers. Live implementation remains at the repository root and `NT_LLM/`. |
| `analysis_policy.json`, `analysis_verification.json` | Original B/combined primary/strict policy, source/code hashes, and the earlier 23-test verification. |
| `retry_verification.json` | Completed B/combined retries with zero recoveries and verified parent/non-target preservation. |
| `historical_A_inclusion_verification.json` | A-inclusive counts, paired intersections, reproduced metrics, and blank clinical decisions. |
| `quote_audit_summary.json` | Aggregate counts from the combined source-text audit, not clinician adjudication. |

B and combined used Qwen3 14B with the same installed digest, temperature 0, top_p 0.1, num_ctx 40960, num_predict 2048, think=False, and a 128-token safety margin. Historical A used the recorded model name and v2 prompt with a 7,000-character prefix and an 8,192-token context; equivalence of its other defaults and weights cannot be established. Treat A comparisons as descriptive rather than a controlled source-coverage experiment.

Primary eligibility requires current structural validity, allowed grouped labels, and matching metadata. Quote-only errors do not exclude otherwise eligible outputs. Strict analysis adds source verification; A actual-prefix matching is separately reported. The primary policy was adopted after execution and inspection of flags.

The shared B/combined primary denominator is 119; the A/B/combined denominator is 117. The corresponding strict intersections are 28 and 17. A's current individual primary eligibility is 126, distinct from its earlier 127-patient five-class evaluation. The [experiment registry](../../docs/EXPERIMENTS.md) and [report](../REPORT.md) explain all denominators.

Figures can be regenerated from aggregate records without restricted data:

```sh
MPLCONFIGDIR=/tmp/narcolepsy-mpl /opt/anaconda3/bin/python review/reproducibility/code/render_submission_figures.py --review-dir review --output-dir /tmp/stanford-paired-figures
MPLCONFIGDIR=/tmp/narcolepsy-mpl /opt/anaconda3/bin/python review/reproducibility/code/render_historical_A_figures.py --review-dir review --output-dir /tmp/stanford-three-way-figures
```

The legacy `--packet NT_LLM/final_packet_20261117` argument remains supported in an authorized local checkout through the compatibility link. No table files are rewritten by the figure helpers.

Recomputing eligibility/metrics requires authorized local notes, references and saved outputs. Commands are in [REPRODUCING_RESULTS.md](../../docs/REPRODUCING_RESULTS.md). The A-inclusive evaluator writes to a new destination and never calls the model. The original data, raw run directories and restricted exports retain their original paths, with no automatic download or external sharing.

No specialist adjudication is included or required within the current computational scope. Blank confirmation/inclusion fields and retained local queues do not represent clinical approval, a validation result, or a blocker to repository review. The [optional specialist notes](../../docs/SPECIALIST_REVIEW_NOTES.md) describe possible future questions only.
