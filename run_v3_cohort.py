"""Prepare, smoke-test, and run the Stanford v3 combined-label cohort locally.

The smoke gate checks technical integrity and synthetic subtype rules, never
selects a prompt using reference accuracy. Full inference uses fresh checkpoints.
"""
import argparse
from argparse import Namespace
import fcntl
import json
import os
import shutil
from pathlib import Path
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import coverage_pipeline as cp
import pandas as pd
from NT_LLM.narcolepsy_analysis import GOLD, read_gold, normalized_id
from NT_LLM.validation import validate_output, evidence_flags, evidence_quote_support
from NT_LLM.label_schemes import grouped_label
from narcolepsy_stanford import INPUT_DIR, normalize_nt_date

PROMPT = cp.ROOT/'prompts/stanford_v3.txt'
BASELINE = cp.ROOT/'NT_LLM/runs/coverage_B_reference_20261109'
SYNTHETIC = [
    {'BDSPPatientID': 'synthetic_unspecified', 'index_date': '20260102',
     'raw_notetxt': '[2026-01-02] Sleep specialist assessment: Narcolepsy is an established diagnosis. The subtype remains undetermined. The patient denies cataplexy. CSF hypocretin has not been measured. No subtype diagnosis has been established.',
     'expected_label': 'Uncertain', 'reference_label': 'Uncertain'},
    {'BDSPPatientID': 'synthetic_without_cataplexy', 'index_date': '20260102',
     'raw_notetxt': '[2026-01-02] Sleep specialist assessment: Established narcolepsy without cataplexy, diagnosed by an outside sleep specialist in 2018. Continue longitudinal management. The original diagnostic sleep study report is unavailable. No diagnostic revision has been made.',
     'expected_label': 'NT2_IH', 'reference_label': 'NT2'},
]


def status(work, stage, **details):
    cp.atomic_json(work/'status.json', {'stage': stage,
        'updated_at': datetime.now(timezone.utc).isoformat(), **details})
    print(json.dumps({'stage': stage, **details}), flush=True)


def fingerprint():
    return {'input_sha256': cp.legacy.file_sha256(INPUT_DIR),
            'gold_sha256': cp.legacy.file_sha256(GOLD),
            'prompt_sha256': cp.sha(PROMPT.read_bytes()), 'sources': cp.source_version(),
            'supervisor_sha256': cp.sha(Path(__file__).read_bytes()),
            'baseline_manifest_sha256': cp.sha((BASELINE/'run_manifest.json').read_bytes())}


def prepare(work):
    cp.configure_prompt(PROMPT, 'combined')
    source = pd.read_parquet(INPUT_DIR); gold = read_gold(GOLD)
    source['BDSPPatientID'] = source.BDSPPatientID.map(normalized_id)
    if len(source) != 128 or len(gold) != 128 or source.BDSPPatientID.duplicated().any():
        raise ValueError('Expected exactly 128 unique cohort and reference records')
    if set(source.BDSPPatientID) != set(gold.BDSPPatientID):
        raise ValueError('Input/reference cohort mismatch')
    if not source.raw_notetxt.fillna('').astype(str).str.strip().ne('').all():
        raise ValueError('Empty cohort notes')
    tokenizer = cp.LocalTokenizer()
    baseline = json.loads((BASELINE/'run_manifest.json').read_text())['config']
    identity = fingerprint()
    for key in ['input_sha256', 'gold_sha256']:
        if identity[key] != baseline[key]:
            raise ValueError('Source or reference differs from the preserved v2 B run')
    for key, value in {'model': cp.MODEL, 'model_digest': tokenizer.model_digest,
                       'options': cp.OPTIONS, 'think': cp.THINK}.items():
        if baseline[key] != value:
            raise ValueError(f'Runtime differs from v2 B: {key}')
    plans = []
    for number, row in enumerate(source.to_dict('records'), 1):
        text = str(row['raw_notetxt'])
        chunks = cp.plan_chunks(tokenizer, row['BDSPPatientID'], normalize_nt_date(row['index_date']), text)
        if ''.join(text[c['start']:c['end']] for c in chunks) != text:
            raise ValueError('Incomplete source partition')
        plans.append({'BDSPPatientID': row['BDSPPatientID'], 'source_chars': len(text),
                      'source_tokens': tokenizer.count(text),
                      'chunks': [{k: v for k, v in c.items() if k != 'text'} for c in chunks]})
        if number % 16 == 0:
            status(work, 'offline_coverage_planning', planned=number, expected=128)
    cp.atomic_json(work/'coverage_plans.json', plans)
    metadata = pd.DataFrame([{'BDSPPatientID': r['BDSPPatientID'],
                             'source_tokens': r['source_tokens'], 'chunks': len(r['chunks'])} for r in plans])
    metadata = metadata.merge(gold[['BDSPPatientID', 'final_label_gold']], on='BDSPPatientID', validate='one_to_one')
    # Deterministic technical sampling: short established-label records plus the
    # smallest record needing actual source chunking. No selection by model accuracy.
    selected = []
    for label in ['NT1', 'NT2', 'IH']:
        choices = metadata[metadata.final_label_gold == label].sort_values(['source_tokens', 'BDSPPatientID'])
        selected.append(choices.iloc[0].BDSPPatientID)
    long = metadata[metadata.chunks > 1].sort_values(['source_tokens', 'BDSPPatientID'])
    if long.empty:
        raise ValueError('No actual multi-chunk smoke case available')
    selected = list(dict.fromkeys([*selected, long.iloc[0].BDSPPatientID]))
    smoke = source.set_index('BDSPPatientID').loc[selected].reset_index()
    smoke = smoke[['BDSPPatientID', 'index_date', 'raw_notetxt']]
    smoke = pd.concat([pd.DataFrame([{k: r[k] for k in smoke.columns} for r in SYNTHETIC]), smoke], ignore_index=True)
    smoke.to_parquet(work/'smoke_input.parquet', index=False)
    smoke_gold = gold[gold.BDSPPatientID.isin(selected)][['BDSPPatientID', 'final_label_gold']]
    smoke_gold = pd.concat([smoke_gold, pd.DataFrame([{'BDSPPatientID': r['BDSPPatientID'], 'final_label_gold': r['reference_label']} for r in SYNTHETIC])], ignore_index=True)
    smoke_gold.to_excel(work/'smoke_reference.xlsx', index=False)
    summary = {'identity': identity, 'patients': 128,
               'label_scheme': 'combined', 'model_digest': tokenizer.model_digest,
               'options': dict(cp.OPTIONS), 'think': cp.THINK,
               'source_calls': sum(len(p['chunks']) for p in plans),
               'multi_chunk_patients': sum(len(p['chunks']) > 1 for p in plans),
               'planned_source_coverage': 1.0, 'smoke_patients': len(smoke),
               'synthetic_patients': len(SYNTHETIC), 'smoke_selection': selected,
               'smoke_input_sha256': cp.legacy.file_sha256(work/'smoke_input.parquet'),
               'smoke_reference_sha256': cp.legacy.file_sha256(work/'smoke_reference.xlsx'),
               'reference_counts': gold.final_label_gold.map(lambda x: grouped_label(x, 'combined')).value_counts().to_dict()}
    cp.atomic_json(work/'preflight.json', summary)
    status(work, 'offline_checks_passed', patients=128, smoke_patients=len(smoke),
           multi_chunk_patients=summary['multi_chunk_patients'], source_calls=summary['source_calls'])
    return summary


def invoke(work, name, input_path, gold_path):
    destination = work/name
    cp.run(Namespace(input=input_path, gold=gold_path, output_dir=destination,
                     strategy='B', resume=destination.exists(), max_patients=None,
                     retry_from=None, prompt_file=PROMPT, label_scheme='combined'))


def smoke_gate(work):
    source = pd.read_parquet(work/'smoke_input.parquet').set_index('BDSPPatientID')
    patients = cp.load_jsonl(work/'smoke/nt_patient_llm_outputs.jsonl')
    calls = cp.load_jsonl(work/'smoke/calls.jsonl')
    if len(patients) != len(source) or {r['BDSPPatientID'] for r in patients} != set(source.index):
        raise ValueError('Smoke cohort incomplete or duplicated')
    if not calls or any(c['status'] != 'valid' or c.get('token_accounting_delta') is None
                        or abs(c['token_accounting_delta']) > 8 for c in calls):
        raise ValueError('Smoke call failure or token accounting discrepancy; inspect raw calls')
    by_id = {r['BDSPPatientID']: r for r in patients}
    quote_audit = []
    for item in patients:
        pid = item['BDSPPatientID']; row = source.loc[pid]
        if item.get('error') or item.get('input_coverage') != 1:
            raise ValueError('Smoke output invalid or source coverage incomplete')
        if validate_output(item['llm_output'], pid, normalize_nt_date(row['index_date']), row.raw_notetxt, 'combined'):
            raise ValueError('Smoke output schema failed')
        if 'nonverbatim_or_unsupported_quote' in evidence_flags(item['llm_output'], row.raw_notetxt):
            raise ValueError('Smoke final evidence quote unsupported by original source')
        quote_audit.append({'BDSPPatientID': pid, 'source_sha256': cp.sha(row.raw_notetxt),
                            'quotes': evidence_quote_support(item['llm_output'], row.raw_notetxt)})
    if not any(r['planned_chunks'] > 1 for r in patients) or not any(':reduce:' in r['call_id'] for r in calls):
        raise ValueError('Smoke did not exercise source chunking and reconciliation')
    for case in SYNTHETIC:
        if by_id[case['BDSPPatientID']]['llm_output']['final_label'] != case['expected_label']:
            raise ValueError('Synthetic subtype rule failed: '+case['BDSPPatientID'])
    cp.atomic_json(work/'smoke_quote_support.json', quote_audit)
    matches = [q for item in quote_audit for q in item['quotes']]
    result = {'passed': True, 'patients': len(patients), 'calls': len(calls),
              'quote_matches': {kind: sum(q['match_type'] == kind for q in matches)
                                for kind in ['exact', 'formatting_only', 'unsupported']},
              'validation_sha256': cp.sha((cp.ROOT/'NT_LLM/validation.py').read_bytes()),
              'source_coverage': 1.0, 'synthetic_subtype_rules_passed': len(SYNTHETIC),
              'token_accounting_deltas': sorted({c['token_accounting_delta'] for c in calls}),
              'runtime_sec': sum(c['elapsed_sec'] for c in calls),
              'clinical_adjudication': 'pending; no reference-accuracy threshold used'}
    cp.atomic_json(work/'smoke_gate.json', result)
    return result


def reuse_saved_smoke(work, parent, preflight):
    """Preserve inference provenance while applying a new offline evidence gate."""
    parent = parent.resolve()
    if parent == work:
        raise ValueError('Saved smoke must be preserved in a separate directory')
    previous = json.loads((parent/'preflight.json').read_text())
    for key in ['input_sha256', 'gold_sha256', 'prompt_sha256']:
        if previous['identity'][key] != preflight['identity'][key]:
            raise ValueError('Saved smoke has incompatible source, reference or prompt')
    manifest = json.loads((parent/'smoke/run_manifest.json').read_text())
    cp.configure_prompt(PROMPT, 'combined')
    expected = {'model': cp.MODEL, 'model_digest': preflight['model_digest'],
                'options': cp.OPTIONS, 'think': cp.THINK, 'safety_tokens': cp.SAFETY_TOKENS,
                'prompt_sha256': cp.sha(cp.PROMPT), 'label_scheme': 'combined', 'strategy': 'B'}
    if any(manifest['config'].get(k) != v for k, v in expected.items()):
        raise ValueError('Saved smoke inference configuration differs')
    if cp.sha((parent/'smoke/prompt_snapshot.txt').read_bytes()) != expected['prompt_sha256']:
        raise ValueError('Saved smoke prompt snapshot changed')
    for filename, key, reader in [('smoke_input.parquet', 'smoke_input_sha256', pd.read_parquet),
                                  ('smoke_reference.xlsx', 'smoke_reference_sha256', pd.read_excel)]:
        if cp.legacy.file_sha256(parent/filename) != previous[key]:
            raise ValueError('Original smoke data changed')
        if not reader(parent/filename).equals(reader(work/filename)):
            raise ValueError('Saved smoke sample differs from newly prepared sample')
    if manifest.get('status') != 'complete':
        raise ValueError('Saved smoke did not complete inference successfully')
    if (work/'smoke').exists():
        raise ValueError('Saved smoke destination must be new')
    shutil.copytree(parent/'smoke', work/'smoke')
    filenames = ['calls.jsonl', 'nt_patient_llm_outputs.jsonl', 'run_manifest.json', 'prompt_snapshot.txt']
    hashes = {name: cp.sha((parent/'smoke'/name).read_bytes()) for name in filenames}
    if any(cp.sha((work/'smoke'/name).read_bytes()) != digest for name, digest in hashes.items()):
        raise ValueError('Smoke copy integrity check failed')
    cp.atomic_json(work/'smoke_revalidation.json', {
        'origin': str(parent), 'origin_artifact_hashes': hashes,
        'inference_reused_without_new_calls': True,
        'original_inference_config': manifest['config'],
        'current_validation_sources': cp.source_version()})


def verify_reused_smoke(work):
    audit = json.loads((work/'smoke_revalidation.json').read_text())
    for name, digest in audit['origin_artifact_hashes'].items():
        if cp.sha((work/'smoke'/name).read_bytes()) != digest:
            raise ValueError('Reused smoke artifacts changed after offline revalidation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--reuse-smoke-from', type=Path,
                        help='Revalidate a compatible completed smoke offline; never inherit full-run checkpoints')
    args = parser.parse_args(); work = args.work_dir.resolve(); work.mkdir(parents=True, exist_ok=True)
    with (work/'.supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            prepared = work/'preflight.json'
            preflight = json.loads(prepared.read_text()) if prepared.exists() else prepare(work)
            if preflight['identity'] != fingerprint():
                raise ValueError('Code, prompt, source, or reference changed after preparation; use a new work directory')
            for filename, key in [('smoke_input.parquet', 'smoke_input_sha256'), ('smoke_reference.xlsx', 'smoke_reference_sha256')]:
                if cp.legacy.file_sha256(work/filename) != preflight[key]:
                    raise ValueError('Prepared smoke data changed')
            if args.prepare_only:
                return
            host = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
            if urlparse(host if '://' in host else 'http://'+host).hostname not in ('127.0.0.1', 'localhost', '::1'):
                raise ValueError('This workflow requires a local Ollama server')
            cp.configure_prompt(PROMPT, 'combined')
            tokenizer = cp.LocalTokenizer()
            if tokenizer.model_digest != preflight['model_digest']:
                raise ValueError('Installed model changed after preflight')
            if args.reuse_smoke_from and not (work/'smoke_revalidation.json').exists():
                reuse_saved_smoke(work, args.reuse_smoke_from, preflight)
            if (work/'smoke_revalidation.json').exists():
                verify_reused_smoke(work)
                status(work, 'smoke_revalidating_offline', expected=preflight['smoke_patients'])
            else:
                status(work, 'smoke_running', expected=preflight['smoke_patients'])
                invoke(work, 'smoke', work/'smoke_input.parquet', work/'smoke_reference.xlsx')
            gate = smoke_gate(work)
            status(work, 'smoke_passed', gate=gate)
            status(work, 'full_128_running', expected=128)
            invoke(work, 'full', INPUT_DIR, GOLD)
            patients = cp.load_jsonl(work/'full/nt_patient_llm_outputs.jsonl')
            if len(patients) != 128:
                raise ValueError('Full cohort incomplete')
            from compare_coverage import compare
            report = work/'comparison_vs_v2_B'
            if report.exists():
                raise ValueError('Comparison directory already exists; preserve existing review artifacts')
            status(work, 'comparison_running', processed=len(patients))
            compare(work/'full', report, label_scheme='combined', baseline_dir=BASELINE)
            status(work, 'complete_with_issues' if any(p.get('error') for p in patients) else 'complete',
                   processed=128, valid=sum(not p.get('error') for p in patients),
                   failed=sum(bool(p.get('error')) for p in patients),
                   report=str(report), clinical_review='pending')
        except BaseException as exc:
            status(work, 'needs_attention', error_type=type(exc).__name__, reason=str(exc))
            raise


if __name__ == '__main__':
    main()
