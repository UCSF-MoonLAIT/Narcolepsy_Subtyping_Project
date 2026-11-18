from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import time
import os
import re
import subprocess
import fcntl
from contextlib import contextmanager
import pandas as pd
import ollama
from tqdm import tqdm

# =========================
# CONFIG
# =========================

REPO_ROOT = Path(__file__).resolve().parent
INPUT_DIR = REPO_ROOT / "NT_LLM" / "NT_goldstd_128pt.parquet"
OUTPUT_DIR = REPO_ROOT / "NT_LLM" / "NT_128pt_outputs"
MODEL_NAME = "qwen3:14b"
BATCH_SIZE = 1
MAX_CHARS = 7000
INPUT_POLICY = "prefix"
MODEL_OPTIONS = {"temperature": 0, "top_p": 0.1, "num_ctx": 8192, "num_predict": 4096}
LAST_RESPONSE_METADATA = {}

PATIENT_ID_COL = "BDSPPatientID"
#ICD_LABEL = "ICD_label"
INDEX_DATE = "index_date"
#NT_DATE_COL = "first_nt_date"
#IH_DATE_COL = "first_ih_date"
#INDEX_SOURCE = "index_source"
NOTE_TEXT_COL = "raw_notetxt"

DEFAULT_PROMPT_FILE = REPO_ROOT / "prompts" / "stanford_v2.txt"
PROMPT_TEMPLATE = DEFAULT_PROMPT_FILE.read_text(encoding="utf-8")


def normalize_nt_date(x):
    if pd.isna(x):
        return "unknown"

    s = str(x).strip()

    # Handle floats like 19940101.0
    if s.endswith(".0"):
        s = s[:-2]

    # YYYYMMDD
    if s.isdigit() and len(s) == 8:
        try:
            return pd.to_datetime(s, format="%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            pass

    # YYYY/MM/DD
    try:
        return pd.to_datetime(s, format="%Y/%m/%d").strftime("%Y-%m-%d")
    except Exception:
        pass

    # YYYY-MM-DD
    try:
        return pd.to_datetime(s, format="%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        pass

    # Fallback: let pandas infer the format
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return "unknown"

def select_note(text, policy=None, max_chars=None):
    """Transparent, label-blind experimental windows; never claims full coverage."""
    policy = policy or INPUT_POLICY
    budget = MAX_CHARS if max_chars is None else max_chars
    if policy == "prefix" or len(text) <= budget:
        return text[:budget], [[0, min(len(text), budget)]]
    # Spread diagnostic mentions across the entire record, retaining surrounding text.
    # Selection does not use reference labels, predicted labels, or diagnosis dates.
    hits = list(re.finditer(r"narcolep|idiopathic hypersomn|MSLT|hypocretin|orexin|"
                            r"assessment|impression", text, re.I))
    centers = [0, max(0, len(text) - 1000)]
    slots = max(0, budget // 1000 - 2)
    if hits and slots:
        centers += [hits[round(i * (len(hits)-1) / max(1, slots-1))].start()
                    for i in range(slots)]
    spans = sorted((max(0, c-300), min(len(text), max(0, c-300)+1000)) for c in centers)
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    parts, kept = [], []
    remaining = budget
    for start, end in merged:
        # Keep the date/header of the containing note so distant windows have provenance.
        headers = list(re.finditer(r"(?m)^\[\d{4}-\d{2}-\d{2}\][^\n]*", text[:start]))
        header = headers[-1].group() if headers else "note date unavailable"
        marker = f"\n[Excerpt chars {start}:{end}; {header}; gaps omitted]\n"
        take = min(end-start, remaining-len(marker))
        if take <= 0:
            break
        parts.append(marker + text[start:start+take])
        kept.append([start, start+take])
        remaining -= len(marker)+take
    return "".join(parts), kept


def build_prompt(row: pd.Series, prompt_template: str = PROMPT_TEMPLATE) -> str:
    value = row[NOTE_TEXT_COL]
    note_text, _ = select_note("" if pd.isna(value) else str(value))
    return prompt_template.format(
        BDSPPatientID=patient_id(row[PATIENT_ID_COL]),
        index_date=normalize_nt_date(row[INDEX_DATE]), note_text=note_text)


def call_ollama(prompt: str, retries: int = 3, sleep_sec: int = 5) -> str:
    global LAST_RESPONSE_METADATA
    LAST_RESPONSE_METADATA = {}
    for attempt in range(retries):
        try:
            response = ollama.Client(timeout=600).chat(
                model=MODEL_NAME, messages=[{"role": "user", "content": prompt}],
                options=MODEL_OPTIONS, keep_alive="30m")
            data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
            LAST_RESPONSE_METADATA = {k: v for k, v in data.items() if k != "message"}
            # Retain reasoning locally too: empty content can coexist with thinking output.
            LAST_RESPONSE_METADATA["message"] = data.get("message")
            return response["message"]["content"] or ""
        except Exception as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"Ollama transport failed after {retries} attempts: {type(exc).__name__}") from exc
            time.sleep(sleep_sec)


def safe_parse_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
    return {"parse_error": True}

# =========================
# MAIN PROCESSING
# =========================

def patient_id(value):
    if pd.isna(value) or not str(value).strip():
        raise ValueError("Input contains a missing patient ID")
    value = str(value).strip()
    return value[:-2] if value.endswith(".0") and value[:-2].isdigit() else value


def process_input_file(input_path: Path, output_dir: Path = OUTPUT_DIR,
                       prompt_template: str = PROMPT_TEMPLATE, max_patients=None):
    print(f"\nProcessing: {input_path.name}")

    df = pd.read_parquet(input_path)

    required_cols = [
        PATIENT_ID_COL,
        INDEX_DATE,
        NOTE_TEXT_COL,
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{input_path.name} missing columns: {missing}")
    ids = df[PATIENT_ID_COL].map(patient_id)
    if ids.duplicated().any():
        raise ValueError("Input contains duplicate patient IDs; expected one row per patient")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "nt_patient_llm_outputs.jsonl"

    processed_keys = set()

    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    key = (patient_id(obj.get("BDSPPatientID")), str(obj.get("index_date")))
                    if key in processed_keys:
                        raise ValueError("Existing output contains duplicate patient/date records")
                    processed_keys.add(key)
                except json.JSONDecodeError as exc:
                    raise ValueError("Existing output has an invalid JSON line") from exc

    records = df.to_dict(orient="records")

    new_count = 0
    with open(output_path, "a", encoding="utf-8") as out_f:
        for start in tqdm(range(0, len(records), BATCH_SIZE)):
            batch = records[start:start + BATCH_SIZE]

            for record in batch:
                row = pd.Series(record)

                BDSPPatientID = row[PATIENT_ID_COL]
                index_date = normalize_nt_date(row[INDEX_DATE])
                note_value = row[NOTE_TEXT_COL]
                note_text = "" if pd.isna(note_value) else str(note_value)

                key = (
                    patient_id(BDSPPatientID),
                    str(index_date),
                )

                if key in processed_keys:
                    continue

                if max_patients is not None and new_count >= max_patients:
                    return
                new_count += 1
                if not note_text.strip():
                    result = {
                        "BDSPPatientID": BDSPPatientID,
                        "index_date": index_date,
                        "llm_output": None,
                        "raw_llm_output": None,
                        "elapsed_sec": 0,
                        "error": "empty_note",
                    }

                    out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    out_f.flush()
                    processed_keys.add(key)
                    continue

                prompt = build_prompt(row, prompt_template)

                try:
                    start_time = time.time()
                    from NT_LLM.validation import validate_output
                    errors = []
                    for attempt in range(1, 3):
                        raw_output = call_ollama(prompt)
                        parsed_output = safe_parse_json(raw_output)
                        errors = validate_output(parsed_output, patient_id(BDSPPatientID), index_date, note_text)
                        attempt_record = {"BDSPPatientID": patient_id(BDSPPatientID),
                                          "attempt": attempt, "raw_llm_output": raw_output,
                                          "validation_errors": errors,
                                          "response_metadata": LAST_RESPONSE_METADATA,
                                          "rendered_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
                        with (output_dir / "attempts.jsonl").open("a", encoding="utf-8") as attempts:
                            attempts.write(json.dumps(attempt_record, ensure_ascii=False) + "\n")
                            attempts.flush()
                            os.fsync(attempts.fileno())
                        if not errors:
                            break
                    elapsed = time.time() - start_time

                    result = {
                        "BDSPPatientID": BDSPPatientID,
                        "index_date": index_date,
                        "llm_output": parsed_output,
                        "raw_llm_output": raw_output,
                        "elapsed_sec": elapsed,
                        "error": ";".join(errors) if errors else None,
                        "input_chars": len(note_text),
                        "selected_spans": select_note(note_text)[1],
                        "rendered_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    }

                except Exception as e:
                    result = {
                        "BDSPPatientID": BDSPPatientID,
                        "index_date": index_date,
                        "llm_output": None,
                        "raw_llm_output": None,
                        "elapsed_sec": None,
                        "error": str(e),
                    }

                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_f.flush()
                os.fsync(out_f.fileno())
                processed_keys.add(key)

    print(f"Saved results to: {output_path}")


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_fingerprint():
    files = [Path(__file__), *sorted((REPO_ROOT / "NT_LLM").glob("*.py"))]
    return hashlib.sha256(b"".join(p.name.encode() + p.read_bytes() for p in files)).hexdigest()


@contextmanager
def run_lock(output_dir):
    with (output_dir / ".inference.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another inference process owns this run") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def run_workflow(input_path=INPUT_DIR, gold_path=None, output_dir=None,
                 prompt_file=DEFAULT_PROMPT_FILE, resume=False,
                 inference_only=False, predictions_path=None, max_patients=None):
    """Run inference, evaluation, and reporting, or evaluate imported predictions."""
    from NT_LLM.narcolepsy_analysis import GOLD, evaluate, read_gold
    from NT_LLM.narcolepsy_report import write_report

    input_path = Path(input_path).resolve()
    gold_path = Path(gold_path or GOLD).resolve()
    prompt_file = Path(prompt_file).resolve()
    prompt_template = prompt_file.read_text(encoding="utf-8")
    # Check format syntax before any model call, without using patient data.
    prompt_template.format(BDSPPatientID="synthetic", index_date="2026-01-01",
                           note_text="synthetic")
    if not inference_only:
        read_gold(gold_path)
    if predictions_path is not None:
        if inference_only:
            raise ValueError("--predictions cannot be combined with --inference-only")
        predictions_path = Path(predictions_path).resolve()
        if not predictions_path.is_file():
            raise FileNotFoundError("Predictions file does not exist")

    now = datetime.now(timezone.utc)
    if output_dir is None:
        if resume:
            raise ValueError("--resume requires --output-dir")
        output_dir = REPO_ROOT / "NT_LLM/runs" / f"{prompt_file.stem}_{now:%Y%m%dT%H%M%S%fZ}"
    output_dir = Path(output_dir).resolve()
    config = {
        "input": str(input_path) if predictions_path is None else None,
        "input_sha256": file_sha256(input_path) if predictions_path is None else None,
        "gold": str(gold_path) if not inference_only else None,
        "gold_sha256": file_sha256(gold_path) if not inference_only else None,
        "prompt_file": prompt_file.name,
        "prompt_sha256": hashlib.sha256(prompt_template.encode("utf-8")).hexdigest(),
        "model": MODEL_NAME, "max_chars": MAX_CHARS,
        "model_options": MODEL_OPTIONS,
        "input_policy": INPUT_POLICY,
        "code_sha256": source_fingerprint(),
        "imported_predictions": str(predictions_path) if predictions_path else None,
        "imported_predictions_sha256": file_sha256(predictions_path) if predictions_path else None,
    }
    manifest_path = output_dir / "run_manifest.json"
    if resume:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous["config"] != config:
            raise ValueError("Run configuration changed; choose a new --output-dir")
        manifest = previous
        manifest.pop("error_type", None)
        manifest.pop("finished_at", None)
    else:
        if output_dir.exists():
            raise ValueError("Output directory already exists; use --resume for a managed run or choose a new directory")
        output_dir.mkdir(parents=True)
        manifest = {
            "config": config, "started_at": now.isoformat(),
            "prediction_source": ("existing predictions (prompt/model provenance unverified)"
                                  if predictions_path else "local model inference"),
            "model": MODEL_NAME, "prompt_file": prompt_file.name,
            "prompt_sha256": config["prompt_sha256"],
        }
        (output_dir / "prompt_snapshot.txt").write_text(prompt_template, encoding="utf-8")

    def save_manifest():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    try:
        manifest["status"] = "running"
        manifest["stage"] = "inference" if predictions_path is None else "evaluation"
        save_manifest()
        if predictions_path is None:
            with run_lock(output_dir):
                process_input_file(input_path, output_dir, prompt_template, max_patients)
            predictions_path = output_dir / "nt_patient_llm_outputs.jsonl"
        if inference_only:
            manifest["status"] = "inference_only_requires_coverage_review"
        else:
            manifest["stage"] = "evaluation"
            save_manifest()
            summary = evaluate(gold_path, predictions_path, output_dir / "analysis_results")
            manifest["status"] = ("complete_with_issues" if any(
                count for name, count in summary["status_counts"].items() if name != "valid"
            ) else "complete")
            manifest["stage"] = "report"
            manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
            save_manifest()
            report_path = write_report(summary, manifest, output_dir)
            print(f"Report: {report_path}")
        manifest["stage"] = "finished"
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_manifest()
    except (Exception, KeyboardInterrupt) as exc:
        manifest["status"] = "failed"
        manifest["error_type"] = type(exc).__name__
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_manifest()
        raise
    return output_dir


if __name__ == "__main__":
    from NT_LLM.narcolepsy_analysis import GOLD
    parser = argparse.ArgumentParser(description="Run Stanford inference, evaluation, and reporting")
    parser.add_argument("--input", type=Path, default=INPUT_DIR)
    parser.add_argument("--gold", type=Path, default=GOLD)
    parser.add_argument("--output-dir", type=Path,
                        help="New run directory; default: NT_LLM/runs/<prompt>_<UTC timestamp>")
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT_FILE,
                        help=f"Prompt template text file (default: {DEFAULT_PROMPT_FILE.name})")
    parser.add_argument("--resume", action="store_true", help="Resume an existing managed run with identical configuration")
    parser.add_argument("--inference-only", action="store_true", help="Skip evaluation and report generation")
    parser.add_argument("--predictions", type=Path,
                        help="Evaluate and report an existing JSONL instead of making model calls")
    parser.add_argument("--max-patients", type=int, help="Maximum NEW patients this invocation; inspect before resume")
    parser.add_argument("--input-policy", choices=["prefix", "evidence-windows"], default="prefix")
    parser.add_argument("--max-chars", type=int, default=7000)
    args = parser.parse_args()
    if args.max_chars < 1000 or args.max_chars > 7000:
        parser.error("--max-chars must be 1000..7000 for the fixed context budget")
    if args.max_patients is not None and args.max_patients < 1:
        parser.error("--max-patients must be positive")
    INPUT_POLICY, MAX_CHARS = args.input_policy, args.max_chars
    run_dir = run_workflow(args.input, args.gold, args.output_dir, args.prompt_file,
                           args.resume, args.inference_only, args.predictions, args.max_patients)
    print(f"Run saved to: {run_dir}")
