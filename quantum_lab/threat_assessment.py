"""Connect measured order finding to toy key recovery and a declared vault policy.

The RSA fixture is public, tiny, unpadded textbook arithmetic. It is never used
to protect vault files. No risk score or production attack time is inferred.
"""
from hashlib import sha256
import json
from math import prod

from quantum_lab.analysis import analyze_counts

POLICY_ID = "post-quantum-key-establishment-v1"
REQUIREMENT = "Post-quantum key establishment for file protection"
LIMITATIONS = [
    "Ideal N=15 simulation; no real RSA key, quantum hardware or practical speedup.",
    "The toy RSA value is a public synthetic fixture, not a vault key or user file.",
    "X25519 relies on elliptic-curve discrete logarithms; this circuit does not attack it.",
    "ML-KEM security is not tested or proved by the factoring experiment.",
    "The recommendation is a declared migration policy, not a quantum-derived risk score.",
    "Shot count and observed frequencies do not select AES or ML-KEM security parameters.",
]


def recover_toy_rsa_value(factors, modulus=15):
    """Recover a public toy challenge using measured factors, with no fallback."""
    public_exponent, original_value = 3, 7
    ciphertext = pow(original_value, public_exponent, modulus)
    fixture = {
        "label": "Public synthetic textbook RSA fixture; not secure encryption",
        "modulus": modulus, "public_exponent": public_exponent,
        "wrapped_value": ciphertext, "original_value": original_value,
        "recovered_value": None, "recovery_verified": False,
    }
    if (modulus != 15 or len(factors) != 2 or any(type(p) is not int or p <= 1 for p in factors)
            or factors[0] == factors[1] or prod(factors) != modulus):
        return fixture
    totient = (factors[0] - 1) * (factors[1] - 1)
    private_exponent = pow(public_exponent, -1, totient)
    recovered = pow(ciphertext, private_exponent, modulus)
    fixture.update(recovered_value=recovered, recovery_verified=recovered == original_value)
    return fixture


def build_threat_assessment(experiment):
    """Recheck actual counts, then record evidence separately from security policy.

    Even inconclusive evidence never recommends a classical fallback. Applying
    this investigation's recommendation requires verified toy key recovery.
    """
    source = experiment["configuration"]
    configuration = {key: source[key] for key in (
        "measured_at_utc", "base", "modulus", "counting_qubits", "work_qubits", "shots",
        "seed_simulator", "seed_transpiler", "backend", "method", "device", "noise_model",
        "qiskit_version", "aer_version", "python_version",
    )}
    if type(configuration["shots"]) is not int or configuration["shots"] < 1:
        raise ValueError("Invalid experiment shot count")
    counts = dict(experiment["counts"])
    # Do not trust a pre-filled success flag or factors from the caller.
    analysis = analyze_counts(counts, configuration["base"], configuration["modulus"],
                              configuration["counting_qubits"])
    if analysis["total_shots"] != configuration["shots"]:
        raise ValueError("Experiment counts do not match its shot count")
    toy = recover_toy_rsa_value(analysis["factors"], configuration["modulus"])
    recovered = toy["recovery_verified"]
    canonical = json.dumps({"configuration": configuration, "counts": counts}, sort_keys=True)
    return {
        "schema_version": 1,
        "assessment_id": sha256(canonical.encode()).hexdigest(),
        "research_question": "Can measured order finding expose factors that recover a toy RSA-wrapped value?",
        "configuration": configuration, "counts": counts,
        "analysis": analysis, "toy_rsa": toy,
        "evidence_status": "toy_recovery_verified" if recovered else "inconclusive",
        "policy": {
            "id": POLICY_ID, "requirement": REQUIREMENT, "recommended_algorithm": "ML-KEM-768",
            "basis": "Declared post-quantum requirement and algorithm assumptions; not measured attack feasibility",
            "can_apply": recovered,
            "application_reason": ("Measured factors recovered the toy value; the investigation can accompany a vault migration choice"
                                   if recovered else "No verified toy recovery in this run; rerun the investigation before applying it"),
        },
        "algorithm_findings": [
            {"Algorithm": "Textbook RSA fixture", "Finding": "Toy value recovered" if recovered else "Inconclusive",
             "Evidence": "Direct measured factoring and classical recovery"},
            {"Algorithm": "X25519", "Finding": "Classical comparison; not selected for the post-quantum requirement",
             "Evidence": "Known discrete-log threat; not attacked by this circuit"},
            {"Algorithm": "ML-KEM-768", "Finding": "Policy recommendation for the post-quantum requirement",
             "Evidence": "Lattice-based design; not tested by this circuit"},
        ],
        "limitations": list(LIMITATIONS),
        "references": ["https://csrc.nist.gov/pubs/fips/203/final",
                       "https://qiskit.qotlabs.org/learning/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/shor-algorithm"],
    }
