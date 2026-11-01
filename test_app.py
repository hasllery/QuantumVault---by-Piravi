"""Widget-level integration tests, using real crypto, Aer and download payloads.

AppTest simulates Streamlit's frontend. The test-only storage factory exposes
the bytes registered by download widgets; it does not replace application or
cryptographic logic. No real keys or uploaded content are written to disk.
"""
import base64
import json
from hashlib import sha256
from copy import deepcopy
from io import StringIO
import logging
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
from streamlit.testing.v1 import AppTest

from components.data import load_benchmark
from crypto_engine.key_management import import_private_key

APP = str(Path(__file__).resolve().with_name("app.py"))
TEST_PASSPHRASE = "synthetic-test-passphrase"


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.storage = None

        def storage_factory(*args, **kwargs):
            self.storage = MemoryMediaFileStorage(*args, **kwargs)
            return self.storage

        self.storage_patch = patch("streamlit.testing.v1.app_test.MemoryMediaFileStorage", storage_factory)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.logs = StringIO()
        handler = logging.StreamHandler(self.logs)
        logging.getLogger().addHandler(handler)
        self.addCleanup(logging.getLogger().removeHandler, handler)

    def app(self, page="Secure Vault"):
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio("navigation").set_value(page).run()
        self.assertFalse(at.exception)
        return at

    def download(self, at, key):
        widget = at.download_button(key)
        self.assertTrue(widget.proto.url)
        filename = widget.proto.url.rsplit("/", 1)[-1]
        return self.storage.get_file(filename).content

    def keypair(self, at, algorithm):
        at.radio("vault_algorithm").set_value(algorithm).run()
        at.button("generate_keys").click().run()
        at.text_input("export_password").set_value(TEST_PASSPHRASE)
        at.text_input("export_confirmation").set_value(TEST_PASSPHRASE)
        at.button("prepare_backup").click().run()
        return self.download(at, "download_public"), self.download(at, "download_private")

    def encrypt(self, at, public, data):
        at.radio("vault_action").set_value("Encrypt").run()
        at.file_uploader("key_upload_Encrypt_0").set_value(("recipient.public.key", public, "application/octet-stream"))
        at.file_uploader("file_upload_Encrypt_0").set_value(("sample.bin", data, "application/octet-stream")).run()
        at.text_input("expected_fingerprint").set_value(sha256(public).hexdigest()).run()
        at.button("process_file").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        return self.download(at, "download_result")

    def upload_package(self, at, private, package):
        at.radio("vault_action").set_value("Decrypt").run()
        at.text_input("import_password").set_value(TEST_PASSPHRASE)
        at.file_uploader("key_upload_Decrypt_0").set_value(("recipient.private.key", private, "application/octet-stream"))
        at.file_uploader("file_upload_Decrypt_0").set_value(("sample.bin.qv", package, "application/octet-stream")).run()

    def assert_no_result(self, at):
        self.assertFalse(any(button.key == "download_result" for button in at.download_button))
        self.assertFalse(at.exception)

    def assert_not_displayed(self, at, sensitive):
        text = "\n".join(str(element.value) for kind in (
            "markdown", "caption", "code", "text", "json", "success", "warning", "error",
        ) for element in at.get(kind))
        text += self.logs.getvalue()
        for value in sensitive:
            self.assertNotIn(value.hex(), text)
            self.assertNotIn(base64.b64encode(value).decode(), text)
        self.assertNotIn("SENSITIVE-FILE-CONTENT-DO-NOT-DISPLAY", text)

    def test_all_pages_and_saved_measurements(self):
        at = self.app("Dashboard")
        self.assertIn("Saved experiment shots", [metric.label for metric in at.metric])
        for page in ("Secure Vault", "Quantum Threat Lab", "Performance Lab", "Security Report"):
            with self.subTest(page=page):
                at.radio("navigation").set_value(page).run()
                self.assertFalse(at.exception)
        at.radio("navigation").set_value("Performance Lab").run()
        saved = load_benchmark()
        expected = pd.DataFrame({name: row["median_ms"] for name, row in saved["algorithms"].items()})
        self.assertEqual(at.dataframe[0].value.to_numpy().tolist(), expected.to_numpy().tolist())

    def test_download_upload_round_trips_both_algorithms(self):
        for algorithm in ("ML-KEM-768", "X25519"):
            for data in (b"", b"SENSITIVE-FILE-CONTENT-DO-NOT-DISPLAY", bytes(range(256)), bytes(range(256)) * 4096):
                with self.subTest(algorithm=algorithm, size=len(data)):
                    at = self.app()
                    public, private = self.keypair(at, algorithm)
                    package = self.encrypt(at, public, data)
                    self.assertNotEqual(package, data)
                    at.download_button("download_result").click().run()
                    self.assertEqual(self.download(at, "download_result"), package)
                    self.upload_package(at, private, package)
                    self.assert_no_result(at)
                    at.button("process_file").click().run()
                    self.assertFalse(at.error)
                    self.assertEqual(self.download(at, "download_result"), data)
                    self.assert_not_displayed(at, [private])

    def test_wrong_keys_tampered_and_malformed_packages_rejected(self):
        for algorithm in ("ML-KEM-768", "X25519"):
            at = self.app()
            public, private = self.keypair(at, algorithm)
            package = self.encrypt(at, public, b"SENSITIVE-FILE-CONTENT-DO-NOT-DISPLAY")
            _, wrong_private = self.keypair(at, algorithm)
            changed = bytearray(package)
            changed[-1] ^= 1
            for key, payload in ((wrong_private, package), (private, bytes(changed)),
                                 (private, package[:-1]), (private, b"invalid"), (b"short", package)):
                with self.subTest(algorithm=algorithm, package_size=len(payload), key_size=len(key)):
                    self.upload_package(at, private, package)
                    at.button("process_file").click().run()
                    self.assertEqual(self.download(at, "download_result"), b"SENSITIVE-FILE-CONTENT-DO-NOT-DISPLAY")
                    self.upload_package(at, key, payload)
                    self.assert_no_result(at)
                    at.button("process_file").click().run()
                    self.assertTrue(at.error)
                    self.assert_no_result(at)
                    self.assert_not_displayed(at, [private, wrong_private])
            at.radio("navigation").set_value("Security Report").run()
            self.assertIn("Rejected", at.dataframe[-1].value["Result"].tolist())

    def test_generated_key_source_and_session_cleanup(self):
        at = self.app()
        public, private = self.keypair(at, "ML-KEM-768")
        at.radio("key_source").set_value("Generated in this session").run()
        at.text_input("expected_fingerprint").set_value(sha256(public).hexdigest()).run()
        at.file_uploader("file_upload_Encrypt_0").set_value(("sample.bin", b"example", "application/octet-stream")).run()
        at.button("process_file").click().run()
        package = self.download(at, "download_result")
        at.radio("vault_action").set_value("Decrypt").run()
        at.file_uploader("file_upload_Decrypt_0").set_value(("sample.bin.qv", package, "application/octet-stream")).run()
        at.button("process_file").click().run()
        self.assertEqual(self.download(at, "download_result"), b"example")
        at.button("clear_session").click().run()
        self.assert_no_result(at)
        self.assertFalse(any(button.key in ("download_public", "download_private") for button in at.download_button))
        self.assertNotIn("recipient_keys", at.session_state)
        self.assertNotIn("vault_events", at.session_state)
        self.assertIsNone(at.file_uploader("file_upload_Encrypt_1").value)

    def test_changed_inputs_invalidate_previous_downloads(self):
        at = self.app()
        public, _ = self.keypair(at, "ML-KEM-768")
        self.encrypt(at, public, b"first")
        at.file_uploader("file_upload_Encrypt_0").set_value(("new.bin", b"second", "application/octet-stream")).run()
        self.assert_no_result(at)
        at.button("process_file").click().run()
        at.radio("navigation").set_value("Dashboard").run()
        at.radio("navigation").set_value("Secure Vault").run()
        self.assert_no_result(at)
        at.radio("vault_algorithm").set_value("X25519").run()
        self.assert_no_result(at)

    def test_quantum_runs_success_and_inconclusive_through_widgets(self):
        at = self.app("Quantum Threat Lab")
        at.selectbox("quantum_shots").set_value(128).run()
        at.button("run_quantum").click().run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(at.success)
        self.assertEqual(at.metric[0].value, "4")
        self.assertEqual(at.metric[1].value, "3 × 5")
        self.assertEqual(int(at.dataframe[0].value["count"].sum()), 128)
        self.assertTrue(at.code)
        at.selectbox("quantum_base").set_value(14).run()
        self.assertTrue(any("Controls have changed" in item.value for item in at.info))
        at.button("run_quantum").click().run(timeout=30)
        self.assertFalse(at.exception)
        self.assertFalse(at.success)
        self.assertEqual(at.metric[0].value, "2")
        self.assertEqual(at.metric[1].value, "None recovered")

    def test_missing_or_invalid_benchmark_shows_error(self):
        at = self.app("Performance Lab")
        with patch("components.data.read_json", side_effect=FileNotFoundError):
            at.run()
            self.assertTrue(at.error)
            self.assertFalse(at.dataframe)
            self.assertFalse(at.exception)
        invalid = deepcopy(load_benchmark())
        invalid["algorithms"]["X25519"]["median_ms"]["key_generation"] = float("nan")
        with patch("components.data.read_json", return_value=invalid):
            at.run()
            self.assertTrue(at.error)
            self.assertFalse(at.dataframe)

    def test_size_limit_and_missing_inputs(self):
        at = self.app()
        self.assertTrue(at.button("process_file").disabled)
        public, _ = self.keypair(at, "X25519")
        at.file_uploader("key_upload_Encrypt_0").set_value(("recipient.public.key", public, "application/octet-stream")).run()
        self.assertTrue(at.button("process_file").disabled)
        # A reduced limit exercises the UI guard without allocating oversized uploads.
        with patch("components.secure_vault.MAX_PLAINTEXT", 4):
            at.file_uploader("file_upload_Encrypt_0").set_value(("large.bin", b"12345", "application/octet-stream")).run()
            at.text_input("expected_fingerprint").set_value(sha256(public).hexdigest()).run()
            at.button("process_file").click().run()
            self.assertTrue(at.error)
            self.assert_no_result(at)

    def test_simulator_failure_does_not_show_previous_results(self):
        at = self.app("Quantum Threat Lab")
        at.selectbox("quantum_shots").set_value(128).run()
        at.button("run_quantum").click().run()
        self.assertTrue(at.success)
        with patch("components.quantum_lab_view.run_period_finding", side_effect=RuntimeError("private diagnostic")):
            at.button("run_quantum").click().run()
        self.assertTrue(at.error)
        self.assertFalse(at.exception)
        self.assertFalse(at.metric)
        self.assertNotIn("private diagnostic", at.error[0].value)
        self.assertNotIn("threat_assessment", at.session_state)

    def test_quantum_evidence_applies_to_vault_and_links_file_operations(self):
        at = self.app()
        at.radio("vault_algorithm").set_value("X25519").run()
        at.radio("navigation").set_value("Quantum Threat Lab").run()
        at.selectbox("quantum_shots").set_value(128).run()
        at.button("run_quantum").click().run()
        report = json.loads(self.download(at, "download_assessment"))
        self.assertTrue(report["toy_rsa"]["recovery_verified"])
        self.assertFalse(at.button("apply_assessment").disabled)
        at.button("apply_assessment").click().run()
        self.assertEqual(at.radio("navigation").value, "Secure Vault")
        self.assertEqual(at.radio("vault_algorithm").value, "ML-KEM-768")
        public, private = self.keypair(at, "ML-KEM-768")
        package = self.encrypt(at, public, b"assessed file")
        receipt = json.loads(self.download(at, "download_receipt"))
        self.assertEqual(receipt["operation"]["Package SHA-256"], sha256(package).hexdigest())
        self.assertEqual(receipt["operation"]["Assessment"], report["assessment_id"])
        self.upload_package(at, private, package)
        at.button("process_file").click().run()
        self.assertEqual(self.download(at, "download_result"), b"assessed file")
        self.assertEqual(json.loads(self.download(at, "download_receipt"))["operation"]["Package SHA-256"],
                         receipt["operation"]["Package SHA-256"])
        at.radio("navigation").set_value("Security Report").run()
        events = at.dataframe[-1].value
        self.assertEqual(events.iloc[-1]["Assessment"], report["assessment_id"])
        self.assertEqual(events.iloc[-1]["Decision"], "Recommendation applied")
        self.assert_not_displayed(at, [private])

    def test_inconclusive_or_changed_controls_cannot_apply_assessment(self):
        at = self.app()
        at.radio("vault_algorithm").set_value("X25519").run()
        at.radio("navigation").set_value("Quantum Threat Lab").run()
        at.selectbox("quantum_shots").set_value(128).run()
        at.button("run_quantum").click().run()
        at.selectbox("quantum_base").set_value(14).run()
        self.assertTrue(at.button("apply_assessment").disabled)
        at.button("run_quantum").click().run()
        report = json.loads(self.download(at, "download_assessment"))
        self.assertFalse(report["policy"]["can_apply"])
        self.assertIsNone(report["toy_rsa"]["recovered_value"])
        self.assertTrue(at.button("apply_assessment").disabled)
        self.assertNotIn("applied_assessment", at.session_state)
        at.radio("navigation").set_value("Secure Vault").run()
        self.assertEqual(at.radio("vault_algorithm").value, "X25519")

    def test_manual_override_and_clear_preserve_honest_assessment_status(self):
        at = self.app("Quantum Threat Lab")
        at.selectbox("quantum_shots").set_value(128).run()
        at.button("run_quantum").click().run()
        at.button("apply_assessment").click().run()
        public, _ = self.keypair(at, "X25519")
        self.assertTrue(any("Manual classical comparison" in item.value for item in at.warning))
        self.encrypt(at, public, b"comparison only")
        self.assertEqual(at.session_state["vault_events"][-1]["Decision"], "Manual classical comparison")
        at.button("clear_session").click().run()
        for key in ("threat_assessment", "applied_assessment", "vault_events", "recipient_keys"):
            self.assertNotIn(key, at.session_state)

    def test_protected_backup_wrong_password_and_fresh_session_recovery(self):
        for algorithm in ("ML-KEM-768", "X25519"):
            with self.subTest(algorithm=algorithm):
                at = self.app()
                public, protected = self.keypair(at, algorithm)
                self.assertEqual(at.text_input("export_password").value, "")
                self.assertEqual(at.text_input("export_confirmation").value, "")
                raw_private = import_private_key(protected, algorithm, TEST_PASSPHRASE)
                package = self.encrypt(at, public, b"session recovery")
                at = self.app()
                at.radio("vault_algorithm").set_value(algorithm).run()
                self.assertNotIn("recipient_keys", at.session_state)
                self.upload_package(at, protected, package)
                at.button("process_file").click().run()
                self.assertEqual(self.download(at, "download_result"), b"session recovery")
                at.text_input("import_password").set_value("wrong-test-passphrase").run()
                self.assert_no_result(at)
                at.button("process_file").click().run()
                self.assertTrue(at.error)
                self.assert_no_result(at)
                self.assert_not_displayed(at, [raw_private])
                self.assertNotIn(TEST_PASSPHRASE, self.logs.getvalue())

    def test_fingerprint_mismatch_changed_key_and_explicit_unverified_override(self):
        at = self.app()
        public, _ = self.keypair(at, "ML-KEM-768")
        self.encrypt(at, public, b"verified")
        changed = bytes([public[0] ^ 1]) + public[1:]
        at.file_uploader("key_upload_Encrypt_0").set_value(("changed.key", changed, "application/octet-stream")).run()
        self.assert_no_result(at)
        self.assertTrue(at.error)
        self.assertTrue(at.button("process_file").disabled)
        at.text_input("expected_fingerprint").set_value("").run()
        self.assertTrue(at.button("process_file").disabled)
        at.checkbox("allow_unverified").check().run()
        self.assertFalse(at.button("process_file").disabled)
        at.file_uploader("key_upload_Encrypt_0").set_value(("original.key", public, "application/octet-stream")).run()
        self.assertFalse(at.checkbox("allow_unverified").value)
        self.assertTrue(at.button("process_file").disabled)

    def test_legacy_import_requires_explicit_format_selection(self):
        at = self.app()
        public, protected = self.keypair(at, "X25519")
        private = import_private_key(protected, "X25519", TEST_PASSPHRASE)
        package = self.encrypt(at, public, b"legacy recovery")
        self.upload_package(at, private, package)
        at.button("process_file").click().run()
        self.assertTrue(at.error)
        at.radio("private_import_mode").set_value("Legacy raw key").run()
        at.button("process_file").click().run()
        self.assertFalse(at.error)
        self.assertEqual(self.download(at, "download_result"), b"legacy recovery")

    def test_actual_twenty_mib_boundary_and_over_limit(self):
        data = bytes(range(256)) * (20 * 1024 * 1024 // 256)
        for algorithm in ("ML-KEM-768", "X25519"):
            with self.subTest(algorithm=algorithm):
                at = self.app()
                public, protected = self.keypair(at, algorithm)
                package = self.encrypt(at, public, data)
                self.upload_package(at, protected, package)
                at.button("process_file").click().run()
                self.assertTrue(self.download(at, "download_result") == data)
                at.radio("vault_action").set_value("Encrypt").run()
                at.file_uploader("key_upload_Encrypt_0").set_value(("public.key", public, "application/octet-stream"))
                at.file_uploader("file_upload_Encrypt_0").set_value(("over.bin", data + b"x", "application/octet-stream")).run()
                at.text_input("expected_fingerprint").set_value(sha256(public).hexdigest()).run()
                at.button("process_file").click().run()
                self.assertTrue(at.error)
                self.assert_no_result(at)

    def test_controlled_study_and_file_benchmark_widgets(self):
        at = self.app("Quantum Threat Lab")
        at.button("run_study").click().run(timeout=180)
        self.assertFalse(at.exception)
        report = json.loads(self.download(at, "download_study"))
        self.assertEqual(len(report["trials"]), 16)
        self.assertEqual(report["metadata"]["planned_trials"], 16)
        self.assertEqual(sum(item["failed_trials"] for item in report["summary"]), 0)
        at.radio("navigation").set_value("Performance Lab").run()
        at.button("run_file_benchmark").click().run(timeout=60)
        self.assertFalse(at.exception)
        self.assertEqual(len(at.dataframe[-1].value), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
