# Results tables and figure captions

Results include the completed authorized retries. No unusable outputs were recovered. All three pipelines use the same four-label evaluation scheme. Historical A is retrospective and was not rerun.

## Table 1 Cohort accounting

| Pipeline | Primary usable / 128 | Usable coverage | Quote-flagged predictions included | Strict eligible / 128 | Retried | Recovered | Remaining unusable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical A | 126 | 98.44% | 45 | 81 | 0 | 0 | 2 |
| Original pipeline B | 120 | 93.75% | 75 | 45 | 8 | 0 | 8 |
| Combined NT2+IH | 127 | 99.22% | 80 | 47 | 1 | 0 | 1 |

Quote-quality flags do not establish diagnostic errors. The A strict count of 81 uses complete-record matching; requiring support within the actual 7,000-character prefix gives 80. A was not retried; its two current structural exclusions differ from the eight B and one combined failures targeted for retry. Strict eligibility otherwise requires support for every final quote.

## Table 2 B versus combined paired performance

| Analysis | Shared patients | B accuracy | Combined accuracy | B balanced accuracy | Combined balanced accuracy | B macro-F1 | Combined macro-F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Primary: full cohort | 119 | 57.98% | 57.98% | 62.85% | 60.36% | 0.5939 | 0.5615 |
| Primary: 34-patient subgroup | 31 | 61.29% | 61.29% | 57.05% | 51.07% | 0.4258 | 0.3782 |
| Strict sensitivity: full cohort | 28 | 57.14% | 67.86% | 63.33% | 67.86% | 0.6114 | 0.6162 |
| Strict sensitivity: 34-patient subgroup | 5 | 80.00% | 80.00% | 83.33% | 83.33% | 0.4500 | 0.4500 |

Each row compares identical eligible patients. Primary and strict subsets differ. Macro-F1 includes all four labels, even when a subset lacks a reference class; balanced accuracy averages recall over reference classes present.

## Table 3 B versus combined primary paired results by reference category

| Reference category | Patients | B precision | Combined precision | B recall | Combined recall | B F1 | Combined F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| NT1 | 15 | 87.50% | 87.50% | 93.33% | 93.33% | 0.9032 | 0.9032 |
| NT2_IH | 34 | 56.14% | 48.48% | 94.12% | 94.12% | 0.7033 | 0.6400 |
| Uncertain | 24 | 25.00% | 16.67% | 29.17% | 8.33% | 0.2692 | 0.1111 |
| Not_NT_IH | 46 | 88.89% | 84.00% | 34.78% | 45.65% | 0.5000 | 0.5915 |

## Table 4 Evidence-quality findings in the 80 flagged combined outputs

| Highest-priority issue | Cases |
| --- | ---: |
| Priority evidence review | 31 |
| Other rewritten or joined quotations | 38 |
| Capitalization/punctuation only | 9 |
| Minor spelling/split-word spacing only | 2 |
| Total | 80 |

Cases are mutually exclusive, assigned by highest-priority issue. All 125 rejected quotations were examined. These are source-text quality findings, not clinical adjudications.

## Figure 1 Primary paired confusion matrices

[Display Figure 1](figures/figure_1_primary_paired_confusion.png). Panels A/B compare 119 shared eligible patients; C/D compare 31 shared eligible patients within the 34-patient beyond-cutoff subgroup. Both pipelines correctly classify 69/119 and 19/31, respectively. Cells show counts and row percentages; zero-support rows are gray.

## Figure 2 Strict sensitivity paired confusion matrices

[Display Figure 2](figures/figure_2_strict_paired_confusion.png). Panels A/B compare 28 shared strict-eligible patients; C/D compare five shared strict-eligible subgroup patients. Original B correctly classifies 16/28 and combined 19/28; both correctly classify 4/5 in the subgroup. These small, selected subsets should not be interpreted as demonstrating superiority on the primary cohort.

All results are development-set reference agreement. No confidence intervals or hypothesis tests are shown. Patient-level data remain in the restricted appendix.


## Table 5 Primary three-way common-cohort performance

| Cohort | Shared patients | Pipeline | Correct | Accuracy | Balanced accuracy | Macro-F1 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Full cohort | 117 | Historical A | 37 | 31.62% | 41.61% | 0.3637 |
| Full cohort | 117 | Original B | 67 | 57.26% | 62.69% | 0.5906 |
| Full cohort | 117 | Combined NT2+IH | 67 | 57.26% | 60.20% | 0.5580 |
| 34-patient subgroup | 31 | Historical A | 5 | 16.13% | 24.79% | 0.0908 |
| 34-patient subgroup | 31 | Original B | 19 | 61.29% | 57.05% | 0.4258 |
| 34-patient subgroup | 31 | Combined NT2+IH | 19 | 61.29% | 51.07% | 0.3782 |

All three pipelines are evaluated on the same patients within each cohort. Historical A used different context/runtime settings; this is not a controlled truncation experiment.

## Table 6 Primary pairwise performance including historical A

| Comparison | Shared patients | First pipeline accuracy | Second pipeline accuracy | First macro-F1 | Second macro-F1 | Corrections | Regressions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical A vs Original B | 118 | 31.36% | 56.78% | 0.3622 | 0.5874 | 48 | 18 |
| Historical A vs Combined NT2+IH | 125 | 30.40% | 56.00% | 0.3495 | 0.5591 | 51 | 19 |
| Original B vs Combined NT2+IH | 119 | 57.98% | 57.98% | 0.5939 | 0.5615 | 7 | 7 |

Denominators differ by pair. Corrections and regressions are from the first pipeline to the second.

## Table 7 Three-way strict source-quote sensitivity

| Cohort | Shared patients | Pipeline | Correct | Accuracy | Balanced accuracy | Macro-F1 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Full cohort | 17 | Historical A | 4 | 23.53% | 21.53% | 0.1417 |
| Full cohort | 17 | Original B | 9 | 52.94% | 61.81% | 0.5952 |
| Full cohort | 17 | Combined NT2+IH | 10 | 58.82% | 66.67% | 0.5750 |
| 34-patient subgroup | 5 | Historical A | 0 | 0.00% | 0.00% | 0.0000 |
| 34-patient subgroup | 5 | Original B | 4 | 80.00% | 83.33% | 0.4500 |
| 34-patient subgroup | 5 | Combined NT2+IH | 4 | 80.00% | 83.33% | 0.4500 |

The three-way results are identical after additionally restricting A quotes to the actual input prefix. Other pairwise strict results can differ by quote scope; see the input-scope sensitivity JSON.

## Figure 3 Historical A and later pipelines on the primary common cohort

[Display Figure 3](figures/figure_3_three_way_primary_confusion.png). Top panels show the 117 patients eligible for all three pipelines; bottom panels show the 31 shared eligible patients within the 34-patient subgroup. Cells are counts and row percentages.

## Figure 4 Historical A and later pipelines on the strict common cohort

[Display Figure 4](figures/figure_4_three_way_strict_confusion.png). Top panels show 17 shared strict-eligible patients; bottom panels show five subgroup patients. Matching A quotes to its actual prefix leaves both intersections unchanged.
