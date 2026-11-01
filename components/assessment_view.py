"""Shared display and explicit vault application of a measured investigation."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pandas as pd
import streamlit as st


def apply_to_vault():
    assessment = st.session_state.get("threat_assessment")
    if not assessment or not assessment["policy"]["can_apply"]:
        return
    configuration = assessment["configuration"]
    if (st.session_state.get("quantum_base"), st.session_state.get("quantum_shots"),
            st.session_state.get("quantum_seed")) != (
            configuration["base"], configuration["shots"], configuration["seed_simulator"]):
        return
    st.session_state.pop("vault_output", None)
    st.session_state["vault_selection"] = "ML-KEM-768"
    st.session_state["vault_algorithm"] = "ML-KEM-768"
    st.session_state["vault_action"] = "Encrypt"
    st.session_state["key_source"] = "Upload a key"
    st.session_state["applied_assessment"] = deepcopy(assessment)
    st.session_state["applied_assessment"]["applied_at_utc"] = datetime.now(timezone.utc).isoformat()
    st.session_state["navigation"] = "Secure Vault"


def render_assessment(assessment, allow_apply=False, controls_match=True):
    st.subheader("Quantum investigation and vault decision", divider="violet")
    st.write(assessment["research_question"])
    toy = assessment["toy_rsa"]
    if toy["recovery_verified"]:
        st.success("Measured factors recovered the synthetic RSA-wrapped value.")
        st.write(f"Public toy modulus {toy['modulus']}, exponent {toy['public_exponent']}, "
                 f"wrapped value {toy['wrapped_value']} → recovered value {toy['recovered_value']}. "
                 "This matches the public fixture value. It is not a real vault key.")
    else:
        st.warning("This run did not recover the toy value. It does not establish that classical cryptography is safe.")
    st.table(pd.DataFrame(assessment["algorithm_findings"]).set_index("Algorithm"))
    st.info("For the declared requirement of post-quantum key establishment, the policy recommends ML-KEM-768. "
            "This circuit supplies the investigation evidence; the policy uses known algorithm assumptions. "
            "It does not measure real-key risk or determine security parameters.")
    st.caption(f"Evidence ID: {assessment['assessment_id']} · Policy: {assessment['policy']['id']}.")
    if allow_apply:
        st.button("Apply ML-KEM recommendation to Secure Vault", key="apply_assessment",
                  type="primary", on_click=apply_to_vault,
                  disabled=not assessment["policy"]["can_apply"] or not controls_match)
        if not controls_match:
            st.caption("Run again with the current controls before applying this investigation.")
        elif not assessment["policy"]["can_apply"]:
            st.caption(assessment["policy"]["application_reason"])
    st.download_button("Download threat assessment", json.dumps(assessment, indent=2).encode(),
                       file_name="quantumvault-threat-assessment.json", mime="application/json",
                       key="download_assessment", on_click="ignore")
    with st.expander("Assessment limits"):
        for limitation in assessment["limitations"]:
            st.write("• " + limitation)
