"""Complete-source, token-budgeted reference inference with immutable call checkpoints.
B: original v2 classification on complete records or all bounded source chunks;
recursive classification of chunk judgments for long records. No extraction-only stage.
"""
import argparse
import contextlib
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'.runtime'))
import pandas as pd
import ollama
from tokenizers import Tokenizer, Regex, AddedToken, models, pre_tokenizers, decoders
from gguf import GGUFReader
import narcolepsy_stanford as legacy
from NT_LLM.validation import validate_output, evidence_flags
from NT_LLM.narcolepsy_analysis import GOLD, evaluate, read_gold, normalized_id

MODEL = 'qwen3:14b'
OPTIONS = {'temperature':0, 'top_p':0.1, 'num_ctx':40960, 'num_predict':2048}
# Explicitly identical across regenerated A and B. Historical A used implicit thinking.
THINK = False
SAFETY_TOKENS = 128
PROMPT = (ROOT/'prompts/stanford_v2.txt').read_text()
LOCAL_MODELS = Path.home()/'.ollama/models'


def sha(value): return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()


def atomic_json(path, value):
    path=Path(path); temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w') as handle:
        json.dump(value,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    temporary.replace(path)


def append_record(path,value):
    with Path(path).open('a') as handle:
        handle.write(json.dumps(value,ensure_ascii=False)+'\n');handle.flush();os.fsync(handle.fileno())


class LocalTokenizer:
    """Reconstruct Qwen2 byte BPE from the exact installed Qwen3 GGUF vocabulary."""
    def __init__(self):
        manifest_path=LOCAL_MODELS/'manifests/registry.ollama.ai/library/qwen3/14b'
        manifest=json.loads(manifest_path.read_text());self.manifest_sha=sha(manifest_path.read_bytes())
        self.model_digest=next(l['digest'] for l in manifest['layers'] if l['mediaType']=='application/vnd.ollama.image.model')
        cache=ROOT/'NT_LLM/tokenizer_cache'/f'{self.model_digest.replace(":","-")}.json'
        if cache.exists(): self.tokenizer=Tokenizer.from_file(str(cache));return
        reader=GGUFReader(str(LOCAL_MODELS/'blobs'/self.model_digest.replace(':','-')),mode='r')
        if reader.get_field('tokenizer.ggml.pre').contents()!='qwen2':
            raise ValueError('Unsupported model pretokenizer')
        tokens=reader.get_field('tokenizer.ggml.tokens').contents()
        merges=[tuple(m.split(' ',1)) for m in reader.get_field('tokenizer.ggml.merges').contents()]
        tokenizer=Tokenizer(models.BPE(vocab={s:i for i,s in enumerate(tokens)},merges=merges,byte_fallback=False))
        pattern=r"(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"
        tokenizer.pre_tokenizer=pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(pattern),behavior='isolated'),pre_tokenizers.ByteLevel(add_prefix_space=False,use_regex=False)])
        tokenizer.decoder=decoders.ByteLevel()
        tokenizer.add_special_tokens([AddedToken(s,special=True,normalized=False) for s in tokens if s.startswith('<|') and s.endswith('|>')])
        cache.parent.mkdir(parents=True,exist_ok=True); tokenizer.save(str(cache));self.tokenizer=tokenizer

    def encode(self,text): return self.tokenizer.encode(text,add_special_tokens=False)
    def count(self,text): return len(self.encode(text).ids)
    def chat_tokens(self,prompt):
        # Matches installed Ollama Go chat template with think=False, no system/tools.
        rendered='<|im_start|>user\n'+prompt+' /no_think<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
        return self.count(rendered)


def render(pid,index,text):
    return PROMPT.format(BDSPPatientID=pid,index_date=index,note_text=text)


def fit(tokenizer,prompt):
    return tokenizer.chat_tokens(prompt)+OPTIONS['num_predict']+SAFETY_TOKENS<=OPTIONS['num_ctx']


def source_header(text,start,end,chunk_index):
    matches=list(re.finditer(r'(?m)^\[\d{4}-\d{2}-\d{2}\][^\n]*',text[:start]))
    containing=matches[-1].group() if matches else 'date/header unavailable; do not infer'
    return f'[Source chunk {chunk_index}; original character offsets {start}:{end}; containing note: {containing}]\n'


def plan_chunks(tokenizer,pid,index,text):
    if fit(tokenizer,render(pid,index,text)):
        return [{'source_id':'source_0000','start':0,'end':len(text),'text':text,'input_tokens':tokenizer.chat_tokens(render(pid,index,text))}]
    chunks=[];start=0; enc=tokenizer.encode(text)
    # Encoding offsets provide lossless character boundaries; all source chars are partitioned.
    ends=sorted(set(end for _,end in enc.offsets if end>0))
    import bisect
    while start<len(text):
        begin=bisect.bisect_right(ends,start);low=begin;high=len(ends)-1;best=None
        while low<=high:
            mid=(low+high)//2;end=ends[mid]
            body=source_header(text,start,end,len(chunks))+text[start:end]
            if fit(tokenizer,render(pid,index,body)):best=end;low=mid+1
            else:high=mid-1
        if best is None or best<=start: raise ValueError('Instructions/output budget leave no source capacity')
        body=source_header(text,start,best,len(chunks))+text[start:best]
        chunks.append({'source_id':f'source_{len(chunks):04d}','start':start,'end':best,'text':body,'input_tokens':tokenizer.chat_tokens(render(pid,index,body))})
        start=best
    assert chunks[0]['start']==0 and chunks[-1]['end']==len(text)
    assert all(a['end']==b['start'] for a,b in zip(chunks,chunks[1:]))
    return chunks


def load_jsonl(path):
    if not Path(path).exists():return []
    records=[]
    for i,line in enumerate(Path(path).open(),1):
        try:records.append(json.loads(line))
        except json.JSONDecodeError as exc:raise ValueError(f'Malformed checkpoint line {i}; use recover-tail, preserving original') from exc
    return records


class CallStore:
    def __init__(self,path,tokenizer,client):
        self.path=path;self.tokenizer=tokenizer;self.client=client
        self.records=load_jsonl(path);self.cache={}
        for r in self.records:
            if r['status']=='valid':self.cache[r['call_id']]=r

    def classify(self,pid,index,body,call_id,source_ids):
        prompt=render(pid,index,body); prompt_hash=sha(prompt)
        if call_id in self.cache:
            saved=self.cache[call_id]
            if saved['prompt_sha256']!=prompt_hash:raise ValueError('Checkpoint prompt changed')
            return saved
        previous=[r for r in self.records if r['call_id']==call_id]
        # Bounded across resumes too; immutable failures are not retried indefinitely.
        if len(previous)>=2:raise RuntimeError(f'Terminal call failure: {call_id}')
        input_tokens=self.tokenizer.chat_tokens(prompt)
        if not fit(self.tokenizer,prompt):raise ValueError('Prompt exceeds explicit input/output budget')
        for attempt in range(len(previous)+1,3):
            started=time.time();data={};raw='';parsed={};errors=[]
            try:
                response=self.client.chat(model=MODEL,messages=[{'role':'user','content':prompt}],options=OPTIONS,think=THINK,keep_alive='30m')
                data=response.model_dump() if hasattr(response,'model_dump') else dict(response)
                raw=data['message'].get('content') or '';parsed=legacy.safe_parse_json(raw)
                errors=validate_output(parsed,pid,index,body)
                # Context overflow must be a hard technical failure, never a silently accepted prediction.
                actual=data.get('prompt_eval_count');accounting_delta=(actual-input_tokens) if actual is not None else None
                if actual is None:errors.append('missing_server_token_accounting')
                if actual is not None and abs(accounting_delta)>8:errors.append('tokenizer_server_mismatch')
                if data.get('done_reason')=='length':errors.append('generation_limit_reached')
                if actual is not None and actual+OPTIONS['num_predict']>OPTIONS['num_ctx']:errors.append('context_budget_exceeded')
            except Exception as exc:
                errors=[f'transport:{type(exc).__name__}'];accounting_delta=None
            record={'call_id':call_id,'patient_id':pid,'attempt':attempt,'source_ids':source_ids,
                    'prompt_sha256':prompt_hash,'estimated_prompt_tokens':input_tokens,
                    'server_prompt_tokens':data.get('prompt_eval_count'),'token_accounting_delta':accounting_delta,
                    'raw_response':data,'raw_llm_output':raw,'llm_output':parsed,
                    'elapsed_sec':time.time()-started,'validation_errors':errors,
                    'status':'failed' if errors else 'valid', 'evidence_flags':evidence_flags(parsed,body) if isinstance(parsed,dict) else []}
            append_record(self.path,record);self.records.append(record)
            if not errors:self.cache[call_id]=record;return record
        raise RuntimeError(f'Terminal call failure: {call_id}')


def compact_judgment(record):
    value=record['llm_output']
    # Carry source identity, label, dates, verbatim evidence and rationale; never raw source-free claims of confirmation.
    return {'source_ids':record['source_ids'],'final_label':value['final_label'],
            'diagnosis_anchor_date':value.get('diagnosis_anchor_date'),'key_evidence':value.get('key_evidence'),
            'key_evidence_quotes':value.get('key_evidence_quotes'),'reasoning':value.get('reasoning')}


def reduce_records(store,tokenizer,pid,index,records):
    level=0
    while len(records)>1:
        groups=[];current=[]
        for record in records:
            candidate=current+[record]
            body='CHUNK CLASSIFICATION JUDGMENTS from all indicated source ranges. Reconcile the longitudinal documented diagnoses using the existing rules. A chunk-level Uncertain does not invalidate an established diagnosis in another chunk. Preserve explicit diagnostic revisions and conflicting evidence. These are model judgments, not new clinical notes.\n'+json.dumps([compact_judgment(r) for r in candidate],ensure_ascii=False)
            if not fit(tokenizer,render(pid,index,body)):
                if not current:raise ValueError('One chunk judgment exceeds reduction budget')
                groups.append(current);current=[record]
            else:current=candidate
        if current:groups.append(current)
        if len(groups)>=len(records):raise ValueError('Reduction cannot make progress within token budget')
        output=[]
        for group_index,group in enumerate(groups):
            source_ids=[s for r in group for s in r['source_ids']]
            body='CHUNK CLASSIFICATION JUDGMENTS (model-derived, reconcile all source ranges; consider diagnostic revision, preserve justified uncertainty):\n'+json.dumps([compact_judgment(r) for r in group],ensure_ascii=False)
            output.append(store.classify(pid,index,body,f'{pid}:reduce:{level}:{group_index}',source_ids))
        records=output;level+=1
    return records[0]


def source_version():
    paths=[Path(__file__),ROOT/'narcolepsy_stanford.py',*sorted((ROOT/'NT_LLM').glob('*.py'))]
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}


def run(args):
    output=args.output_dir.resolve();tokenizer=LocalTokenizer()
    source=pd.read_parquet(args.input);source['BDSPPatientID']=source.BDSPPatientID.map(normalized_id)
    if source.BDSPPatientID.duplicated().any():raise ValueError('Duplicate input IDs')
    if {'index_date','raw_notetxt'}-set(source):raise ValueError('Missing prepared notes/index_date')
    if args.gold:read_gold(args.gold)
    config={'strategy':args.strategy,'input_sha256':legacy.file_sha256(args.input),
            'gold_sha256':legacy.file_sha256(args.gold) if args.gold else None,
            'prompt_sha256':sha(PROMPT),'model':MODEL,'model_digest':tokenizer.model_digest,
            'model_manifest_sha256':tokenizer.manifest_sha,'options':OPTIONS,'think':THINK,
            'safety_tokens':SAFETY_TOKENS,'sources':source_version(),
            'packages':{p:importlib.metadata.version(p) for p in ['ollama','tokenizers','gguf','pandas']}}
    if args.resume:
        manifest=json.loads((output/'run_manifest.json').read_text())
        if config!=manifest['config']:raise ValueError('Incompatible run/code/model/input; choose new directory')
    else:
        parent = None
        if args.retry_from:
            parent=json.loads((args.retry_from/'run_manifest.json').read_text())
            if parent['config']!=config:raise ValueError('Retry parent has incompatible configuration')
        if output.exists():raise ValueError('Output directory must be new')
        output.mkdir(parents=True);manifest={'config':config,'started_at':datetime.now(timezone.utc).isoformat()}
        if parent:
            manifest['retry_parent']={'directory':str(args.retry_from.resolve()),
                                     'manifest_sha256':legacy.file_sha256(args.retry_from/'run_manifest.json')}
            for filename in ['calls.jsonl','nt_patient_llm_outputs.jsonl']:
                kept=[r for r in load_jsonl(args.retry_from/filename)
                      if (r.get('status')=='valid' if filename=='calls.jsonl' else not r.get('error'))]
                for record in kept:append_record(output/filename,record)
        (output/'prompt_snapshot.txt').write_text(PROMPT)
        for relative in config['sources']:
            target=output/'code'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,target)
    with (output/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        manifest['status']='running';atomic_json(output/'run_manifest.json',manifest)
        client=ollama.Client(timeout=1800)
        store=CallStore(output/'calls.jsonl',tokenizer,client)
        done=load_jsonl(output/'nt_patient_llm_outputs.jsonl');done_ids={normalized_id(r['BDSPPatientID']) for r in done}
        if len(done_ids)!=len(done):raise ValueError('Duplicate patient output IDs')
        added=0
        try:
            for row in source.to_dict('records'):
                pid=row['BDSPPatientID'];index=legacy.normalize_nt_date(row['index_date'])
                if pid in done_ids:continue
                if args.max_patients is not None and added>=args.max_patients:break
                text='' if pd.isna(row['raw_notetxt']) else str(row['raw_notetxt'])
                started=time.time()
                planned_text=text[:7000] if args.strategy=='A' else text
                chunks=plan_chunks(tokenizer,pid,index,planned_text) if text else []
                plan={'BDSPPatientID':pid,'source_chars':len(text),'planned_chars':len(planned_text),
                      'source_tokens':tokenizer.count(text),'instruction_chat_tokens':tokenizer.chat_tokens(render(pid,index,'')),
                      'source_sha256':sha(text),'chunks':[{k:v for k,v in c.items() if k!='text'} for c in chunks]}
                atomic_json(output/f'plan_{pid}.json',plan)
                completed=[];result=None;error=None
                try:
                    if not chunks:raise ValueError('empty_note')
                    for chunk in chunks:
                        completed.append(store.classify(pid,index,chunk['text'],f'{pid}:{chunk["source_id"]}',[chunk['source_id']]))
                    result=reduce_records(store,tokenizer,pid,index,completed)
                except Exception as exc:error=f'{type(exc).__name__}: {exc}'
                evaluated=sum(c['end']-c['start'] for c in chunks[:len(completed)])
                patient={'BDSPPatientID':pid,'index_date':index,'llm_output':result['llm_output'] if result else None,
                         'raw_llm_output':result['raw_llm_output'] if result else None,'error':error,
                         'elapsed_sec':time.time()-started,'source_chars':len(text),'planned_chars':len(planned_text),
                         'evaluated_source_chars':evaluated,'input_coverage':evaluated/len(text) if text else 0,
                         'planned_chunks':len(chunks),'valid_source_chunks':len(completed),
                         'final_call_id':result['call_id'] if result else None}
                append_record(output/'nt_patient_llm_outputs.jsonl',patient);done.append(patient);added+=1
                print(json.dumps({'processed':len(done),'expected':len(source),'valid':sum(not r['error'] for r in done),
                                  'last_coverage':patient['input_coverage'],'elapsed_sec':patient['elapsed_sec']}),flush=True)
            manifest['status']='paused_for_technical_review' if len(done)<len(source) else ('complete_with_issues' if any(r['error'] for r in done) else 'complete')
            manifest['counts']={'expected':len(source),'processed':len(done),'valid':sum(not r['error'] for r in done),
                                'failed':sum(bool(r['error']) for r in done),'reviewed':0,'unresolved':len(source)}
            if args.gold and done:
                with contextlib.redirect_stdout(io.StringIO()):evaluate(args.gold,output/'nt_patient_llm_outputs.jsonl',output/'analysis_results')
        except BaseException as exc:
            manifest['status']='interrupted_or_failed';manifest['error_type']=type(exc).__name__;raise
        finally:
            manifest['updated_at']=datetime.now(timezone.utc).isoformat();atomic_json(output/'run_manifest.json',manifest)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=legacy.INPUT_DIR);p.add_argument('--gold',type=Path,default=GOLD)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--strategy',choices=['A','B'],default='B');p.add_argument('--resume',action='store_true');p.add_argument('--max-patients',type=int);p.add_argument('--retry-from',type=Path,help='New compatible run inheriting successful immutable checkpoints; retries failed patients')
    args=p.parse_args()
    if args.resume and args.retry_from:p.error('--resume and --retry-from are mutually exclusive')
    if args.max_patients is not None and args.max_patients<1:p.error('--max-patients must be positive')
    run(args)
