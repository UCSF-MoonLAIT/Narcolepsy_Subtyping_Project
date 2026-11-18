"""Offline audit and review-assisted handoff. Patient-level files stay under NT_LLM."""
import argparse
import contextlib
import io
import json
import re
from pathlib import Path

import pandas as pd
import narcolepsy_stanford as runner
from NT_LLM.narcolepsy_analysis import GOLD, LABELS, evaluate, read_gold, read_predictions, normalized_id
from NT_LLM.validation import evidence_flags, validate_output
from NT_LLM.label_schemes import grouped_label, labels_for

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / 'NT_LLM/runs/stanford_v2_20261022T003015723429Z'


def export_package(input_path, predictions_path, output_dir, gold_path=None, label_scheme="five", evaluation_policy='recorded'):
    """Reconcile against INPUT, not only successful output. Never fill clinical decisions."""
    labels_for(label_scheme)
    if evaluation_policy not in ['recorded', 'classification', 'strict']:
        raise ValueError('Unknown evaluation policy')
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError('Package destination must be new; preserve existing review decisions')
    source = pd.read_parquet(input_path)
    required = {'BDSPPatientID', 'index_date', 'raw_notetxt'}
    if required - set(source):
        raise ValueError('Prepared patient notes with patient ID and index date are required')
    source['BDSPPatientID'] = source.BDSPPatientID.map(normalized_id)
    if source.BDSPPatientID.duplicated().any():
        raise ValueError('Duplicate input IDs')
    rows = [json.loads(line) for line in Path(predictions_path).open()]
    predictions = read_predictions(Path(predictions_path))  # validates uniqueness and identity presence
    if set(predictions.BDSPPatientID) - set(source.BDSPPatientID):
        raise ValueError('Predictions outside expected input cohort')
    by_id = {normalized_id(r['BDSPPatientID']): r for r in rows}
    gold = read_gold(gold_path).set_index('BDSPPatientID').final_label_gold.to_dict() if gold_path else {}
    records = []
    for row in source.to_dict('records'):
        pid = row['BDSPPatientID']; item = by_id.get(pid); value = (item or {}).get('llm_output') or {}
        value = value if isinstance(value, dict) else {}
        note = '' if pd.isna(row['raw_notetxt']) else str(row['raw_notetxt'])
        errors = validate_output(value, pid, runner.normalize_nt_date(row['index_date']), note, label_scheme=label_scheme) if item else ['missing_prediction']
        quote_only_error = (item or {}).get('error') == 'unsupported_final_evidence_quote'
        if item and item.get('error') and not (evaluation_policy != 'recorded' and quote_only_error):
            errors.append('recorded_inference_failure')
        if item and item.get('index_date') != runner.normalize_nt_date(row['index_date']):
            errors.append('outer_index_date_mismatch')
        flags = evidence_flags(value, note)
        if evaluation_policy == 'strict' and 'nonverbatim_or_unsupported_quote' in flags:
            errors.append('unsupported_final_evidence_quote')
        if gold.get(pid) and grouped_label(gold[pid], label_scheme) != value.get('final_label'):
            flags.append('reference_disagreement_requires_review')
        if item and item.get('input_coverage') is not None:
            if item['input_coverage'] < 1:
                flags.append('incomplete_validated_source_coverage')
            if item.get('planned_chunks',1) > 1:
                flags.append('chunk_reconciliation_requires_review')
        elif len(note) > 7000:
            flags.append('historical_input_selection_requires_review')
        if value.get('diagnosis_anchor_date') is None:
            flags.append('unknown_diagnosis_date')
        status = 'missing' if item is None else ('failed' if errors else 'valid')
        anchor=value.get('diagnosis_anchor_date')
        precision = ('day' if isinstance(anchor,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',anchor)
                     else 'month' if isinstance(anchor,str) and re.fullmatch(r'\d{4}-\d{2}',anchor)
                     else 'year' if isinstance(anchor,str) and re.fullmatch(r'\d{4}',anchor) else 'unknown')
        records.append({**{k:v for k,v in row.items() if k!='raw_notetxt'},
                        'BDSPPatientID': pid, 'model_index_date': runner.normalize_nt_date(row['index_date']),
                        'model_label': value.get('final_label'), 'model_confidence': value.get('confidence'),
                        'model_diagnosis_anchor_date': anchor if precision=='day' and 'invalid_diagnosis_date' not in errors else None,
                        'model_diagnosis_date_original': anchor,
                        'model_diagnosis_date_precision': precision,
                        'output_status': status, 'failure_reasons': ';'.join(errors),
                        'metric_eligible': status == 'valid',
                        'recorded_run_error': (item or {}).get('error'),
                        'evaluation_policy': evaluation_policy,
                        'review_flags': ';'.join(flags),
                        'priority': 0 if errors else (1 if value.get('final_label') in ['NT1','NT2','IH','NT2_IH'] or 'reference_disagreement_requires_review' in flags or 'nonverbatim_or_unsupported_quote' in flags else 2),
                        'source_predictions_sha256': runner.file_sha256(Path(predictions_path))})
    result = pd.DataFrame(records)
    output_dir.mkdir(parents=True)
    result.to_csv(output_dir/'model_results.csv', index=False)
    # Separate blank reviewer decisions: confidence is never confirmation.
    review = result[['BDSPPatientID', 'priority', 'review_flags', 'failure_reasons']].copy()
    review['review_status'] = 'unreviewed'
    for field in ['reviewed_label', 'reviewed_diagnosis_date', 'date_precision', 'confirmed',
                  'analysis_inclusion', 'rationale', 'reviewer', 'reviewed_at', 'source_evidence', 'adjudication_criteria_version']:
        review[field] = ''
    review.sort_values(['priority','BDSPPatientID']).to_csv(output_dir/'review_queue.csv',index=False)
    result[result.output_status != 'valid'].to_csv(output_dir/'failed_or_missing.csv',index=False)
    counts = {'expected': len(source), 'processed': len(rows), 'valid': int((result.output_status=='valid').sum()),
              'failed': int((result.output_status=='failed').sum()), 'missing': int((result.output_status=='missing').sum()),
              'reviewed': 0, 'unresolved': len(source), 'confirmed': 0, 'analysis_included': 0,
              'delivery_status': 'PARTIAL: unreviewed development predictions; no confirmed cases',
              'input_sha256': runner.file_sha256(Path(input_path)),
              'predictions_sha256': runner.file_sha256(Path(predictions_path)),
              'predictions_path': str(Path(predictions_path).resolve()),
              'export_code_sha256': runner.file_sha256(Path(__file__)),
              'label_scheme': label_scheme,
              'evaluation_policy': evaluation_policy,
              'quote_quality_flagged_records': int(result.review_flags.str.contains('nonverbatim_or_unsupported_quote', regex=False).sum()),
              'gold_sha256': runner.file_sha256(Path(gold_path)) if gold_path else None}
    (output_dir/'status.json').write_text(json.dumps(counts, indent=2)+'\n')
    # Read exported IDs as strings to verify no coercion or row loss.
    reread = pd.read_csv(output_dir/'model_results.csv', dtype={'BDSPPatientID': str})
    assert reread.BDSPPatientID.tolist() == source.BDSPPatientID.tolist()
    assert len(review)==len(source) and not review.BDSPPatientID.duplicated().any()
    return counts


def audit(output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError('Audit destination must be new')
    output_dir.mkdir(parents=True)
    source = pd.read_parquet(runner.INPUT_DIR)
    gold = read_gold(GOLD)
    ids = source.BDSPPatientID.map(normalized_id)
    texts = source.raw_notetxt.fillna('').astype(str)
    rows = [json.loads(l) for l in (BASELINE/'nt_patient_llm_outputs.jsonl').open()]
    results = {}
    for name, path in [('historical_unverified', ROOT/'NT_LLM/NT_128pt_outputs/nt_patient_llm_outputs.jsonl'),
                       ('stanford_v2', BASELINE/'nt_patient_llm_outputs.jsonl')]:
        with contextlib.redirect_stdout(io.StringIO()):
            results[name] = evaluate(GOLD, path, output_dir/name)
    cohort = pd.read_csv(ROOT/'NT_LLM/NT_cohort_1697_MSLT_flag_from_CPT.csv', dtype={'BDSPPatientID': str})
    elapsed = [r['elapsed_sec'] for r in rows if isinstance(r.get('elapsed_sec'), (int,float))]
    headers = [list(re.finditer(r'(?m)^\[(\d{4}-\d{2}-\d{2})\]', t)) for t in texts]
    ordering = {'ascending':0,'descending':0,'mixed':0,'zero_or_one_header':0}
    for hs in headers:
        dates = [h.group(1) for h in hs]
        key = 'zero_or_one_header' if len(dates)<2 else 'ascending' if dates==sorted(dates) else 'descending' if dates==sorted(dates,reverse=True) else 'mixed'
        ordering[key]+=1
    source_dir = ROOT/'NT_LLM/stanford_NT_IH_sleeponly_notes_128_for_LLM'
    exact_source_match = sum((source_dir/f'{pid}.txt').exists() and (source_dir/f'{pid}.txt').read_text()==t for pid,t in zip(ids,texts))
    lost_mentions = sum(not re.search(r'narcolep|idiopathic hypersomn', t[:7000], re.I) and bool(re.search(r'narcolep|idiopathic hypersomn',t[7000:],re.I)) for t in texts)
    audit_info = {'reference_input_records':len(source), 'reference_gold_records':len(gold),
                  'duplicate_input_ids':int(ids.duplicated().sum()),
                  'input_only_ids':len(set(ids)-set(gold.BDSPPatientID)), 'gold_only_ids':len(set(gold.BDSPPatientID)-set(ids)),
                  'empty_notes':int((texts.str.len()==0).sum()), 'notes_truncated_at_7000':int((texts.str.len()>7000).sum()),
                  'median_note_chars':float(texts.str.len().median()), 'max_note_chars':int(texts.str.len().max()),
                  'full_text_character_coverage':float(texts.str.len().clip(upper=7000).sum()/texts.str.len().sum()),
                  'diagnostic_terms_only_after_cutoff':lost_mentions, 'note_header_order':ordering,
                  'exact_note_file_matches':int(exact_source_match),
                  'production_cohort_rows':len(cohort), 'production_unique_ids':int(cohort.BDSPPatientID.nunique()),
                  'production_note_column_available':'raw_notetxt' in cohort,
                  'reference_ids_in_production_cohort':len(set(ids)&set(cohort.BDSPPatientID)),
                  'measured_mean_seconds_per_patient':sum(elapsed)/len(elapsed),
                  'measured_median_seconds_per_patient':float(pd.Series(elapsed).median()),
                  'projected_1697_hours_same_settings':1697*sum(elapsed)/len(elapsed)/3600,
                  'projection_limit':'Historical wall time includes inference only; retries, changed selection/settings and clinical review add time.',
                  'baseline_source_prompt_matches_current':(BASELINE/'prompt_snapshot.txt').read_bytes()==runner.DEFAULT_PROMPT_FILE.read_bytes(),
                  'input_hash_matches_baseline_manifest':runner.file_sha256(runner.INPUT_DIR)==json.loads((BASELINE/'run_manifest.json').read_text())['config']['input_sha256'],
                  'evaluations':results}
    (output_dir/'audit_summary.json').write_text(json.dumps(audit_info,indent=2)+'\n')
    g=gold.set_index('BDSPPatientID').final_label_gold.to_dict(); by_id={normalized_id(r['BDSPPatientID']):r for r in rows}
    review=[]
    categories={0:'Input truncation; competing explanation/reference definition needs clinician review',
                23:'Correct NT1 example supported by supplied evidence; still not clinically adjudicated',
                26:'Reference/clinical-definition disagreement: documented subtype despite control reference',
                36:'Missing explicit IH diagnosis in supplied notes; clinical-definition review required',
                46:'Later diagnostic revision may be omitted; clinician review required',
                66:'Possible unsupported subtype inference and omitted later testing; clinician review required',
                77:'Input defect: first diagnostic mention occurs after cutoff',
                103:'Runner/generation failure: empty content saved as parse_error without error flag'}
    for i,category in categories.items():
        pid=ids.iloc[i]; t=texts.iloc[i]; r=by_id[pid]; v=r.get('llm_output') or {}
        hits=list(re.finditer(r'narcolep\w*|idiopathic hypersomn\w*',t,re.I))
        later=next((h for h in hits if h.start()>7000),None)
        supplied,_=runner.select_note(t,policy='prefix',max_chars=7000)
        row={'case_ordinal':i, 'BDSPPatientID':pid,'reference_label':g[pid], 'model_label':v.get('final_label'),
             'provisional_category_not_adjudication':category,'note_chars':len(t),
             'first_diagnostic_mention_offset':hits[0].start() if hits else None,
             'model_quotes':json.dumps(v.get('key_evidence_quotes',[])), 'model_reasoning':v.get('reasoning'),
             'later_source_excerpt':t[max(0,later.start()-150):later.end()+450] if later else '',
             'raw_response_chars':len(r.get('raw_llm_output') or ''),
             'reconstructed_prompt_sha256':__import__('hashlib').sha256(runner.build_prompt(source.iloc[i],(BASELINE/'prompt_snapshot.txt').read_text()).encode()).hexdigest(),
             'raw_record_1based_line':next(j+1 for j,x in enumerate(rows) if normalized_id(x['BDSPPatientID'])==pid),
             'evaluation_status':'invalid_prediction' if not v.get('final_label') else 'valid'}
        review.append(row)
    pd.DataFrame(review).to_csv(output_dir/'representative_review.csv',index=False)
    trace_id=ids.iloc[77]; trace=by_id[trace_id]
    (output_dir/'trace_rendered_prompt.txt').write_text(runner.build_prompt(source.iloc[77],(BASELINE/'prompt_snapshot.txt').read_text()))
    (output_dir/'trace_raw_and_parsed.json').write_text(json.dumps(trace,indent=2))
    export_package(runner.INPUT_DIR, BASELINE/'nt_patient_llm_outputs.jsonl',output_dir/'baseline_handoff',GOLD)
    print(json.dumps({k:v for k,v in audit_info.items() if k!='evaluations'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    a=sub.add_parser('audit'); a.add_argument('--output-dir',type=Path,required=True)
    p=sub.add_parser('package'); p.add_argument('--input',type=Path,required=True);p.add_argument('--predictions',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--gold',type=Path)
    args=parser.parse_args()
    if args.command=='audit': audit(args.output_dir)
    else: print(json.dumps(export_package(args.input,args.predictions,args.output_dir,args.gold),indent=2))
