import unittest
from decisionkit import tokens, train, Engine

class LanguageTests(unittest.TestCase):
    def test_scripts_preserved(self):
        for text in ['退款','返金','환불','remboursement','Rückerstattung','reembolso','возврат','استرداد','वापसी','คืนเงิน','hoàn tiền']:
            self.assertTrue(tokens(text),text)
    def test_normalization(self):
        self.assertEqual(tokens('ＣＡＦÉ'),tokens('cafe\u0301'))
    def test_local_learning(self):
        for a,b in [('возврат денег','ошибка программы'),('استرداد المال','خطأ البرنامج'),('환불 요청','프로그램 오류')]:
            engine=Engine(train([{'text':a,'label':'refund'},{'text':b,'label':'bug'}]),':memory:')
            try: self.assertEqual(engine.decide(a)['result']['label'],'refund')
            finally: engine.close()

if __name__=='__main__': unittest.main()
