import json
from pathlib import Path
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import patch

import pandas as pd
import coverage_pipeline as cp
from NT_LLM.validation import quote_support, evidence_flags
from run_v3_cohort import reuse_saved_smoke, verify_reused_smoke
from test_coverage import CharacterTokenizer
from test_submission import valid


class QuoteSupportTests(unittest.TestCase):
    def test_exact_and_formatting_matches_return_original_character_spans(self):
        text = 'α note: has cataplexy "as bad as ever"\n  and remains sleepy.'
        for quote, kind in [('has cataplexy', 'exact'),
                            ("has cataplexy 'as bad as ever' and remains sleepy.", 'formatting_only')]:
            result = quote_support(quote, text)
            self.assertEqual(result['match_type'], kind)
            self.assertEqual(result['raw_quote'], quote)
            self.assertEqual(result['source_quote'], text[result['source_start']:result['source_end']])
        flags = evidence_flags({'key_evidence_quotes': ["has cataplexy 'as bad as ever' and remains sleepy."]}, text)
        self.assertIn('quote_formatting_normalized', flags)
        self.assertNotIn('nonverbatim_or_unsupported_quote', flags)

    def test_substantive_changes_and_word_apostrophes_are_rejected(self):
        for quote, source in [
            ('Cataplexy is present.', 'Cataplexy is not present.'),
            ('latency 8 minutes', 'latency 18 minutes'),
            ('latency 8 minutes', 'latency *** minutes'),
            ('narcolepsy confirmed', 'Narcolepsy confirmed'),
            ('sleep-onset REM', 'sleep onset REM'),
            ('sleep onset', 'sleeponset'),
            ('narcolepsy confirmed', 'narcolepsy was confirmed'),
            ('patient"s diagnosis', "patient's diagnosis"),
        ]:
            with self.subTest(quote=quote, source=source):
                result = quote_support(quote, source)
                self.assertEqual(result['match_type'], 'unsupported')
                self.assertIsNone(result['source_quote'])
        self.assertEqual(quote_support('', 'text')['match_type'], 'unsupported')

    def test_saved_smoke_reuse_retains_original_inference_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); parent = root/'old'; work = root/'new'
            (parent/'smoke').mkdir(parents=True); work.mkdir()
            cp.configure_prompt(cp.ROOT/'prompts/stanford_v3.txt', 'combined')
            identity = {k: 'same' for k in ['input_sha256', 'gold_sha256', 'prompt_sha256']}
            previous = {'identity': identity}
            frame = pd.DataFrame({'BDSPPatientID': ['synthetic'], 'raw_notetxt': ['synthetic note']})
            reference = pd.DataFrame({'BDSPPatientID': ['synthetic'], 'final_label_gold': ['NT2']})
            for folder in [parent, work]:
                frame.to_parquet(folder/'smoke_input.parquet', index=False)
                reference.to_excel(folder/'smoke_reference.xlsx', index=False)
            for name, key in [('smoke_input.parquet', 'smoke_input_sha256'), ('smoke_reference.xlsx', 'smoke_reference_sha256')]:
                previous[key] = cp.legacy.file_sha256(parent/name)
            (parent/'preflight.json').write_text(json.dumps(previous))
            config = {'model': cp.MODEL, 'model_digest': 'test_digest', 'options': cp.OPTIONS,
                      'think': cp.THINK, 'safety_tokens': cp.SAFETY_TOKENS,
                      'prompt_sha256': cp.sha(cp.PROMPT), 'label_scheme': 'combined', 'strategy': 'B'}
            (parent/'smoke/run_manifest.json').write_text(json.dumps({'status': 'complete', 'config': config}))
            (parent/'smoke/prompt_snapshot.txt').write_text(cp.PROMPT)
            for name in ['calls.jsonl', 'nt_patient_llm_outputs.jsonl']:
                (parent/'smoke'/name).write_text('{"raw_output":"preserved"}\n')
            before = {p.name: p.read_bytes() for p in (parent/'smoke').iterdir()}
            reuse_saved_smoke(work, parent, {'identity': identity, 'model_digest': 'test_digest'})
            verify_reused_smoke(work)
            self.assertFalse((work/'full').exists())
            for name, original in before.items():
                self.assertEqual((parent/'smoke'/name).read_bytes(), original)
                self.assertEqual((work/'smoke'/name).read_bytes(), original)
            (work/'smoke/calls.jsonl').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'changed'):
                verify_reused_smoke(work)
            cp.configure_prompt(cp.ROOT/'prompts/stanford_v2.txt', 'five')

    def test_full_patient_fails_substantive_quote_change_but_retains_raw_output(self):
        class Client:
            def chat(self, **kwargs):
                value = valid('101'); value['final_label'] = 'NT2_IH'
                value['key_evidence_quotes'] = ['Cataplexy is present.']
                return {'message': {'content': json.dumps(value)},
                        'prompt_eval_count': len(kwargs['messages'][0]['content']), 'done_reason': 'stop'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source.parquet'
            pd.DataFrame([{'BDSPPatientID': '101', 'index_date': '20260102',
                           'raw_notetxt': 'Cataplexy is not present.'}]).to_parquet(source)
            args = Namespace(input=source, gold=None, output_dir=root/'run', strategy='B',
                             resume=False, max_patients=None, retry_from=None,
                             prompt_file=cp.ROOT/'prompts/stanford_v3.txt', label_scheme='combined')
            with patch.object(cp, 'LocalTokenizer', CharacterTokenizer), patch.object(cp.ollama, 'Client', return_value=Client()):
                cp.run(args)
            row = cp.load_jsonl(root/'run/nt_patient_llm_outputs.jsonl')[0]
            self.assertEqual(row['error'], 'unsupported_final_evidence_quote')
            self.assertEqual(row['evidence_quote_support'][0]['match_type'], 'unsupported')
            self.assertEqual(row['llm_output']['key_evidence_quotes'], ['Cataplexy is present.'])
            self.assertIn('Cataplexy is present.', row['raw_llm_output'])
            cp.configure_prompt(cp.ROOT/'prompts/stanford_v2.txt', 'five')
