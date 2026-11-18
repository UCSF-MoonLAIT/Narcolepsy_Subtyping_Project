# Stanford historical A and later pipeline methods and results

## Scope and principal finding

This report evaluates three saved pipelines on the Stanford 128-patient development cohort: historical A (v2 prompt, first 7,000 characters), original B (v2 prompt, complete available source), and combined NT2+IH (v3 prompt, complete available source). All are scored using the same four-label mapping and current primary eligibility rules. Historical A is a retrospective baseline with different runtime settings, not a controlled coverage-only comparator.

On 117 patients eligible for all three pipelines, accuracy was 31.62% for A and 57.26% for each later pipeline. On the separate 119-patient B-versus-combined intersection, accuracy remained 57.98% for each, with lower balanced accuracy and macro-F1 for the combined pipeline. These results support higher observed accuracy for the later implementations relative to historical A, without isolating the effect of full-record coverage from runtime and implementation differences.

Authorized retries of the eight original B failures and one combined failure recovered no usable outputs. Historical A was not rerun. All results are reference agreement on reused development cases; “usable,” “quote-supported,” and “clinically confirmed” remain distinct, and no new clinical adjudication was performed for this repository review.

## Methods

### Cohort and classification task

The cohort shared by all three runs comprised the existing 128 Stanford patients with selected, de-identified longitudinal documentation and reference labels from the study workbook. Documentation was enriched for sleep-related content but did not necessarily include the complete medical history, original diagnostic workup, or outside testing. The cases had been reused during pipeline development; there was no independent held-out validation cohort in this comparison.

Historical A and original B assigned NT1, NT2, IH, Uncertain, or Not_NT_IH. The combined pipeline directly assigned NT1, NT2_IH, Uncertain, or Not_NT_IH. For evaluation, NT2 and IH were mapped to NT2_IH in copies of both v2 pipelines’ predictions and the reference labels. Original predictions, references, and source text were preserved. Uncertain was a study label, not a technical failure or an imputed replacement for a missing prediction.

The prompts directed the model to abstract the diagnosis established in the longitudinal record rather than independently diagnose from isolated symptoms or test results. Both prompt versions accepted documented established specialist diagnoses when original testing was unavailable. The v3 prompt explicitly mapped established NT2, IH, or specialist terminology “narcolepsy without cataplexy” to NT2_IH. It retained Uncertain for unresolved narcolepsy subtype and prohibited inferring NT2 solely from unspecified narcolepsy plus a separate denial of cataplexy. An established diagnosis within the combined group was distinguished from a tentative differential. Not_NT_IH required documented evidence against both disorders; coexisting OSA or an unsupported narcolepsy test alone did not establish that category.

The B-versus-combined component compared two implementations with revised diagnostic instructions, output-label handling, and validation behavior; historical A adds a third implementation with different source selection and runtime settings. It was not an experiment isolating label merging as the sole change. Reference labels were used for offline evaluation and were not inserted into model classification prompts.

### Model and execution settings for the later runs

The two later runs used the same installed Qwen3 14B model digest through Ollama, temperature 0, top_p 0.1, a 40,960-token context window, a 2,048-token generation allowance, think=False, and a 128-token safety margin. The selected model, source data, references, prompts, and executed code were tracked with hashes. Each run used its own frozen code and prompt. Local tokenizer estimates were checked against server token accounting. Settings and exact model identifiers are retained in the reproducibility supplement.

### Historical A baseline and comparison design

Historical A was the completed October 2026 local-inference run using the Stanford v2 prompt and only the first 7,000 characters of each record. It used the same source and reference file hashes and the same v2 prompt hash as original B. Its manifest recorded Qwen3 14B, temperature 0, top_p 0.1, and an 8,192-token context. It did not record an explicit think setting, generation-token limit, or model digest sufficient to establish equivalence to the later frozen execution environments. Consequently, the three runs share the recorded model name, but identical historical model weights and execution defaults cannot be verified. Historical A is not the unstarted matched-settings truncation experiment.

We evaluated saved A outputs offline with the same current four-label mapping, structural validator, source-metadata checks, and primary classification policy used for the later runs. This retrospective evaluation is separate from A’s historical five-class evaluation and can yield different eligibility counts. No A inference was rerun, outputs repaired, or failures retried for this inclusion. The imported-output snapshot with unverified inference provenance was not used.

For primary three-way comparisons, all pipelines were scored on the same intersection of eligible patients. Pairwise intersections were also retained because they can include more patients; their estimates must not be mixed with three-way estimates as though denominators were identical. The B-versus-combined comparison remains separately reported on its original 119-patient intersection.

The existing strict screen verifies final quotes against the complete original record for each pipeline. For historical A, we additionally checked whether every quote was supported within the 7,000-character prefix actually presented to the model. This actual-input sensitivity is reported separately rather than silently treating full-record support as proof that A saw the cited text. Detailed source-text auditing of quote alterations remained limited to the 80 combined outputs; A received automated structural and quote verification, not equivalent clinical adjudication.

### Source processing and chunk reconciliation for the later runs

Original B and combined NT2+IH both used strategy B. The historical 7,000-character cutoff was not a truncation or chunking threshold for either later pipeline. A complete available record was classified directly if the prompt, source text, output allowance, and safety margin fit within the context window. Otherwise, source text was partitioned into contiguous chunks at tokenizer-derived character boundaries, retaining source identifiers and character offsets. The planned chunks covered the entire available record without planned gaps or truncation. In each run, 45/128 records required multiple source chunks and 83 fit in one source call. Planned full coverage did not imply that every source call completed successfully.

Each source chunk was classified using the full v2 prompt for original B or the full v3 prompt for the combined pipeline. For multi-chunk records, the same respective prompt was reused with the note-text input replaced by compact JSON judgments containing source identifiers, predicted label, diagnosis-anchor date, evidence indicators, quotations, and reasoning. Confidence was not included in this compact reconciliation input. The exact instruction prepended to those judgments was identical in both pipelines:

> CHUNK CLASSIFICATION JUDGMENTS (model-derived, reconcile all source ranges; consider diagnostic revision, preserve justified uncertainty):

Groups of judgments were recursively reconciled until one patient-level output remained. The code used a longer explanatory header while estimating how many judgments would fit; that longer header, including the statement about a chunk-level Uncertain not invalidating an established diagnosis elsewhere, was not the text sent in the reconciliation call. The shorter instruction above was the executed reconciliation header.

The final reconciliation operated on model-generated judgments, not the complete raw notes again. Information could therefore be lost during classification or compression, and a source-matching quotation could still be insufficient or irrelevant to the final diagnosis. Whole-record quote matching was performed offline for both pipelines; the combined inference runner also enforced a final quote gate against the original source text.

### Technical and structural validation

In the later runs, each inference call allowed at most two attempts within its run, including resumption. Checks identified transport errors; malformed or empty JSON; generation-limit termination; missing server token counts; local/server prompt-token discrepancies exceeding eight tokens; and context-budget overflow. Calls failing validation did not count as valid source or reconciliation checkpoints.

The current offline structural validator, also used in the later inference runs, required matching patient identifier and index date; an allowed study label; confidence coded high, medium, or low; a diagnosis-anchor-date field containing null or a valid YYYY-MM-DD calendar date; all five evidence indicators coded Yes, No, Unclear, or NotMentioned; a nonempty list of nonempty quotation strings; and nonempty reasoning. The evidence indicators covered chronic excessive daytime sleepiness, cataplexy, MSLT positivity, low CSF hypocretin, and an alternative diagnosis.

A null diagnosis date was allowed. Missing fields, partial dates, placeholders, and invalid calendar dates failed the full-date requirement. A validly formatted date did not establish source support or clinical correctness. Date accuracy was not a separately adjudicated endpoint in the reported classification metrics.

### Evidence flags and evaluation eligibility

Final quotations were classified as exact, formatting-only, or unsupported against the original supplied text. Formatting-only matching tolerated whitespace differences and equivalent quotation delimiters, while retaining wording, case, numbers, masking, negation, and other punctuation. Original quote text and available matching source spans were retained. If any final quote was unsupported, the patient received a quote-quality flag even if other quotes matched.

The combined inference runner recorded unsupported_final_evidence_quote as a patient-level error. Original B did not use that same final-quote gate. Consequently, historical run “valid/failed” counts were not directly comparable as an evidence-quality screen. Offline verification applied the same source-matching procedure to both pipelines.

For all three runs, the current primary classification analysis required structurally valid predictions, allowed labels, and matching patient/source metadata. Quote-only errors were retained as flags and did not exclude otherwise eligible predictions. Other recorded errors, missing or unusable final outputs, and metadata mismatches were excluded. The strict quote sensitivity analysis required primary eligibility plus support for every final quote. Missing predictions were never imputed, and reference disagreement was not grounds for excluding a structurally valid output. These eligibility rules were adopted after execution and inspection of quote flags, rather than specified prospectively.

Additional review flags identified the following conditions. Multiple flags could occur in one record.

| Review flag | Trigger and meaning | Effect on classification eligibility |
| --- | --- | --- |
| Unsupported quotation | One or more quotations failed source matching | Retained in primary metrics; excluded from strict quote sensitivity. Does not prove an incorrect label. |
| Formatting-normalized quotation | Quote passed permitted whitespace or delimiter normalization | Accepted in both analyses if other checks passed. |
| Date requires source review | Non-null date string did not occur literally in the source | Review flag only; string presence or absence is not clinical date verification. |
| Unknown diagnosis date | Anchor date was null | Allowed structurally; not an exclusion by itself. |
| Candidate requires clinical verification | Positive diagnostic label: NT1, NT2, IH, or NT2_IH | Review flag only. |
| Reference disagreement | Grouped model and reference labels differed | Counted as incorrect in reference-based metrics, not excluded. |
| Incomplete validated source coverage | Recorded evaluated source coverage was below 100% | Review flag; eligibility followed recorded errors and structural/metadata checks, without an additional standalone coverage exclusion. |
| Chunk reconciliation requires review | More than one source chunk was used | Review flag only. |

The export code also contained a historical-input-selection safeguard for records longer than 7,000 characters without coverage metadata; this was not the processing policy of the two strategy B runs. The later-run and A-specific review queues prioritized technical/structural failures first, then positive diagnostic candidates, reference disagreements, and unsupported quotations, followed by remaining records. Priority was an operational triage rule, not an estimate of clinical harm. Confidence did not determine eligibility or confirmation.

### Source-text quality audit

All 80 combined-pipeline quote-only flagged outputs underwent an agent-assisted source-text audit covering all 125 rejected quotations. Automated token comparisons and nearest contiguous source-span searches proposed comparison passages and highlighted insertions, omissions, substitutions, number or negation changes, and possible masked-content expansion. Candidate spans and annotations were checked case by case against original text, with corrections to misleading automatic matches. Previously checked annotations were reused only after quote identity, source hashes, and reviewed spans were reverified.

Each case was counted once according to the highest-priority observed issue: potentially substantive alterations requiring priority evidence review; other rewritten or joined quotations; capitalization/punctuation-only changes; or minor spelling/split-word-spacing changes. Generic-subject substitutions were distinguished from reconstruction of masked clinical findings. A close textual match did not override the acceptance rule, establish that a claim was false elsewhere in the record, or authorize recovery of redacted information.

This audit assessed textual fidelity and descriptive reference agreement. It was not blinded independent clinician adjudication, and inter-reviewer reliability was not measured. It did not verify all clinical claims in accepted quotations or provide an equivalent detailed audit of every original B or historical A quotation. No new clinical confirmations, adjudicated diagnosis dates, revised clinical labels, or human inclusion decisions were assigned. These activities were excluded from the submission scope. Original labels and source text were not edited.

### Clinical review scope for this repository review

No new specialist clinical review was performed or requested for this repository review. The submission reports retrospective computational agreement with the existing reference workbook and an agent-assisted source-text audit. It does not report newly confirmed diagnoses, specialist-adjudicated diagnosis dates, revised references, or clinical deployment readiness.

Clinical adjudication would require a qualified clinician, preferably with sleep-medicine expertise, to interpret the underlying longitudinal record, resolve model/reference disagreements, assess whether evidence establishes a diagnosis or subtype, and verify clinically meaningful dates. A finding that a quote is verbatim or that a JSON field is valid does not answer those questions. Such specialist effort is outside the current computational scope scope.

Existing references, unresolved disagreements, and evidence flags were retained without reinterpretation. Human confirmation and adjudication fields remain blank, representing work not performed rather than approval or exclusion. Historical review queues are preserved only for traceability or possible future work; completing them is not a requirement of this repository review's approved computational scope. Clinical validity and reference-label reliability beyond the original labeling process remain limitations.

### Authorized retries and preservation of results

On November 18, the eight original B outputs unusable under the primary policy and the one unusable combined output were retried in separate directories. Each retry environment was verified against its parent’s frozen code, prompt, model digest, generation settings, package versions, input/reference hashes, and validation rules. Previously valid call checkpoints were reused; failed calls received up to two new attempts within the authorized retry run. Successful patient outputs, including all 80 combined quote-only flagged outputs, were inherited without retry.

After both groups completed, the same primary and strict policies were applied offline and paired comparisons were recalculated. Retries were limited to this single authorized round. Recovery was defined by the same output eligibility checks, not by agreement with a reference label. Parent artifacts and all non-target patient outputs were verified unchanged. Initial outputs and new failed attempts remain separately traceable.

### Metrics and retained subgroup

We calculated accuracy, balanced accuracy, macro-F1, and per-class precision, recall, and F1. Macro-F1 averaged all four study labels with zero division assigned zero, including classes absent from a subset. Balanced accuracy averaged recall over reference classes present. Each pipeline’s individual results used its own eligible records; paired comparisons used the eligible intersection separately for primary and strict analyses. All 128 patients remained in cohort reconciliation. Correct eligible predictions divided by all expected records were also tracked as expected-record accuracy; this is a coverage-sensitive accounting measure, not accuracy among available predictions.

The exploratory 34-patient beyond-cutoff subgroup contained records with a case-insensitive match for “narcolep” or “idiopathic hypersomn” after character 7,000 and neither pattern in the first 7,000 characters. It was defined by terminology position, not clinical adjudication of where decisive evidence occurred. Both later pipelines used complete-source strategy B. Shared eligible denominators within this subgroup could be smaller than 34.

Changed labels, corrections, and regressions were calculated against the supplied grouped references. A correction meant original B incorrect and combined correct; a regression meant the reverse. No confidence intervals, hypothesis tests, or independent validation were performed. Per-pipeline confusion matrices in the packet describe individual eligible cohorts and are not paired-cohort matrices.

## Results

### Historical A eligibility and individual results

Historical A recorded 128 outputs, of which 126 passed the current primary checks. Two failed current structural validation: one invalid diagnosis date and one empty/invalid parsed JSON output. Its original saved evaluation reported 127 eligible predictions under an older evaluation policy. The current report uses 126 consistently and does not reuse the old denominator or five-class performance values.

On its own 126 eligible patients, A correctly classified 38 (30.16%), with balanced accuracy 39.66% and macro-F1 0.3482. Forty-five of these primary-eligible outputs carried unsupported-quote flags under full-record matching. A’s strict full-record source-quote screen retained 81 predictions; verification against its actual prefix retained 80. One output passed against the full record but failed the prefix screen. That record was not in the three-way strict intersection, so the three-way strict estimates below are identical under the two quote-scope definitions.

### Primary three-way comparison

| Cohort | Shared patients | Pipeline | Correct | Accuracy | Balanced accuracy | Macro-F1 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Full cohort | 117 | Historical A | 37 | 31.62% | 41.61% | 0.3637 |
| Full cohort | 117 | Original B | 67 | 57.26% | 62.69% | 0.5906 |
| Full cohort | 117 | Combined NT2+IH | 67 | 57.26% | 60.20% | 0.5580 |
| 34-patient subgroup | 31 | Historical A | 5 | 16.13% | 24.79% | 0.0908 |
| 34-patient subgroup | 31 | Original B | 19 | 61.29% | 57.05% | 0.4258 |
| 34-patient subgroup | 31 | Combined NT2+IH | 19 | 61.29% | 51.07% | 0.3782 |

The full-cohort primary intersection contained 117 patients: 14 NT1, 33 NT2_IH, 24 Uncertain, and 46 Not_NT_IH. Historical A correctly classified 37, compared with 67 for each later pipeline. Relative to A, the observed accuracy difference was 25.64 percentage points for each later pipeline. This is a retrospective difference between implementations, not a causal estimate of the benefit of reading more source text.

Within the retained 34-patient subgroup, 31 patients were eligible for all three runs. A correctly classified five, compared with 19 for each later run. This subgroup comparison directly describes how the historical prefix implementation performed when target terminology appeared only after its cutoff, while remaining confounded by runtime differences. It does not establish that terminology after the cutoff was the sole reason for individual errors.

### Primary pairwise comparisons

| Comparison | Shared patients | First pipeline accuracy | Second pipeline accuracy | First macro-F1 | Second macro-F1 | Corrections | Regressions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical A vs Original B | 118 | 31.36% | 56.78% | 0.3622 | 0.5874 | 48 | 18 |
| Historical A vs Combined NT2+IH | 125 | 30.40% | 56.00% | 0.3495 | 0.5591 | 51 | 19 |
| Original B vs Combined NT2+IH | 119 | 57.98% | 57.98% | 0.5939 | 0.5615 | 7 | 7 |

Each row uses its own shared eligible patients. On the 34-patient subgroup, A versus B used 31 patients (16.13% versus 61.29%; 17 corrections and three regressions), while A versus combined used 34 (14.71% versus 61.76%; 20 corrections and four regressions). These pairwise estimates complement, rather than replace, the three-way comparison.

### Three-way strict sensitivity and input scope

| Cohort | Shared patients | Pipeline | Correct | Accuracy | Balanced accuracy | Macro-F1 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Full cohort | 17 | Historical A | 4 | 23.53% | 21.53% | 0.1417 |
| Full cohort | 17 | Original B | 9 | 52.94% | 61.81% | 0.5952 |
| Full cohort | 17 | Combined NT2+IH | 10 | 58.82% | 66.67% | 0.5750 |
| 34-patient subgroup | 5 | Historical A | 0 | 0.00% | 0.00% | 0.0000 |
| 34-patient subgroup | 5 | Original B | 4 | 80.00% | 83.33% | 0.4500 |
| 34-patient subgroup | 5 | Combined NT2+IH | 4 | 80.00% | 83.33% | 0.4500 |

Only 17 patients were eligible for all three runs under strict full-record quote verification. The actual-input restriction for A left this intersection unchanged. The shared strict subgroup contained five patients: A was correct on none and each later pipeline on four. These small, selected subsets are descriptive and do not support broad superiority claims.

The prefix restriction does affect some other denominators. A-versus-combined strict full-record matching had 28 shared patients, whereas matching A quotations to its actual prefix left 27. Both versions are retained explicitly in the aggregate supplementary results. A-versus-B strict matching had 28 shared patients under either definition. Input-scope checks do not change primary classification eligibility.

### Later-pipeline usable outputs and retry outcomes

Both pipelines recorded outcomes for all 128 patients. The final primary evaluation retained 120 original B predictions (93.75%) and 127 combined predictions (99.22%). The seven-output difference was 5.47 percentage points in usable-output coverage. It was not an accuracy gain.

| Pipeline | Initial usable outputs / 128 | Outputs retried | New failed call attempts | Usable outputs recovered | Remaining unusable outputs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original pipeline B | 120 | 8 | 16 | 0 | 8 |
| Combined NT2+IH | 127 | 1 | 2 | 0 | 1 |

On the last retry attempt for each original B target, five failures involved invalid diagnosis dates, two involved invalid labels, and one involved malformed/empty JSON with generation-limit termination. The single combined target again failed diagnosis-date validation. These are output-validation failures, not evidence that the patients themselves were unsuitable for study inclusion. With no recoveries, primary and strict performance remained identical to the initial evaluation.

Seventy-five original B predictions and 80 combined predictions had unsupported-quote flags but remained primary eligible. Strict quote sensitivity retained 45 original B and 47 combined predictions. The combined parent manifest’s 47 “valid” and 81 “failed” outcomes reflect its original gate: the 81 comprise 80 quote-only flagged outputs plus one unusable output. They must not be interpreted as 81 classification failures under the approved primary policy.

On each pipeline’s individual primary cohort, original B accuracy was 57.50% (69/120), balanced accuracy 62.67%, and macro-F1 0.5907. Combined values were 56.69% (72/127), 60.64%, and 0.5624. Correct predictions divided by all 128 expected records were 53.91% and 56.25%, respectively. These measures reflect different eligible cohorts; the paired comparisons below provide the direct classification comparison.

### B versus combined paired performance

| Analysis | Cohort | Shared patients | Original B accuracy | Combined accuracy | Original B balanced accuracy | Combined balanced accuracy | Original B macro-F1 | Combined macro-F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary classification | Full cohort | 119 | 57.98% | 57.98% | 62.85% | 60.36% | 0.5939 | 0.5615 |
| Primary classification | Beyond-cutoff subgroup | 31 | 61.29% | 61.29% | 57.05% | 51.07% | 0.4258 | 0.3782 |
| Strict quote sensitivity | Full cohort | 28 | 57.14% | 67.86% | 63.33% | 67.86% | 0.6114 | 0.6162 |
| Strict quote sensitivity | Beyond-cutoff subgroup | 5 | 80.00% | 80.00% | 83.33% | 83.33% | 0.4500 | 0.4500 |

The primary intersection contained 119 patients. The union of primary eligible records contained all 128 patients: one was eligible only for original B and eight only for the combined pipeline. Thus, paired accuracy describes the 119 patients with usable outputs from both pipelines; it does not include all 128 expected patients.

Both pipelines correctly classified 69/119 shared patients. There were 21 changed labels: seven corrections, seven regressions, and seven changes between incorrect labels. Sixty-two predictions were correct under both pipelines and 43 incorrect under both. Balanced accuracy and macro-F1 were lower for the combined pipeline despite equal overall accuracy.

### B versus combined primary paired results by reference category

| Reference category | Patients | Original B precision | Combined precision | Original B recall | Combined recall | Original B F1 | Combined F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| NT1 | 15 | 87.50% | 87.50% | 93.33% | 93.33% | 0.9032 | 0.9032 |
| NT2_IH | 34 | 56.14% | 48.48% | 94.12% | 94.12% | 0.7033 | 0.6400 |
| Uncertain | 24 | 25.00% | 16.67% | 29.17% | 8.33% | 0.2692 | 0.1111 |
| Not_NT_IH | 46 | 88.89% | 84.00% | 34.78% | 45.65% | 0.5000 | 0.5915 |

NT1 performance was unchanged. NT2_IH recall remained 94.12%, while precision decreased from 56.14% to 48.48%. Not_NT_IH recall increased from 34.78% to 45.65%, while Uncertain recall decreased from 29.17% to 8.33%. These shifts account for unchanged overall accuracy alongside lower balanced accuracy and macro-F1.

### Beyond-cutoff subgroup

Original B had 31 usable predictions among the 34 subgroup patients, compared with 34 for the combined pipeline. On the shared 31, both correctly classified 19 (61.29%). Five labels changed: two corrections, two regressions, and one change between incorrect labels. The paired reference distribution was 12 NT2_IH, six Uncertain, 13 Not_NT_IH, and no NT1. The absence of NT1 contributes a zero term to the fixed four-class macro-F1 and should be considered when interpreting its magnitude.

On their individual eligible subgroup cohorts, original B correctly classified 19/31 and the combined pipeline 21/34. These individual figures do not establish paired superiority. The subgroup identifies records potentially vulnerable to the historical prefix cutoff; it does not directly measure an effect of truncation in the two complete-source runs evaluated here.

### Strict quote sensitivity

The strict intersection contained 28 patients. Original B correctly classified 16/28 and the combined pipeline 19/28, with four corrections and one regression. Its reference distribution was three NT1, six NT2_IH, five Uncertain, and 14 Not_NT_IH. The higher combined accuracy in this selected subset does not establish improvement in the larger primary cohort.

The strict subgroup retained eight original B and 11 combined predictions individually, with only five shared eligible patients. Both correctly classified four of these five, and no labels changed. The five reference cases comprised two NT2_IH and three Not_NT_IH, with neither NT1 nor Uncertain represented. Strict results are conditional on both pipelines passing source-quote checks; their small, selected denominators limit interpretation.

### Evidence-quality findings

The 80 flagged combined outputs contained 277 quotations: 152 passed source matching and 125 were rejected. Findings were counted at both case and rejected-quote levels.

| Highest-priority issue within a case | Cases |
| --- | ---: |
| Priority evidence review | 31 |
| Other rewritten or joined quotations | 38 |
| Capitalization/punctuation-only changes | 9 |
| Minor spelling/split-word-spacing-only changes | 2 |
| Total | 80 |

Among the 125 rejected quotes, 36 were assigned priority review, 53 other rewriting/joining issues, 34 capitalization or punctuation changes, and two minor text-normalization changes. Masked clinical-content expansion or cross-passage replacement affected 33 quotes in 28 cases. Seventy-four cases had at least one other accepted quote; six had none. Forty-nine flagged cases were single-chunk and 31 multi-chunk, so quote problems were not confined to reconciliation.

Within this selected flagged group, 46/80 labels agreed with the grouped reference and 34 disagreed. Neither quote failure nor quote acceptance established diagnostic correctness, and the source-text audit did not adjudicate these disagreements. Minor changes identified in the audit were not retrospectively accepted by relaxing the source-matching rules.

## Interpretation and limitations

The combined pipeline improved technical output coverage but did not improve primary paired accuracy; balanced accuracy and macro-F1 were lower. Authorized retries produced no additional usable predictions and did not change this conclusion. The beyond-cutoff subgroup showed equal paired accuracy and lower combined balanced accuracy and macro-F1. Strict sensitivity favored combined accuracy in a much smaller selected cohort, which cannot support a general superiority claim.

Historical A had lower observed accuracy and macro-F1 than the later implementations on the shared primary cohort, especially within the beyond-cutoff subgroup. Because A used a shorter context and unverified execution defaults, the magnitude cannot be attributed solely to source truncation. A matched-settings experiment would be needed to isolate that effect. A also produced usable outputs more often than original B under the current structural rule (126 versus 120), illustrating that output coverage and diagnostic agreement are separate outcomes.

The comparison is limited by development-cohort reuse, post-run selection of the primary eligibility policy, absence of independent validation or uncertainty intervals, incomplete available clinical histories, prompt and validation differences between pipelines, incomplete historical A model/runtime provenance, and possible information loss in recursive reconciliation. The reference workbook was preserved rather than independently readjudicated. Date validity was checked computationally, but date accuracy and clinical utility were not established. Detailed source-text auditing focused on the 80 combined quote-flagged outputs and was not an independent clinician quality assessment of all outputs.

These results support reporting improved usable-output coverage with unchanged paired accuracy, not improved diagnostic performance or clinical readiness. Any future claim about clinical validity or readiness would require appropriate clinician review and independent validation; those activities are outside this repository review.

## Conclusion

Combining NT2 and idiopathic hypersomnia into a single inference category did not improve classification agreement over the pipeline that assigned them separately. When both pipelines were evaluated using the same four-category scheme on 119 shared eligible patients, accuracy was identical at 57.98%, while macro-F1 decreased from 0.5939 to 0.5615 with combined labeling. The combined pipeline produced more usable outputs—127 of 128 patients versus 120 of 128—but this operational advantage did not translate into better paired classification performance. These findings do not support label consolidation as a sufficient solution to the remaining classification difficulties.

The comparison with historical pipeline A identified limited source access as an important potential contributor to earlier poor performance. A processed only the first 7,000 characters of each record, and 34 patients had target diagnostic terminology exclusively beyond that cutoff. On the 117 patients eligible for all three pipelines, accuracy was 31.62% for historical A and 57.26% for each later full-source pipeline. Within the 31 shared eligible subgroup patients, accuracy was 16.13% for A and 61.29% for both later pipelines. These observations underscore the importance of preserving access to longitudinal documentation. However, differences in context size and other runtime settings prevent attributing the improvement solely to source coverage.

Full-source processing therefore addressed an identified input limitation but did not eliminate difficulties interpreting diagnostic certainty, conflicting longitudinal documentation, or supporting evidence. The combined pipeline’s lower NT2/IH precision and reduced recognition of reference-Uncertain cases suggest that collapsing diagnostic categories did not resolve these challenges. Persistent quotation-fidelity problems further demonstrate that structurally valid outputs and source-matched quotations cannot establish clinical correctness.

Overall, this development-cohort comparison supports prioritizing source completeness while evaluating label consolidation separately from output usability. The results remain descriptive agreement with existing reference labels: the primary eligibility policy was adopted after execution, no new specialist adjudication was performed, and no independent validation cohort was evaluated. The findings support further methodological refinement, rather than claims of clinical validation or deployment readiness.

## Supporting records

- [Results tables and figures](TABLES_AND_FIGURES.md), including [three-way primary confusion matrices](figures/figure_3_three_way_primary_confusion.png) and [three-way strict matrices](figures/figure_4_three_way_strict_confusion.png).

- [Historical A and three-pipeline results](results/historical_A/comparison.json), [actual-input quote sensitivity](results/historical_A/input_scope_strict_comparison.json), and [historical A configuration](reproducibility/historical_A_run_manifest.json).

- [Primary paired metrics](results/primary/paired_comparisons.json) and [strict sensitivity paired metrics](results/strict_sensitivity/paired_comparisons.json).
- [Aggregate evidence review](EVIDENCE_REVIEW.md) and [quote-audit counts](reproducibility/quote_audit_summary.json).
- [Reproducibility guide](reproducibility/README.md), with original prompt snapshots, frozen inference code/configurations, evaluation code, and artifact hashes.
- [Retry verification](reproducibility/retry_verification.json), documenting completion, failures, and preserved parent/non-target outputs.

Patient-level predictions, quotations, failure details, and blank adjudication fields remain in the separate restricted appendix. Retained review queues do not represent an outstanding submission requirement. The general packet contains aggregate results only.
