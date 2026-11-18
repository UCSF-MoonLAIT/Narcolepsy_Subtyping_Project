# Stanford narcolepsy and hypersomnia pipeline comparison

This repository records intermediate method-development work for a larger clinical research project. It compares separate versus combined NT2/IH labeling, with historical prefix pipeline A as a baseline for investigating incomplete note coverage. Results are development-set agreement with existing references, not independent clinical validation.

## Start here

| Read next | Purpose |
| --- | --- |
| [Current report](review/REPORT.md) | Methods, results, limitations, and agreed conclusion. |
| [Results tables and figures](review/TABLES_AND_FIGURES.md) | Seven tables and four paired/three-way confusion-matrix figures. |
| [Review snapshot index](review/README.md) | What is included, version/date, and how to navigate the results. |
| [Experiment registry](docs/EXPERIMENTS.md) | Which A, B, combined, and retry runs supplied the results. |
| [Reproduce results](docs/REPRODUCING_RESULTS.md) | Offline evaluation, figure generation, and checks. |
| [Code map](docs/CODE_MAP.md) | Live entry points versus frozen code snapshots. |
| [Data and access](docs/DATA_AND_ACCESS.md) | Aggregate repository content versus authorized local patient data. |
| [Freeze-readiness audit](docs/FREEZE_READINESS.md) | Verified checks, disclosed limitations, and final commit scope. |

## Current findings

| Pipeline | Usable outputs / 128 | Accuracy on the same 117 patients | Macro-F1 on those 117 |
| --- | ---: | ---: | ---: |
| Historical A: v2, first 7,000 characters | 126 | 31.62% | 0.3637 |
| Original B: v2, complete available record | 120 | 57.26% | 0.5906 |
| Combined NT2+IH: v3, complete available record | 127 | 57.26% | 0.5580 |

The separate B-versus-combined comparison retains 119 shared patients: both have 57.98% accuracy, with macro-F1 0.5939 versus 0.5615. Combining labels improved usable-output coverage but did not improve paired classification. Historical A's lower agreement and the retained 34-patient beyond-cutoff subgroup identify incomplete source access as an important potential contributor to earlier poor performance; runtime differences prevent a coverage-only causal claim. Authorized B/combined retries recovered no usable outputs.

## Repository layout

```text
review/          Current aggregate report, tables, figures, metrics, and provenance
docs/           Project overview, experiment tracking, code map, and reproduction guide
prompts/         Live v2 and v3 prompt templates
tests/          Synthetic/model-mocked checks; no inference during tests
NT_LLM/          Four live helper modules plus ignored local data, runs, and restricted files
archive/         Local historical material; only its index is included in Git
*.py             Live CLI entry points retained at the root for path compatibility
```

Executable files retain their original paths because imports, data locations, and frozen-run compatibility depend on them. Use the code map instead of treating every script as an instruction to run it. Frozen inference/evaluation snapshots in `review/reproducibility/` are evidence of executed versions; live root scripts and `NT_LLM/*.py` are the implementation entry points.

No new specialist adjudication is included in this work. [Optional specialist review notes](docs/SPECIALIST_REVIEW_NOTES.md) describe questions for possible future work, not a required task or completed clinical review. No inference is needed to inspect the results. See [project overview](docs/PROJECT_OVERVIEW.md) and [change history](docs/CHANGELOG.md).
