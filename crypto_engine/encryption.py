"""Versioned binary envelopes: ML-KEM-768, HKDF-SHA256, AES-256-GCM."""
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pqcrypto.kem import ml_kem_768

from crypto_engine.pqc import pqc_encapsulate, pqc_decapsulate

MAGIC = b"QuantumVault\x01"
SALT_SIZE = 16
NONCE_SIZE = 12
HEADER_SIZE = len(MAGIC) + ml_kem_768.CIPHERTEXT_SIZE + SALT_SIZE + NONCE_SIZE


def derive_aes_key(shared_secret, salt):
    """Derive a fresh 256-bit encryption key."""
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                info=b"QuantumVault-ML-KEM-768-v1").derive(shared_secret)


def encrypt_pqc_file(file_data, recipient_public_key):
    """Encrypt bytes; the returned envelope never contains the private key."""
    kem_ciphertext, secret = pqc_encapsulate(recipient_public_key)
    salt, nonce = os.urandom(SALT_SIZE), os.urandom(NONCE_SIZE)
    header = MAGIC + kem_ciphertext + salt + nonce
    encrypted = AESGCM(derive_aes_key(secret, salt)).encrypt(nonce, file_data, header)
    return header + encrypted


def decrypt_pqc_file(encrypted_package, recipient_private_key):
    """Return authenticated plaintext, or raise ValueError/InvalidTag."""
    if not isinstance(encrypted_package, bytes):
        raise TypeError("Encrypted package must be bytes")
    if len(encrypted_package) < HEADER_SIZE + 16:
        raise ValueError("Truncated QuantumVault package")
    if not encrypted_package.startswith(MAGIC):
        raise ValueError("Unsupported QuantumVault format or version")
    offset = len(MAGIC)
    kem_ciphertext = encrypted_package[offset:offset + ml_kem_768.CIPHERTEXT_SIZE]
    offset += ml_kem_768.CIPHERTEXT_SIZE
    salt = encrypted_package[offset:offset + SALT_SIZE]
    nonce = encrypted_package[offset + SALT_SIZE:HEADER_SIZE]
    secret = pqc_decapsulate(recipient_private_key, kem_ciphertext)
    return AESGCM(derive_aes_key(secret, salt)).decrypt(
        nonce, encrypted_package[HEADER_SIZE:], encrypted_package[:HEADER_SIZE])
