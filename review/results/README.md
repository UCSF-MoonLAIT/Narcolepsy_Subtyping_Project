# Aggregate results index

| Folder | Interpretation |
| --- | --- |
| [primary/](primary/) | Original B versus combined. Individual pipeline summaries have their own eligible denominators; `paired_comparisons.json` uses identical patients within each comparison. |
| [strict_sensitivity/](strict_sensitivity/) | B versus combined after source-quote verification. Different patient composition from primary. |
| [historical_A/](historical_A/) | A-inclusive individual, pairwise and three-way results under current four-label rules; additional actual-prefix quote sensitivity. |

The B/combined primary intersection is 119 patients, while the three-way A/B/combined intersection is 117. Both have 31 shared patients in the 34-patient beyond-cutoff subgroup. Strict intersections are 28 and 17, respectively, with five subgroup patients each.

Individual confusion matrices in pipeline subfolders are not paired-cohort figures. Use the [paired and three-way figures](../figures/README.md) for direct comparisons. [TABLES_AND_FIGURES.md](../TABLES_AND_FIGURES.md) provides captions and metric definitions. A's primary eligibility of 126 and four-label metrics must not be mixed with the older five-label evaluation's 127-patient denominator.

All JSON here is aggregate. Patient-level reconciliation tables remain in authorized local storage, not this results tree.
