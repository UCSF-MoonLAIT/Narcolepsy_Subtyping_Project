"""Consolidated development-set comparison; immutable model outputs, separate review."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import pandas as pd
import re
from NT_LLM.narcolepsy_analysis import GOLD, read_gold, normalized_id, evaluate, EVALUATION_POLICIES
from NT_LLM.validation import evidence_flags
from NT_LLM.label_schemes import labels_for, grouped_label
from narcolepsy_stanford import INPUT_DIR
from submission_tools import BASELINE, export_package
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_recall_fscore_support

LABEL_ORDER=['NT1','NT2','IH','Uncertain','Not_NT_IH']


def paired_comparison(table,left,right,valid_ids,label_scheme="five"):
    """Compare identical evaluation-valid patients; failures never become predictions."""
    labels = labels_for(label_scheme)
    paired=table[table.BDSPPatientID.isin(valid_ids[left] & valid_ids[right])]
    result={'patients':len(paired),'label_order':labels,'metrics':{}}
    if paired.empty:return result
    paired = paired.copy()
    for column in ['final_label_gold', left+'_label', right+'_label']:
        paired[column] = paired[column].map(lambda x: grouped_label(x, label_scheme))
    truth=paired.final_label_gold
    for name in [left,right]:
        predicted=paired[name+'_label']
        precision,recall,f1,support=precision_recall_fscore_support(truth,predicted,labels=labels,zero_division=0)
        result['metrics'][name]={'accuracy':float(accuracy_score(truth,predicted)),
            'balanced_accuracy':float(balanced_accuracy_score(truth,predicted)),
            'macro_f1':float(f1_score(truth,predicted,labels=labels,average='macro',zero_division=0)),
            'per_class':{label:{'precision':float(precision[i]),'recall':float(recall[i]),
                'f1':float(f1[i]),'support':int(support[i])} for i,label in enumerate(labels)}}
    old=paired[left+'_label'];new=paired[right+'_label']
    result.update(changed=int((old!=new).sum()),corrected=int(((old!=truth)&(new==truth)).sum()),
                  regressed=int(((old==truth)&(new!=truth)).sum()),
                  both_correct=int(((old==truth)&(new==truth)).sum()),
                  both_incorrect=int(((old!=truth)&(new!=truth)).sum()))
    return result


def compare(b_dir,output_dir,a_dir=None,label_scheme="five",baseline_dir=BASELINE,evaluation_policy="recorded"):
    labels = labels_for(label_scheme)
    baseline_name = "historical_A" if baseline_dir.resolve() == BASELINE.resolve() else "prior_v2"
    if output_dir.exists():raise ValueError('Choose new comparison directory')
    output_dir.mkdir(parents=True)
    source=pd.read_parquet(INPUT_DIR);source['BDSPPatientID']=source.BDSPPatientID.map(normalized_id)
    gold=read_gold(GOLD);merged=gold.merge(source,on='BDSPPatientID',validate='one_to_one',suffixes=('_gold',''))
    merged['final_label_gold_original'] = merged.final_label_gold
    merged['final_label_gold'] = merged.final_label_gold.map(lambda x: grouped_label(x, label_scheme))
    runs={baseline_name:baseline_dir,'B':b_dir}
    if a_dir:runs['matched_A']=a_dir
    metrics={};by_run={};valid_ids={};eligibility={}
    source_path = INPUT_DIR if evaluation_policy != "recorded" else None
    for name,folder in runs.items():
        path=folder/'nt_patient_llm_outputs.jsonl'
        if not path.exists():continue
        records=[json.loads(l) for l in path.open()]
        by_run[name]={normalized_id(r['BDSPPatientID']):r for r in records}
        if len(by_run[name])!=len(records):raise ValueError('Duplicate patient IDs')
        with contextlib.redirect_stdout(io.StringIO()):metrics[name]=evaluate(GOLD,path,output_dir/name,label_scheme=label_scheme,evaluation_policy=evaluation_policy,source_path=source_path)
        evaluated=pd.read_csv(output_dir/name/'NT_merged_results.csv',dtype={'BDSPPatientID':str})
        eligibility[name]=evaluated.set_index('BDSPPatientID').to_dict('index')
        valid_ids[name]=set(evaluated.loc[evaluated.evaluation_status=='valid','BDSPPatientID'].map(normalized_id))
    b_calls=[json.loads(l) for l in (b_dir/'calls.jsonl').open()] if (b_dir/'calls.jsonl').exists() else []
    rows=[]
    for row in merged.to_dict('records'):
        pid=row['BDSPPatientID'];text=row['raw_notetxt']
        d={k:v for k,v in row.items() if k!='raw_notetxt'}
        d['diagnostic_terms_only_after_old_cutoff']=not bool(re.search(r'narcolep|idiopathic hypersomn',text[:7000],re.I)) and bool(re.search(r'narcolep|idiopathic hypersomn',text[7000:],re.I))
        for name,records in by_run.items():
            item=records.get(pid,{}) ;value=item.get('llm_output') or {}
            d[name+'_label_original']=value.get('final_label');d[name+'_label']=grouped_label(value.get('final_label'),label_scheme);d[name+'_error']=item.get('error') or (None if item else 'missing_prediction')
            d[name+'_evidence_quotes']=json.dumps(value.get('key_evidence_quotes',[]),ensure_ascii=False)
            d[name+'_reasoning']=value.get('reasoning');d[name+'_diagnosis_date_original']=value.get('diagnosis_anchor_date')
            d[name+'_input_coverage']=item.get('input_coverage',min(len(text),7000)/len(text) if name=='historical_A' else None)
            d[name+'_elapsed_sec']=item.get('elapsed_sec');d[name+'_review_flags']=';'.join(evidence_flags(value,text))
            status=eligibility[name].get(pid,{})
            d[name+'_metric_eligible']=pid in valid_ids[name]
            d[name+'_evaluation_status']=status.get('evaluation_status','missing_prediction')
            d[name+'_quote_quality_status']=status.get('quote_quality_status','not_checked')
        plan_path=b_dir/f'plan_{pid}.json'
        if plan_path.exists():
            plan=json.loads(plan_path.read_text());spans={c['source_id']:c['end']-c['start'] for c in plan['chunks']}
            source_calls=[c for c in b_calls if c['patient_id']==pid and ':source_' in c['call_id']]
            sent={s for c in source_calls if c.get('server_prompt_tokens') is not None for s in c['source_ids']}
            valid_sources={s for c in source_calls if c['status']=='valid' for s in c['source_ids']}
            d['B_planned_source_char_coverage']=plan['planned_chars']/len(text)
            d['B_sent_source_char_coverage']=sum(spans.get(s,0) for s in sent)/len(text)
            d['B_validated_source_char_coverage']=sum(spans.get(s,0) for s in valid_sources)/len(text)
        d['B_label_changed_from_'+baseline_name]=d.get('B_label')!=d.get(baseline_name+'_label')
        d['reference_conflict_pending_review']=d.get('B_label') is not None and d.get('B_label')!=d['final_label_gold']
        d['subtype_false_positive_vs_reference']=d.get('B_label') in ['NT1','NT2','IH','NT2_IH'] and d['reference_conflict_pending_review']
        d['review_status']='unreviewed'
        for field in ['reviewed_label','reviewer','rationale','confirmed','analysis_inclusion']:d[field]=''
        rows.append(d)
    table=pd.DataFrame(rows);table.to_csv(output_dir/'consolidated_review.csv',index=False)
    changed=int(table['B_label_changed_from_'+baseline_name].sum())
    paired=table.BDSPPatientID.isin(valid_ids['B'] & valid_ids[baseline_name])
    paired_changes=int((table.loc[paired,'B_label']!=table.loc[paired,baseline_name+'_label']).sum())
    summary={'performance_interpretation':'Development-set performance; no clinical confirmation',
             'label_scheme':label_scheme,'label_order':labels,'evaluation_policy':evaluation_policy,
             'baseline_directory':str(baseline_dir.resolve()),
             'expected_reference_patients':len(gold),'evaluations':metrics,
             'B_processed':len(by_run.get('B',{})),
             'prediction_changes_including_missing_or_invalid':changed,
             'paired_label_predictions':int(paired.sum()),'paired_label_changes':paired_changes,
             'beyond_cutoff_patients':int(table.diagnostic_terms_only_after_old_cutoff.sum()),
             'B_source_prompt_tokens':None,'confirmed':0,'reviewed':0,
             'B_all_reference_complete':len(by_run.get('B',{}))==len(gold)}
    group=table[table.diagnostic_terms_only_after_old_cutoff]
    summary['paired_comparisons']={}
    for left in [baseline_name,'matched_A']:
        if left in by_run and 'B' in by_run:
            summary['paired_comparisons'][left+'_vs_B']={
                'all':paired_comparison(table,left,'B',valid_ids,label_scheme),
                'beyond_cutoff_34':paired_comparison(group,left,'B',valid_ids,label_scheme)}
    for label,data in [('all',table),('beyond_cutoff_34',group)]:
        summary[label]={'expected':len(data)}
        for name in by_run:
            good=data.BDSPPatientID.isin(valid_ids[name])
            summary[label][name]={'valid':int(good.sum()),'correct':int((data.loc[good,name+'_label']==data.loc[good,'final_label_gold']).sum())}
    calls=b_dir/'calls.jsonl'
    if calls.exists():
        records=[json.loads(l) for l in calls.open()]
        summary['B_runtime_sec_all_attempts']=sum(r['elapsed_sec'] for r in records)
        summary['B_source_prompt_tokens']=sum(r.get('server_prompt_tokens') or 0 for r in records)
        summary['B_calls']=len(records)
        summary['B_transport_or_invalid_calls']=sum(r['status']!='valid' for r in records)
        summary['B_token_accounting_deltas']=sorted(set(r.get('token_accounting_delta') for r in records if r.get('token_accounting_delta') is not None))
    for group_name, group_table in [('beyond_cutoff_34',group)]:
        group_dir=output_dir/group_name;group_dir.mkdir()
        group_gold=gold[gold.BDSPPatientID.isin(group_table.BDSPPatientID)]
        group_gold.to_excel(group_dir/'reference_subset.xlsx',index=False)
        for name,records in by_run.items():
            selected=[r for pid,r in records.items() if pid in set(group_table.BDSPPatientID)]
            if not selected:continue
            subset_path=group_dir/f'{name}_predictions.jsonl'
            subset_path.write_text(''.join(json.dumps(r)+'\n' for r in selected))
            with contextlib.redirect_stdout(io.StringIO()):
                summary[group_name][name]['evaluation']=evaluate(group_dir/'reference_subset.xlsx',subset_path,group_dir/name,label_scheme=label_scheme,evaluation_policy=evaluation_policy,source_path=source_path)
    (output_dir/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    if by_run.get('B'):export_package(INPUT_DIR,b_dir/'nt_patient_llm_outputs.jsonl',output_dir/'B_handoff',GOLD,label_scheme=label_scheme,evaluation_policy=evaluation_policy)
    (output_dir/'findings.md').write_text('\n'.join([
        '# Stanford 128 development comparison', '',
        f'Evaluation policy: **{evaluation_policy}**. Quote-quality flags are retained separately from prediction eligibility.', '',
        '| Configuration | Expected | Valid | Invalid/missing | Accuracy | Balanced accuracy | Macro F1 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
        *[f'| {name} | {m["gold_patients"]} | {m["metric_denominator"]} | {m["gold_patients"]-m["metric_denominator"]} | '
          + (f'{m["metrics"]["accuracy"]:.3f} | {m["metrics"]["balanced_accuracy"]:.3f} | {m["metrics"]["macro_f1"]:.3f} |' if m['metrics'] else 'unavailable | unavailable | unavailable |') for name,m in metrics.items()], '',
        f'Paired label predictions: {int(paired.sum())}; changed labels among paired records: {paired_changes}.',
        'Metrics use eligible matched predictions under the stated policy; all expected records remain in the reconciliation and coverage counts. Classification metrics do not establish source-grounded evidence or clinical validity.',
        'Pilot cases are selected for technical checks. Cohort comparisons use identical evaluation-valid patients; failures are reported separately.',
        f'Expected 128 reference patients; B processed {summary["B_processed"]}.',
        'Original reference labels are preserved; analysis labels use the selected grouping. Model confidence does not confer confirmation.',
        'See comparison.json for denominator-specific metrics, confusion matrices, and the 34-patient subset.',
        'See consolidated_review.csv for each original date field, predictions, changes, evidence quotes, and unresolved reference conflicts.',
        'B visits every source chunk but recursive classification compresses prior judgments. This can discard clinically relevant detail; full source, raw responses, and range plans remain available for review.',
        ('The historical A has unrecorded thinking/output defaults.' if baseline_name == 'historical_A' else 'The prior_v2 baseline is the preserved coverage B run. Both runs are evaluated using the selected grouping; inspect manifests for runtime provenance.'),
        'The complete current target cohort is the 128 Stanford patients. Historical MGB cohorts are outside scope. Estimate remaining runtime from repaired-pipeline token/call volume and measured speed.',
        'Clinical confirmation and inclusion remain pending user review. No results have been shared externally.', '']))
    with (output_dir/'findings.md').open('a') as handle:
        for name,groups in summary['paired_comparisons'].items():
            handle.write(f'\nPaired development comparison: {name}\n\n')
            for group,result in groups.items():
                handle.write(f'- {group}: {result["patients"]} evaluation-valid paired patients')
                if result['patients']:
                    handle.write(f'; {result["corrected"]} corrected, {result["regressed"]} regressed, {result["changed"]} changed labels.')
                handle.write('\n')
            handle.write(f'\nPaired macro-F1 uses all {len(labels)} study labels, including zero-support classes. Balanced accuracy averages recall over reference classes present in that paired subset. See comparison.json for precision/recall/support.\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--B',type=Path,required=True);p.add_argument('--A',type=Path);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--label-scheme',choices=['five','combined'],default='five')
    p.add_argument('--baseline-dir',type=Path,default=BASELINE,help='Saved historical predictions to compare on the same grouping')
    p.add_argument('--evaluation-policy',choices=EVALUATION_POLICIES,default='recorded')
    a=p.parse_args();s=compare(a.B,a.output_dir,a.A,a.label_scheme,a.baseline_dir,a.evaluation_policy)
    print(json.dumps({k:v for k,v in s.items() if k!='evaluations'},indent=2))
