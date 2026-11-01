import pandas as pd
import streamlit as st

from quantum_lab.period_finding import run_period_finding
from quantum_lab.threat_assessment import build_threat_assessment
from components.assessment_view import render_assessment
from components.study_view import render_study


def render():
    st.caption("QUANTUMVAULT / QUANTUM THREAT LAB")
    st.title("Investigate the threat. Inform the vault choice.")
    st.write("Run controlled modular multiplication and an inverse QFT on Qiskit Aer. "
             "Use measured factors to investigate recovery of a synthetic RSA-wrapped value, "
             "then carry the evidence into a vault migration decision. The modulus is fixed at 15.")
    st.warning("The single-run investigation is ideal; the controlled study also tests synthetic noise. "
               "This does not break real RSA or X25519, "
               "and does not prove ML-KEM security.")
    a, b, c = st.columns(3)
    base = a.selectbox("Coprime base", (2, 4, 7, 8, 11, 13, 14), key="quantum_base")
    shots = b.selectbox("Shots", (128, 512, 1024, 4096), index=2, key="quantum_shots")
    seed = c.number_input("Simulator seed", min_value=0, max_value=2 ** 32 - 1, value=42,
                          step=1, key="quantum_seed")
    if st.button("Run quantum experiment", type="primary", key="run_quantum"):
        st.session_state.pop("quantum_result", None)
        st.session_state.pop("threat_assessment", None)
        try:
            with st.spinner("Executing the order-finding circuit on Aer…"):
                experiment = run_period_finding(base=base, shots=shots, seed=seed)
                assessment = build_threat_assessment(experiment)
                st.session_state["quantum_result"] = experiment
                st.session_state["threat_assessment"] = assessment
        except Exception:
            # Do not echo raw server exceptions into the product interface.
            st.error("The simulator could not complete this run. Check the local Qiskit/Aer installation and retry.")
    render_study()
    result = st.session_state.get("quantum_result")
    if result is None:
        st.info("Choose a base and run the experiment. Base 14 demonstrates a period that yields no factors.")
        return
    configuration, analysis = result["configuration"], result["analysis"]
    st.caption(f"Displayed run: base {configuration['base']} · {configuration['shots']} shots · "
               f"seed {configuration['seed_simulator']} · {configuration['measured_at_utc']}.")
    controls_match = (base, shots, seed) == (configuration["base"], configuration["shots"], configuration["seed_simulator"])
    if not controls_match:
        st.info("Controls have changed. The result below is from the displayed run; run again to use the new controls.")
    (st.success if analysis["status"] == "success" else st.warning)(analysis["message"])
    a, b = st.columns(2)
    a.metric("Estimated period", analysis["estimated_period"] or "Inconclusive")
    b.metric("Nontrivial factors", " × ".join(map(str, analysis["factors"])) or "None recovered")
    st.subheader("Actual measurements", divider="violet")
    st.bar_chart(pd.DataFrame.from_dict(result["counts"], orient="index", columns=["Shots"]))
    st.dataframe(pd.DataFrame(analysis["outcomes"]), width="stretch")
    with st.expander("Circuit and explicit inverse QFT"):
        st.code(result["circuit"], language=None)
        st.code(result["inverse_qft_circuit"], language=None)
    with st.expander("Simulator configuration"):
        st.json(configuration)
    st.caption("Factoring is the toy illustration. The related quantum threat to X25519 concerns "
               "elliptic-curve discrete logarithms; ML-KEM uses lattice-based key establishment.")
    render_assessment(st.session_state["threat_assessment"], allow_apply=True, controls_match=controls_match)
