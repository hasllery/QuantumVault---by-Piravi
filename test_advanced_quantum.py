"""Unit and integration tests for advanced quantum enhancements:
1. Shor Discrete Logarithm over Edwards Elliptic Curve (ECDLP targeting X25519)
2. Hardware-calibrated noise engine (T1, T2, readout error)
3. Scalable Draper QFT quantum adder and modular arithmetic
"""
import unittest

from qiskit import QuantumCircuit
from quantum_lab.ecdlp import (
    CURVE_P, CURVE_D, GROUP_ORDER, GENERATOR, NEUTRAL_ELEMENT,
    edwards_add, edwards_scalar_mul, solve_ecdlp, build_ecdlp_circuit
)
from quantum_lab.calibrated_noise import (
    build_calibrated_backend, extract_calibration_report,
    get_hardware_noise_model, run_circuit_with_calibrated_noise
)
from quantum_lab.draper_adder import (
    run_draper_addition, build_draper_adder_gate, build_draper_modular_multiplier_gate
)


class AdvancedQuantumTests(unittest.TestCase):
    def test_edwards_group_law(self):
        # Neutral element addition
        self.assertEqual(edwards_add(GENERATOR, NEUTRAL_ELEMENT), GENERATOR)
        self.assertEqual(edwards_add(NEUTRAL_ELEMENT, GENERATOR), GENERATOR)

        # Cyclic group order verification
        cur = GENERATOR
        for _ in range(GROUP_ORDER - 1):
            self.assertNotEqual(cur, NEUTRAL_ELEMENT)
            cur = edwards_add(cur, GENERATOR)
        self.assertEqual(cur, NEUTRAL_ELEMENT)
        self.assertEqual(edwards_scalar_mul(GROUP_ORDER), NEUTRAL_ELEMENT)

    def test_shor_ecdlp_attack(self):
        # Test solving for discrete logarithms d = 1, 3, 5, 7
        for secret_d in [1, 3, 5, 7]:
            result = solve_ecdlp(private_key_d=secret_d, shots=64, seed=42)
            analysis = result["analysis"]
            self.assertEqual(analysis["status"], "success")
            self.assertEqual(analysis["recovered_private_key_d"], secret_d)
            self.assertGreater(analysis["valid_shots"], 0)

    def test_ecdlp_circuit_structure(self):
        circuit = build_ecdlp_circuit(private_key_d=3)
        self.assertEqual(circuit.num_qubits, 9)
        self.assertGreater(circuit.depth(), 0)

    def test_hardware_calibrated_noise(self):
        backend = build_calibrated_backend(num_qubits=8, seed=42)
        report = extract_calibration_report(backend)
        self.assertEqual(report["num_qubits"], 8)
        self.assertEqual(len(report["qubit_properties"]), 8)
        for q in report["qubit_properties"]:
            self.assertGreater(q["T1_us"], 0.0)
            self.assertGreater(q["T2_us"], 0.0)

        # Run circuit under calibrated noise
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()
        res = run_circuit_with_calibrated_noise(qc, backend=backend, shots=200, seed=42)
        self.assertEqual(res["shots"], 200)
        self.assertIn("counts", res)
        self.assertGreater(len(res["counts"]), 0)

    def test_draper_adder_arithmetic(self):
        # Test addition of various pairs modulo 16
        test_pairs = [(0, 0), (3, 4), (5, 7), (10, 5), (15, 1), (14, 3)]
        for a, b in test_pairs:
            res = run_draper_addition(num_qubits=4, a=a, b=b, shots=1, seed=42)
            self.assertTrue(res["success"])
            self.assertEqual(res["measured_sum"], (a + b) % 16)

    def test_draper_gates(self):
        gate = build_draper_adder_gate(num_qubits=4, constant=3)
        self.assertEqual(gate.num_qubits, 4)
        multiplier_gate = build_draper_modular_multiplier_gate(base=2, modulus=15, num_qubits=4)
        self.assertEqual(multiplier_gate.num_qubits, 4)


if __name__ == "__main__":
    unittest.main()

