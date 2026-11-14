import unittest
from fractions import Fraction
from iskra_backflow import recheck, forward, backward

class BackflowTests(unittest.TestCase):
    def test_neutral_case(self):
        result = recheck(7, 3, 5)
        self.assertEqual(result['forward'], '50')
        self.assertEqual(result['backflow'], '7')
        self.assertTrue(result['roundtrip_exact'])
        self.assertTrue(result['forward_consistent'])

    def test_negative_and_fractional(self):
        for value in (-11, 0, Fraction(1, 3)):
            for multiplier in (-3, Fraction(2, 7), 5):
                with self.subTest(value=value, multiplier=multiplier):
                    self.assertTrue(recheck(value, Fraction(4, 9), multiplier)['roundtrip_exact'])

    def test_zero_multiplier_rejected(self):
        with self.assertRaises(ValueError):
            forward(2, 3, 0)
        with self.assertRaises(ValueError):
            backward(2, 3, 0)

if __name__ == '__main__':
    unittest.main()
