# Freeze-readiness audit

Audited November 18, 2026. **The computational content is ready for a repository snapshot within the agreed intermediate-research scope. The repository is not formally frozen: it has no Git commit and no tracked files yet.**

## Verified checks

| Area | Result |
| --- | --- |
| Saved-output evaluation | Independently recomputed all A/B/combined primary/strict comparisons; exact aggregate match. No inference. |
| Input-scope sensitivity | A actual-prefix quotation analysis independently reproduced, including affected pairwise denominators. |
| Tables | All seven tables checked cell by cell against source metrics. |
| Matrices | All 36 paired/three-way comparison matrices reconcile with denominators, correct counts, class supports, accuracy, balanced accuracy, and macro-F1. |
| Figures | All four PNGs regenerated identically in a Git-visible-only copy, without patient data. PDF generation also succeeded. |
| Tests | All 23 tests passed in that data-free copy, using the locally installed dependency environment. |
| Original artifacts | Hashes of 1,509 protected local files and 25 live code/prompt/requirement files verified unchanged. |
| Initial review manifest | Complete inventory, no missing/unmanifested review files, and all hashes matched before the audit. Final manifest refreshed for audit records. |
| Privacy and Git scope | No known cohort identifiers or private-key markers found in versionable text; no patient table/raw-data formats in the reviewed file set. Protected runs and exports stay ignored. |
| Documentation | Numerical narrative, policy distinctions, no-clinical-review scope, current navigation and relative links checked. Seven explicit private-data links remain only in optional specialist notes and require local authorization. |

The [machine-readable audit](../review/reproducibility/freeze_audit.json) and [recorded audit environment](../review/reproducibility/audit_environment.json) provide supporting evidence. No fresh dependency installation was tested; the data-free copy reused installed dependencies, including third-party `.runtime` packages. This is not a claim of independent clinical or cross-environment validation.

## Disclosed limitations that do not block this scope

The cohort was reused during development; the eligibility policy was adopted after execution; historical A differs in runtime settings; no new specialist adjudication or independent validation was performed. Strict subsets are small and selected. The report states these limits and does not claim clinical readiness or a coverage-only causal effect.

The legacy native-label handoff exporter is not authoritative for grouped A outputs. The current mapped evaluator, A-specific review exports, and supported reproduction commands were checked and are consistent. Fixing or extending that legacy pathway can be separate future work.

## Formal freeze step still required

Review the [final commit scope](FINAL_COMMIT_FILES.md), stage only the exact allowlist, and create a local Git commit. That commit hash is the repository's reproducible revision identifier. No staging, commit, tag, push, or external publication was performed by this audit. A subsequent content change requires refreshed hashes and a new commit rather than reusing a freeze label.

Patient notes, raw runs, reference workbooks, reviewer exports, runtime caches, and superseded experiment archives must not be included. Their local preservation does not mean they belong in the reviewer-facing Git commit.
