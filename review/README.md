# Current aggregate review snapshot

Updated November 18, 2026. This is an intermediate repository deliverable for the Stanford 128-patient project, not a journal submission or a clinically validated product.

1. Read [REPORT.md](REPORT.md) for the question, methods, three-run results, limitations, and conclusion.
2. Open [TABLES_AND_FIGURES.md](TABLES_AND_FIGURES.md) for seven tables and four figures. [Figures](figures/) are available as PNG and PDF.
3. Use [results/](results/) for aggregate metrics. `primary/` and `strict_sensitivity/` retain the original B-versus-combined comparisons; `historical_A/` adds pairwise/three-way comparisons and A-prefix quote sensitivity. These analyses have different explicitly labeled denominators.
4. Read [EVIDENCE_REVIEW.md](EVIDENCE_REVIEW.md) for the aggregate source-text audit of 80 combined outputs.
5. Use [reproducibility/](reproducibility/README.md) for prompt snapshots, frozen inference versions, evaluation code, and provenance records. [manifest.json](manifest.json) inventories the aggregate snapshot with file hashes.

The principal comparison concerns separate versus combined labeling; historical A provides supporting context about note coverage. All three runs use the same four-label evaluation mapping. The 34-patient subgroup is retained. Retry results are complete and unchanged from the initial classification estimates.

Patient-level data and review exports are excluded from this aggregate folder and Git. Authorized local copies remain in `NT_LLM/`, described in [data and access](../docs/DATA_AND_ACCESS.md). The earlier `NT_LLM/final_packet_20261117/general` path resolves here for compatibility; it is not a second copy of the results. Clinical adjudication was not performed and is not a completion condition for this computational scope.
