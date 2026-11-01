"""Report dependency versions and ML-KEM agreement without secret output."""
import argparse
import importlib
from importlib.metadata import version
import json
import platform
import sys

DEPENDENCIES = [("streamlit", "streamlit"), ("cryptography", "cryptography"),
                ("pqcrypto.kem.ml_kem_768", "pqcrypto"), ("qiskit", "qiskit"),
                ("qiskit_aer", "qiskit-aer"), ("jwcrypto", "jwcrypto"),
                ("numpy", "numpy"), ("pandas", "pandas"), ("plotly", "plotly")]


def check_environment():
    checks = [{"name": "Python 3.11", "ok": sys.version_info[:2] == (3, 11), "version": platform.python_version()}]
    for module, distribution in DEPENDENCIES:
        try:
            importlib.import_module(module)
            checks.append({"name": distribution, "ok": True, "version": version(distribution)})
        except Exception:
            checks.append({"name": distribution, "ok": False,
                           "action": "Install requirements-lock.txt using this environment's Python executable"})
    try:
        from crypto_engine.pqc import generate_pqc_keys, pqc_encapsulate, pqc_decapsulate
        public, private = generate_pqc_keys()
        ciphertext, secret = pqc_encapsulate(public)
        checks.append({"name": "ML-KEM-768 agreement", "ok": secret == pqc_decapsulate(private, ciphertext)})
    except Exception:
        checks.append({"name": "ML-KEM-768 agreement", "ok": False, "action": "Check pqcrypto; do not substitute another algorithm"})
    return {"python_executable": sys.executable, "checks": checks, "ok": all(item["ok"] for item in checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = check_environment()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in report["checks"]:
            print(item["name"], "OK" if item["ok"] else "FAILED", item.get("version", item.get("action", "")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
