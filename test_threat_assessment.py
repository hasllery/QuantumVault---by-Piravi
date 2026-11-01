"""Measured evidence must drive the toy recovery; no success fallback."""
from copy import deepcopy
import unittest

from quantum_lab.period_finding import run_period_finding
from quantum_lab.threat_assessment import build_threat_assessment, recover_toy_rsa_value


class ThreatAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.experiment = run_period_finding(shots=128, seed=42)

    def test_measured_factors_drive_toy_recovery(self):
        assessment = build_threat_assessment(self.experiment)
        self.assertEqual(assessment["analysis"]["factors"], [3, 5])
        self.assertEqual(assessment["toy_rsa"]["wrapped_value"], 13)
        self.assertEqual(assessment["toy_rsa"]["recovered_value"], 7)
        self.assertTrue(assessment["toy_rsa"]["recovery_verified"])
        self.assertTrue(assessment["policy"]["can_apply"])
        self.assertEqual(assessment["policy"]["recommended_algorithm"], "ML-KEM-768")

    def test_no_factors_means_no_toy_recovery(self):
        for factors in ([], [1, 15], [3, 3], [5, 5], [3, 7]):
            with self.subTest(factors=factors):
                recovery = recover_toy_rsa_value(factors)
                self.assertFalse(recovery["recovery_verified"])
                self.assertIsNone(recovery["recovered_value"])

    def test_forged_analysis_is_ignored(self):
        experiment = deepcopy(self.experiment)
        experiment["counts"] = {"00000000": 128}
        # Keep the original precomputed success. Only counts should matter.
        assessment = build_threat_assessment(experiment)
        self.assertEqual(assessment["evidence_status"], "inconclusive")
        self.assertFalse(assessment["policy"]["can_apply"])
        self.assertIsNone(assessment["toy_rsa"]["recovered_value"])
        self.assertEqual(assessment["policy"]["recommended_algorithm"], "ML-KEM-768")

    def test_valid_period_can_be_inconclusive(self):
        assessment = build_threat_assessment(run_period_finding(base=14, shots=128, seed=42))
        self.assertEqual(assessment["analysis"]["estimated_period"], 2)
        self.assertFalse(assessment["policy"]["can_apply"])
        self.assertEqual(assessment["analysis"]["factors"], [])

    def test_invalid_counts_fail_closed(self):
        for counts in ({"00000000": 127}, {"invalid": 128}, {"00000000": -1}):
            experiment = deepcopy(self.experiment)
            experiment["counts"] = counts
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                build_threat_assessment(experiment)

    def test_evidence_identity_and_no_real_secret_fields(self):
        assessment = build_threat_assessment(self.experiment)
        self.assertEqual(assessment["assessment_id"], build_threat_assessment(self.experiment)["assessment_id"])
        changed = deepcopy(self.experiment)
        changed["counts"] = {"00000000": 128}
        self.assertNotEqual(assessment["assessment_id"], build_threat_assessment(changed)["assessment_id"])
        self.assertNotIn("private_exponent", assessment["toy_rsa"])
        self.assertNotIn("private_key", str(assessment))
        self.assertNotIn("shared_secret", str(assessment))


if __name__ == "__main__":
    unittest.main(verbosity=2)
