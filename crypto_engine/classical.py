"""Educational ephemeral-static X25519 file protection baseline."""
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption,
)

MAGIC = b"QuantumVault-X25519\x01"
PUBLIC_KEY_SIZE = 32
SALT_SIZE = 16
NONCE_SIZE = 12
HEADER_SIZE = len(MAGIC) + PUBLIC_KEY_SIZE + SALT_SIZE + NONCE_SIZE


def generate_classical_keys():
    """Return the recipient's (raw public key, raw private key) as bytes."""
    private = X25519PrivateKey.generate()
    return (
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
        private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
    )


def classical_encapsulate(recipient_public_key):
    """Return (fresh ephemeral public key, X25519 shared secret).

    This is a baseline key-agreement adapter, not a standardized HPKE suite.
    """
    recipient = X25519PublicKey.from_public_bytes(recipient_public_key)
    ephemeral = X25519PrivateKey.generate()
    secret = ephemeral.exchange(recipient)
    sender_public = ephemeral.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return sender_public, secret


def classical_decapsulate(recipient_private_key, sender_public_key):
    """Recover the shared secret from the recipient and ephemeral keys."""
    private = X25519PrivateKey.from_private_bytes(recipient_private_key)
    sender = X25519PublicKey.from_public_bytes(sender_public_key)
    return private.exchange(sender)


def derive_classical_aes_key(shared_secret, salt):
    """Use the same HKDF settings as PQC, with an X25519-specific context."""
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                info=b"QuantumVault-X25519-v1").derive(shared_secret)


def encrypt_classical_file(file_data, recipient_public_key):
    """Encrypt bytes with a fresh ephemeral key, salt, and AES-GCM nonce."""
    sender_public, secret = classical_encapsulate(recipient_public_key)
    salt, nonce = os.urandom(SALT_SIZE), os.urandom(NONCE_SIZE)
    header = MAGIC + sender_public + salt + nonce
    ciphertext = AESGCM(derive_classical_aes_key(secret, salt)).encrypt(
        nonce, file_data, header)
    return header + ciphertext


def decrypt_classical_file(encrypted_package, recipient_private_key):
    """Return only authenticated plaintext; reject malformed packages."""
    if not isinstance(encrypted_package, bytes):
        raise TypeError("Encrypted package must be bytes")
    if len(encrypted_package) < HEADER_SIZE + 16:
        raise ValueError("Truncated QuantumVault X25519 package")
    if not encrypted_package.startswith(MAGIC):
        raise ValueError("Unsupported QuantumVault X25519 format or version")
    offset = len(MAGIC)
    sender_public = encrypted_package[offset:offset + PUBLIC_KEY_SIZE]
    offset += PUBLIC_KEY_SIZE
    salt = encrypted_package[offset:offset + SALT_SIZE]
    nonce = encrypted_package[offset + SALT_SIZE:HEADER_SIZE]
    secret = classical_decapsulate(recipient_private_key, sender_public)
    return AESGCM(derive_classical_aes_key(secret, salt)).decrypt(
        nonce, encrypted_package[HEADER_SIZE:], encrypted_package[:HEADER_SIZE])
