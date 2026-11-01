# QuantumVault security model

QuantumVault is a local research prototype. It provides authenticated file
protection and investigation tooling, with the following explicit boundaries.
Independent security review has not been performed.

## Trust boundary

The user trusts this computer, its operating system, Python server, dependencies
and application code. The server binds to 127.0.0.1. Files, private keys and
passphrases are processed in that local server's memory, not only in the browser.
There are no user accounts, multi-user authorization, remote deployment controls
or claims of resistance to a compromised host. Do not expose this server publicly.

An attacker may replace a recipient public key, alter a ciphertext or key backup,
guess a weak backup passphrase offline, rename files, or alter an unsigned receipt.
The prototype does not prevent endpoint compromise, malicious extensions,
screen capture, coerced disclosure, denial of service or loss of keys.

## File protection

ML-KEM-768 and X25519 remain the original byte-based library workflows. Both use
HKDF-SHA256 and AES-256-GCM with fresh salt and nonce. Their version-1 package
headers remain authenticated. Existing binary formats have not been replaced.
Correct authentication is required before recovered bytes are offered for download.
This verifies the package under the key, not the sender's identity.

Plaintext is limited to 20 MiB and packages to 21 MiB by the application. Data is
not streamed; multiple in-memory copies may exist. Download names are sanitized
for path separators, control characters, Windows reserved names and length. Names
are not included inside the authenticated format; renaming does not authenticate
or alter file contents. X25519 is an educational ephemeral-static baseline, not a
claim of standardized HPKE interoperability.

## Protected private key backups

Default export is compact JWE through JWCrypto 1.6.1, using the registered
`PBES2-HS512+A256KW` key-management algorithm and `A256GCM` content encryption.
JWE is defined in [RFC 7516](https://www.rfc-editor.org/rfc/rfc7516.html), and these
algorithms in [RFC 7518](https://www.rfc-editor.org/rfc/rfc7518.html#section-4.8).
The library handles PBKDF2, random content keys, AES key wrap and GCM; the app does
not implement these primitives.

The application profile uses a random 16-byte PBES2 salt, exactly 220000 PBKDF2
HMAC-SHA512 iterations, a random 12-byte GCM IV and a 16-byte tag. The work factor
is informed by the [OWASP password-storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#pbkdf2),
not a certification or a guarantee against weak passphrases. Export/import accepts
12 to 128 characters. Longer memorable passphrases are preferable to predictable
test values. Keep them separately from the backup.

X25519 is serialized as standard PKCS8 DER *inside* the authenticated JWE. The
installed pqcrypto backend exposes opaque ML-KEM byte keys without a PKCS8
serialization API, so those bytes are the encrypted payload. A common standard
JWE container keeps authenticated password protection consistent between the two
algorithms; app-specific protected headers identify version, algorithm and inner
format. This application profile has not had independent protocol review.

Preflight validation occurs before password derivation. It rejects tokens over
8192 bytes, non-compact forms, headers over the allowed bound, duplicate or
unexpected header names, compression, unsupported versions/algorithms/formats,
non-integer or changed iteration settings and incorrect salt/key/IV/cipher/tag
lengths. The profile permits no attacker-chosen KDF work factor. The library's
global maximum iteration setting is raised to this fixed value because its default
cap is lower; application parsing still accepts **exactly** 220000 iterations.
Only the two declared JWE algorithms are allowed. X25519 DER is length-bounded
and checked for the expected key type after authenticated decryption.

Raw export is absent from the default interface. Earlier raw private keys can
still be imported only after explicitly selecting **Legacy raw key**. That mode
does not make legacy files encrypted. Wrong passphrases, changed containers and
wrong algorithms produce generic failures with no recovered file. Export input
passphrases are cleared after preparation; import passphrases remain in the
masked session widget until changed, navigation cleanup or Clear session data.

## Recipient fingerprint verification

SHA-256 fingerprints are computed from the actual public-key bytes used for
encryption. The expected fingerprint must come through a separate trusted channel,
such as an in-person exchange or an already-authenticated organizational channel.
The app accepts case/colon/whitespace variants of a 64-digit hex fingerprint.

A mismatch or malformed expectation blocks encryption. Without an expectation,
the key is labeled unverified and an explicit demonstration override is required.
Changing the key, algorithm, operation or key source invalidates that override.
Comparison is recomputed against the live key, not a remembered “verified” flag.
Operation records capture the verification status and public fingerprint.

Displaying a fingerprint, copying it from this same page, or clicking the override
does not prove identity. A match is meaningful only if the expectation is trustworthy.
The app has no certificate authority, directory, authenticated key-delivery service,
sender signatures, revocation protocol or organizational identity system.

## Data retention and evidence

The app does not automatically write user keys, passwords or plaintext to disk.
Streamlit keeps uploaded and downloadable data in session/server memory. Clear
session data drops app-held data but is not guaranteed secure memory erasure and
does not delete downloads. Keep a protected backup before reloading; there is no
key or passphrase recovery service. No secrets or plaintext previews are printed
in reporting views. Error messages avoid raw backend diagnostics.

Controlled-study and synthetic file-benchmark records are public experiment data
and are saved under unique filenames. They contain no uploaded files or private
keys. Assessment JSON and receipts contain configuration, results, algorithm
choices, public fingerprints and ciphertext hashes. Receipts are unsigned; a hash
matches a package to a record but does not authenticate the record's author.

## Review still required

Independent protocol review, package/dependency security review, protected host
operation, deployment hardening, multi-user isolation testing, authenticated key
distribution and operational incident/recovery procedures remain external work.
The automated checks and this self-review do not substitute for those activities.
