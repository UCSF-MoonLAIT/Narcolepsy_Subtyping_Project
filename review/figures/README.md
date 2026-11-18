# Figures

| Figure | Patients compared | Files |
| --- | --- | --- |
| 1: Primary B versus combined | 119 shared patients; 31 subgroup patients | [PNG](figure_1_primary_paired_confusion.png), [PDF](figure_1_primary_paired_confusion.pdf) |
| 2: Strict B versus combined | 28 shared patients; five subgroup patients | [PNG](figure_2_strict_paired_confusion.png), [PDF](figure_2_strict_paired_confusion.pdf) |
| 3: Primary A/B/combined | 117 shared patients; 31 subgroup patients | [PNG](figure_3_three_way_primary_confusion.png), [PDF](figure_3_three_way_primary_confusion.pdf) |
| 4: Strict A/B/combined | 17 shared patients; five subgroup patients | [PNG](figure_4_three_way_strict_confusion.png), [PDF](figure_4_three_way_strict_confusion.pdf) |

Cells show counts and percentages within each reference category. Gray rows have no reference cases. Macro-F1 still uses all four study labels. The complete captions are in [TABLES_AND_FIGURES.md](../TABLES_AND_FIGURES.md).

`paired_confusion_matrices.json` supports regeneration of Figures 1–2. Figures 3–4 use the aggregate A-inclusive comparison JSON. All figures can be regenerated without patient data using the [offline reproduction commands](../../docs/REPRODUCING_RESULTS.md). Historical A differs in runtime/source selection; the figures are descriptive comparisons rather than causal estimates of coverage alone.
