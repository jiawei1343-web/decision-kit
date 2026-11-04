import unittest
from semantic import SemanticClassifier

class SemanticContractTests(unittest.TestCase):
    def test_overlong_rejected_before_encoding(self):
        class Tokenizer:
            def encode(self,text): return list(range(20))
        class Model:
            tokenizer=Tokenizer(); max_seq_length=10
            def encode(self,*args,**kwargs): raise AssertionError('must not encode truncated input')
        classifier=SemanticClassifier.__new__(SemanticClassifier); classifier.model=Model()
        self.assertEqual(classifier.classify('text',{'a':'one','b':'two'})['reason'],'input_exceeds_model_context')
    def test_invalid_margin(self):
        classifier=SemanticClassifier.__new__(SemanticClassifier)
        with self.assertRaises(ValueError): classifier.classify('text',{'a':'one','b':'two'},float('nan'))

if __name__=='__main__': unittest.main()
