"""Bounded, repeated ideal/noisy N=15 investigation with explicit denominators."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from itertools import product
import json
from math import isqrt, sqrt
from pathlib import Path
import platform
from statistics import median
from time import perf_counter
from uuid import uuid4

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from quantum_lab.analysis import analyze_counts
from quantum_lab.period_finding import build_period_finding_circuit, inverse_qft
from quantum_lab.threat_assessment import recover_toy_rsa_value

BASIS = ["rz", "sx", "x", "cx"]
ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "small": {"shots": [1, 32], "seeds": [41, 42], "noise_rates": [0.0, 0.01]},
    "extended": {"shots": [1, 8, 64], "seeds": [41, 42, 43, 44, 45], "noise_rates": [0.0, 0.01]},
}


def rotation_multiplier(multiplier):
    """Bit rotation implements multiplication by 2, 4 or 8 modulo 15.

    Both |0> and |15> are fixed. No measured period or expected counts are used.
    """
    if multiplier not in (1, 2, 4, 8):
        raise ValueError("Rotation multiplier supports 1, 2, 4, 8 only")
    circuit = QuantumCircuit(4, name=f"rotate x{multiplier} mod 15")
    for _ in range({1: 0, 2: 1, 4: 2, 8: 3}[multiplier]):
        for left, right in ((2, 3), (1, 2), (0, 1)):
            circuit.swap(left, right)
    return circuit.to_gate()


def build_rotation_circuit(base=2, counting_qubits=4):
    if base not in (2, 4, 8) or type(counting_qubits) is not int or not 2 <= counting_qubits <= 4:
        raise ValueError("Rotation experiment supports bases 2, 4, 8 and 2 to 4 counting qubits")
    phase, work = QuantumRegister(counting_qubits, "phase"), QuantumRegister(4, "work")
    measured = ClassicalRegister(counting_qubits, "measured")
    circuit = QuantumCircuit(phase, work, measured)
    circuit.h(phase)
    circuit.x(work[0])
    for index in range(counting_qubits):
        multiplier = pow(base, 2 ** index, 15)
        if multiplier != 1:
            circuit.append(rotation_multiplier(multiplier).control(1), [phase[index], *work])
    circuit.compose(inverse_qft(counting_qubits), qubits=phase, inplace=True)
    circuit.measure(phase, measured)
    return circuit


def noise_model(rate):
    if type(rate) not in (int, float) or not 0 <= rate <= 0.03:
        raise ValueError("Synthetic one-qubit depolarizing rate must be between 0 and 0.03")
    model = NoiseModel()
    if rate:
        model.add_all_qubit_quantum_error(depolarizing_error(rate, 1), ["rz", "sx", "x"])
        model.add_all_qubit_quantum_error(depolarizing_error(5 * rate, 2), ["cx"])
    return model


def noise_coverage(operations, model, rate):
    """Check the executed basis and the actual model's instruction coverage."""
    unknown = set(operations) - set(BASIS) - {"measure", "barrier"}
    if unknown:
        raise ValueError("Circuit was not fully decomposed to the declared noisy basis")
    attached = set(model.noise_instructions)
    affected = {gate: int(count) for gate, count in operations.items() if gate in attached}
    if rate and (not affected or "cx" not in affected or set(operations).intersection(BASIS) - attached):
        raise ValueError("Noise does not cover the executed unitary gate basis")
    return {"attached_instructions": sorted(attached), "affected_operations": affected,
            "affected_gate_count": sum(affected.values()), "verified": bool(affected) if rate else not attached}


def wilson(successes, trials):
    if type(trials) is not int or type(successes) is not int or trials < 1 or not 0 <= successes <= trials:
        raise ValueError("Invalid success denominator")
    z, n = 1.959963984540054, trials
    proportion = successes / n
    denominator = 1 + z * z / n
    center = (proportion + z * z / (2 * n)) / denominator
    half = z * sqrt(proportion * (1 - proportion) / n + z * z / (4 * n * n)) / denominator
    return {"successes": successes, "trials": trials, "proportion": proportion,
            "wilson_95_low": max(0.0, center - half), "wilson_95_high": min(1.0, center + half)}


def classical_factors(modulus=15):
    if type(modulus) is not int or modulus != 15:
        raise ValueError("This comparison supports N=15 only")
    for divisor in range(2, isqrt(modulus) + 1):
        if modulus % divisor == 0:
            return [divisor, modulus // divisor]
    return []


def classical_baseline(repetitions=100):
    classical_factors()
    durations = []
    for _ in range(repetitions):
        start = perf_counter()
        factors = classical_factors()
        durations.append((perf_counter() - start) * 1000)
    return {"algorithm": "trial division", "modulus": 15, "factors": factors,
            "repetitions": repetitions, "median_ms": median(durations),
            "scope": "classical factoring only; quantum rows time circuit construction, compilation, simulation and analysis separately"}


def run_trial(implementation, shots, seed, rate):
    """One independent measurement trial, N=15, base=2, 4 counting qubits."""
    if implementation not in ("matrix", "rotation"):
        raise ValueError("Unsupported circuit implementation")
    if type(shots) is not int or not 1 <= shots <= 2048 or type(seed) is not int or not 0 <= seed < 2 ** 32:
        raise ValueError("Invalid shot budget or seed")
    model = noise_model(rate)
    start = perf_counter()
    circuit = (build_period_finding_circuit(counting_qubits=4) if implementation == "matrix"
               else build_rotation_circuit())
    construction_ms = (perf_counter() - start) * 1000
    method = "density_matrix" if rate else "statevector"
    simulator = AerSimulator(method=method, device="CPU", noise_model=model,
                             max_parallel_threads=1, max_memory_mb=256)
    start = perf_counter()
    compiled = transpile(circuit, basis_gates=BASIS, seed_transpiler=17, optimization_level=1)
    compilation_ms = (perf_counter() - start) * 1000
    operations = dict(compiled.count_ops())
    coverage = noise_coverage(operations, model, rate)
    start = perf_counter()
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    simulation_ms = (perf_counter() - start) * 1000
    if not result.success:
        raise RuntimeError("Simulator failed")
    counts = {str(key): int(value) for key, value in result.get_counts().items()}
    if sum(counts.values()) != shots:
        raise RuntimeError("Measurement count mismatch")
    start = perf_counter()
    analysis = analyze_counts(counts, counting_qubits=4)
    recovery = recover_toy_rsa_value(analysis["factors"])
    analysis_ms = (perf_counter() - start) * 1000
    useful = sum(outcome["count"] for outcome in analysis["outcomes"] if outcome["factors"])
    return {"implementation": implementation, "shots": shots, "seed": seed, "noise_rate": rate,
            "status": "completed", "period_recovered": analysis["estimated_period"] == 4,
            "factors_recovered": analysis["factors"] == [3, 5],
            "toy_recovered": recovery["recovery_verified"], "counts": counts,
            "analysis": analysis, "usable_factor_shots": useful,
            "width": compiled.num_qubits, "depth": compiled.depth(), "operations": operations,
            "noise_coverage": coverage, "method": method,
            "construction_ms": construction_ms, "compilation_ms": compilation_ms,
            "simulation_ms": simulation_ms, "analysis_ms": analysis_ms}


def summarize(rows):
    """Every planned trial remains in the success denominator, including errors."""
    grouped = {}
    for row in rows:
        key = (row["implementation"], row["noise_rate"], row["shots"])
        grouped.setdefault(key, []).append(row)
    summaries = []
    for (implementation, rate, shots), group in sorted(grouped.items()):
        complete = [row for row in group if row["status"] == "completed"]
        item = {"implementation": implementation, "noise_rate": rate, "shots": shots,
                "planned_trials": len(group), "failed_trials": len(group) - len(complete),
                "inconclusive_trials": sum(not row["factors_recovered"] for row in complete)}
        for metric in ("period_recovered", "factors_recovered", "toy_recovered"):
            item[metric] = wilson(sum(bool(row.get(metric, False)) for row in group), len(group))
        if complete:
            for timing in ("construction_ms", "compilation_ms", "simulation_ms", "analysis_ms"):
                item["median_" + timing] = median(row[timing] for row in complete)
            item["executed_shots"] = sum(row["shots"] for row in complete)
            item["usable_factor_shot_fraction"] = sum(row["usable_factor_shots"] for row in complete) / item["executed_shots"]
            item["depth"] = complete[0]["depth"]
            item["cx_gates"] = complete[0]["operations"].get("cx", 0)
        summaries.append(item)
    return summaries


def run_study(profile="small", progress=None):
    if profile not in PROFILES:
        raise ValueError("Choose small or extended profile")
    grid = PROFILES[profile]
    settings = list(product(("matrix", "rotation"), grid["noise_rates"], grid["shots"], grid["seeds"]))
    if len(settings) > 96 or sum(setting[2] for setting in settings) > 100_000:
        raise ValueError("Experiment workload exceeds local limits")
    rows = []
    started = datetime.now(timezone.utc).isoformat()
    for index, (implementation, rate, shots, seed) in enumerate(settings):
        try:
            row = run_trial(implementation, shots, seed, rate)
        except Exception:
            row = {"implementation": implementation, "noise_rate": rate, "shots": shots, "seed": seed,
                   "status": "failed", "error": "Circuit compilation, simulation or analysis failed"}
        rows.append(row)
        if progress:
            progress(index + 1, len(settings))
    metadata = {"schema_version": 1, "started_at_utc": started,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(), "profile": profile,
                "modulus": 15, "base": 2, "counting_qubits": 4, "work_qubits": 4,
                "grid": grid, "planned_trials": len(settings), "basis_gates": BASIS,
                "optimization_level": 1, "seed_transpiler": 17, "max_parallel_threads": 1,
                "noise": "Synthetic depolarizing after rz/sx/x at p and cx at 5p; not device calibrated; no readout noise",
                "criteria": "Period equals 4, verified factors equal 3 and 5, synthetic RSA recovery equals 7; no known-answer fallback",
                "reference": "Order 4 and factors 3,5 are classical evaluation ground truth, never circuit inputs or recovery fallbacks",
                "denominator": "All planned independent-seed trials per setting, including failures; shots are not trials",
                "interval": "95 percent Wilson binomial interval per setting; small sample, no multiple-comparison adjustment",
                "versions": {name: version(name) for name in ("qiskit", "qiskit-aer", "numpy")},
                "python": platform.python_version(), "platform": platform.platform()}
    report = {"metadata": metadata, "trials": rows, "summary": summarize(rows),
              "classical_baseline": classical_baseline(),
              "interpretation": "Pilot measurements, not quantum advantage or production threat estimates. Few trials cannot establish a reliable budget; gate counts can inform the next experiment, not cryptographic parameters."}
    report["evidence_id"] = sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    return report


def save_study(report):
    directory = ROOT / "quantum_lab" / "records"
    directory.mkdir(exist_ok=True)
    path = directory / (datetime.now(timezone.utc).strftime("study-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8] + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="small")
    args = parser.parse_args()
    report = run_study(args.profile, lambda n, total: print(f"Completed trial {n}/{total}", flush=True))
    print("Saved:", save_study(report))
    print(json.dumps(report["summary"], indent=2))
