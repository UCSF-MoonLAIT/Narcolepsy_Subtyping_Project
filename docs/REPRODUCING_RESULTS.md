# Reproduce results without inference

Run commands from the repository root. The locally validated interpreter is `/opt/anaconda3/bin/python`; another environment must provide [requirements.txt](../requirements.txt). The exact inference package versions/model identifiers are in the [saved configurations](../review/reproducibility/README.md). Viewing aggregate results or regenerating figures does not require starting Ollama.

## Check live code

```sh
MPLCONFIGDIR=/tmp/narcolepsy-mpl /opt/anaconda3/bin/python -m unittest discover -s tests -v
```

These tests use synthetic or mocked inputs and make no model calls.

## Regenerate figures from aggregate records

```sh
MPLCONFIGDIR=/tmp/narcolepsy-mpl /opt/anaconda3/bin/python review/reproducibility/code/render_submission_figures.py --review-dir review --output-dir /tmp/stanford-paired-figures
MPLCONFIGDIR=/tmp/narcolepsy-mpl /opt/anaconda3/bin/python review/reproducibility/code/render_historical_A_figures.py --review-dir review --output-dir /tmp/stanford-three-way-figures
```

The first command generates Figures 1–2; the second generates Figures 3–4. Both use aggregate matrices and metrics, require no patient records, and leave the published tables unchanged.

## Recompute classification with authorized local data

Choose new destinations; never overwrite earlier runs or reviewed records.

```sh
MPLCONFIGDIR=/tmp/narcolepsy-mpl /opt/anaconda3/bin/python compare_classification.py --B NT_LLM/runs/retry_B_combined_20261118T062415Z/combined_NT2_IH/retry_run --baseline-dir NT_LLM/runs/retry_B_combined_20261118T062415Z/original_B/retry_run --output-dir NT_LLM/runs/B_combined_reproduced_NEW
MPLCONFIGDIR=/tmp/narcolepsy-mpl /opt/anaconda3/bin/python review/reproducibility/code/evaluate_historical_A.py --output-dir NT_LLM/runs/A_three_way_reproduced_NEW
```

These read saved outputs and make no model calls. The A-inclusive evaluator applies the same current four-label structural policy to all runs, calculates pairwise and three-way intersections, and reports A's actual-prefix quote check separately. Current A eligibility is 126, not the older 127-patient five-class denominator.

## What not to run for review

`coverage_pipeline.py`, `run_v3_cohort.py` without `--prepare-only`, `run_reference_comparison.py`, and the historical `narcolepsy_stanford.py` CLI can start inference. No further inference is required for this snapshot. Exact frozen inference code/configurations remain available for provenance; previously failed outputs were retried only in the authorized separate round.

See [experiment registry](EXPERIMENTS.md), [data and access](DATA_AND_ACCESS.md), and [snapshot provenance](../review/reproducibility/README.md). Earlier operational runbooks are preserved locally in the navigation archive and are not current instructions for a reviewer.
