"""Offline exact-token coverage accounting for historical clipping and proposed B chunks."""
import json
from pathlib import Path
import pandas as pd
from coverage_pipeline import LocalTokenizer, plan_chunks, render, OPTIONS, SAFETY_TOKENS
from narcolepsy_stanford import INPUT_DIR, normalize_nt_date


def main():
    output=Path('NT_LLM/submission_20261109/token_coverage')
    output.mkdir(parents=True,exist_ok=True)
    tokenizer=LocalTokenizer();source=pd.read_parquet(INPUT_DIR);rows=[]
    for row in source.to_dict('records'):
        pid=str(row['BDSPPatientID']);index=normalize_nt_date(row['index_date']);text=row['raw_notetxt']
        chunks=plan_chunks(tokenizer,pid,index,text)
        original_tokens=tokenizer.count(text);kept_tokens=tokenizer.count(text[:7000])
        item={'BDSPPatientID':pid,'source_chars':len(text),'source_tokens':original_tokens,
              'baseline_chars':len(text[:7000]),'baseline_note_tokens':kept_tokens,
              'baseline_char_coverage':min(7000,len(text))/len(text),
              'baseline_note_token_coverage':kept_tokens/original_tokens,
              'baseline_rendered_tokens':tokenizer.chat_tokens(render(pid,index,text[:7000])),
              'original_num_ctx':8192,'original_num_predict':'implicit model/server default; not retained historically',
              'B_source_chunks':len(chunks),'B_planned_char_coverage':sum(c['end']-c['start'] for c in chunks)/len(text),
              'B_total_source_prompt_tokens':sum(c['input_tokens'] for c in chunks),
              'B_max_source_prompt_tokens':max(c['input_tokens'] for c in chunks),
              'B_instruction_chat_tokens':tokenizer.chat_tokens(render(pid,index,'')),
              'B_output_reserved_per_call':OPTIONS['num_predict'],'B_safety_reserved_per_call':SAFETY_TOKENS,
              'diagnostic_terms_only_after_cutoff':not bool(__import__('re').search(r'narcolep|idiopathic hypersomn',text[:7000],__import__('re').I)) and bool(__import__('re').search(r'narcolep|idiopathic hypersomn',text[7000:],__import__('re').I))}
        rows.append(item)
        (output/f'plan_{pid}.json').write_text(json.dumps({k:v for k,v in item.items()}|{'chunks':[{k:v for k,v in c.items() if k!='text'} for c in chunks]},indent=2))
        print(json.dumps({'planned':len(rows),'expected':len(source),'chunks':len(chunks)}),flush=True)
    table=pd.DataFrame(rows);table.to_csv(output/'patient_input_coverage.csv',index=False)
    summary={'patients':len(table),'total_source_tokens':int(table.source_tokens.sum()),
             'baseline_input_tokens':int(table.baseline_note_tokens.sum()),
             'baseline_note_token_coverage':float(table.baseline_note_tokens.sum()/table.source_tokens.sum()),
             'baseline_rendered_prompt_tokens_min':int(table.baseline_rendered_tokens.min()),
             'baseline_rendered_prompt_tokens_max':int(table.baseline_rendered_tokens.max()),
             'baseline_prompts_exceeding_8192':int((table.baseline_rendered_tokens>8192).sum()),
             'B_total_source_calls':int(table.B_source_chunks.sum()),'B_direct_full_record_patients':int((table.B_source_chunks==1).sum()),
             'B_source_prompt_tokens':int(table.B_total_source_prompt_tokens.sum()),
             'B_coverage':float((table.source_chars*table.B_planned_char_coverage).sum()/table.source_chars.sum()),
             'budget':OPTIONS,'safety_tokens':SAFETY_TOKENS,
             'model_digest':tokenizer.model_digest,
             'accounting_note':'Counts reconstructed from installed GGUF Qwen2 byte BPE; chat accounting verified separately against server. Historical server counts were not retained.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
