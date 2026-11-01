import unittest
from benchmark.file_performance import benchmark_files, validate_report
from copy import deepcopy


class FileBenchmarkTests(unittest.TestCase):
    def test_saved_report_validation(self):
        report = benchmark_files(sizes=(0,), repetitions=1)
        self.assertIs(validate_report(report), report)
        for field, value in (("encrypt_median_ms", float("nan")), ("package_bytes", -1),
                             ("overhead_bytes", 0), ("algorithm", "unknown")):
            invalid = deepcopy(report)
            invalid["measurements"][0][field] = value
            with self.assertRaises(ValueError):
                validate_report(invalid)
        with self.assertRaises(KeyError):
            validate_report({})

    def test_measured_package_overhead_and_timings(self):
        rows = benchmark_files(sizes=(0, 1024), repetitions=2)["measurements"]
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row["package_bytes"] - row["plaintext_bytes"], row["overhead_bytes"])
            self.assertGreater(row["overhead_bytes"], 16)
            self.assertGreaterEqual(row["encrypt_median_ms"], 0)
            self.assertGreaterEqual(row["decrypt_median_ms"], 0)
        for algorithm in ("ML-KEM-768", "X25519"):
            self.assertEqual(len({row["overhead_bytes"] for row in rows if row["algorithm"] == algorithm}), 1)

    def test_invalid_workloads(self):
        for kwargs in ({"sizes":(21 * 1024 ** 2,)}, {"sizes":(-1,)}, {"repetitions":31}, {"repetitions":True}):
            with self.assertRaises(ValueError):
                benchmark_files(**kwargs)
