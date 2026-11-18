import contextlib
import io
import json
from argparse import Namespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import coverage_pipeline as cp
import compare_coverage as comparison
from NT_LLM.label_schemes import grouped_label, labels_for
from NT_LLM.narcolepsy_analysis import evaluate
from NT_LLM.validation import validate_output, evidence_flags
from test_coverage import CharacterTokenizer
from test_submission import valid


class CombinedTests(unittest.TestCase):
    def tearDown(self):
        cp.configure_prompt(cp.ROOT/'prompts/stanford_v2.txt', 'five')

    def test_schema_validation_and_prompt_pairing(self):
        cp.configure_prompt(cp.ROOT/'prompts/stanford_v3.txt', 'combined')
        value = valid(); value['final_label'] = 'NT2_IH'
        self.assertEqual(validate_output(value, '001', '2026-01-02', 'synthetic note', 'combined'), [])
        self.assertIn('invalid_label', validate_output(value, '001', '2026-01-02', 'synthetic note'))
        self.assertIn('candidate_requires_clinical_verification', evidence_flags(value, 'synthetic note'))
        for label in ['NT2', 'IH']:
            value['final_label'] = label
            self.assertIn('invalid_label', validate_output(value, '001', '2026-01-02', 'synthetic note', 'combined'))
        with self.assertRaisesRegex(ValueError, 'output labels'):
            cp.configure_prompt(cp.ROOT/'prompts/stanford_v3.txt', 'five')

    def test_combined_evaluation_and_export_preserve_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); gold = root/'gold.xlsx'; source = root/'source.parquet'
            ids = ['101', '102', '103', '104', '105']
            reference = ['NT1', 'NT2', 'IH', 'Uncertain', 'Not_NT_IH']
            pd.DataFrame({'bdsp_patient_id': ids, 'final_label_gold': reference}).to_excel(gold, index=False)
            pd.DataFrame([{'BDSPPatientID': p, 'index_date': '20260102', 'raw_notetxt': 'synthetic note'} for p in ids]).to_parquet(source)
            digest = gold.read_bytes()
            for name, combined in [('old', False), ('new', True)]:
                folder = root/name; folder.mkdir()
                rows = []
                for pid, label in zip(ids, reference):
                    value = valid(pid); value['final_label'] = grouped_label(label, 'combined') if combined else label
                    rows.append({'BDSPPatientID': pid, 'index_date': '2026-01-02', 'llm_output': value, 'error': None})
                (folder/'nt_patient_llm_outputs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            with contextlib.redirect_stdout(io.StringIO()), patch.object(comparison, 'INPUT_DIR', source), patch.object(comparison, 'GOLD', gold):
                result = comparison.compare(root/'new', root/'report', label_scheme='combined', baseline_dir=root/'old')
            for summary in result['evaluations'].values():
                self.assertEqual(summary['metric_denominator'], 5)
                self.assertEqual(summary['metrics']['accuracy'], 1)
                self.assertEqual(summary['metrics']['macro_f1'], 1)
                self.assertEqual(len(summary['confusion_matrix']), 4)
            merged = pd.read_csv(root/'report/B/NT_merged_results.csv')
            self.assertEqual(merged.final_label_gold_original.tolist(), reference)
            self.assertEqual(merged.final_label_gold.tolist(), [grouped_label(x, 'combined') for x in reference])
            review = pd.read_csv(root/'report/B_handoff/review_queue.csv', keep_default_na=False)
            self.assertTrue((review.confirmed == '').all())
            self.assertEqual(gold.read_bytes(), digest)
            # Failure/invalid/missing records remain outside the metric denominator.
            path = root/'new/nt_patient_llm_outputs.jsonl'
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            rows[0]['error'] = 'retained failure'
            rows[1]['llm_output']['final_label'] = 'other'
            path.write_text(''.join(json.dumps(r)+'\n' for r in rows[:-1]))
            with contextlib.redirect_stdout(io.StringIO()):
                summary = evaluate(gold, path, root/'partial', 'combined')
            self.assertEqual(summary['metric_denominator'], 2)
            self.assertEqual(summary['status_counts']['inference_error'], 1)
            self.assertEqual(summary['status_counts']['invalid_prediction'], 1)
            self.assertEqual(summary['status_counts']['missing_prediction'], 1)

    def test_combined_chunk_reduction_resume_and_prompt_change_rejected(self):
        import re
        class Client:
            def chat(self, **kwargs):
                prompt = kwargs['messages'][0]['content']
                pid = re.search(r'BDSPPatientID: (\S+)', prompt).group(1)
                value = valid(pid); value['final_label'] = 'NT2_IH'
                return {'message': {'content': json.dumps(value)}, 'prompt_eval_count': len(prompt), 'done_reason': 'stop'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source.parquet'; gold = root/'gold.xlsx'
            pd.DataFrame([{'BDSPPatientID': '101', 'index_date': '20260102', 'raw_notetxt': 'synthetic note '+('x '*18000)}]).to_parquet(source)
            pd.DataFrame({'bdsp_patient_id': ['101'], 'final_label_gold': ['IH']}).to_excel(gold, index=False)
            args = Namespace(input=source, gold=gold, output_dir=root/'run', strategy='B', resume=False,
                             max_patients=None, retry_from=None, prompt_file=cp.ROOT/'prompts/stanford_v3.txt', label_scheme='combined')
            with patch.object(cp, 'LocalTokenizer', CharacterTokenizer), patch.object(cp.ollama, 'Client', return_value=Client()):
                cp.run(args)
                rows = cp.load_jsonl(args.output_dir/'nt_patient_llm_outputs.jsonl')
                self.assertEqual(rows[0]['input_coverage'], 1)
                self.assertGreater(rows[0]['planned_chunks'], 1)
                calls = cp.load_jsonl(args.output_dir/'calls.jsonl')
                self.assertTrue(any(':reduce:' in r['call_id'] for r in calls))
                before = (args.output_dir/'calls.jsonl').read_bytes()
                args.resume = True; cp.run(args)
                self.assertEqual((args.output_dir/'calls.jsonl').read_bytes(), before)
                args.prompt_file = cp.ROOT/'prompts/stanford_v2.txt'; args.label_scheme = 'five'
                with self.assertRaisesRegex(ValueError, 'Incompatible'):
                    cp.run(args)
            manifest = json.loads((args.output_dir/'run_manifest.json').read_text())
            self.assertEqual(manifest['config']['prompt_file'], 'stanford_v3.txt')
            self.assertEqual(manifest['config']['label_scheme'], 'combined')

    def test_smoke_gate_requires_subtype_rules_coverage_and_reconciliation(self):
        from run_v3_cohort import SYNTHETIC, smoke_gate
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'smoke').mkdir()
            source = [{k: case[k] for k in ['BDSPPatientID', 'index_date', 'raw_notetxt']} for case in SYNTHETIC]
            source.append({'BDSPPatientID': 'long', 'index_date': '20260102', 'raw_notetxt': 'synthetic note'})
            pd.DataFrame(source).to_parquet(root/'smoke_input.parquet')
            patients = []
            for row in source:
                pid = row['BDSPPatientID']; value = valid(pid)
                value['key_evidence_quotes'] = [row['raw_notetxt']]
                value['final_label'] = 'Uncertain' if pid == 'synthetic_unspecified' else 'NT2_IH'
                patients.append({'BDSPPatientID': pid, 'llm_output': value, 'error': None,
                                 'input_coverage': 1, 'planned_chunks': 2 if pid == 'long' else 1})
            calls = [{'call_id': 'long:reduce:0:0', 'status': 'valid', 'token_accounting_delta': -2, 'elapsed_sec': 1}]
            patient_path = root/'smoke/nt_patient_llm_outputs.jsonl'
            def save():
                patient_path.write_text(''.join(json.dumps(p)+'\n' for p in patients))
                (root/'smoke/calls.jsonl').write_text(''.join(json.dumps(c)+'\n' for c in calls))
            save()
            self.assertTrue(smoke_gate(root)['passed'])
            patients[0]['llm_output']['final_label'] = 'NT2_IH'; save()
            with self.assertRaisesRegex(ValueError, 'Synthetic subtype rule'):
                smoke_gate(root)
            patients[0]['llm_output']['final_label'] = 'Uncertain'
            patients[-1]['input_coverage'] = 0.5; save()
            with self.assertRaisesRegex(ValueError, 'source coverage'):
                smoke_gate(root)
            patients[-1]['input_coverage'] = 1
            calls[0]['call_id'] = 'long:source_0000'; save()
            with self.assertRaisesRegex(ValueError, 'reconciliation'):
                smoke_gate(root)
