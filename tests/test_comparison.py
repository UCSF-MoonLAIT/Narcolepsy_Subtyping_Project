import unittest
import pandas as pd
from compare_coverage import paired_comparison


class PairedComparisonTests(unittest.TestCase):
    def test_same_valid_population_excludes_failure_and_counts_regressions(self):
        table=pd.DataFrame([
            {'BDSPPatientID':'a','final_label_gold':'NT1','A_label':'Uncertain','B_label':'NT1'},
            {'BDSPPatientID':'b','final_label_gold':'IH','A_label':'IH','B_label':'NT2'},
            {'BDSPPatientID':'failed','final_label_gold':'NT2','A_label':'NT2','B_label':'NT2'},
        ])
        result=paired_comparison(table,'A','B',{'A':{'a','b','failed'},'B':{'a','b'}})
        self.assertEqual(result['patients'],2)
        self.assertEqual(result['corrected'],1)
        self.assertEqual(result['regressed'],1)
        self.assertEqual(result['changed'],2)
        self.assertEqual(result['metrics']['B']['accuracy'],0.5)
        self.assertEqual(result['metrics']['B']['per_class']['NT2']['support'],0)
        self.assertAlmostEqual(result['metrics']['B']['macro_f1'],0.2)

    def test_empty_overlap_is_explicit(self):
        table=pd.DataFrame(columns=['BDSPPatientID','final_label_gold','A_label','B_label'])
        self.assertEqual(paired_comparison(table,'A','B',{'A':set(),'B':set()})['patients'],0)
