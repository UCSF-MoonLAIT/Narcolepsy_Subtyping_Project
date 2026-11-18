import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json
import coverage_pipeline as cp
from test_submission import valid


class CharacterTokenizer:
    model_digest='synthetic';manifest_sha='synthetic'
    def chat_tokens(self,text):return len(text)
    def count(self,text):return len(text)
    def encode(self,text):
        return type('Encoding',(),{'offsets':[(i,i+1) for i in range(len(text))],'ids':list(range(len(text)))})()


class CoverageTests(unittest.TestCase):
    def test_lossless_partition_and_complete_record(self):
        tokenizer=CharacterTokenizer()
        with patch.object(cp,'PROMPT','{note_text}'),patch.dict(cp.OPTIONS,{'num_ctx':1200,'num_predict':50}):
            self.assertEqual(cp.plan_chunks(tokenizer,'001','unknown','short')[0]['text'],'short')
            text='[2026-01-01] note\n'+('alpha beta '*650)+'late diagnosis'
            chunks=cp.plan_chunks(tokenizer,'001','unknown',text)
            self.assertGreater(len(chunks),1)
            self.assertEqual(''.join(text[c['start']:c['end']] for c in chunks),text)
            self.assertEqual(chunks[-1]['end'],len(text))
            self.assertTrue(all(cp.fit(tokenizer,cp.render('001','unknown',c['text'])) for c in chunks))

    def test_call_resume_and_terminal_retry_bound(self):
        class Client:
            calls=0
            def chat(self,**kwargs):
                self.calls+=1;p=kwargs['messages'][0]['content']
                return {'message':{'content':json.dumps(valid())},'prompt_eval_count':len(p),'done_reason':'stop'}
        with tempfile.TemporaryDirectory() as directory,patch.object(cp,'PROMPT','{note_text}'):
            client=Client();path=Path(directory)/'calls.jsonl';tokenizer=CharacterTokenizer()
            store=cp.CallStore(path,tokenizer,client)
            store.classify('001','2026-01-02','synthetic note','001:source_0000',['source_0000'])
            fresh=cp.CallStore(path,tokenizer,client)
            fresh.classify('001','2026-01-02','synthetic note','001:source_0000',['source_0000'])
            self.assertEqual(client.calls,1)
            with self.assertRaisesRegex(ValueError,'prompt changed'):
                fresh.classify('001','2026-01-02','changed','001:source_0000',['source_0000'])
            class BadClient:
                def chat(self,**kwargs):return {'message':{'content':''},'prompt_eval_count':999999,'done_reason':'length'}
            failed=cp.CallStore(Path(directory)/'bad.jsonl',tokenizer,BadClient())
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'Terminal call failure'):
                    failed.classify('001','2026-01-02','note','bad',['source_0000'])
            self.assertEqual(len(failed.records),2)
            self.assertIn('tokenizer_server_mismatch',failed.records[0]['validation_errors'])
            self.assertIn('generation_limit_reached',failed.records[0]['validation_errors'])

    def test_compaction_keeps_all_source_identifiers(self):
        record={'source_ids':['source_0000','source_0001'],'llm_output':valid()}
        self.assertEqual(cp.compact_judgment(record)['source_ids'],record['source_ids'])

class WorkflowTests(unittest.TestCase):
    def test_full_workflow_resume_and_compatible_retry_fork(self):
        from argparse import Namespace
        import pandas as pd
        import re
        class Client:
            def chat(self,**kwargs):
                prompt=kwargs['messages'][0]['content']
                pid=re.search(r'BDSPPatientID: (\S+)',prompt).group(1)
                return {'message':{'content':json.dumps(valid(pid))},'prompt_eval_count':len(prompt),'done_reason':'stop'}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.parquet';gold=root/'gold.xlsx'
            pd.DataFrame([{'BDSPPatientID':p,'index_date':'20260102','raw_notetxt':'synthetic note '+('x '*18000)} for p in ['101','102']]).to_parquet(source)
            pd.DataFrame({'bdsp_patient_id':[101,102],'final_label_gold':['NT2','NT2']}).to_excel(gold,index=False)
            args=Namespace(output_dir=root/'run',input=source,gold=gold,strategy='B',resume=False,max_patients=1,retry_from=None)
            with patch.object(cp,'LocalTokenizer',CharacterTokenizer),patch.object(cp.ollama,'Client',return_value=Client()):
                cp.run(args)
                first=cp.load_jsonl(args.output_dir/'nt_patient_llm_outputs.jsonl')
                self.assertEqual(len(first),1)
                self.assertEqual(first[0]['input_coverage'],1)
                self.assertGreater(first[0]['planned_chunks'],1)
                args.resume=True;args.max_patients=None;cp.run(args)
                all_rows=cp.load_jsonl(args.output_dir/'nt_patient_llm_outputs.jsonl')
                self.assertEqual(len(all_rows),2)
                original=(args.output_dir/'nt_patient_llm_outputs.jsonl').read_bytes()
                cp.run(args)
                self.assertEqual((args.output_dir/'nt_patient_llm_outputs.jsonl').read_bytes(),original)
                args.output_dir=root/'fork';args.resume=False;args.retry_from=root/'run';cp.run(args)
                self.assertEqual((root/'run/nt_patient_llm_outputs.jsonl').read_bytes(),original)
                self.assertEqual(len(cp.load_jsonl(root/'fork/nt_patient_llm_outputs.jsonl')),2)
                self.assertEqual(json.loads((root/'fork/run_manifest.json').read_text())['status'],'complete')
