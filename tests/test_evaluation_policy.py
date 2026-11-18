import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import compare_coverage as comparison
from NT_LLM.narcolepsy_analysis import evaluate
from test_submission import valid


class EvaluationPolicyTests(unittest.TestCase):
    def fixture(self, root):
        ids = [str(n) for n in range(101, 110)]
        source = root/'source.parquet'; gold = root/'gold.xlsx'
        pd.DataFrame([{'BDSPPatientID': p, 'index_date': '20260102', 'raw_notetxt': 'synthetic note'} for p in ids]).to_parquet(source)
        pd.DataFrame({'bdsp_patient_id': ids, 'final_label_gold': ['IH'] * len(ids)}).to_excel(gold, index=False)
        old = root/'v2'; new = root/'v3'; old.mkdir(); new.mkdir()
        rows = []
        for pid in ids:
            value = valid(pid); value['final_label'] = 'IH'
            if pid == '102': value['key_evidence_quotes'] = ['invented quote']
            rows.append({'BDSPPatientID': pid, 'index_date': '2026-01-02', 'llm_output': value, 'error': None})
        (old/'nt_patient_llm_outputs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        new_rows = json.loads(json.dumps(rows))
        for row in new_rows:
            pid = row['BDSPPatientID']; value = row['llm_output']; value['final_label'] = 'NT2_IH'
            if pid in ['102', '103', '104']: row['error'] = 'unsupported_final_evidence_quote'
            if pid == '103': value['patient_id'] = 'wrong'
            if pid == '104': value['confidence'] = 'invalid'
            if pid == '105': row['error'] = 'transport failure with retained label'
            if pid == '106': value['final_label'] = 'wrong'
            if pid == '107': row['error'] = 'terminal invalid date'; row['llm_output'] = None
            if pid == '109': row['index_date'] = value['index_date'] = '2026-01-03'
        new_rows = [r for r in new_rows if r['BDSPPatientID'] != '108']
        (new/'nt_patient_llm_outputs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in new_rows))
        return source, gold, old, new

    def test_primary_includes_only_quote_errors_with_usable_outputs_and_keeps_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, gold, old, new = self.fixture(root)
            raw = (new/'nt_patient_llm_outputs.jsonl').read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                summary = evaluate(gold, new/'nt_patient_llm_outputs.jsonl', root/'primary', 'combined', 'classification', source)
                strict = evaluate(gold, new/'nt_patient_llm_outputs.jsonl', root/'strict', 'combined', 'strict', source)
            self.assertEqual(summary['metric_denominator'], 2)
            self.assertEqual(summary['quote_flagged_predictions_in_metrics'], 1)
            self.assertEqual(summary['quote_only_recorded_errors_in_metrics'], 1)
            self.assertEqual(summary['status_counts']['prediction_metadata_mismatch'], 2)
            self.assertEqual(summary['status_counts']['invalid_prediction'], 2)
            self.assertEqual(summary['status_counts']['inference_error'], 2)
            self.assertEqual(summary['status_counts']['missing_prediction'], 1)
            self.assertEqual(strict['metric_denominator'], 1)
            self.assertEqual(strict['status_counts']['quote_quality_failure'], 1)
            table = pd.read_csv(root/'primary/NT_merged_results.csv', dtype={'BDSPPatientID': str})
            flagged = table.set_index('BDSPPatientID').loc['102']
            self.assertTrue(flagged.metric_eligible)
            self.assertEqual(flagged.error, 'unsupported_final_evidence_quote')
            self.assertEqual(flagged.quote_quality_status, 'flagged')
            self.assertEqual((new/'nt_patient_llm_outputs.jsonl').read_bytes(), raw)
            with self.assertRaisesRegex(ValueError, 'original source notes'):
                evaluate(gold, new/'nt_patient_llm_outputs.jsonl', root/'bad', 'combined', 'strict')
            with self.assertRaisesRegex(ValueError, 'original source notes'):
                evaluate(gold, new/'nt_patient_llm_outputs.jsonl', root/'bad_primary', 'combined', 'classification')

    def test_paired_metrics_and_handoff_use_same_policy_for_both_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, gold, old, new = self.fixture(root)
            with patch.object(comparison, 'INPUT_DIR', source), patch.object(comparison, 'GOLD', gold), contextlib.redirect_stdout(io.StringIO()):
                primary = comparison.compare(new, root/'primary', label_scheme='combined', baseline_dir=old, evaluation_policy='classification')
                strict = comparison.compare(new, root/'strict', label_scheme='combined', baseline_dir=old, evaluation_policy='strict')
            self.assertEqual(primary['evaluations']['prior_v2']['metric_denominator'], 9)
            self.assertEqual(strict['evaluations']['prior_v2']['metric_denominator'], 8)
            self.assertEqual(primary['paired_comparisons']['prior_v2_vs_B']['all']['patients'], 2)
            self.assertEqual(strict['paired_comparisons']['prior_v2_vs_B']['all']['patients'], 1)
            handoff = pd.read_csv(root/'primary/B_handoff/model_results.csv', dtype={'BDSPPatientID': str}).set_index('BDSPPatientID')
            self.assertTrue(handoff.loc['102', 'metric_eligible'])
            self.assertEqual(handoff.loc['102', 'recorded_run_error'], 'unsupported_final_evidence_quote')
            self.assertIn('nonverbatim_or_unsupported_quote', handoff.loc['102', 'review_flags'])
            decisions = pd.read_csv(root/'primary/B_handoff/review_queue.csv', keep_default_na=False)
            self.assertTrue((decisions.confirmed == '').all())
            strict_handoff = pd.read_csv(root/'strict/B_handoff/model_results.csv', dtype={'BDSPPatientID': str}).set_index('BDSPPatientID')
            self.assertFalse(strict_handoff.loc['102', 'metric_eligible'])
