# QuantumVault

QuantumVault is a local Streamlit research prototype combining post-quantum file
protection with a controlled quantum threat investigation. ML-KEM-768 and X25519
establish shared secrets; both file modes use HKDF-SHA256 and AES-256-GCM.
Qiskit investigates order finding for **N=15**. It does not encrypt vault files,
break real RSA or X25519, estimate production attack times or demonstrate quantum
advantage. Independent security review and production deployment verification
have not been completed.
# 

## Working application

| Page | Implemented behavior |
| --- | --- |
| Dashboard | Recorded evidence distinguished from current-session study and policy |
| Secure Vault | Both modes, protected private-key backups, expected-fingerprint matching, authenticated recovery, ciphertext-linked unsigned receipts |
| Quantum Threat Lab | Genuine controlled modular multiplication and inverse QFT, measured analysis, synthetic RSA recovery, explicit migration-policy application, repeated ideal/noisy experiments |
| Performance Lab | Preserved key-establishment benchmark and separate whole-file measurements |
| Security Report | Algorithm comparison, last checked recipient state, applied evidence, operation outcomes and limitations |

## Windows installation with Python 3 11

Run in PowerShell from the project folder. Preserve any existing working
environment; use a new environment directory when reproducing setup.

```powershell
cd C:\Users\HP\works\QuantumVault
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe environment_check.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the local address, normally http://127.0.0.1:8501/. Activation and execution
policy changes are unnecessary. If `py` is unavailable, use your installed Python
3.11 executable: `& 'C:\path\to\Python311\python.exe' -m venv .venv`.

`requirements-lock.txt` pins the complete tested dependency set; `requirements.txt`
lists direct requirements. Tested versions include Python 3.11.9, Streamlit
1.66.1, cryptography 50.0.2, pqcrypto 0.3.4, jwcrypto 1.6.1, Qiskit 2.6.1 and Aer
0.18.2. Version locking does not replace dependency review. The environment checker
reports imports, versions and a real ML-KEM agreement without displaying secrets;
`environment_check.py --json` gives machine-readable results.

## Protected backup and file recovery

1. Generate recipient keys in Secure Vault and download the public key.
2. Enter and confirm a strong backup passphrase of 12–128 characters. Prepare and
   download the protected `.private.qvkey` backup. Keep the passphrase separately.
   Export passphrase fields clear after preparation. Lost keys or forgotten
   passphrases cannot be recovered by the app.
3. A sender uploads the public key and obtains its expected SHA-256 fingerprint
   through a **separate trusted channel**. Entering a matching expectation enables
   encryption; a mismatch blocks it. A match proves equality with that expectation,
   not independent recipient identity. Copying the value from this same page is
   only a demonstration of matching. The explicit unverified-key demo override
   resets when key, algorithm, operation or source changes.
4. Upload a file, encrypt and download the package. Save any linked receipt.
5. After reloading or clearing the session, choose Decrypt, Upload a key and
   Protected key backup. Upload the backup, enter its passphrase, re-upload the
   downloaded package, decrypt and compare the recovered bytes. Repeat with
   X25519 for the classical comparison.

Plaintext limit: **20 MiB**. Package limit: **21 MiB**. Empty, text and binary files
are supported; download filenames are sanitized. Wrong keys, algorithms,
passphrases and modified authenticated data fail without recovered downloads.
Changed inputs and navigation clear stale file outputs. Clear session data drops
app-held keys/uploads/results, but cannot erase downloads or guarantee secure
memory erasure. Import passphrases can remain in the masked widget until changed,
navigation removes it or the session is cleared. Back up keys before reloading.

### Backup construction and compatibility

The backend supplies opaque ML-KEM bytes without an encrypted serialization API.
Backups use standard compact **JWE** through jwcrypto: PBES2-HS512+A256KW,
PBKDF2-HMAC-SHA512 at exactly 220000 iterations, and A256GCM. The library generates
fresh salt, IV and content key. X25519 payloads use PKCS8 DER; ML-KEM retains backend
bytes. Application headers bind version, algorithm and payload format. The JWE
format is standard; this application schema and ML-KEM serialization choice have
not had independent review.

Preflight rejects unknown versions/algorithms/headers, duplicate headers, bad
lengths, unsupported KDF cost and backups over 8192 bytes before expensive password
processing. Legacy raw-key **import** is explicit compatibility behavior; normal
raw export is removed. Existing authenticated file formats and the three original
crypto engine files are preserved. See [security model](docs/SECURITY_MODEL.md)
for library support, format rationale, resource bounds and official references.

## Controlled quantum investigation

Question: **How do circuit implementation, measurement budget and simulated noise
affect reliable period recovery and synthetic key recovery?**

The study fixes N=15, base 2, four counting and four work qubits. It compares the
original permutation-matrix controlled multipliers with equivalent controlled
bit rotations. Complete-operator tests cover supported bases 2, 4 and 8; the
explicit inverse QFT remains.

| Profile | Shots per trial | Seeds | Noise p | Variants | Trials |
| --- | --- | --- | --- | --- | ---: |
| small | 1, 32 | 41, 42 | 0, 0.01 | matrix, rotation | 16 |
| extended | 1, 8, 64 | 41–45 | 0, 0.01 | matrix, rotation | 60 |

The UI runs these bounded grids with progress and JSON export. The Python runner
supports bounded budgets with caps of 96 trials and 100000 total shots. Compilation
uses rz/sx/x/cx, seed 17, optimization level 1. CPU statevector handles ideal runs;
CPU density-matrix handles noisy runs, using one thread and a 256 MiB memory cap.
Synthetic depolarization follows rz/sx/x at p and cx at 5p. Executed gate inventory
must actually be covered by the model or the trial fails. This is not calibrated
hardware noise and includes no readout noise.

Predefined success means verified order 4, factors 3 and 5, and synthetic RSA
fixture recovery of value 7. Reference answers score results and never supply
recovery fallbacks. Invalid/nonminimal phase candidates remain inconclusive.
All planned trials, including failures, stay in denominators. Reports contain
separate period/factor/value proportions with Wilson 95% intervals, counts, seeds,
errors, versions, backend settings, width/depth/gates and separate construction,
compilation, simulation and analysis times. **A trial is a full run, not a shot.**

### Actual extended results

The [60-trial record](quantum_lab/records/study-20261101T092636Z-735f0c81.json)
finished on 1 November 2026 with zero execution failures. Each cell gives synthetic
value recovery out of five trials and its Wilson 95% interval. Period, factor and
value success coincide in this record.

| Circuit and noise p | 1 shot | 8 shots | 64 shots |
| --- | --- | --- | --- |
| Matrix ideal | 2/5 [0.118, 0.769] | 5/5 [0.566, 1.000] | 5/5 [0.566, 1.000] |
| Matrix 0.01 | 1/5 [0.036, 0.624] | 3/5 [0.231, 0.882] | 5/5 [0.566, 1.000] |
| Rotation ideal | 0/5 [0.000, 0.434] | 5/5 [0.566, 1.000] | 5/5 [0.566, 1.000] |
| Rotation 0.01 | 1/5 [0.036, 0.624] | 4/5 [0.376, 0.964] | 5/5 [0.566, 1.000] |

Both circuits use eight qubits. Under this compilation, matrix depth/CX count is
1936/489; rotation is 330/180. That is a measured circuit-size reduction. Five trials
give wide, overlapping intervals: 5/5 does not establish reliable recovery or a
general budget recommendation. Usable factor-shot fraction is not fidelity or a
cryptographic safety score.

Classical trial division of N=15 took a median approximately **0.002400 ms** over
100 calls after warm-up. That measures factoring only. Quantum rows time classical
circuit simulation, not quantum hardware; separate timing boundaries and local
machine load prevent a hardware-speedup inference. Inspect per-setting timings
in the record and [full method](docs/EXPERIMENT_METHOD.md).

### Link to useful vault decisions

The single-run lab creates an assessment from measured evidence. Applying its
recommendation explicitly selects ML-KEM under the declared post-quantum migration
policy. Known cryptographic assumptions motivate that choice; toy shot counts
do not prove ML-KEM security, attack X25519 or select AES/ML-KEM parameters.
Controlled-study statistics remain separate from this policy. Evidence IDs and
unsigned receipts link assessments, session operations and ciphertext SHA-256.
A hash links bytes; it does not authenticate a receipt's author. Receipts are not
certificates, signed audit records or sender signatures.

```powershell
.\.venv\Scripts\python.exe -m quantum_lab.experiments --profile small
.\.venv\Scripts\python.exe -m quantum_lab.experiments --profile extended
.\.venv\Scripts\python.exe -m benchmark.file_performance
```

New runs save unique files under `quantum_lab/records/` and `benchmark/records/`.
Original `quantum_lab/results.json` and `benchmark/results.json` remain unchanged.

## Actual performance measurements

The original benchmark uses 30 repetitions for key generation, sender establishment
and receiver recovery. It excludes HKDF, AES-GCM and complete packages. X25519
sender time includes ephemeral-key generation.

The separate [whole-file record](benchmark/records/files-20261101T092705Z-f9979aa4.json)
uses identical synthetic inputs, five repetitions and one warm-up. Times include
in-memory establishment, HKDF, AES-GCM and packaging/recovery, excluding recipient
key generation and disk I/O.

| Mode | Input bytes | Package bytes | Encrypt ms | Decrypt ms |
| --- | ---: | ---: | ---: | ---: |
| ML-KEM-768 | 0 | 1145 | 0.8108 | 0.2901 |
| ML-KEM-768 | 1024 | 2169 | 1.1517 | 0.3880 |
| ML-KEM-768 | 1048576 | 1049721 | 3.1302 | 2.7031 |
| X25519 | 0 | 96 | 0.3705 | 0.4189 |
| X25519 | 1024 | 1120 | 0.3634 | 0.3589 |
| X25519 | 1048576 | 1048672 | 2.8474 | 3.0851 |

Package overhead is 1145 and 96 bytes respectively. These are local observations
affected by load and versions, without a statistical performance claim.

## Architecture and testing

- `app.py`, `components/`: Streamlit pages and session state.
- `crypto_engine/pqc.py`, `encryption.py`, `classical.py`: preserved crypto engines.
- `crypto_engine/key_management.py`: bounded JWE backups and fingerprint checks.
- `quantum_lab/`: circuits, phase analysis, assessment and repeated experiments.
- `benchmark/`: original KEM and separate file measurements.
- `utils/files.py`: safe download names.
- Root `test_*.py`: real crypto/simulator tests, failure cases and Streamlit AppTest.

The starting baseline was rerun: **40 passed**. Expanded working and fresh-install
suites each passed 61 tests; the final fresh suite passed **62 tests in 69.050 seconds**,
including the added malformed-benchmark validation test.
See [verification evidence](docs/verification/README.md) and [current test log](docs/test-results.txt)
for the final count and browser checks. Coverage includes actual 20 MiB recovery
for both modes, over-limit rejection, empty/text/binary inputs, wrong credentials,
tampering, new-session backup recovery, fingerprint mismatch/change, stale output,
cleanup, equivalent circuits, real noise coverage, statistics/failure denominators,
classical baselines and applied evidence receipts.

## Team demonstration

1. Abeed introduces the problem and user journey.
2. Vismai runs the single base-2 investigation, inspects measurements and applies
   the declared migration policy.
3. Hassan saves protected recipient keys, matches an expected fingerprint,
   encrypts a synthetic file and downloads its package and unsigned receipt.
4. Hassan reloads and recovers using those saved files. Show wrong-passphrase
   rejection, then clear session data.
5. Vismai runs the small controlled study and explains trials, uncertainty and
   synthetic noise. Use the recorded extended run when time is short and label it.
6. Riya compares the two kinds of benchmark and explains outstanding limitations.

The [presentation guide](docs/QuantumVault_Team_Presentation_Guide.docx) contains
beginner explanations, speaking scripts, roles, rehearsal and judge answers.
[Independent teammate acceptance](docs/TEAM_ACCEPTANCE.md) is pending; automated
fresh installation is separate evidence.

## Threat model and missing-question review

The local host and Python process must be trusted. Keys, passwords and plaintext
reach server memory. There are no accounts, multi-user isolation, authenticated
key directory, revocation, sender signatures or hardened service deployment.
Password strength matters; lost keys/passphrases prevent recovery. Do not use
this prototype as a public sensitive-file service.

What is most important still missing? **Independent security review, authenticated
key distribution and deployment verification.** A teammate must also complete
installation and recovery independently. Additional toy factoring features do
not close those gaps. See [security model](docs/SECURITY_MODEL.md) for details.
