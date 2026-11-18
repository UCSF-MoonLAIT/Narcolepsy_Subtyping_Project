from pathlib import Path
import json,hashlib,contextlib,io,itertools
import pandas as pd
from sklearn.metrics import accuracy_score,balanced_accuracy_score,f1_score,precision_recall_fscore_support,confusion_matrix
import sys
root=Path.cwd();sys.path.insert(0,str(root));sys.path.insert(0,str(root/'.runtime'))
from NT_LLM.narcolepsy_analysis import evaluate,GOLD,read_gold,normalized_id
from narcolepsy_stanford import INPUT_DIR,normalize_nt_date
from NT_LLM.validation import evidence_quote_support
from NT_LLM.label_schemes import grouped_label
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True);out=parser.parse_args().output_dir.resolve();out.mkdir(exist_ok=False)
runs={'historical_A':root/'NT_LLM/runs/stanford_v2_20261022T003015723429Z','original_B':root/'NT_LLM/runs/retry_B_combined_20261118T062415Z/original_B/retry_run','combined_NT2_IH':root/'NT_LLM/runs/retry_B_combined_20261118T062415Z/combined_NT2_IH/retry_run'}
labels=['NT1','NT2_IH','Uncertain','Not_NT_IH'];hashes={}
for folder in runs.values():
 for name in ['nt_patient_llm_outputs.jsonl','run_manifest.json','prompt_snapshot.txt']:
  p=folder/name
  if p.exists():hashes[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
source=pd.read_parquet(INPUT_DIR);source['BDSPPatientID']=source.BDSPPatientID.map(normalized_id);texts=source.set_index('BDSPPatientID').raw_notetxt.to_dict();subgroup={p for p,t in texts.items() if not __import__('re').search(r'narcolep|idiopathic hypersomn',t[:7000],__import__('re').I) and __import__('re').search(r'narcolep|idiopathic hypersomn',t[7000:],__import__('re').I)};assert len(subgroup)==34
result={'description':'Retrospective descriptive four-label comparison of historical prefix A, complete-source original B and combined NT2/IH; not a controlled truncation experiment.','source_quote_verification':'Common strict analysis checks original full supplied record for every run. A-prefix quote verification is additionally reported separately because A received only the first 7000 characters.','label_order':labels,'policies':{},'input_artifacts_sha256':hashes}
for policy in ['classification','strict']:
 sums={};tables={};eligible={}
 for name,folder in runs.items():
  dest=out/policy/name
  with contextlib.redirect_stdout(io.StringIO()):sums[name]=evaluate(GOLD,folder/'nt_patient_llm_outputs.jsonl',dest,label_scheme='combined',evaluation_policy=policy,source_path=INPUT_DIR)
  t=pd.read_csv(dest/'NT_merged_results.csv',dtype={'BDSPPatientID':str});tables[name]=t.set_index('BDSPPatientID');eligible[name]=set(t.loc[t.metric_eligible,'BDSPPatientID'])
 def comparison(names,ids):
  ids=sorted(ids);r={'patients':len(ids),'metrics':{}}
  for name in names:
   truth=tables[name].loc[ids,'final_label_gold'];pred=tables[name].loc[ids,'final_label'];pr,rc,f,su=precision_recall_fscore_support(truth,pred,labels=labels,zero_division=0)
   r['metrics'][name]={'correct':int((truth==pred).sum()),'accuracy':float(accuracy_score(truth,pred)) if ids else None,'balanced_accuracy':float(balanced_accuracy_score(truth,pred)) if ids else None,'macro_f1':float(f1_score(truth,pred,labels=labels,average='macro',zero_division=0)) if ids else None,'per_class':{k:{'support':int(su[i]),'precision':float(pr[i]),'recall':float(rc[i]),'f1':float(f[i])} for i,k in enumerate(labels)},'confusion_matrix':confusion_matrix(truth,pred,labels=labels).tolist()}
  if len(names)==2:
   a,b=names;truth=tables[a].loc[ids,'final_label_gold'];ap=tables[a].loc[ids,'final_label'];bp=tables[b].loc[ids,'final_label'];r.update(corrected=int(((ap!=truth)&(bp==truth)).sum()),regressed=int(((ap==truth)&(bp!=truth)).sum()))
  return r
 pairs={}
 for a,b in itertools.combinations(runs,2):
  ids=eligible[a]&eligible[b];pairs[a+'_vs_'+b]={'all':comparison([a,b],ids),'beyond_cutoff_34':comparison([a,b],ids&subgroup)}
 common=set.intersection(*eligible.values());three={'all':comparison(list(runs),common),'beyond_cutoff_34':comparison(list(runs),common&subgroup)}
 result['policies'][policy]={'individual':sums,'pairwise':pairs,'three_way_common':three}
# Check what A actually saw, without altering common-policy results.
a=[json.loads(l) for l in (runs['historical_A']/'nt_patient_llm_outputs.jsonl').read_text().splitlines() if l.strip()];details=[]
for item in a:
 pid=normalized_id(item['BDSPPatientID']);v=item.get('llm_output') or {};full=evidence_quote_support(v,texts[pid]);prefix=evidence_quote_support(v,texts[pid][:7000]);details.append({'BDSPPatientID':pid,'full_record_quotes_pass':bool(full) and all(q['match_type']!='unsupported' for q in full),'actual_prefix_quotes_pass':bool(prefix) and all(q['match_type']!='unsupported' for q in prefix)})
pd.DataFrame(details).to_csv(out/'historical_A_quote_scope_reconciliation.csv',index=False)
result['historical_A_quote_scope']={'full_record_pass':sum(r['full_record_quotes_pass'] for r in details),'actual_prefix_pass':sum(r['actual_prefix_quotes_pass'] for r in details),'full_pass_but_prefix_fail':sum(r['full_record_quotes_pass'] and not r['actual_prefix_quotes_pass'] for r in details)}
# Actual-input sensitivity uses A's observed prefix rather than the full record.
eligible['historical_A'] &= {r['BDSPPatientID'] for r in details if r['actual_prefix_quotes_pass']}
common=set.intersection(*eligible.values())
scope_results={'definition':'Primary structural eligibility plus quotes supported by actual model input: first 7000 characters for historical A, full available record for B/combined.','label_order':labels,'individual':{name:comparison([name],ids) for name,ids in eligible.items()},'three_way_common':{'all':comparison(list(runs),common),'beyond_cutoff_34':comparison(list(runs),common&subgroup)},'pairwise':{}}
for a,b in itertools.combinations(runs,2):
 ids=eligible[a]&eligible[b];scope_results['pairwise'][a+'_vs_'+b]={'all':comparison([a,b],ids),'beyond_cutoff_34':comparison([a,b],ids&subgroup)}
(out/'input_scope_strict_comparison.json').write_text(json.dumps(scope_results,indent=2)+'\n')
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
result['original_artifacts_unchanged']=True;result['inference_performed']=False
(out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'output':str(out),'primary_eligible':{k:v['metric_denominator'] for k,v in result['policies']['classification']['individual'].items()},'three_way':result['policies']['classification']['three_way_common']['all'],'quote_scope':result['historical_A_quote_scope']},indent=2))
