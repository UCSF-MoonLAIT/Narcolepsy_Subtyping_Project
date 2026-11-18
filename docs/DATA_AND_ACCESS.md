# Data and access

## Included in the reviewer-facing repository

`review/` contains aggregate reports, confusion matrices, per-class metrics, settings, prompt/code snapshots, and file hashes. `docs/`, live code, prompts, and tests describe how the work was conducted. No new specialist clinical adjudication is included.

## Authorized local material excluded from Git

| Material | Existing local location |
| --- | --- |
| Prepared Stanford notes | `NT_LLM/NT_goldstd_128pt.parquet` |
| Original selected note text | `NT_LLM/stanford_NT_IH_sleeponly_notes_128_for_LLM/` |
| Original reference workbook | `NT_LLM/Stanford_NT_IH_128_sleep_only_2026-07-27_with_first_dx_dates.xlsx` |
| Saved raw runs, attempts, checkpoints and source plans | `NT_LLM/runs/` |
| Restricted comparison tables and audit annotations | `NT_LLM/final_packet_20261117/restricted_review/` |
| Earlier handoff packages and historical source cohorts | Other local `NT_LLM/` directories/files |
| Superseded packet documents and intermediate private exports | Local dated `archive/20261118*/` directories |

A clone can inspect aggregate evidence without these files. Recomputing patient-level eligibility or metrics requires authorized access to the original local source, references, and saved predictions. Matching hashes establish artifact identity, not permission to access data. There is no automatic data download or external sharing step.

The restricted appendix contains identifiers, note excerpts, and blank historical review queues. Links in the optional specialist notes resolve only in an authorized local checkout. Those queues are retained for traceability, not a requirement to recruit a specialist. Do not add raw data or reviewer exports to the public aggregate tree.

`NT_LLM/` is ignored by default except for its README and four explicitly retained Python modules. All archived experiment code and document snapshots, including patient tables, remain local and ignored; only `archive/README.md` is versionable. Logs, environments, and secrets are also ignored. Aggregate JSON and figures in `review/` are deliberately versionable. Git ignore rules prevent accidental additions; they are not an access-control system.
