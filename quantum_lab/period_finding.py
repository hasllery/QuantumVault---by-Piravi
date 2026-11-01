"""Genuine phase-estimation circuit for order finding modulo 15 on Aer."""
import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from math import pi
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit_aer import AerSimulator

from quantum_lab.analysis import analyze_counts, validate_experiment


def modular_multiplication_gate(multiplier, modulus=15):
    """Map |x> to |multiplier*x mod 15> for x<15, leaving |15> fixed.

    The matrix is built from the complete reversible permutation, without
    supplying an order or orbit. Dense synthesis is suitable only for this toy.
    Qubit 0 is the least significant work-register bit.
    """
    if modulus != 15 or type(multiplier) is not int or multiplier not in (1, 2, 4, 7, 8, 11, 13, 14):
        raise ValueError("Multiplier must be a unit modulo 15")
    matrix = np.zeros((16, 16), dtype=complex)
    for value in range(16):
        target = multiplier * value % modulus if value < modulus else value
        matrix[target, value] = 1
    return UnitaryGate(matrix, label=f"x{multiplier} mod 15")


def inverse_qft(num_qubits):
    """Explicit inverse QFT with bit-reversal swaps and negative phases."""
    if type(num_qubits) is not int or not 1 <= num_qubits <= 8:
        raise ValueError("inverse QFT supports 1 to 8 qubits")
    circuit = QuantumCircuit(num_qubits, name="inverse QFT")
    for qubit in range(num_qubits // 2):
        circuit.swap(qubit, num_qubits - qubit - 1)
    for target in range(num_qubits):
        for control in range(target):
            circuit.cp(-pi / (2 ** (target - control)), control, target)
        circuit.h(target)
    return circuit


def build_period_finding_circuit(base=2, modulus=15, counting_qubits=8):
    """Prepare |+> counting register, work |1>, controlled powers, inverse QFT."""
    validate_experiment(base, modulus, counting_qubits)
    counting = QuantumRegister(counting_qubits, "phase")
    work = QuantumRegister(4, "work")
    measured = ClassicalRegister(counting_qubits, "measured")
    circuit = QuantumCircuit(counting, work, measured, name="order finding N=15")
    circuit.h(counting)
    circuit.x(work[0])
    for index in range(counting_qubits):
        multiplier = pow(base, 2 ** index, modulus)
        # Identity powers need no operation; this uses modular exponentiation,
        # not a hard-coded period or a hard-coded measurement distribution.
        if multiplier != 1:
            controlled = modular_multiplication_gate(multiplier, modulus).control(1)
            circuit.append(controlled, [counting[index], *work])
    circuit.compose(inverse_qft(counting_qubits), qubits=counting, inplace=True)
    circuit.measure(counting, measured)
    return circuit


def run_period_finding(base=2, modulus=15, counting_qubits=8, shots=1024, seed=42):
    """Execute Aer and return JSON-ready circuit, counts, configuration and analysis."""
    if type(shots) is not int or not 1 <= shots <= 100_000:
        raise ValueError("shots must be an integer from 1 to 100000")
    if seed is not None and (type(seed) is not int or not 0 <= seed < 2 ** 32):
        raise ValueError("seed must be None or a 32-bit unsigned integer")
    circuit = build_period_finding_circuit(base, modulus, counting_qubits)
    simulator = AerSimulator(method="statevector", device="CPU", max_parallel_threads=1)
    compiled = transpile(circuit, simulator, seed_transpiler=seed, optimization_level=1)
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    if not result.success:
        raise RuntimeError(f"Aer experiment failed: {result.status}")
    counts = {str(bits): int(count) for bits, count in result.get_counts().items()}
    if sum(counts.values()) != shots:
        raise RuntimeError("Aer returned an unexpected number of measurements")
    return {
        "configuration": {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "base": base, "modulus": modulus, "counting_qubits": counting_qubits,
            "work_qubits": 4, "shots": shots, "seed_simulator": seed,
            "seed_transpiler": seed, "backend": simulator.name,
            "method": "statevector", "device": "CPU", "noise_model": "none (ideal)",
            "max_parallel_threads": 1, "optimization_level": 1,
            "qiskit_version": version("qiskit"), "aer_version": version("qiskit-aer"),
            "python_version": platform.python_version(),
        },
        "circuit": str(circuit.draw(output="text", fold=120)),
        "inverse_qft_circuit": str(inverse_qft(counting_qubits).draw(output="text", fold=120)),
        "compiled_depth": compiled.depth(), "compiled_operations": dict(compiled.count_ops()),
        "counts": dict(sorted(counts.items())),
        "analysis": analyze_counts(counts, base, modulus, counting_qubits),
    }


def main():
    # Windows terminals may default to cp1252, which cannot print circuit lines.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=int, default=2)
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, help="Optional JSON output file")
    args = parser.parse_args()
    result = run_period_finding(base=args.base, shots=args.shots, seed=args.seed)
    print(result["circuit"])
    print("\nExplicit inverse QFT:\n", result["inverse_qft_circuit"])
    summary = {key: value for key, value in result.items() if key not in ("circuit", "inverse_qft_circuit")}
    print(json.dumps(summary, indent=2))
    print("Toy ideal simulation of factoring 15; not a real-world RSA or X25519 break.")
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
