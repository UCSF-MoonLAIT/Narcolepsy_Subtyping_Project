import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_reference_comparison as controller


class ResumeGateTests(unittest.TestCase):
    def test_resume_checks_original_early_cases_without_spending_new_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'B';run.mkdir()
            rows=[{'BDSPPatientID':str(i),'error':None,'input_coverage':1,
                   'planned_chunks':1} for i in range(3)]
            rows.append({'BDSPPatientID':'later','error':'retained failure',
                         'input_coverage':0,'planned_chunks':1})
            calls=[{'patient_id':r['BDSPPatientID'],'status':'valid' if not r['error'] else 'failed',
                    'elapsed_sec':1,'token_accounting_delta':-2} for r in rows]
            for name,data in [('nt_patient_llm_outputs.jsonl',rows),('calls.jsonl',calls)]:
                (run/name).write_text(''.join(json.dumps(r)+'\n' for r in data))
            gate=controller.technical_gate(run,3,first_only=True)
            self.assertEqual(gate['patients'],3)
            with self.assertRaisesRegex(RuntimeError,'invalid output'):
                controller.technical_gate(run,3)
            pilot=root/'pilot'
            def invoke(path,strategy,*args,**kwargs):
                if path==run:
                    self.assertNotIn('limit',kwargs)
                    raise RuntimeError('reached full resume')
            real_gate=controller.technical_gate
            def gate_for(path,*args,**kwargs):
                return {'patients':3} if path==pilot else real_gate(path,*args,**kwargs)
            with patch.object(controller,'BASE',root),patch.object(controller,'STATUS',root/'status.json'),patch.object(controller,'ROOT',root),patch.object(controller,'PILOT',pilot),patch.object(controller,'FULL_B',run),patch.object(controller,'wait_for_unlock'),patch.object(controller,'invoke',side_effect=invoke) as invoked,patch.object(controller,'technical_gate',side_effect=gate_for),patch.object(controller,'snapshot'):
                with self.assertRaisesRegex(RuntimeError,'reached full resume'):
                    controller.main()
                self.assertEqual(invoked.call_count,2)
