import unittest
from bot.strategy.svm_strategy import sma, build_sma_features


class TestStrategy(unittest.TestCase):
    def test_sma(self):
        arr = [1,2,3,4,5]
        self.assertEqual(sma(arr, 3), [2.0,3.0,4.0])

    def test_build_features(self):
        closes = [100,101,102,103,104,105,106,107,108,109,110,111,112,113,114]
        x,y = build_sma_features(closes)
        self.assertTrue(x.shape[0] > 0)
        self.assertEqual(x.shape[1], 3)
        self.assertEqual(y.shape[0], x.shape[0])


if __name__ == '__main__':
    unittest.main()
