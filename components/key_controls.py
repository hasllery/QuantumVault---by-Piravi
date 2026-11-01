"""Protected backup and recipient verification widgets; no key bytes displayed."""
import streamlit as st

from crypto_engine.key_management import export_private_key, public_fingerprint, match_fingerprint, KeyBackupError


def invalidate_backup():
    st.session_state.pop("protected_backup", None)
    st.session_state.pop("backup_error", None)


def invalidate_recipient():
    st.session_state.pop("vault_output", None)
    st.session_state.pop("recipient_verification", None)
    st.session_state["allow_unverified"] = False


def prepare_backup():
    invalidate_backup()
    algorithm = st.session_state["vault_algorithm"]
    password = st.session_state.get("export_password", "")
    try:
        if password != st.session_state.get("export_confirmation", ""):
            raise KeyBackupError("Mismatch")
        public, private = st.session_state["recipient_keys"][algorithm]
        st.session_state["protected_backup"] = {
            "data": export_private_key(private, algorithm, password),
            "algorithm": algorithm, "fingerprint": public_fingerprint(public, algorithm),
        }
    except (KeyBackupError, KeyError, ValueError):
        st.session_state["backup_error"] = "Use matching passphrases of 12 to 128 characters."
    finally:
        st.session_state["export_password"] = ""
        st.session_state["export_confirmation"] = ""


def render_keys(algorithm, keygen):
    if st.button("Generate recipient keys", key="generate_keys"):
        invalidate_recipient()
        invalidate_backup()
        pairs = st.session_state.get("recipient_keys", {})
        pairs[algorithm] = keygen()
        st.session_state["recipient_keys"] = pairs
    pair = st.session_state.get("recipient_keys", {}).get(algorithm)
    if pair is not None:
        public, _ = pair
        st.caption(f"Public-key fingerprint (SHA-256): {public_fingerprint(public, algorithm)}")
        st.download_button("Download public key", public, file_name=f"{algorithm.lower()}.public.key",
                           mime="application/octet-stream", key="download_public", on_click="ignore")
        st.text_input("Backup passphrase", type="password", max_chars=128, key="export_password", on_change=invalidate_backup)
        st.text_input("Confirm backup passphrase", type="password", max_chars=128, key="export_confirmation", on_change=invalidate_backup)
        st.button("Prepare protected private key", key="prepare_backup", on_click=prepare_backup)
        if st.session_state.get("backup_error"):
            st.error(st.session_state["backup_error"])
        backup = st.session_state.get("protected_backup")
        if backup and backup["algorithm"] == algorithm and backup["fingerprint"] == public_fingerprint(public, algorithm):
            st.download_button("Download protected private key", backup["data"],
                               file_name=f"{algorithm.lower()}.private.qvkey", mime="application/octet-stream",
                               key="download_private", on_click="ignore")
        st.info("Save the public key and protected private key; keep the passphrase separately. "
                "Reloading may lose session keys. Lost keys or forgotten passphrases cannot be recovered by this app.")
    return pair


def recipient_check(public, algorithm, invalidate_output):
    try:
        fingerprint = public_fingerprint(public, algorithm)
    except ValueError:
        st.session_state.pop("recipient_verification", None)
        st.error("Public key format or length is invalid for this algorithm.")
        return False
    st.caption(f"Recipient fingerprint (SHA-256): {fingerprint}")
    expected = st.text_input("Expected fingerprint from a trusted separate channel", key="expected_fingerprint",
                             on_change=invalidate_output)
    status, accepted = "Unverified", False
    if expected.strip():
        try:
            accepted = match_fingerprint(public, algorithm, expected)
        except ValueError:
            accepted = False
        if accepted:
            status = "Matched supplied fingerprint"
            st.success("Fingerprint matches your supplied expectation.")
        else:
            status = "Mismatch"
            st.error("Fingerprint mismatch or invalid expectation. Encryption is blocked.")
    else:
        st.warning("Recipient key is unverified. Obtain its fingerprint through a trusted separate channel.")
        accepted = st.checkbox("Continue with an unverified recipient key for this demonstration", key="allow_unverified",
                               on_change=invalidate_output)
    st.caption("A match confirms equality with your supplied expectation. Displaying or copying this fingerprint "
               "here does not independently verify identity.")
    st.session_state["recipient_verification"] = {"algorithm": algorithm, "fingerprint": fingerprint, "status": status}
    return accepted
