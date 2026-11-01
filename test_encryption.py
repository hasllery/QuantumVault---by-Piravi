"""Round trips and rejection tests for the encrypted envelope."""
import unittest
from cryptography.exceptions import InvalidTag
from crypto_engine.pqc import generate_pqc_keys, pqc_encapsulate, pqc_decapsulate
from crypto_engine.encryption import encrypt_pqc_file, decrypt_pqc_file, HEADER_SIZE


class EncryptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public, cls.private = generate_pqc_keys()

    def test_kem(self):
        ciphertext, secret = pqc_encapsulate(self.public)
        self.assertEqual(secret, pqc_decapsulate(self.private, ciphertext))
        self.assertEqual((len(self.public), len(self.private), len(ciphertext), len(secret)),
                         (1184, 2400, 1088, 32))

    def test_round_trips(self):
        for data in (b"", b"QuantumVault: Protecting files using post-quantum cryptography.",
                     bytes(range(256)) * 4096):
            with self.subTest(size=len(data)):
                package = encrypt_pqc_file(data, self.public)
                self.assertEqual(data, decrypt_pqc_file(package, self.private))

    def test_randomized_encryption(self):
        self.assertNotEqual(encrypt_pqc_file(b"same", self.public),
                            encrypt_pqc_file(b"same", self.public))

    def test_tampering(self):
        package = encrypt_pqc_file(b"sample", self.public)
        for offset in (0, len(b"QuantumVault\x01"), HEADER_SIZE - 20, HEADER_SIZE - 1, -1):
            changed = bytearray(package)
            changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises((ValueError, InvalidTag)):
                decrypt_pqc_file(bytes(changed), self.private)

    def test_wrong_key(self):
        _, wrong_key = generate_pqc_keys()
        with self.assertRaises(InvalidTag):
            decrypt_pqc_file(encrypt_pqc_file(b"sample", self.public), wrong_key)

    def test_malformed(self):
        package = encrypt_pqc_file(b"sample", self.public)
        for data in (b"", package[:HEADER_SIZE], package[:-1], package + b"extra"):
            with self.subTest(size=len(data)), self.assertRaises((ValueError, InvalidTag)):
                decrypt_pqc_file(data, self.private)


if __name__ == "__main__":
    unittest.main(verbosity=2)
