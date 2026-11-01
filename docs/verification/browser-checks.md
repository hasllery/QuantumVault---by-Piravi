# Live browser checks on 1 November 2026

Application: fresh locked environment on localhost port 8502. Browser: in-app
browser. Only a synthetic 38-byte fixture and test-only passphrases were used.
Downloaded files were uploaded back through the application's file chooser.

| Workflow | Observed result |
| --- | --- |
| ML-KEM recipient generation | Public fingerprint and public-key download available |
| ML-KEM protected backup | Download succeeded; export fields cleared |
| Wrong expected fingerprint | Explicit mismatch error; encryption disabled |
| Matching expected fingerprint | Match status; encryption enabled after file upload |
| ML-KEM encrypt/download/reload | Encryption succeeded; reload lost generated session keys |
| ML-KEM downloaded backup/package import | Authentication passed; recovered bytes equal original fixture |
| Changed import passphrase | Prior recovered download removed after committing field |
| Wrong passphrase | Generic rejection; no recovered download |
| X25519 protected backup | Download succeeded; export fields cleared |
| X25519 matching fingerprint and encryption | Match displayed; package downloaded |
| X25519 downloaded backup/package import | Authentication passed; recovered bytes equal original fixture |
| X25519 ciphertext modified by one byte | Generic rejection; recovered download removed |
| Clear session data | Key exports, passphrase widgets, uploaded names and result removed; Encrypt disabled |

Expected fingerprints were copied from the generated keys for this local demo.
This tests matching behavior, **not independent identity authentication**.
The UI explains that a real expectation must come through a trusted channel.

The browser controller needed visible controls and Enter to commit some fields.
Attempted clicks without a subsequent state change were not counted as successful
checks. AppTest separately covers both modes in new sessions, wrong keys and
algorithms, actual 20 MiB boundaries, changed-key invalidation and receipts.

Recovery screenshot: ../protected-recovery.jpg. Bytes were compared without
printing contents. No private bytes or passphrases are included here. Synthetic
downloads remain in the browser's download location; session clearing does not
remove downloaded files.
