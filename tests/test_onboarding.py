import tempfile
import unittest
from pathlib import Path
from setup_wizard import create_profile
from evals.calibrate import analyze
from evals.compare import summarize

class OnboardingTests(unittest.TestCase):
    def test_profile_runs_offline(self):
        from runtime import Runtime
        import json
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'profile'; create_profile(path)
            runtime=Runtime(path/'config.json')
            try: self.assertEqual(runtime.decide(json.loads((path/'request.json').read_text(encoding='utf-8')))['value'],'billing')
            finally: runtime.close()
            with self.assertRaises(FileExistsError): create_profile(path)
    def test_small_calibration_is_not_certainty(self):
        result=analyze([{'correct':True,'margin':.05,'language':'zh'}])['bins'][0]
        self.assertFalse(result['sufficient_for_initial_analysis'])
        self.assertLess(result['wilson_95'][0],.5)
    def test_cost_per_correct_includes_failed_calls(self):
        result=summarize([{'status':'completed','correct':True,'cost':{'estimated_usd':1,'unknown_charge':False}},{'status':'needs_review','correct':False,'cost':{'estimated_usd':2,'unknown_charge':False}}])
        self.assertEqual(result['estimated_cost_per_correct'],3)
