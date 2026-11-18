import json
from pathlib import Path
import tempfile
import unittest
from recover_checkpoint import recover
from submission_tools import export_package
from test_submission import valid
import pandas as pd


class RecoveryTests(unittest.TestCase):
    def test_crash_tail_recovery_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'raw.jsonl';target=root/'recovered.jsonl'
            original=b'{"id":1}\n{"id":';source.write_bytes(original)
            recover(source,target)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(target.read_bytes(),b'{"id":1}\n')
            source.write_bytes(b'broken\n{"id":1}\n')
            with self.assertRaisesRegex(ValueError,'incomplete final write'):recover(source,root/'refused.jsonl')

    def test_partial_dates_preserved_without_day_invention(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.parquet';pred=root/'pred.jsonl'
            pd.DataFrame([{'BDSPPatientID':'001','index_date':'20260102',
                           'first_nt_date':'2020','raw_notetxt':'synthetic note'}]).to_parquet(source)
            value=valid();value['diagnosis_anchor_date']='2020'
            pred.write_text(json.dumps({'BDSPPatientID':'001','index_date':'2026-01-02','llm_output':value})+'\n')
            export_package(source,pred,root/'package')
            row=pd.read_csv(root/'package/model_results.csv',dtype=str,keep_default_na=False).iloc[0]
            self.assertEqual(row['index_date'],'20260102')
            self.assertEqual(row['first_nt_date'],'2020')
            self.assertEqual(row['model_diagnosis_date_original'],'2020')
            self.assertEqual(row['model_diagnosis_date_precision'],'year')
            self.assertEqual(row['model_diagnosis_anchor_date'],'')


class CoverageExportTests(unittest.TestCase):
    def test_complete_coverage_does_not_inherit_old_clipping_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.parquet';pred=root/'pred.jsonl'
            pd.DataFrame([{'BDSPPatientID':'001','index_date':'20260102',
                           'raw_notetxt':'synthetic note '+('x '*5000)}]).to_parquet(source)
            record={'BDSPPatientID':'001','index_date':'2026-01-02','llm_output':valid(),
                    'input_coverage':1.0,'planned_chunks':2}
            pred.write_text(json.dumps(record)+'\n')
            export_package(source,pred,root/'good')
            flags=pd.read_csv(root/'good/model_results.csv').iloc[0].review_flags
            self.assertNotIn('historical_input_selection',flags)
            self.assertIn('chunk_reconciliation',flags)
            record['llm_output']=['invalid output type'];pred.write_text(json.dumps(record)+'\n')
            counts=export_package(source,pred,root/'bad')
            self.assertEqual(counts['failed'],1)
