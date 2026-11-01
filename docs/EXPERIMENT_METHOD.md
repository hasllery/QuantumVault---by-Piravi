# Controlled quantum investigation method

## Research question and fixed scope

How do circuit implementation, measurement budget and simulated noise affect
reliable period recovery and synthetic key recovery? The study supports N=15,
base 2, four counting qubits and four work qubits. It does not silently extend
the dense-unitary method to larger moduli or attack production cryptography.

Two circuits implement the same modular arithmetic: the existing full permutation
matrix controlled multipliers and an explicit bit-rotation construction using
controlled SWAP-based multipliers. The rotation form supports bases 2, 4 and 8;
the comparative study fixes base 2. Both fix |0> and |15>. Tests compare complete
controlled-multiplier matrices and whole measurement-free circuit operators,
including bases with different orders. The inverse QFT is retained unchanged.

## Experimental grid fixed before execution

| Profile | Shots per trial | Measurement seeds | One-qubit noise p | Circuit variants | Trials |
| --- | --- | --- | --- | --- | ---: |
| small | 1 and 32 | 41 and 42 | 0 and 0.01 | matrix and rotation | 16 |
| extended | 1, 8 and 64 | 41 to 45 | 0 and 0.01 | matrix and rotation | 60 |

These are pilot samples with intentionally small budgets, not large statistical
studies. Distinct measurement seeds give repeated sampling trials. Transpilation
seed 17 and optimization level 1 are fixed to isolate sampling from compiler
randomness. The runner rejects workloads exceeding 96 trials or 100000 total
shots. No input file, recipient key or vault data is used.

## Execution and noise coverage

Both implementations are transpiled into `rz`, `sx`, `x`, `cx`. Ideal execution
uses CPU statevector simulation. Noisy execution uses a CPU density-matrix
simulation with a synthetic depolarizing channel after every rz/sx/x at p and
every cx at 5p. Simulations use one thread and a 256 MiB simulator memory cap.
Virtual rz errors are a deliberate synthetic model choice, not a realistic
device characterization. There is no readout noise or hardware calibration.

The executed instruction inventory must contain only the declared basis,
measurement and optional barriers. The model's actual `noise_instructions` must
cover executed unitary gates, including cx. Otherwise the trial fails. Each trial
records its affected gate inventory and total count. A model object alone is not
accepted as proof that noise acted. Tests also compare actual ideal and noisy
measurement distributions for a fixed seed and verify nonzero coverage.

See [Qiskit Aer noise construction](https://qiskit.github.io/qiskit-aer/tutorials/3_building_noise_models.html).

## Success criteria and denominators

Each trial is one full execution at its specified shot budget. Period success
means the result equals the known reference order 4. Factor success means a
verified pair 3 and 5 is recovered. Synthetic RSA recovery succeeds only when
those measured factors recover public fixture value 7 from wrapped value 13.
Known reference values are used for scoring only; they are not injected into
circuit inputs, measurement counts or recovery fallbacks.

Post-processing computes a bounded rational approximation to each measured phase
and validates modular exponentiation. It additionally rejects a nonminimal order
multiple, since a reduced phase with that larger denominator is inconsistent with
the minimal order. Zero phases and reduced denominators that fail validation stay
inconclusive. Divisor checks validate an observed candidate; no candidate-multiple
search or known-factor fallback supplies missing quantum evidence.

All planned trials stay in setting-specific denominators. Compilation/simulation
errors count as failed trials and as unsuccessful recoveries; completed trials
without factors count as inconclusive. The report gives separate period, factor
and toy-recovery counts/proportions and 95% Wilson binomial intervals per setting.
Shots are not counted as independent trials. The interval is conditional on the
fixed synthetic setting and does not include model uncertainty; there is no
multiple-comparison adjustment. Two or five trials give wide uncertainty and
cannot establish a reliable measurement-budget recommendation.

The usable factor-shot fraction describes counts whose phases pass classical
validation and yield factors. It is not quantum-state fidelity, a cryptographic
confidence score or an attack probability against real keys. Zero-shot postselection
and dropping failed runs are not performed. Inspect raw counts and errors.

## Timings and classical comparison

Construction, compilation, simulation and classical analysis are timed separately
using a monotonic high-resolution clock. Reports retain width, depth, gate counts,
all seeds, versions, platform, timestamps and backend method. Timing includes
Python/backend overhead and system load and is observational, not a controlled
hardware benchmark.

Classical trial division factors the same tiny N=15. Its median over 100 calls
after warm-up measures factoring only. Quantum execution timings describe
classical simulation of a quantum circuit, not quantum processor wall time.
Timing boundaries are intentionally reported separately; no advantage is inferred
from this comparison. Classical factoring is expected to be preferable at this size.

## Relationship to application decisions

The single-run threat assessment and its explicit vault migration button remain
separate from this controlled study. A declared post-quantum requirement still
selects ML-KEM based on known assumptions, not observed shot frequencies.
Study gate counts and recovery statistics can guide the next experimental
circuit/budget comparison, with the small-sample caveat. They never choose AES
or ML-KEM security parameters, estimate production attack times, prove ML-KEM
security or establish quantum advantage. There is no direct X25519 attack.

## Reproduction and saved records

```powershell
.\.venv\Scripts\python.exe -m quantum_lab.experiments --profile small
.\.venv\Scripts\python.exe -m quantum_lab.experiments --profile extended
```

The Streamlit Quantum Threat Lab exposes the same runner with progress and JSON
export. Each completed study is written to a unique `quantum_lab/records/study-*.json`
using exclusive creation; earlier runs are not overwritten. Failed trials remain
in the report. CLI and UI records may have different timings even with identical
seeds. Original `quantum_lab/results.json` and the original KEM benchmark remain
unchanged. Whole-file benchmarks use separate `benchmark/records/files-*.json`.
