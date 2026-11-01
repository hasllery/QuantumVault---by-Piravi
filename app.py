"""QuantumVault local Streamlit application. Run with streamlit run app.py."""
import streamlit as st

from components import dashboard, secure_vault, quantum_lab_view, performance_lab, security_report

st.set_page_config(page_title="QuantumVault", page_icon="🔐", layout="wide")
st.markdown("""<style>
    .block-container {max-width: 1200px; padding-top: 4rem;}
    [data-testid="stMetric"] {background: #151d32; border: 1px solid #2a3552;
        border-radius: 12px; padding: 1rem;}
    h1 {letter-spacing: -0.04em;}
    [data-testid="stSidebar"] {border-right: 1px solid #2a3552;}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("QuantumVault")
    st.caption("FILE PROTECTION · QUANTUM AWARENESS")
    page = st.radio("Workspace", (
        "Dashboard", "Secure Vault", "Quantum Threat Lab", "Performance Lab", "Security Report",
    ), key="navigation", on_change=secure_vault.invalidate_output)
    st.divider()
    st.caption("Local research prototype\n\nML-KEM-768 / X25519 · AES-256-GCM")
    if st.button("Clear session data", key="clear_session"):
        next_epoch = st.session_state.get("upload_epoch", 0) + 1
        for key in list(st.session_state):
            if key != "navigation":
                del st.session_state[key]
        st.session_state["upload_epoch"] = next_epoch
        st.rerun()
    st.caption("Clears app-held keys, uploads and results. Downloaded files stay on your computer.")

{
    "Dashboard": dashboard.render,
    "Secure Vault": secure_vault.render,
    "Quantum Threat Lab": quantum_lab_view.render,
    "Performance Lab": performance_lab.render,
    "Security Report": security_report.render,
}[page]()
