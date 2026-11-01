"""Whole-file measurements kept separate from the original KEM benchmark."""
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import platform
import math
from uuid import uuid4

from benchmark.performance import measure
from crypto_engine.pqc import generate_pqc_keys
from crypto_engine.encryption import encrypt_pqc_file, decrypt_pqc_file
from crypto_engine.classical import generate_classical_keys, encrypt_classical_file, decrypt_classical_file

ROOT = Path(__file__).resolve().parents[1]


def validate_report(report):
    """Reject incomplete or nonsensical local evidence before displaying it."""
    metadata = report["metadata"]
    if metadata["schema_version"] != 1 or metadata["statistic"] != "median":
        raise ValueError("Unsupported file benchmark")
    if type(metadata["repetitions"]) is not int or not 1 <= metadata["repetitions"] <= 30:
        raise ValueError("Invalid repetitions")
    if not all(isinstance(metadata[key], str) and metadata[key] for key in ("measured_at_utc", "scope")):
        raise ValueError("Invalid metadata")
    rows = report["measurements"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10:
        raise ValueError("Invalid measurements")
    for row in rows:
        if row["algorithm"] not in ("ML-KEM-768", "X25519"):
            raise ValueError("Invalid algorithm")
        for key in ("plaintext_bytes", "package_bytes", "overhead_bytes"):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError("Invalid size")
        if row["package_bytes"] - row["plaintext_bytes"] != row["overhead_bytes"]:
            raise ValueError("Inconsistent package sizes")
        for key in ("encrypt_median_ms", "decrypt_median_ms"):
            if type(row[key]) not in (int, float) or not math.isfinite(row[key]) or row[key] < 0:
                raise ValueError("Invalid timing")
    return report


def benchmark_files(sizes=(0, 1024, 1048576), repetitions=5):
    if type(repetitions) is not int or not 1 <= repetitions <= 30:
        raise ValueError("Use 1 to 30 repetitions")
    if not sizes or len(sizes) > 5 or any(type(n) is not int or not 0 <= n <= 20 * 1024 ** 2 for n in sizes):
        raise ValueError("Use up to five file sizes between zero and 20 MiB")
    rows = []
    for name, generate, encrypt, decrypt in (
        ("ML-KEM-768", generate_pqc_keys, encrypt_pqc_file, decrypt_pqc_file),
        ("X25519", generate_classical_keys, encrypt_classical_file, decrypt_classical_file),
    ):
        public, private = generate()
        for size in sizes:
            data = (bytes(range(256)) * ((size + 255) // 256))[:size]
            package = encrypt(data, public)
            if decrypt(package, private) != data:
                raise RuntimeError("Benchmark round trip failed")
            rows.append({"algorithm": name, "plaintext_bytes": size, "package_bytes": len(package),
                         "overhead_bytes": len(package) - size,
                         "encrypt_median_ms": measure(lambda: encrypt(data, public), repetitions),
                         "decrypt_median_ms": measure(lambda: decrypt(package, private), repetitions)})
    return {"metadata": {"schema_version": 1, "measured_at_utc": datetime.now(timezone.utc).isoformat(),
                         "python": platform.python_version(), "platform": platform.platform(),
                         "versions": {name: version(name) for name in ("cryptography", "pqcrypto")},
                         "repetitions": repetitions, "warmup_calls_per_operation": 1,
                         "statistic": "median", "fixture": "same synthetic repeated bytes 0 to 255 for both algorithms",
                         "scope": "in-memory key establishment, HKDF, AES-GCM and package creation/recovery; excludes recipient key generation and disk I/O"},
            "measurements": rows}


def save_benchmark(report):
    directory = ROOT / "benchmark" / "records"
    directory.mkdir(exist_ok=True)
    path = directory / (datetime.now(timezone.utc).strftime("files-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8] + ".json")
    with path.open("x", encoding="utf-8") as target:
        json.dump(report, target, indent=2)
    return path


if __name__ == "__main__":
    report = benchmark_files()
    print(json.dumps(report, indent=2))
    print("Saved:", save_benchmark(report))
