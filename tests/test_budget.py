import unittest
from budget import Budget

class BudgetTests(unittest.TestCase):
    def setUp(self): self.b=Budget(':memory:')
    def tearDown(self): self.b.close()
    def test_reservation_and_settlement(self):
        token=self.b.reserve('a',.8,1)
        self.assertIsNone(self.b.reserve('a',.3,1))
        self.b.settle(token,.2)
        self.assertIsNotNone(self.b.reserve('a',.8,1))
    def test_unknown_kept(self):
        self.b.reserve('a',1,1)
        self.assertEqual(self.b.summary('a'),{'reserved':1})
        self.assertIsNotNone(self.b.reserve('b',1,1))
    def test_settle_only_once(self):
        token=self.b.reserve('a',1,1); self.b.settle(token,.5)
        with self.assertRaises(ValueError): self.b.settle(token,0)
    def test_invalid_cost(self):
        for value in [-1,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError): self.b.reserve('a',value,1)

if __name__=='__main__': unittest.main()
