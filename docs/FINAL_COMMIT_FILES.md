# Final Git commit scope

The reviewed final allowlist contains **120 files**. The exact repository-relative paths are in [FINAL_COMMIT_FILES.txt](FINAL_COMMIT_FILES.txt). This is a commit plan only: nothing has been staged or committed.

| Group | Files |
| --- | ---: |
| Root configuration, README and live entry points | 13 |
| Live helper modules and local-data index | 5 |
| Reviewer documentation and audit/commit scope | 11 |
| Prompt templates and guide | 3 |
| Synthetic or mocked tests | 8 |
| Aggregate review snapshot and reproducibility records | 79 |
| Historical index only | 1 |

## Included

The commit should contain the current README, ignore rules, live code, requirements, prompts, tests, all reviewer documentation, and the aggregate `review/` tree. This includes the agreed report/conclusion, seven tables, four PNG/PDF figures, aggregate JSON metrics, historical A provenance, later-run frozen inference snapshots, retry records, environment/audit records, and review manifest. Only `archive/README.md` is included from the archive.

The optional specialist handoff is aggregate discussion material; it contains no case identifiers or clinical decisions. Its seven local-data links require authorization and are not data files to add.

## Excluded

- All patient notes, reference workbooks, source tables, identifiers and clinical excerpts in local datasets.
- All raw A/B/combined run directories, checkpoints, call responses, source plans, and patient-level recomputed outputs.
- The restricted appendix, its case/quote/reviewer CSVs, and historical handoff packages.
- Archived C/legacy experiment code, stopped-run artifacts, superseded report/status documents, and intermediate packet copies.
- `.runtime/`, tokenizer/model caches, virtual environments, bytecode, logs, secrets and `.git/` internals.

Local preservation and Git inclusion are separate. Original A runs remain on disk; aggregate A results and documented provenance are included in this commit. No model execution or specialist adjudication is needed to create the snapshot.

## Stage the exact allowlist when authorized

```sh
git add --pathspec-from-file=docs/FINAL_COMMIT_FILES.txt
git diff --cached --stat
git diff --cached --check
```

Use the exact path list rather than `git add .`. Review the staged contents before creating the commit. The current repository has no HEAD commit; a successful local commit is still necessary to give the snapshot a fixed revision identifier. A push or external publication is not part of this scope.

## Explicit source and test paths

**Root configuration, README and live entry points**

- `.gitignore`
- `README.md`
- `compare_classification.py`
- `compare_coverage.py`
- `coverage_audit.py`
- `coverage_pipeline.py`
- `estimate_runtime.py`
- `narcolepsy_stanford.py`
- `recover_checkpoint.py`
- `requirements.txt`
- `run_reference_comparison.py`
- `run_v3_cohort.py`
- `submission_tools.py`

**Live helper modules and local-data index**

- `NT_LLM/README.md`
- `NT_LLM/label_schemes.py`
- `NT_LLM/narcolepsy_analysis.py`
- `NT_LLM/narcolepsy_report.py`
- `NT_LLM/validation.py`

**Prompt templates and guide**

- `prompts/README.md`
- `prompts/stanford_v2.txt`
- `prompts/stanford_v3.txt`

**Synthetic or mocked tests**

- `tests/test_combined.py`
- `tests/test_comparison.py`
- `tests/test_coverage.py`
- `tests/test_evaluation_policy.py`
- `tests/test_quote_support.py`
- `tests/test_recovery.py`
- `tests/test_reference_supervisor.py`
- `tests/test_submission.py`

