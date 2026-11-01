import pandas as pd
import streamlit as st

from components.data import DATA_ERRORS, load_benchmark
from components.assessment_view import render_assessment


def render():
    st.caption("QUANTUMVAULT / SECURITY REPORT")
    st.title("Evidence, assumptions and limits.")
    st.subheader("Algorithm comparison", divider="violet")
    st.table(pd.DataFrame([
        {"Property": "Key establishment", "ML-KEM-768": "Lattice-based KEM", "X25519": "Elliptic-curve key agreement"},
        {"Property": "Quantum role", "ML-KEM-768": "Post-quantum design", "X25519": "Classical baseline"},
        {"Property": "File encryption", "ML-KEM-768": "AES-256-GCM", "X25519": "AES-256-GCM"},
        {"Property": "Key derivation", "ML-KEM-768": "HKDF-SHA256", "X25519": "HKDF-SHA256"},
    ]).set_index("Property"))
    try:
        benchmark = load_benchmark()
        st.caption("Sizes below come from the saved benchmark's measured backend outputs, in bytes.")
        st.dataframe(pd.DataFrame({name: data["sizes_bytes"]
                                  for name, data in benchmark["algorithms"].items()}), width="stretch")
    except DATA_ERRORS:
        st.warning("Saved measured sizes are unavailable.")
    latest = st.session_state.get("threat_assessment")
    applied = st.session_state.get("applied_assessment")
    if latest:
        render_assessment(latest)
    else:
        st.info("No current-session quantum investigation. Run Quantum Threat Lab to create measured evidence.")
    if applied:
        st.caption(f"Vault policy applied at {applied['applied_at_utc']} from evidence {applied['assessment_id']}. "
                   "A later inconclusive run does not reverse that prior user choice.")
    verification = st.session_state.get("recipient_verification")
    if verification:
        st.caption(f"Last checked recipient: {verification['status']} · {verification['algorithm']} · {verification['fingerprint']}")
    st.subheader("This session's file checks", divider="violet")
    events = st.session_state.get("vault_events", [])
    if events:
        st.dataframe(pd.DataFrame(events), hide_index=True, width="stretch")
    else:
        st.info("No file operations have been checked in this session. Use Secure Vault to begin.")
    st.caption("Last 20 operations only. Authenticated means AES-GCM verification passed. "
               "Rejected may mean a wrong key, wrong algorithm, malformed package or tampering; "
               "it does not identify which. This is a session summary, not a persistent audit log.")
    st.subheader("Know the boundaries", divider="violet")
    st.markdown("""- **Authenticate public keys.** An attacker can substitute an unverified recipient key.
- **Protect private keys.** Default exports are passphrase-protected JWE backups. Legacy raw import is explicit. Lost keys or forgotten passphrases cannot be recovered by the app. The backup profile still needs independent review.
- **Sender identity is not verified.** Successful decryption authenticates the package, not the person who sent it.
- **Run locally.** Uploaded bytes reach the local Python server. This prototype has no user accounts or deployment hardening.
- **Memory processing.** Plaintext is limited to 20 MiB; clear session data when finished. Clearing is not guaranteed secure memory erasure.
- **Quantum investigation scope.** Measured factors drive recovery of a synthetic textbook RSA value. Factoring 15 does not break production RSA or X25519.
- **Measured performance has a scope.** Key-establishment and in-memory whole-file results are separate; neither measures deployment or disk throughput.
- **Independent review remains outstanding.** This is a research prototype, not audited production security software.""")
    st.subheader("Migration direction", divider="violet")
    st.write("Use the vault to compare X25519 and ML-KEM-768 while retaining the same "
             "HKDF-SHA256 and AES-256-GCM file protection. Real deployments also need authenticated "
             "key distribution, protected key storage, protocol review and operational controls.")
    st.markdown("[ML-KEM standard: NIST FIPS 203](https://csrc.nist.gov/pubs/fips/203/final)")
