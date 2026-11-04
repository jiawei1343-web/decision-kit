import unittest
from decisionkit import Engine, train, evaluate

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.model=train([{'text':'refund payment money','label':'billing'},{'text':'crash broken error','label':'technical'}])
        self.engine=Engine(self.model, ':memory:')
    def tearDown(self): self.engine.close()
    def test_classification(self):
        r=self.engine.decide('refund payment')
        self.assertEqual(r['result']['label'],'billing')
        self.assertEqual(r['status'],'completed')
        self.assertFalse(r['result']['calibrated'])
    def test_unknown_abstains(self): self.assertEqual(self.engine.decide('天气晴朗')['status'],'needs_review')
    def test_cache_isolation(self):
        self.engine.decide('refund')
        self.assertEqual(self.engine.decide('refund')['route'],'exact_cache')
        self.assertEqual(self.engine.decide('refund',project='other')['route'],'local_classifier')
    def test_threshold_changes_invalidate(self):
        self.engine.decide('refund')
        self.assertEqual(self.engine.decide('refund',min_margin=1)['status'],'needs_review')
    def test_invalid_input(self):
        for text in ('',None,'x'*100001):
            with self.assertRaises(ValueError): self.engine.decide(text)
        with self.assertRaises(ValueError): self.engine.decide('refund',min_margin=float('nan'))
    def test_training_requires_classes(self):
        with self.assertRaises(ValueError): train([{'text':'hello','label':'one'}])
    def test_evaluation(self):
        report=evaluate(self.model,[{'text':'refund payment','label':'billing'},{'text':'unseen','label':'technical'}])
        self.assertEqual(report['accepted'],1)
        self.assertEqual(report['accepted_accuracy'],1)

if __name__=='__main__': unittest.main()
