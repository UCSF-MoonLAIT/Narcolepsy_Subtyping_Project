# Prompt templates

- [stanford_v2.txt](stanford_v2.txt): five-label chart abstraction used by historical A and original B.
- [stanford_v3.txt](stanford_v3.txt): combined NT2/IH chart abstraction used by the combined pipeline.

The exact executed prompt snapshots and run configurations are in [review/reproducibility](../review/reproducibility/README.md). The v3 prompt is not the chunk-combination header: reconciliation reuses each run's full respective prompt with model-derived chunk judgments in the source-text field. See the [methods](../review/REPORT.md#source-processing-and-chunk-reconciliation-for-the-later-runs).

These templates are retained without changing the completed runs. Reading them does not start inference.
