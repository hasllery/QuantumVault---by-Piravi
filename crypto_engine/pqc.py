"""ML-KEM-768 key encapsulation using pqcrypto."""
from pqcrypto.kem import ml_kem_768


def generate_pqc_keys():
    """Return (public_key, private_key) as bytes."""
    return ml_kem_768.generate_keypair()


def pqc_encapsulate(public_key):
    """Return (KEM ciphertext, shared secret)."""
    return ml_kem_768.encrypt(public_key)


def pqc_decapsulate(private_key, ciphertext):
    """Recover the encapsulated shared secret."""
    return ml_kem_768.decrypt(private_key, ciphertext)
