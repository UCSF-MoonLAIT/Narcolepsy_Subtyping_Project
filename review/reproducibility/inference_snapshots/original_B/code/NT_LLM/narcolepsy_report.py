"""Write an aggregate run report without patient IDs or clinical text."""
from pathlib import Path


def write_report(summary, manifest, output_dir):
    output_dir = Path(output_dir)
    statuses = summary["status_counts"]
    coverage = summary["metric_denominator"] / summary["gold_patients"] if summary["gold_patients"] else 0
    lines = [
        "# Narcolepsy subtyping run report", "",
        f"- Run status: {manifest['status']}",
        f"- Prediction source: {manifest['prediction_source']}",
        f"- Model configured: {manifest['model']}",
        f"- Prompt configured: {manifest['prompt_file']}",
        f"- Prompt SHA-256: {manifest['prompt_sha256']}",
        f"- Started (UTC): {manifest['started_at']}",
        f"- Finished (UTC): {manifest['finished_at']}", "",
        "## Coverage", "",
        f"Gold patients: **{summary['gold_patients']}**. Prediction records: "
        f"**{summary['prediction_records']}**. Valid matched predictions: "
        f"**{summary['metric_denominator']} ({coverage:.1%})**.", "",
        "| Evaluation status | Count |", "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {count} |" for name, count in statuses.items())
    lines.extend(["", "## Metrics", "",
                  "Metrics use valid matched predictions only. Failed, invalid, missing, and "
                  "unmatched cases remain in the coverage counts and patient-level CSV.", ""])
    metrics = summary["metrics"]
    if metrics is None:
        lines.append("No valid matched predictions; metrics are unavailable.")
    else:
        lines.extend(["| Metric | Value |", "| --- | ---: |"])
        for key in ["accuracy", "balanced_accuracy", "macro_f1", "weighted_f1"]:
            lines.append(f"| {key} | {metrics[key]:.4f} |")
        lines.extend(["", "### Per-class metrics", "",
                      "| Label | Precision | Recall | F1 |", "| --- | ---: | ---: | ---: |"])
        for label, values in metrics["per_class"].items():
            lines.append(f"| {label} | {values['precision']:.4f} | {values['recall']:.4f} | {values['f1']:.4f} |")
        lines.extend(["", "![Confusion matrix](analysis_results/confusion_matrix.png)"])
    lines.extend(["", "## Run artifacts", "",
                  "- [Evaluation summary](analysis_results/evaluation_summary.json)",
                  "- [Patient-level results](analysis_results/NT_merged_results.csv)",
                  "- [Run manifest](run_manifest.json)",
                  "- [Prompt snapshot](prompt_snapshot.txt)", ""])
    path = output_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
