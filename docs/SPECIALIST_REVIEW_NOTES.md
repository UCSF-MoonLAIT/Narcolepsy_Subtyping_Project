# Specialist review notes for optional future adjudication

Prepared November 18, 2026. Status: questions and supporting observations for a future qualified clinician, preferably a sleep-medicine specialist. **No specialist review or clinical adjudication has been performed through this document.** This work is outside the current computational scope and is not a prerequisite for submitting the computational comparison.

## Purpose and study context

The study task is to abstract the established diagnosis documented in the available longitudinal record. It is not to independently diagnose a patient by assembling isolated symptoms and test results. The available selected notes may omit outside testing, original diagnostic workup, or earlier encounters. Existing reference labels remain unchanged.

The submission compares historical A (v2 prompt, first 7,000 characters), original B (v2 prompt, complete available source), and combined NT2+IH (v3 prompt, complete available source). Evaluation uses four categories: NT1, NT2_IH, Uncertain, and Not_NT_IH. NT2 and IH are grouped in analysis copies of the v2 outputs and references. Historical A has different runtime settings and is a descriptive baseline, not a controlled truncation-only experiment.

Current primary eligibility is 126/128 for A, 120/128 for B, and 127/128 for combined. On the 117 patients eligible for all three, accuracy is 31.62%, 57.26%, and 57.26%, respectively. The separate B-versus-combined comparison uses 119 patients and has 57.98% accuracy for both. These are reference-agreement results, not newly clinically confirmed diagnoses.

## Work already completed

- Computational output-structure and metadata checks, including permitted labels, evidence fields, and full-date format.
- Automated quotation matching against source text, with exact, permitted formatting-only, and unsupported outcomes. For A, support against its actual 7,000-character input was additionally checked.
- An agent-assisted source-text audit of all 80 combined-pipeline quote-flagged outputs and all 125 rejected quotations. This checked textual fidelity, not clinical correctness.
- Primary and strict sensitivity analyses, patient reconciliation, and paired comparisons, including the 34-patient beyond-cutoff subgroup.
- A separate authorized retry round for eight B failures and one combined failure. No usable outputs were recovered. Quote-only flagged combined outputs were not retried.

These checks do not resolve clinical label disagreements, establish that an accepted quotation adequately supports a diagnosis, verify clinical diagnosis dates, or validate the reference labels anew.

## Questions for specialist discussion

### 1 Established diagnoses versus unresolved diagnostic categories

The v3 prompt preserves established specialist diagnoses even when original testing is unavailable. It maps established NT2 or IH, including established specialist terminology “narcolepsy without cataplexy,” to NT2_IH. It does not infer NT2 solely from unspecified narcolepsy plus a separate denial of cataplexy. Established narcolepsy with unresolved subtype remains Uncertain when the four-category assignment cannot be resolved.

Questions to consider if review is undertaken:

- Does the record document an established diagnosis, a tentative differential, an unresolved workup, or a copied historical mention?
- Is the subtype terminology used in an actual diagnostic assessment, or is it inferred from separate symptom statements?
- Does uncertainty concern whether a disorder is established, whether its subtype is established, or only whether original testing remains available?
- Where diagnoses conflict over time, is there an explicit revision by the treating clinician, or merely inconsistent documentation?

These questions evaluate the study's abstraction rules; they are not instructions to reconstruct a diagnosis from missing or masked information.

### 2 NT2_IH versus Uncertain disagreements

On the 119-patient B-versus-combined primary cohort, NT2_IH recall was 94.12% in both pipelines, while precision decreased from 56.14% to 48.48%. Among 24 reference-Uncertain patients, Uncertain recall decreased from 29.17% to 8.33%. These reference-based findings identify a useful discussion area; they do not prove which individual model or reference labels should be changed.

For any reviewed disagreement, assess whether the model overinterpreted historical or tentative documentation, whether relevant source information was lost, or whether the supplied reference itself warrants reconsideration. A model/reference disagreement alone does not establish a reference error. Missing original testing alone was not intended to invalidate an otherwise established specialist diagnosis under the study prompts.

### 3 Not_NT_IH and alternative explanations

The study rule requires a documented conclusion supporting neither NT nor IH. A coexisting alternative condition, an incomplete workup, or a result that does not support narcolepsy alone is not automatically equivalent to excluding both disorders.

If review occurs, distinguish an established alternative explanation from a suspected alternative, a comorbidity, or insufficient evidence. Record what the clinician actually concluded and whether a later assessment revised that conclusion. Do not treat the model's evidence flag as a clinical conclusion.

### 4 Potentially substantive quotation alterations

The 80 flagged combined outputs were grouped by the highest-priority issue in each case:

| Source-text finding | Cases | Question for possible clinical review |
| --- | ---: | --- |
| Priority evidence review | 31 | Could the alteration change the apparent diagnosis, subtype, test interpretation, or timeline? |
| Other rewritten or joined quotations | 38 | Is the diagnostic claim supported elsewhere, despite inaccurate quotation construction? |
| Capitalization/punctuation only | 9 | Is there any clinically meaningful change, beyond the identified superficial difference? |
| Minor spelling/split-word-spacing only | 2 | Is the change limited to text normalization? |

There were 125 rejected quotations among 277 total quotations. Masked clinical-content expansion or cross-passage replacement affected 33 quotations in 28 cases. Priority examples at the aggregate level included changed diagnostic statements, changed numbers, added subtype wording, and supplied terms or dates where the source was masked. These observations must not be described as 31 proven incorrect diagnoses or 28 proven false clinical claims.

For each issue, separate two judgments: whether the quotation is faithful to the cited passage, and whether the assigned diagnosis is supported by the original record. Do not restore masked values. If supporting information occurs in another passage, identify that passage separately rather than accepting it as a verbatim quotation of the original passage.

Seventy-four flagged cases had at least one other matched quote and six had none. Another matched quote is not automatically sufficient diagnostic evidence. The detailed source-text audit did not independently adjudicate every A or B quotation.

### 5 Diagnosis dates and technical failures

The output schema allowed a valid full date or null. Invalid dates, partial dates, and placeholders could make an output unusable even when the underlying diagnostic reasoning might be interpretable. A technical failure is not evidence that the patient should be excluded from the study.

If a date is clinically reviewed, distinguish the reported historical diagnosis date, the date of a diagnostic test, the first available documentation of an established diagnosis, and the ICD-derived index date. Record only the precision supported by the source. Do not invent a month or day to satisfy the model schema. A full date passing the format check, or occurring literally in the source, is not by itself a verified clinical anchor date.

### 6 Longitudinal reconciliation and source availability

The later pipelines reconcile compact chunk judgments rather than rereading all raw notes in one final call. A future review should consult original source passages and their chronology, not only model summaries. Check whether the final result lost qualifications, diagnostic revisions, or contradictory evidence.

Quote-quality issues occurred in both single-chunk and multi-chunk outputs: 49 and 31 of the 80 flagged cases, respectively. They cannot be attributed exclusively to reconciliation. Historical A's limited prefix is a separate source-availability issue; missing later documentation in its input should not be confused with evidence against a diagnosis. The 34-patient subgroup is defined by terminology position, not adjudicated diagnostic difficulty.

## Suggested review sequence if separately authorized

Start with the 31 priority source-text cases. Cases involving model/reference disagreements, the six without another matched quotation, or potentially consequential date problems can overlap this group; these counts must not be added as though they were disjoint. Expand review to other disagreements only if the specialist and study team consider it useful. This is suggested triage, not an adjudication result or a required submission task.

For each case, identify the original source passages, distinguish an existing reference decision from a proposed new decision, and state what remains unresolved. Preserve both agreement and disagreement outcomes. A selected review of flagged cases cannot establish overall cohort validity or provide an unbiased estimate of performance after reference revision.

## Record template for future decisions

Use an authorized, separately versioned patient-level record. Do not place patient identifiers or clinical excerpts in the general submission document.

| Field | What to record if review occurs |
| --- | --- |
| Review status | Not reviewed, reviewed, or unresolved; do not imply completion from queue membership. |
| Case identifier | Existing study identifier, within restricted storage only. |
| Reviewer and date | Reviewer identity/qualification and actual review date. |
| Materials examined | Source notes, relevant date range, outside reports if available, and model/reference versions. |
| Supported study category | A reviewer-assigned category, or unresolved; leave blank until assessed. |
| Source evidence | Exact supporting passages and traceable locations; preserve masking. |
| Diagnostic reasoning | Why the documentation supports the decision, including conflicting evidence and uncertainty. |
| Date and precision | Supported original date text and day/month/year/unknown precision; no invented components. |
| Quotation fidelity | Whether the original output quoted accurately, separately from label correctness. |
| Reference conflict | Whether the original reference is retained, a correction is proposed, or uncertainty remains. |
| Inclusion decision | A separate decision only if required by explicit study rules; do not infer it from diagnosis or output usability. |
| Criteria/version | The study-rule version and any adjudication agreement used. |

Existing queues use slightly different column names. The combined queue has `reviewed_label`, `reviewed_diagnosis_date`, `date_precision`, `confirmed`, `analysis_inclusion`, `rationale`, `reviewer`, and `adjudication_criteria_version`. The quote-audit queue has `adjudicated_label`, `clinical_reviewer`, `clinical_review_rationale`, and `analysis_inclusion_decision`. Use a documented mapping rather than treating these as already completed decisions.

Original references, raw model outputs, and published computational metrics must remain preserved. Any later adjudicated labels or revised analyses should be separately versioned and clearly distinguished from this repository review's original-reference evaluation. No review entry, label correction, clinical confirmation, or inclusion decision is created by this handoff.

## Supporting restricted files

- [Priority source-text queue](../NT_LLM/final_packet_20261117/restricted_review/quote_audit/clinical_review_queue.csv): suggested case-level focus from the agent-assisted audit; clinical fields are unfilled.
- [Checked case-level textual findings](../NT_LLM/final_packet_20261117/restricted_review/quote_audit/case_review_textually_checked.csv).
- [Checked quotation-level findings](../NT_LLM/final_packet_20261117/restricted_review/quote_audit/quote_review_textually_checked.csv).
- [Combined primary review queue](../NT_LLM/final_packet_20261117/restricted_review/primary/combined_pipeline/review_queue.csv) and [patient-level comparison](../NT_LLM/final_packet_20261117/restricted_review/primary/consolidated_review.csv).
- [Historical A current-policy patient results](../NT_LLM/final_packet_20261117/restricted_review/historical_A/primary/patient_results.csv) and [actual-prefix quote reconciliation](../NT_LLM/final_packet_20261117/restricted_review/historical_A/quote_scope_reconciliation.csv).
- [Methods and results](../review/REPORT.md) and [aggregate evidence review](../review/EVIDENCE_REVIEW.md).

The restricted exports contain patient-level information and are for authorized recipients only. This document has not been sent to a specialist or any other recipient.
