"""Read saved, non-secret project measurements without inventing defaults."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(relative_path):
    with (ROOT / relative_path).open(encoding="utf-8-sig") as source:
        return json.load(source)


def load_benchmark():
    result = read_json("benchmark/results.json")
    for algorithm in ("ML-KEM-768", "X25519"):
        entry = result["algorithms"][algorithm]
        for operation in ("key_generation", "sender_establishment", "receiver_recovery"):
            value = entry["median_ms"][operation]
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid timing in saved benchmark")
        for field in ("public_key", "private_key", "transmitted_key_material", "shared_secret"):
            if type(entry["sizes_bytes"][field]) is not int or entry["sizes_bytes"][field] <= 0:
                raise ValueError("Invalid size in saved benchmark")
    if result["metadata"]["statistic"] != "median":
        raise ValueError("Unsupported benchmark statistic")
    return result


DATA_ERRORS = (OSError, ValueError, KeyError, TypeError)
