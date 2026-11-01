"""Bounded RFC 7516/7518 JWE key backups and explicit fingerprint matching.

Application headers bind version, algorithm and inner serialization. JWCrypto
performs PBES2, AES key wrapping and authenticated content encryption. This
application profile has not undergone independent security review.
"""
import base64
from hashlib import sha256
import hmac
import json
import os
import re

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, NoEncryption, load_der_private_key,
)
from jwcrypto import jwa, jwe, jwk

ITERATIONS = 220_000
MAX_CONTAINER = 8192
PUBLIC_SIZES = {"ML-KEM-768": 1184, "X25519": 32}
PRIVATE_SIZES = {"ML-KEM-768": 2400, "X25519": 32}
ALLOWED = ["PBES2-HS512+A256KW", "A256GCM"]
# The library's default cap is below our fixed work factor. The application
# accepts exactly ITERATIONS, never an arbitrary user-specified cost.
jwa.default_max_pbkdf2_iterations = ITERATIONS


class KeyBackupError(ValueError):
    """Invalid backup, algorithm or password; callers should show a generic error."""


def _algorithm(algorithm):
    if algorithm not in PUBLIC_SIZES:
        raise KeyBackupError("Unsupported key algorithm")


def _password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise KeyBackupError("Use a passphrase of 12 to 128 characters")
    return jwk.JWK.from_password(password)


def _decode(segment):
    if not isinstance(segment, str) or not segment or not re.fullmatch(r"[A-Za-z0-9_-]+", segment):
        raise KeyBackupError("Invalid backup encoding")
    return base64.b64decode(segment + "=" * (-len(segment) % 4), altchars=b"-_", validate=True)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise KeyBackupError("Duplicate backup header")
        result[key] = value
    return result


def inspect_backup(data, algorithm):
    """Validate all attacker-controlled sizes and KDF settings before deriving."""
    _algorithm(algorithm)
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_CONTAINER:
        raise KeyBackupError("Invalid backup size")
    try:
        parts = data.decode("ascii").split(".")
        if len(parts) != 5 or len(parts[0]) > 1024:
            raise KeyBackupError("Invalid compact JWE")
        protected, wrapped, iv, ciphertext, tag = map(_decode, parts)
        header = json.loads(protected, object_pairs_hook=_unique_object)
        expected = {"alg", "enc", "p2s", "p2c", "qv_version", "qv_algorithm", "qv_format"}
        if not isinstance(header, dict) or set(header) != expected:
            raise KeyBackupError("Unsupported backup header")
        if (header["alg"] != ALLOWED[0] or header["enc"] != ALLOWED[1]
                or type(header["qv_version"]) is not int or header["qv_version"] != 1
                or header["qv_algorithm"] != algorithm
                or type(header["p2c"]) is not int or header["p2c"] != ITERATIONS):
            raise KeyBackupError("Unsupported backup profile")
        fmt = "pqcrypto-raw" if algorithm == "ML-KEM-768" else "pkcs8-der"
        size = 2400 if algorithm == "ML-KEM-768" else 48
        if (header["qv_format"] != fmt or len(_decode(header["p2s"])) != 16
                or (len(wrapped), len(iv), len(ciphertext), len(tag)) != (40, 12, size, 16)):
            raise KeyBackupError("Invalid backup field lengths")
        return header
    except (ValueError, UnicodeError, TypeError, KeyError) as exc:
        raise KeyBackupError("Invalid protected key backup") from None


def export_private_key(private_key, algorithm, password):
    _algorithm(algorithm)
    if not isinstance(private_key, bytes) or len(private_key) != PRIVATE_SIZES[algorithm]:
        raise KeyBackupError("Invalid private key length")
    recipient = _password(password)
    if algorithm == "X25519":
        payload = X25519PrivateKey.from_private_bytes(private_key).private_bytes(
            Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    else:
        # pqcrypto exposes opaque byte keys, not a PKCS8 serializer.
        payload = private_key
    salt = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode()
    header = {"alg": ALLOWED[0], "enc": ALLOWED[1], "p2s": salt, "p2c": ITERATIONS,
              "qv_version": 1, "qv_algorithm": algorithm,
              "qv_format": "pqcrypto-raw" if algorithm == "ML-KEM-768" else "pkcs8-der"}
    token = jwe.JWE(payload, protected=json.dumps(header), algs=ALLOWED, recipient=recipient)
    encoded = token.serialize(compact=True).encode("ascii")
    inspect_backup(encoded, algorithm)
    return encoded


def import_private_key(data, algorithm, password):
    inspect_backup(data, algorithm)
    recipient = _password(password)
    try:
        token = jwe.JWE(algs=ALLOWED)
        token.deserialize(data.decode("ascii"), key=recipient)
        if algorithm == "ML-KEM-768":
            private = token.payload
        else:
            key = load_der_private_key(token.payload, password=None)
            if not isinstance(key, X25519PrivateKey):
                raise KeyBackupError("Wrong key type")
            private = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        if len(private) != PRIVATE_SIZES[algorithm]:
            raise KeyBackupError("Wrong key length")
        return private
    except Exception:
        # No backend exceptions or cryptographic data are shown by callers.
        raise KeyBackupError("Could not unlock protected key backup") from None


def public_fingerprint(public_key, algorithm):
    _algorithm(algorithm)
    if not isinstance(public_key, bytes) or len(public_key) != PUBLIC_SIZES[algorithm]:
        raise ValueError("Invalid public key length")
    return sha256(public_key).hexdigest()


def match_fingerprint(public_key, algorithm, expected):
    observed = public_fingerprint(public_key, algorithm)
    normalized = re.sub(r"[\s:]", "", expected).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("Expected fingerprint must contain 64 hexadecimal characters")
    return hmac.compare_digest(observed, normalized)
