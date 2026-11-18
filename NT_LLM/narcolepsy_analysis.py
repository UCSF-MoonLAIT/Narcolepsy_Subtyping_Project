"""Evaluate the Stanford five-class patient predictions."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from NT_LLM.label_schemes import labels_for, grouped_label
from NT_LLM.validation import validate_output, evidence_quote_support
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, precision_score, recall_score)

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "NT_LLM/Stanford_NT_IH_128_sleep_only_2026-07-27_with_first_dx_dates.xlsx"
PREDICTIONS = ROOT / "NT_LLM/NT_128pt_outputs/nt_patient_llm_outputs.jsonl"
OUTPUT = ROOT / "NT_LLM/NT_128pt_outputs/analysis_results"
LABELS = ["NT1", "NT2", "IH", "Uncertain", "Not_NT_IH"]
STATUSES = ["valid", "missing_prediction", "unmatched_prediction", "inference_error",
            "invalid_prediction", "prediction_metadata_mismatch", "quote_quality_failure"]
EVALUATION_POLICIES = ['recorded', 'classification', 'strict']
QUOTE_ERROR = 'unsupported_final_evidence_quote'


def normalized_id(value):
    if pd.isna(value) or not str(value).strip():
        raise ValueError("A patient ID is missing")
    value = str(value).strip()
    return value[:-2] if value.endswith(".0") and value[:-2].isdigit() else value


def read_predictions(path, label_scheme='five', source_records=None):
    records = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid prediction JSONL line {number}") from exc
            if not isinstance(item, dict) or "BDSPPatientID" not in item:
                raise ValueError(f"Prediction line {number} lacks a patient ID")
            prediction = item.get("llm_output")
            prediction = prediction if isinstance(prediction, dict) else {}
            mapped = dict(prediction, final_label=grouped_label(prediction.get('final_label'), label_scheme))
            schema_errors = validate_output(mapped, item['BDSPPatientID'], item.get('index_date'), '', label_scheme)
            source = (source_records or {}).get(normalized_id(item['BDSPPatientID']))
            matches = evidence_quote_support(prediction, source['raw_notetxt']) if source is not None else []
            quote_status = ('not_checked' if source_records is None else
                            'source_missing' if source is None else
                            'unavailable' if not matches else
                            'flagged' if any(q['match_type'] == 'unsupported' for q in matches) else 'passed')
            records.append({
                "BDSPPatientID": normalized_id(item["BDSPPatientID"]),
                "index_date": item.get("index_date"),
                "final_label": prediction.get("final_label"),
                "confidence": prediction.get("confidence"),
                "diagnosis_anchor_date": prediction.get("diagnosis_anchor_date"),
                "error": item.get("error"),
                "parse_error": bool(prediction.get("parse_error")),
                "embedded_id_match": str(prediction.get("patient_id")) == str(item["BDSPPatientID"]),
                "embedded_date_match": str(prediction.get("index_date")) == str(item.get("index_date")),
                "structural_errors": ';'.join(schema_errors),
                "source_metadata_match": source_records is None or (source is not None and item.get('index_date') == source['index_date']),
                "quote_quality_status": quote_status,
                "unsupported_quote_count": sum(q['match_type'] == 'unsupported' for q in matches),
                "formatting_only_quote_count": sum(q['match_type'] == 'formatting_only' for q in matches),
            })
    if not records:
        raise ValueError("Prediction JSONL is empty")
    result = pd.DataFrame(records)
    if result.BDSPPatientID.duplicated().any():
        raise ValueError("Prediction JSONL contains duplicate patient IDs")
    return result


def read_gold(gold_path):
    gold = pd.read_excel(gold_path).rename(columns={"bdsp_patient_id": "BDSPPatientID"})
    required = {"BDSPPatientID", "final_label_gold"}
    if required - set(gold.columns):
        raise ValueError(f"Gold standard missing columns: {sorted(required - set(gold.columns))}")
    gold["BDSPPatientID"] = gold.BDSPPatientID.map(normalized_id)
    if gold.BDSPPatientID.duplicated().any():
        raise ValueError("Gold standard contains duplicate patient IDs")
    if not gold.final_label_gold.isin(LABELS).all():
        raise ValueError("Gold standard has missing or non-study labels")
    return gold


def evaluate(gold_path, predictions_path, output_dir, label_scheme="five", evaluation_policy='recorded', source_path=None):
    if evaluation_policy not in EVALUATION_POLICIES:
        raise ValueError('Unknown evaluation policy')
    if evaluation_policy != 'recorded' and source_path is None:
        raise ValueError('Classification and strict analyses require original source notes for metadata and separate quote-quality checks')
    labels = labels_for(label_scheme)
    gold = read_gold(gold_path)
    source_records = None
    if source_path is not None:
        from narcolepsy_stanford import normalize_nt_date
        source = pd.read_parquet(source_path)
        source['BDSPPatientID'] = source.BDSPPatientID.map(normalized_id)
        if source.BDSPPatientID.duplicated().any():
            raise ValueError('Duplicate source patient IDs')
        source['index_date'] = source.index_date.map(normalize_nt_date)
        source['raw_notetxt'] = source.raw_notetxt.fillna('').astype(str)
        source_records = source.set_index('BDSPPatientID').to_dict('index')
    predictions = read_predictions(predictions_path, label_scheme, source_records)
    gold['final_label_gold_original'] = gold.final_label_gold
    predictions['final_label_original'] = predictions.final_label
    gold['final_label_gold'] = gold.final_label_gold.map(lambda x: grouped_label(x, label_scheme))
    predictions['final_label'] = predictions.final_label.map(lambda x: grouped_label(x, label_scheme))
    merged = gold.merge(predictions, on="BDSPPatientID", how="outer",
                        indicator=True, validate="one_to_one")

    def status(row):
        if row["_merge"] == "left_only":
            return "missing_prediction"
        if row["_merge"] == "right_only":
            return "unmatched_prediction"
        recorded_error = pd.notna(row['error']) and bool(str(row['error']).strip())
        quote_only = row['error'] == QUOTE_ERROR
        if recorded_error and not (evaluation_policy != 'recorded' and quote_only):
            return "inference_error"
        if row["parse_error"] or pd.isna(row["final_label"]) or row["final_label"] not in labels:
            return "invalid_prediction"
        if not row["embedded_id_match"] or not row["embedded_date_match"]:
            return "prediction_metadata_mismatch"
        if evaluation_policy != 'recorded':
            if not row['source_metadata_match']:
                return 'prediction_metadata_mismatch'
            if row['structural_errors']:
                return 'invalid_prediction'
            if evaluation_policy == 'strict' and row['quote_quality_status'] != 'passed':
                return 'quote_quality_failure'
        return "valid"

    merged["evaluation_status"] = merged.apply(status, axis=1)
    merged['metric_eligible'] = merged.evaluation_status.eq('valid')
    valid = merged[merged.evaluation_status == "valid"]
    counts = merged.evaluation_status.value_counts()
    summary = {
        "gold_patients": len(gold), "prediction_records": len(predictions),
        "status_counts": {key: int(counts.get(key, 0)) for key in STATUSES},
        "metric_denominator": len(valid),
        "expected_record_accuracy": float((valid.final_label_gold == valid.final_label).sum() / len(gold)) if len(gold) else None,
        "prediction_distribution": {label: int((predictions.final_label == label).sum()) for label in labels},
        "label_order": labels,
        "label_scheme": label_scheme,
        "evaluation_policy": evaluation_policy,
        "quote_quality_counts": {key: int((predictions.quote_quality_status == key).sum())
                                 for key in ['passed', 'flagged', 'unavailable', 'source_missing', 'not_checked']},
        "quote_flagged_predictions_in_metrics": int((valid.quote_quality_status == 'flagged').sum()),
        "quote_only_recorded_errors_in_metrics": int((valid.error == QUOTE_ERROR).sum()),
        "label_mapping": {"NT2": "NT2_IH", "IH": "NT2_IH"} if label_scheme == "combined" else {},
        "metric_definition": f"{len(labels)}-class metrics on eligible matched predictions under {evaluation_policy} policy; macro-F1 uses all study labels",
        "eligibility_definition": {
            'recorded': 'Historical policy: exclude every recorded output error; require label/parse and embedded metadata validity.',
            'classification': 'Require complete structural output, valid label and matching metadata. A quote-only recorded error does not exclude a prediction; evidence flags remain visible. Other errors remain excluded.',
            'strict': 'Classification eligibility plus source-grounded quote checks applied identically to every run using original notes.',
        }[evaluation_policy],
        "provenance": {"reference_sha256": hashlib.sha256(Path(gold_path).read_bytes()).hexdigest(),
                       "predictions_sha256": hashlib.sha256(Path(predictions_path).read_bytes()).hexdigest(),
                       "source_sha256": hashlib.sha256(Path(source_path).read_bytes()).hexdigest() if source_path else None,
                       "evaluation_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       "validation_code_sha256": hashlib.sha256((ROOT/'NT_LLM/validation.py').read_bytes()).hexdigest()},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = ["BDSPPatientID", "final_label_gold", "final_label", "final_label_gold_original", "final_label_original", "evaluation_status",
               "confidence", "index_date", "diagnosis_anchor_date", "error",
               "metric_eligible", "quote_quality_status", "unsupported_quote_count", "formatting_only_quote_count", "structural_errors", "source_metadata_match",
               "ICD_label", "first_nt_date", "first_ih_date"]
    merged[[c for c in columns if c in merged]].to_csv(output_dir / "NT_merged_results.csv", index=False)

    if len(valid):
        truth, predicted = valid.final_label_gold, valid.final_label
        summary["metrics"] = {
            "accuracy": accuracy_score(truth, predicted),
            "balanced_accuracy": balanced_accuracy_score(truth, predicted),
            "macro_f1": f1_score(truth, predicted, labels=labels, average="macro", zero_division=0),
            "weighted_f1": f1_score(truth, predicted, average="weighted"),
            "per_class": {label: {
                "support": int((truth == label).sum()),
                "predicted_count": int((predicted == label).sum()),
                "precision": precision_score(truth, predicted, labels=[label], average=None, zero_division=0)[0],
                "recall": recall_score(truth, predicted, labels=[label], average=None, zero_division=0)[0],
                "f1": f1_score(truth, predicted, labels=[label], average=None, zero_division=0)[0],
            } for label in labels},
        }
        matrix = confusion_matrix(truth, predicted, labels=labels)
        summary["confusion_matrix"] = matrix.tolist()
        fig, ax = plt.subplots(figsize=(8, 7))
        ConfusionMatrixDisplay(matrix, display_labels=labels).plot(
            ax=ax, cmap="Blues", values_format="d", colorbar=False)
        ax.set(title="LLM vs Gold Standard Confusion Matrix",
               xlabel="Predicted Label", ylabel="Gold Standard Label")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        fig.savefig(output_dir / "confusion_matrix.png", dpi=300, bbox_inches="tight")
        plt.close(fig)
    else:
        summary["metrics"] = None
    (output_dir / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2, default=lambda x: x.item()) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=lambda x: x.item()))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=GOLD)
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--label-scheme", choices=["five", "combined"], default="five")
    parser.add_argument('--evaluation-policy', choices=EVALUATION_POLICIES, default='recorded')
    parser.add_argument('--source', type=Path, help='Original notes for quote-quality and metadata checks')
    args = parser.parse_args()
    evaluate(args.gold, args.predictions, args.output_dir, label_scheme=args.label_scheme,
             evaluation_policy=args.evaluation_policy, source_path=args.source)
