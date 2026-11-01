"""Independent arithmetic/circuit checks and statistical experiment guards."""
import unittest
from unittest.mock import patch

import numpy as np
from qiskit.quantum_info import Operator
from qiskit_aer.noise import NoiseModel

from quantum_lab.period_finding import modular_multiplication_gate, build_period_finding_circuit
from quantum_lab.experiments import (
    rotation_multiplier, build_rotation_circuit, run_trial, noise_model, noise_coverage,
    wilson, summarize, run_study, classical_factors,
)
from quantum_lab.analysis import analyze_counts


class ExperimentTests(unittest.TestCase):
    def test_full_multiplier_and_control_equivalence(self):
        for multiplier in (1, 2, 4, 8):
            matrix = Operator(modular_multiplication_gate(multiplier).control(1)).data
            rotation = Operator(rotation_multiplier(multiplier).control(1)).data
            np.testing.assert_allclose(matrix, rotation, atol=1e-10)

    def test_complete_circuit_equivalence(self):
        for base in (2, 4, 8):
            matrix = build_period_finding_circuit(base=base, counting_qubits=3).remove_final_measurements(inplace=False)
            rotation = build_rotation_circuit(base=base, counting_qubits=3).remove_final_measurements(inplace=False)
            self.assertTrue(Operator(matrix).equiv(Operator(rotation)))

    def test_real_ideal_and_noisy_execution(self):
        ideal = run_trial("rotation", 128, 42, 0.0)
        noisy = run_trial("rotation", 128, 42, 0.01)
        self.assertTrue(ideal["toy_recovered"])
        self.assertEqual(sum(noisy["counts"].values()), 128)
        self.assertTrue(noisy["noise_coverage"]["verified"])
        self.assertGreater(noisy["noise_coverage"]["affected_gate_count"], 0)
        self.assertNotEqual(ideal["counts"], noisy["counts"])
        self.assertLess(noisy["usable_factor_shots"], ideal["usable_factor_shots"])

    def test_noise_must_cover_executed_basis(self):
        with self.assertRaises(ValueError):
            noise_coverage({"cx": 5, "sx": 1}, NoiseModel(), 0.01)
        with self.assertRaises(ValueError):
            noise_coverage({"unitary": 1}, noise_model(0.01), 0.01)
        self.assertTrue(noise_coverage({"cx": 2}, noise_model(0), 0)["verified"])

    def test_wilson_and_failure_denominators(self):
        interval = wilson(5, 10)
        self.assertAlmostEqual(interval["wilson_95_low"], 0.23659309)
        self.assertAlmostEqual(interval["wilson_95_high"], 0.76340691)
        rows = [{"implementation": "rotation", "noise_rate": 0, "shots": 1, "status": "failed"} for _ in range(3)]
        summary = summarize(rows)[0]
        self.assertEqual(summary["planned_trials"], 3)
        self.assertEqual(summary["failed_trials"], 3)
        self.assertEqual(summary["toy_recovered"]["proportion"], 0)

    def test_runner_keeps_failed_trials_and_bounds(self):
        with patch("quantum_lab.experiments.run_trial", side_effect=RuntimeError("synthetic failure")):
            report = run_study()
        self.assertEqual(len(report["trials"]), 16)
        self.assertEqual(sum(row["failed_trials"] for row in report["summary"]), 16)
        self.assertEqual(classical_factors(), [3, 5])
        for kwargs in ({"implementation":"bad", "shots":1,"seed":1,"rate":0},
                       {"implementation":"matrix", "shots":3000,"seed":1,"rate":0}):
            with self.assertRaises(ValueError):
                run_trial(**kwargs)

    def test_nonminimal_noisy_candidate_is_not_a_recovery_fallback(self):
        analysis = analyze_counts({"0100": 10}, base=4, counting_qubits=4)
        self.assertIsNone(analysis["estimated_period"])
        self.assertEqual(analysis["factors"], [])
        self.assertEqual(analyze_counts({"1000": 10}, base=4, counting_qubits=4)["estimated_period"], 2)
        self.assertIsNone(analyze_counts({"0000": 10}, counting_qubits=4)["estimated_period"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
