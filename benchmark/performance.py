"""Key-establishment timings, excluding HKDF and file encryption."""
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from importlib.metadata import version

from crypto_engine.classical import (
    generate_classical_keys, classical_encapsulate, classical_decapsulate,
)
from crypto_engine.pqc import generate_pqc_keys, pqc_encapsulate, pqc_decapsulate


def _validate_repetitions(repetitions):
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError("repetitions must be a positive integer")


def measure(function, repetitions=30):
    """Return median milliseconds after one untimed warm-up invocation."""
    _validate_repetitions(repetitions)
    function()
    results = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        function()
        results.append((time.perf_counter_ns() - start) / 1_000_000)
    return statistics.median(results)


def benchmark_algorithms(repetitions=30):
    """Return JSON-serializable sizes, median timings, and measurement context.

    Key generation includes raw-byte export for both implementations. Sender
    setup includes public-key loading, fresh ephemeral key generation for
    X25519, shared-secret computation, and transmitted-material serialization.
    Receiver setup includes key loading and shared-secret recovery. All inputs
    are prepared outside the timed region; the recipient key is reused.
    """
    _validate_repetitions(repetitions)
    results = {
        "metadata": {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "versions": {name: version(name) for name in ("cryptography", "pqcrypto")},
            "repetitions": repetitions,
            "warmup_calls_per_operation": 1,
            "statistic": "median",
            "clock": "perf_counter_ns",
            "scope": "key establishment only; excludes HKDF, AES-GCM and file I/O",
            "sender_scope": "fresh sender material and shared secret; X25519 includes ephemeral key generation",
            "receiver_scope": "recover shared secret from byte-encoded keys and sender material",
        },
        "algorithms": {},
    }
    for name, keygen, sender, receiver in (
        ("ML-KEM-768", generate_pqc_keys, pqc_encapsulate, pqc_decapsulate),
        ("X25519", generate_classical_keys, classical_encapsulate, classical_decapsulate),
    ):
        public, private = keygen()
        material, secret = sender(public)
        if secret != receiver(private, material):
            raise RuntimeError(f"{name}: shared-secret verification failed")
        results["algorithms"][name] = {
            "sizes_bytes": {
                "public_key": len(public), "private_key": len(private),
                "transmitted_key_material": len(material), "shared_secret": len(secret),
            },
            "median_ms": {
                "key_generation": measure(keygen, repetitions),
                "sender_establishment": measure(lambda: sender(public), repetitions),
                "receiver_recovery": measure(lambda: receiver(private, material), repetitions),
            },
        }
    return results


if __name__ == "__main__":
    print(json.dumps(benchmark_algorithms(), indent=2))
