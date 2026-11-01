"""Classical post-processing of measured quantum phases; no order search."""
from fractions import Fraction
from math import gcd


def validate_experiment(base, modulus, counting_qubits):
    """Keep the dense-unitary teaching example explicitly bounded to N=15."""
    if type(modulus) is not int or modulus != 15:
        raise ValueError("This demonstration supports only modulus N=15")
    if type(base) is not int or not 1 < base < modulus or gcd(base, modulus) != 1:
        raise ValueError("base must be an integer between 2 and 14 coprime to 15")
    if type(counting_qubits) is not int or not 2 <= counting_qubits <= 8:
        raise ValueError("counting_qubits must be an integer from 2 to 8")


def extract_factors(base, modulus, period):
    """Try Shor's gcd step only for a verified even order candidate."""
    if type(period) is not int or period <= 0 or period % 2:
        return []
    if pow(base, period, modulus) != 1:
        return []
    root = pow(base, period // 2, modulus)
    if root in (1, modulus - 1):
        return []
    factors = sorted({gcd(root - 1, modulus), gcd(root + 1, modulus)})
    if len(factors) == 2 and all(1 < factor < modulus for factor in factors):
        if factors[0] * factors[1] == modulus:
            return factors
    return []


def analyze_counts(counts, base=2, modulus=15, counting_qubits=8):
    """Estimate orders from measured phases using bounded rational approximation.

    A denominator is accepted only when a**denominator == 1 (mod N).
    Zero phases and reduced denominators that fail verification stay inconclusive;
    we do not search multiples or insert a known order/factors as a fallback.
    """
    validate_experiment(base, modulus, counting_qubits)
    outcomes = []
    support = {}
    for bitstring, count in sorted(counts.items()):
        if (not isinstance(bitstring, str) or len(bitstring) != counting_qubits
                or any(bit not in "01" for bit in bitstring)):
            raise ValueError("Counts must use fixed-width binary measurement strings")
        if type(count) is not int or count <= 0:
            raise ValueError("Measurement counts must be positive integers")
        measured = int(bitstring, 2)
        phase = Fraction(measured, 2 ** counting_qubits)
        approximation = phase.limit_denominator(modulus - 1)
        candidate = approximation.denominator
        verified = measured != 0 and pow(base, candidate, modulus) == 1
        period = candidate
        if verified:
            # Normalize a verified multiple by divisors only. This never searches
            # new candidate multiples or supplies an order for zero/invalid phases.
            for divisor in range(2, candidate + 1):
                while period % divisor == 0 and pow(base, period // divisor, modulus) == 1:
                    period //= divisor
            # A reduced rational with denominator larger than the true order
            # is not a consistent phase of that order. Noise must not turn an
            # arbitrary verified multiple into a claimed recovered period.
            verified = period == candidate
        factors = extract_factors(base, modulus, period) if verified else []
        if verified:
            support[period] = support.get(period, 0) + count
        outcomes.append({
            "bitstring": bitstring, "count": count, "measured_integer": measured,
            "phase": str(phase), "rational_approximation": str(approximation),
            "candidate_period": candidate if measured else None,
            "verified_period": period if verified else None,
            "verified": verified, "factors": factors,
            "reason": ("Zero phase carries no period information" if measured == 0 else
                       "Candidate fails modular or minimal-order verification; outcome is inconclusive"
                       if not verified else "Verified period yields nontrivial factors" if factors
                       else "Verified period, but gcd step yields no nontrivial factor pair"),
        })
    estimated = max(support, key=lambda r: (support[r], -r)) if support else None
    factors = extract_factors(base, modulus, estimated) if estimated else []
    return {
        "status": "success" if factors else "inconclusive",
        "estimated_period": estimated, "factors": factors,
        "verified_period_shots": sum(support.values()),
        "total_shots": sum(counts.values()), "outcomes": outcomes,
        "message": ("Nontrivial factors recovered from measured phases" if factors else
                    "No nontrivial factor pair recovered; rerun with more shots or another coprime base"),
    }
