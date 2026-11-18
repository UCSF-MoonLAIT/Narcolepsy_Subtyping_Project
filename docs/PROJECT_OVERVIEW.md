# Project overview

This intermediate work evaluates whether combining narcolepsy type 2 and idiopathic hypersomnia during inference improves chart-abstraction performance. The broader clinical research project is outside this repository snapshot's claims.

The cohort is the existing 128 Stanford patients with selected de-identified notes and a preserved reference workbook. Historical MGB/57-patient datasets and the three original Word documents remain local historical material, outside the current comparison.

## Questions and status

| Question | Status |
| --- | --- |
| Separate v2 labels versus combined v3 inference | Evaluated using the same four-label mapping and paired patients. |
| Historical limited source access versus later implementations | Evaluated descriptively using historical A; runtime settings differ. |
| Performance in the 34 beyond-cutoff records | Retained in primary and strict comparisons. |
| Retry of eight B and one combined unusable outputs | Complete; no usable recoveries. |
| Quotation fidelity | Automated checks for all runs; detailed agent-assisted textual audit of 80 combined outputs. |
| New specialist adjudication | Not performed; outside current scope. |
| Independent/held-out clinical validation | Not performed; no clinical-readiness claim. |

Primary eligibility includes structurally valid predictions with quote-only flags. Strict sensitivity additionally requires quote support. Existing reference labels, original outputs, and raw notes remain unchanged. The primary policy was adopted after run execution and inspection of flags. See the report for this and other limitations.

Current results are at [review/REPORT.md](../review/REPORT.md). The [experiment registry](EXPERIMENTS.md) records run identities and eligible cohorts; [CHANGELOG.md](CHANGELOG.md) records major analytical decisions. Reproducing saved-output evaluation is separate from starting model inference.
