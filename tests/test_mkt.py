import unittest
import math

from src.mkt import calculate_mkt, R


class TestMKT(unittest.TestCase):

    def test_empty_returns_zero(self):
        self.assertEqual(calculate_mkt([]), 0.0)

    def test_single_temperature(self):
        result = calculate_mkt([25.0])
        self.assertAlmostEqual(result, 25.0, places=2)

    def test_constant_temperature(self):
        result = calculate_mkt([25.0, 25.0, 25.0, 25.0])
        self.assertAlmostEqual(result, 25.0, places=2)

    def test_two_temperatures(self):
        result = calculate_mkt([20.0, 30.0])
        self.assertGreater(result, 20.0)
        self.assertLess(result, 30.0)

    def test_mkt_above_arithmetic_mean(self):
        temps = [15.0, 35.0]
        result = calculate_mkt(temps)
        arithmetic_mean = sum(temps) / len(temps)
        self.assertGreater(result, arithmetic_mean)

    def test_custom_activation_energy(self):
        temps = [20.0, 30.0]
        result_default = calculate_mkt(temps)
        result_custom = calculate_mkt(temps, activation_energy=100.0)
        self.assertNotEqual(result_default, result_custom)

    def test_negative_temperatures(self):
        result = calculate_mkt([-18.0, -20.0, -19.0])
        self.assertGreater(result, -20.0)
        self.assertLess(result, -18.0)

    def test_manual_calculation(self):
        temps = [25.0, 30.0]
        dh = 83.144 * 1000
        n = len(temps)
        total = sum(math.exp(-dh / (R * (t + 273.15))) for t in temps)
        expected_k = dh / (R * (-math.log(total / n)))
        expected = expected_k - 273.15
        result = calculate_mkt(temps)
        self.assertAlmostEqual(result, expected, places=5)

    def test_many_temperatures(self):
        temps = [25.0 + i * 0.5 for i in range(20)]
        result = calculate_mkt(temps)
        self.assertGreater(result, 25.0)
        self.assertLess(result, 35.0)


if __name__ == '__main__':
    unittest.main()
