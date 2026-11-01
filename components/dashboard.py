import streamlit as st

from components.data import DATA_ERRORS, load_benchmark, read_json


def render():
    st.caption("QUANTUMVAULT / OVERVIEW")
    st.title("Protect files. Understand the threat.")
    st.write("Encrypt with post-quantum key establishment, compare a classical baseline, "
             "and carry measured quantum threat evidence into a vault migration decision.")
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Your workspace", divider="violet")
        st.markdown("""- **Secure Vault** — generate recipient keys, encrypt a file and recover it.
- **Quantum Threat Lab** — investigate synthetic RSA recovery with Aer and apply a migration recommendation.
- **Performance Lab** — inspect saved local measurements.
- **Security Report** — review sizes, session integrity checks and limitations.""")
    with right:
        st.info("Both file modes use HKDF-SHA256 and AES-256-GCM. "
                "Only their key-establishment method changes.")
    st.subheader("Recorded project evidence", divider="violet")
    try:
        quantum = read_json("quantum_lab/results.json")
        configuration, analysis = quantum["configuration"], quantum["analysis"]
        a, b, c = st.columns(3)
        a.metric("Saved experiment shots", configuration["shots"])
        b.metric("Estimated period", analysis["estimated_period"] or "Inconclusive")
        c.metric("Recovered factors", " × ".join(map(str, analysis["factors"])) or "None")
        st.caption(f"Saved Aer run · N={configuration['modulus']} · base {configuration['base']} · "
                   f"{configuration['measured_at_utc']}. Run a fresh experiment in Quantum Threat Lab.")
    except DATA_ERRORS:
        st.warning("Saved quantum results are unavailable. Run the Quantum Threat Lab for new measurements.")
    try:
        benchmark = load_benchmark()
        st.caption(f"Benchmark evidence: {benchmark['metadata']['repetitions']} repetitions per operation · "
                   f"recorded {benchmark['metadata']['measured_at_utc']}.")
    except DATA_ERRORS:
        st.warning("Saved benchmark results are unavailable. Performance Lab explains how to regenerate them.")
    applied = st.session_state.get("applied_assessment")
    study = st.session_state.get("study_report")
    if study:
        failed = sum(row['failed_trials'] for row in study['summary'])
        st.info(f"Current-session controlled study: {study['metadata']['planned_trials']} planned trials, {failed} failures. "
                "Inspect trial proportions and uncertainty in Quantum Threat Lab.")
    if applied:
        st.info(f"Vault migration choice applied from quantum evidence {applied['assessment_id'][:12]}. "
                "Security Report connects this choice with session file operations.")
    st.warning("Research prototype. Authenticate recipient public keys before use. "
               "The quantum lab studies only 15 with ideal and synthetic-noise simulation; it does not break real RSA or X25519.")
