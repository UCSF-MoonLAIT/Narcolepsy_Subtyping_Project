"""Locally supervise pilot gates, full B, matched truncated A, and final packaging.
No clinical decisions or external sharing. Can resume after process/host interruption.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from coverage_pipeline import ROOT, atomic_json, load_jsonl
from estimate_runtime import estimate

BASE=ROOT/'NT_LLM/submission_20261109'
PILOT=ROOT/'NT_LLM/runs/coverage_B_pilot_20261109'
FULL_B=ROOT/'NT_LLM/runs/coverage_B_reference_20261109'
FULL_A=ROOT/'NT_LLM/runs/coverage_A_matched_reference_20261109'
STATUS=BASE/'comparison_status.json'


def status(stage, **extra):
    value={'stage':stage,'updated_at':datetime.now(timezone.utc).isoformat(),**extra}
    atomic_json(STATUS,value)
    (ROOT/'REFERENCE_RUN_STATUS.md').write_text('# Stanford 128 live execution status\n\n'+
        f'Updated UTC: {value["updated_at"]}\n\nCurrent stage: **{stage}**.\n\n'+
        'Model predictions remain separate from pending user review. Reference labels are unchanged.\n\n'+
        'Detailed live status: `NT_LLM/submission_20261109/comparison_status.json`.\n\n'+
        '\n'.join(f'- {k}: {v}' for k,v in extra.items())+'\n')


def wait_for_unlock(directory):
    while True:
        try:
            with (directory/'.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return
        except BlockingIOError:time.sleep(5)


def invoke(directory,strategy,input_path=None,limit=None):
    command=[sys.executable,str(ROOT/'coverage_pipeline.py'),'--output-dir',str(directory),'--strategy',strategy]
    if input_path:command+=['--input',str(input_path)]
    if limit:command+=['--max-patients',str(limit)]
    if directory.exists():command+=['--resume']
    env=dict(os.environ,MPLCONFIGDIR='/tmp/narcolepsy-mpl')
    log=BASE/(directory.name+'.log')
    with log.open('a') as handle:
        subprocess.run(command,cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT,check=True)


def technical_gate(directory,minimum,must_chunk=False,first_only=False):
    patients=load_jsonl(directory/'nt_patient_llm_outputs.jsonl');calls=load_jsonl(directory/'calls.jsonl')
    if len(patients)<minimum:raise RuntimeError('Technical pilot incomplete')
    if first_only:
        patients=patients[:minimum]
        ids={str(r['BDSPPatientID']) for r in patients}
        calls=[c for c in calls if str(c['patient_id']) in ids]
    if any(r.get('error') or r.get('input_coverage')!=1 for r in patients):raise RuntimeError('B technical gate: invalid output or incomplete source coverage')
    if must_chunk and not any(r['planned_chunks']>1 for r in patients):raise RuntimeError('No multi-chunk patient tested')
    if any(c['status']!='valid' for c in calls):raise RuntimeError('Technical gate: call required failure investigation')
    if any(abs(c.get('token_accounting_delta') or 0)>8 for c in calls):raise RuntimeError('Token accounting discrepancy')
    return {'patients':len(patients),'calls':len(calls),'valid':len(patients),'source_coverage':1.0,
            'runtime_sec':sum(c['elapsed_sec'] for c in calls),
            'evidence_flags_require_review':sum(bool(c.get('evidence_flags')) for c in calls)}


def snapshot(label):
    target=BASE/f'comparison_{label}'
    if not target.exists():
        command=[sys.executable,str(ROOT/'compare_coverage.py'),'--B',str(FULL_B),'--output-dir',str(target)]
        if (FULL_A/'nt_patient_llm_outputs.jsonl').exists():command+=['--A',str(FULL_A)]
        with (BASE/'packaging.log').open('a') as handle:
            subprocess.run(command,cwd=ROOT,env=dict(os.environ,MPLCONFIGDIR='/tmp/narcolepsy-mpl'),stdout=handle,stderr=subprocess.STDOUT,check=True)
    atomic_json(BASE/'runtime_projection.json',estimate(FULL_B))
    return str(target)


def main():
    BASE.mkdir(parents=True,exist_ok=True)
    with (BASE/'.supervisor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            status('waiting_for_active_technical_pilot')
            wait_for_unlock(PILOT)
            invoke(PILOT,'B',BASE/'coverage_pilot_input.parquet')
            gate=technical_gate(PILOT,3,must_chunk=True);atomic_json(BASE/'technical_pilot_gate.json',gate)
            status('B_full_reference_early_batch',pilot=gate)
            completed=len(load_jsonl(FULL_B/'nt_patient_llm_outputs.jsonl'))
            if completed<3:
                invoke(FULL_B,'B',limit=3-completed)
            early=technical_gate(FULL_B,3,first_only=True)
            snapshot('B_early_partial')
            status('B_full_reference_running',pilot=gate,early_batch=early)
            invoke(FULL_B,'B')
            b_summary=snapshot('B_complete')
            status('matched_A_running',B_review=b_summary)
            invoke(FULL_A,'A')
            final=snapshot('final')
            # Mechanical decision support only: C needs a separate engineering decision.
            summary=json.loads((Path(final)/'comparison.json').read_text())
            b=summary['evaluations']['B']; historical=summary['evaluations']['historical_A']
            adequate_technical=(b['metric_denominator']==128)
            improvement=bool(b['metrics'] and historical['metrics'] and b['metrics']['macro_f1']>historical['metrics']['macro_f1'])
            status('reference_comparison_complete',final_review=final,
                   C_assessment='Investigate explicit extraction alternative before configuration freeze' if not (adequate_technical and improvement) else 'Assess residual errors clinically before deciding whether extraction adds value',
                   clinical_review='pending; no cases confirmed or included',delivery_cohort='Stanford 128 patients; complete current target; no MGB dependencies')
        except BaseException as exc:
            status('needs_engineering_attention',error_type=type(exc).__name__,reason=str(exc))
            raise


if __name__=='__main__':main()
