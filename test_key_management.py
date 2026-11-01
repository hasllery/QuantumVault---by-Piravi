"""Protected key containers, KDF preflight bounds and recipient binding."""
import base64
import json
import hmac
import unittest
from unittest.mock import patch

from crypto_engine.key_management import (
    export_private_key, import_private_key, inspect_backup, match_fingerprint,
    public_fingerprint, KeyBackupError, MAX_CONTAINER,
)
from crypto_engine.pqc import generate_pqc_keys
from crypto_engine.classical import generate_classical_keys
from utils.files import safe_name

PASSWORD = "synthetic-unit-test-passphrase"


def change_header(data, **updates):
    parts = data.decode().split(".")
    header = json.loads(base64.urlsafe_b64decode(parts[0] + "=" * (-len(parts[0]) % 4)))
    header.update(updates)
    parts[0] = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    return ".".join(parts).encode()


class KeyManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = {"ML-KEM-768": generate_pqc_keys(), "X25519": generate_classical_keys()}
        cls.backups = {name: export_private_key(pair[1], name, PASSWORD) for name, pair in cls.pairs.items()}

    def test_round_trips_and_randomized_backups(self):
        for algorithm, (public, private) in self.pairs.items():
            with self.subTest(algorithm=algorithm):
                self.assertTrue(hmac.compare_digest(import_private_key(self.backups[algorithm], algorithm, PASSWORD), private))
                self.assertNotEqual(self.backups[algorithm], export_private_key(private, algorithm, PASSWORD))
                self.assertNotIn(base64.urlsafe_b64encode(private), self.backups[algorithm])

    def test_wrong_password_and_ciphertext_tampering(self):
        for algorithm, backup in self.backups.items():
            with self.assertRaises(KeyBackupError):
                import_private_key(backup, algorithm, "wrong-test-passphrase")
            parts = backup.decode().split(".")
            parts[3] = ("A" if parts[3][0] != "A" else "B") + parts[3][1:]
            with self.assertRaises(KeyBackupError):
                import_private_key(".".join(parts).encode(), algorithm, PASSWORD)

    def test_profile_and_resource_limits_before_kdf(self):
        original = self.backups["ML-KEM-768"]
        bad = [b"", b"x" * (MAX_CONTAINER + 1), b"a.b.c.d.e", original[:-1],
               change_header(original, p2c=10 ** 12), change_header(original, p2c=True),
               change_header(original, qv_version=2), change_header(original, alg="dir"),
               change_header(original, enc="A128GCM"), change_header(original, zip="DEF"),
               change_header(original, p2s="A" * 1000)]
        with patch("crypto_engine.key_management.jwe.JWE", side_effect=AssertionError("KDF must not run")):
            for data in bad:
                with self.subTest(size=len(data)), self.assertRaises(KeyBackupError):
                    import_private_key(data, "ML-KEM-768", PASSWORD)

    def test_algorithm_and_header_authentication(self):
        with self.assertRaises(KeyBackupError):
            import_private_key(self.backups["ML-KEM-768"], "X25519", PASSWORD)
        # A valid-length changed salt passes preflight but must fail authentication.
        changed = change_header(self.backups["X25519"], p2s=base64.urlsafe_b64encode(b"0" * 16).rstrip(b"=").decode())
        inspect_backup(changed, "X25519")
        with self.assertRaises(KeyBackupError):
            import_private_key(changed, "X25519", PASSWORD)

    def test_password_and_raw_key_bounds(self):
        for password in ("short", "x" * 129, None):
            with self.assertRaises(KeyBackupError):
                export_private_key(self.pairs["X25519"][1], "X25519", password)
        with self.assertRaises(KeyBackupError):
            export_private_key(b"short", "ML-KEM-768", PASSWORD)

    def test_fingerprint_matching_and_changed_key(self):
        for algorithm, (public, _) in self.pairs.items():
            fingerprint = public_fingerprint(public, algorithm)
            self.assertTrue(match_fingerprint(public, algorithm, ":".join(fingerprint.upper()[i:i+2] for i in range(0,64,2))))
            changed = bytes([public[0] ^ 1]) + public[1:]
            self.assertFalse(match_fingerprint(changed, algorithm, fingerprint))
            with self.assertRaises(ValueError):
                match_fingerprint(public, algorithm, "not a fingerprint")

    def test_safe_download_names(self):
        for name in ("../secret.txt", "C:\\private\\file.bin", "CON.txt", "..", "bad\x00name?.txt"):
            result = safe_name(name)
            self.assertTrue(result)
            self.assertFalse(any(char in result for char in '/\\\x00?'))
            self.assertNotEqual(result, "CON.txt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
