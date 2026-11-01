"""Security checks for the independent X25519 baseline."""
import unittest

from cryptography.exceptions import InvalidTag
from crypto_engine.classical import (
    MAGIC, HEADER_SIZE, generate_classical_keys, classical_encapsulate,
    classical_decapsulate, encrypt_classical_file, decrypt_classical_file,
)
from crypto_engine.encryption import encrypt_pqc_file, decrypt_pqc_file
from crypto_engine.pqc import generate_pqc_keys


class ClassicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public, cls.private = generate_classical_keys()

    def test_key_agreement(self):
        sender, secret = classical_encapsulate(self.public)
        self.assertEqual((len(self.public), len(self.private), len(sender), len(secret)),
                         (32, 32, 32, 32))
        self.assertEqual(secret, classical_decapsulate(self.private, sender))

    def test_round_trips(self):
        for data in (b"", b"QuantumVault classical baseline test.", bytes(range(256)) * 4096):
            with self.subTest(size=len(data)):
                self.assertEqual(data, decrypt_classical_file(
                    encrypt_classical_file(data, self.public), self.private))

    def test_fresh_ephemeral_key(self):
        first = encrypt_classical_file(b"same", self.public)
        second = encrypt_classical_file(b"same", self.public)
        self.assertNotEqual(first[len(MAGIC):len(MAGIC) + 32],
                            second[len(MAGIC):len(MAGIC) + 32])

    def test_tampering(self):
        package = encrypt_classical_file(b"sample", self.public)
        for offset in (0, len(MAGIC), len(MAGIC) + 32, HEADER_SIZE - 1, HEADER_SIZE, -1):
            modified = bytearray(package)
            modified[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises((ValueError, InvalidTag)):
                decrypt_classical_file(bytes(modified), self.private)

    def test_wrong_key(self):
        _, wrong_private = generate_classical_keys()
        with self.assertRaises(InvalidTag):
            decrypt_classical_file(encrypt_classical_file(b"sample", self.public), wrong_private)

    def test_malformed(self):
        package = encrypt_classical_file(b"sample", self.public)
        for data in (b"", package[:HEADER_SIZE], package[:-1], package + b"extra"):
            with self.subTest(size=len(data)), self.assertRaises((ValueError, InvalidTag)):
                decrypt_classical_file(data, self.private)
        with self.assertRaises(TypeError):
            decrypt_classical_file("not bytes", self.private)

    def test_invalid_keys(self):
        for key in (b"", bytes(31), bytes(33), bytes(32)):
            with self.subTest(key_length=len(key)), self.assertRaises(ValueError):
                classical_encapsulate(key)
        with self.assertRaises(ValueError):
            classical_decapsulate(self.private, bytes(32))
        with self.assertRaises(ValueError):
            classical_decapsulate(b"short", self.public)

    def test_algorithm_formats_are_distinct(self):
        pq_public, pq_private = generate_pqc_keys()
        with self.assertRaises(ValueError):
            decrypt_classical_file(encrypt_pqc_file(b"sample", pq_public), self.private)
        with self.assertRaises(ValueError):
            decrypt_pqc_file(encrypt_classical_file(b"sample", self.public), pq_private)


if __name__ == "__main__":
    unittest.main(verbosity=2)
