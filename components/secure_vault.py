"""Session-scoped UI; file protection delegates to the existing crypto engines."""
from hashlib import sha256
import json

import streamlit as st
from cryptography.exceptions import InvalidTag

from crypto_engine.pqc import generate_pqc_keys
from crypto_engine.encryption import encrypt_pqc_file, decrypt_pqc_file
from crypto_engine.classical import generate_classical_keys, encrypt_classical_file, decrypt_classical_file
from crypto_engine.key_management import import_private_key
from components.key_controls import render_keys, recipient_check, invalidate_recipient, invalidate_backup
from utils.files import safe_name

ALGORITHMS = {
    "ML-KEM-768": (generate_pqc_keys, encrypt_pqc_file, decrypt_pqc_file),
    "X25519": (generate_classical_keys, encrypt_classical_file, decrypt_classical_file),
}
MAX_PLAINTEXT = 20 * 1024 * 1024
MAX_PACKAGE = 21 * 1024 * 1024


def invalidate_output():
    st.session_state.pop("vault_output", None)


def remember_algorithm():
    invalidate_recipient()
    invalidate_backup()
    st.session_state["vault_selection"] = st.session_state["vault_algorithm"]


def record_event(algorithm, action, result, package_digest=None):
    events = st.session_state.get("vault_events", [])
    event = {
        "Algorithm": algorithm, "Operation": action, "Result": result,
    }
    assessment = st.session_state.get("applied_assessment")
    if assessment:
        event["Assessment"] = assessment["assessment_id"]
        event["Decision"] = ("Recommendation applied" if algorithm == "ML-KEM-768" else "Manual classical comparison")
    if package_digest:
        event["Package SHA-256"] = package_digest
    if action == "Encrypt":
        verification = st.session_state.get("recipient_verification", {})
        event["Recipient verification"] = verification.get("status", "Unverified")
        if verification.get("fingerprint"):
            event["Recipient fingerprint"] = verification["fingerprint"]
    st.session_state["vault_events"] = (events + [event])[-20:]
    return event


def render():
    st.caption("QUANTUMVAULT / SECURE VAULT")
    st.title("A file. A recipient. A protected package.")
    st.write("Generate a recipient key pair or upload an existing key. "
             "Share the public key with senders; keep the private key separate.")
    epoch = st.session_state.get("upload_epoch", 0)
    preferred = st.session_state.get("vault_selection", "ML-KEM-768")
    algorithm = st.radio("Key establishment", tuple(ALGORITHMS), horizontal=True,
                         index=tuple(ALGORITHMS).index(preferred), key="vault_algorithm", on_change=remember_algorithm)
    assessment = st.session_state.get("applied_assessment")
    if assessment:
        if algorithm == "ML-KEM-768":
            st.info("ML-KEM-768 selected from your applied quantum investigation and migration policy.")
        else:
            st.warning("Manual classical comparison selected. The applied assessment did not validate X25519 as post-quantum secure.")
        st.caption(f"Applied evidence: {assessment['assessment_id']} · No security parameters were inferred from shot counts.")
    keygen, encrypt, decrypt = ALGORITHMS[algorithm]
    if algorithm == "X25519":
        st.info("X25519 is the classical comparison. Choose ML-KEM-768 for post-quantum key establishment.")
    st.subheader("1 / Recipient keys", divider="violet")
    pair = render_keys(algorithm, keygen)
    st.subheader("2 / Protect or recover", divider="violet")
    action = st.radio("Operation", ("Encrypt", "Decrypt"), horizontal=True,
                      key="vault_action", on_change=invalidate_recipient)
    source = st.radio("Key source", ("Upload a key", "Generated in this session"),
                      key="key_source", on_change=invalidate_recipient)
    key_data = None
    protected_import, password = False, ""
    if source == "Upload a key":
        key_kind = "public" if action == "Encrypt" else "private"
        if action == "Decrypt":
            mode = st.radio("Private-key format", ("Protected key backup", "Legacy raw key"),
                            key="private_import_mode", on_change=invalidate_output)
            protected_import = mode == "Protected key backup"
            if protected_import:
                password = st.text_input("Private-key passphrase", type="password", max_chars=128,
                                         key="import_password", on_change=invalidate_output)
            else:
                st.warning("Legacy raw-key import is for earlier unencrypted backups only. Use protected backups for new keys.")
        uploaded_key = st.file_uploader(f"Recipient {key_kind} key", type=["key", "qvkey"],
                                       max_upload_size=1, key=f"key_upload_{action}_{epoch}",
                                       on_change=invalidate_recipient)
        if uploaded_key is not None:
            key_data = uploaded_key.getvalue()
    elif pair is not None:
        key_data = pair[0] if action == "Encrypt" else pair[1]
    else:
        st.info("Generate recipient keys above, or select Upload a key.")
    accepted = True
    if action == "Encrypt" and key_data is not None:
        accepted = recipient_check(key_data, algorithm, invalidate_output)
    elif action == "Decrypt":
        st.session_state.pop("recipient_verification", None)
    upload = st.file_uploader("File to encrypt" if action == "Encrypt" else "Encrypted package",
                              max_upload_size=21, key=f"file_upload_{action}_{epoch}",
                              on_change=invalidate_output)
    st.caption("Up to 20 MiB of plaintext or 21 MiB per encrypted package. Empty and binary files are supported.")
    if st.button("Encrypt file" if action == "Encrypt" else "Decrypt package", type="primary",
                 key="process_file", disabled=upload is None or key_data is None or not accepted
                 or (protected_import and not password)):
        invalidate_output()
        data = upload.getvalue()
        limit = MAX_PLAINTEXT if action == "Encrypt" else MAX_PACKAGE
        if len(data) > limit:
            st.error("This file exceeds the supported size for this operation.")
        else:
            try:
                if protected_import:
                    key_data = import_private_key(key_data, algorithm, password)
                processed = encrypt(data, key_data) if action == "Encrypt" else decrypt(data, key_data)
            except (ValueError, TypeError, InvalidTag):
                record_event(algorithm, action, "Rejected")
                st.error("Could not process this file. Check the algorithm, key, passphrase and package. "
                         "A damaged or modified package is rejected; no recovered file is available.")
            else:
                name = safe_name(upload.name)
                output_name = name + ".qv" if action == "Encrypt" else (
                    name[:-3] if name.endswith(".qv") else "recovered.bin")
                st.session_state["vault_output"] = {
                    "data": processed, "name": output_name or "recovered.bin", "action": action,
                }
                event = record_event(algorithm, action, "Encrypted" if action == "Encrypt" else "Authenticated",
                                     sha256(processed if action == "Encrypt" else data).hexdigest())
                if assessment:
                    st.session_state["vault_output"]["receipt"] = {
                        "schema_version": 1, "operation": event,
                        "policy_id": assessment["policy"]["id"],
                        "requirement": assessment["policy"]["requirement"],
                        "notice": "Unsigned companion record; not a signature, security certificate or part of the authenticated package",
                    }
    output = st.session_state.get("vault_output")
    if output is not None:
        st.success("Encryption complete." if output["action"] == "Encrypt" else
                   "Authentication passed. The recovered file is ready.")
        st.download_button("Download encrypted package" if output["action"] == "Encrypt" else
                           "Download recovered file", output["data"], file_name=output["name"],
                           mime="application/octet-stream", key="download_result", on_click="ignore")
        if "receipt" in output:
            st.download_button("Download protection receipt", json.dumps(output["receipt"], indent=2).encode(),
                               file_name="quantumvault-protection-receipt.json", mime="application/json",
                               key="download_receipt", on_click="ignore")
            st.caption("The receipt links the encrypted package hash to your assessment and algorithm choice. "
                       "It is an unsigned companion record, not an authenticity guarantee.")
    st.caption("Use Clear session data when finished. Files, keys and import passphrases reach the local Python server "
               "in memory. Clearing does not erase downloaded files or guarantee secure memory erasure. "
               "No plaintext preview, key contents or shared secrets are printed.")
