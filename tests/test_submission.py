import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import narcolepsy_stanford as runner
from NT_LLM.validation import validate_output, evidence_flags, EVIDENCE_FIELDS
from submission_tools import export_package


def valid(pid='001'):
    return {'patient_id': pid, 'index_date': '2026-01-02', 'final_label': 'NT2',
            'confidence': 'high', 'diagnosis_anchor_date': None,
            'key_evidence': {k: 'NotMentioned' for k in EVIDENCE_FIELDS},
            'key_evidence_quotes': ['synthetic note'], 'reasoning': 'Synthetic case.'}


class IntegrityTests(unittest.TestCase):
    def test_validation_and_date_precision(self):
        value=valid()
        self.assertEqual(validate_output(value,'001','2026-01-02','synthetic note'),[])
        value['diagnosis_anchor_date']='2020'
        self.assertIn('invalid_diagnosis_date',validate_output(value,'001','2026-01-02','synthetic note'))
        value['patient_id']='other'
        self.assertIn('patient_id_mismatch',validate_output(value,'001','2026-01-02','synthetic note'))
        self.assertIn('empty_or_invalid_json',validate_output(runner.safe_parse_json(''),'001','2026-01-02',''))
        self.assertEqual(runner.safe_parse_json('```json\n{"a":1}\n```'),{'a':1})
        self.assertIn('nonverbatim_or_unsupported_quote',evidence_flags(value,'different note'))

    def test_terminal_failure_retry_retention_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); source=p/'input.parquet'
            pd.DataFrame([{'BDSPPatientID':'001','index_date':'20260102','raw_notetxt':'synthetic note'}]).to_parquet(source)
            with patch.object(runner,'call_ollama',return_value='') as call:
                runner.process_input_file(source,p/'run')
                self.assertEqual(call.call_count,2)
                runner.process_input_file(source,p/'run')
                self.assertEqual(call.call_count,2)
            rows=[json.loads(l) for l in (p/'run/nt_patient_llm_outputs.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['error'],'empty_or_invalid_json')
            self.assertEqual(len((p/'run/attempts.jsonl').read_text().splitlines()),2)
            # Malformed crash tail fails explicitly instead of silently skipping a patient.
            with (p/'run/nt_patient_llm_outputs.jsonl').open('a') as handle: handle.write('{')
            with self.assertRaisesRegex(ValueError,'invalid JSON'):
                runner.process_input_file(source,p/'run')

    def test_export_reconciliation_and_no_invented_review(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); source=p/'input.parquet'; predictions=p/'predictions.jsonl'
            pd.DataFrame([{'BDSPPatientID':pid,'index_date':'20260102','raw_notetxt':'synthetic note'} for pid in ['001','002']]).to_parquet(source)
            row={'BDSPPatientID':'001','index_date':'2026-01-02','llm_output':valid(),'error':None}
            predictions.write_text(json.dumps(row)+'\n')
            counts=export_package(source,predictions,p/'package')
            self.assertEqual((counts['expected'],counts['processed'],counts['valid'],counts['missing']),(2,1,1,1))
            review=pd.read_csv(p/'package/review_queue.csv',dtype=str,keep_default_na=False)
            self.assertEqual(set(review.review_status),{'unreviewed'})
            self.assertTrue((review.confirmed=='').all() and (review.analysis_inclusion=='').all())
            self.assertEqual(set(review.BDSPPatientID),{'001','002'})
            with self.assertRaisesRegex(ValueError,'must be new'): export_package(source,predictions,p/'package')
            predictions.write_text((json.dumps(row)+'\n')*2)
            with self.assertRaisesRegex(ValueError,'duplicate'): export_package(source,predictions,p/'dup')
            row['BDSPPatientID']='999';predictions.write_text(json.dumps(row)+'\n')
            with self.assertRaisesRegex(ValueError,'outside'):export_package(source,predictions,p/'unmatched')


if __name__=='__main__': unittest.main()
