# Historical material

Only this archive index belongs to the final commit. The historical files described below remain preserved locally and ignored by Git.

The current reviewer entry points are [review/](../review/README.md) and [docs/](../docs/PROJECT_OVERVIEW.md). Archived content is not the current analysis or an instruction to restart inference.

The November 18 navigation change moved superseded root status, findings, brief, and runbook documents into the local `20261118_navigation/previous_root_documents/` directory. Dated `20261118*` snapshots can contain patient-level exports and remain ignored by Git. The local navigation archive records moved paths and pre/post hashes. Original raw data, all saved run directories, and the complete earlier B release retain their original locations. Historical A is retained and included in current aggregate comparisons.

The earlier archive guide is preserved below for provenance; local-only artifact links may not resolve in a data-free clone.

---

# Historical code and intermediate results

Cleanup date: November 13, 2026. This archive separates historical material from the current B workflow. Archiving does not authorize additional inference.

## Locations

- `20261113/staged_c/`: preserved extraction-first v1/v2 scripts, prompts, stopped controller, documentation and 12 tests.
- `20261113/legacy/`: historical 57-patient runner, standalone offline smoke script, v1 Stanford prompt and the obsolete evidence-window test.
- `20261113/documents_before_cleanup/`: complete pre-cleanup README, brief, findings, progress, status and runbook.
- `../NT_LLM/submission_20261109/archive/interim/`: superseded pilot/interim result snapshots, including the 100-patient figures used in the earlier presentation.
- `../NT_LLM/submission_20261109/archive/staged_c/`: staged plans, failed-smoke reviews, interim C reviews and logs.
- `../NT_LLM/submission_20261109/archive/timing_estimates/`: projections superseded by actual B completion.

`20261113/move_manifest.json` records original relative paths, new paths and pre-move file hashes. Moved files preserve their contents. A separate cleanup verification records protected source/run/package hashes and core checks.

## Historical reproduction

Archived scripts and tests retain their original contents and import/path assumptions. They are not current entry points and are excluded from default test discovery. To reproduce an archived offline test, restore the original layout in a separate temporary checkout using the move manifest; retain current core dependencies and place archived prompts/scripts/tests at their original paths. Do not restore files over the current working tree or start C inference. The original frozen run snapshots and final package provide additional exact code/prompt provenance.

The standalone legacy smoke script uses a repository-root-relative `__file__` assumption, so executing it directly at its archive path is not supported. Use the isolated restored layout. This preserves the historical script byte-for-byte rather than rewriting it as a new version.

## Protected material

Original Stanford inputs, reference workbook, original note text, historical source data, all `NT_LLM/runs/` directories and `comparison_B_complete_20261113/` plus ZIP retain their original locations. They were not deleted or moved. The copied reference workbook is not byte-identical to the authoritative workbook and remains preserved.

The current default tests remain in `../tests/`. Current code still imports `narcolepsy_stanford.py`; that file is a required shared dependency despite its legacy CLI.
