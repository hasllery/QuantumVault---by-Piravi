"""Verify arithmetic, Fourier transform, real Aer measurements and failures."""
import unittest

import numpy as np
from qiskit.quantum_info import Operator

from quantum_lab.analysis import analyze_counts, extract_factors
from quantum_lab.period_finding import (
    modular_multiplication_gate, inverse_qft, build_period_finding_circuit,
    run_period_finding,
)


class QuantumTests(unittest.TestCase):
    def test_all_modular_multipliers_and_control_states(self):
        for multiplier in (1, 2, 4, 7, 8, 11, 13, 14):
            matrix = Operator(modular_multiplication_gate(multiplier).control(1)).data
            for value in range(16):
                for control in (0, 1):
                    target = multiplier * value % 15 if control and value < 15 else value
                    expected = np.zeros(32)
                    expected[2 * target + control] = 1
                    with self.subTest(multiplier=multiplier, value=value, control=control):
                        np.testing.assert_allclose(matrix[:, 2 * value + control], expected, atol=1e-10)

    def test_inverse_qft_against_fourier_matrix(self):
        for qubits in (2, 3, 4):
            dimension = 2 ** qubits
            indices = np.arange(dimension)
            expected = np.exp(-2j * np.pi * np.outer(indices, indices) / dimension) / np.sqrt(dimension)
            np.testing.assert_allclose(Operator(inverse_qft(qubits)).data, expected, atol=1e-10)

    def test_aer_recovers_order_and_factors(self):
        result = run_period_finding(shots=512, seed=42)
        self.assertEqual(sum(result["counts"].values()), 512)
        self.assertEqual(set(result["counts"]), {"00000000", "01000000", "10000000", "11000000"})
        self.assertEqual(result["analysis"]["estimated_period"], 4)
        self.assertEqual(result["analysis"]["factors"], [3, 5])
        self.assertEqual(result["analysis"]["status"], "success")

    def test_another_base_has_different_order(self):
        result = run_period_finding(base=4, counting_qubits=4, shots=128, seed=7)
        self.assertEqual(set(result["counts"]), {"0000", "1000"})
        self.assertEqual(result["analysis"]["estimated_period"], 2)
        self.assertEqual(result["analysis"]["factors"], [3, 5])

    def test_aer_valid_order_can_fail_to_factor(self):
        result = run_period_finding(base=14, counting_qubits=4, shots=128, seed=7)
        self.assertEqual(result["analysis"]["estimated_period"], 2)
        self.assertEqual(result["analysis"]["factors"], [])
        self.assertEqual(result["analysis"]["status"], "inconclusive")

    def test_inconclusive_counts_have_no_fallback(self):
        for counts in ({}, {"00000000": 10}, {"10000000": 10}, {"00010000": 10}):
            result = analyze_counts(counts)
            self.assertEqual(result["status"], "inconclusive")
            self.assertIsNone(result["estimated_period"])
            self.assertEqual(result["factors"], [])

    def test_factor_validation(self):
        self.assertEqual(extract_factors(2, 15, 4), [3, 5])
        for period in (None, 0, -4, 2, 3, 8):
            self.assertEqual(extract_factors(2, 15, period), [])

    def test_invalid_input(self):
        for kwargs in ({"modulus": 21}, {"base": 3}, {"base": 1}, {"counting_qubits": 9}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build_period_finding_circuit(**kwargs)
        for kwargs in ({"shots": 0}, {"shots": True}, {"seed": -1}):
            with self.assertRaises(ValueError):
                run_period_finding(**kwargs)
        for counts in ({"01": 1}, {"0000000x": 1}, {"00000000": -1}):
            with self.assertRaises(ValueError):
                analyze_counts(counts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
