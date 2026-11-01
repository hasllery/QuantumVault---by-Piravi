"""Repeated quantum investigation, distinct from the single-run vault policy."""
import json
import pandas as pd
import streamlit as st

from quantum_lab.experiments import run_study, save_study, PROFILES


def render_study():
    with st.expander("Controlled ideal and noisy investigation"):
        st.write("Investigate how circuit implementation, measurement budget and synthetic noise affect "
                 "period and toy-value recovery. Fixed N=15, base 2, four counting and four work qubits.")
        profile = st.selectbox("Experiment workload", tuple(PROFILES), key="study_profile")
        st.caption("Small: 16 trials. Extended: 60 trials. Each compares matrix and rotation circuits. "
                   "Noise is synthetic depolarization, not a device calibration. Runs are bounded for this laptop.")
        if st.button("Run controlled study", key="run_study"):
            st.session_state.pop("study_report", None)
            bar = st.progress(0.0, text="Preparing experiments")
            try:
                report = run_study(profile, lambda n, total: bar.progress(n / total, text=f"Completed {n} of {total} trials"))
                path = save_study(report)
                st.session_state["study_report"] = report
                st.session_state["study_saved_name"] = path.name
            except Exception:
                st.error("The controlled study could not complete. No previous study is displayed as a new result.")
            bar.empty()
        report = st.session_state.get("study_report")
        if report is None:
            st.info("Run a study to obtain repeated measurements. This does not replace the single-run vault investigation below.")
            return
        st.caption(f"Displayed study: {report['metadata']['profile']} · {report['metadata']['started_at_utc']} · "
                   f"Evidence {report['evidence_id']}.")
        if profile != report["metadata"]["profile"]:
            st.info("The workload changed. Run again to generate results for the current workload.")
        rows = []
        for summary in report["summary"]:
            interval = summary["toy_recovered"]
            rows.append({"Circuit": summary["implementation"], "Noise p": summary["noise_rate"],
                         "Shots per trial": summary["shots"], "Trials": summary["planned_trials"],
                         "Failed": summary["failed_trials"], "Inconclusive": summary["inconclusive_trials"],
                         "Toy recovery proportion": interval["proportion"],
                         "Wilson 95% lower": interval["wilson_95_low"], "Wilson 95% upper": interval["wilson_95_high"],
                         "Usable factor shot fraction": summary.get("usable_factor_shot_fraction"),
                         "Depth": summary.get("depth"), "CX gates": summary.get("cx_gates"),
                         "Median compile ms": summary.get("median_compilation_ms"),
                         "Median simulate ms": summary.get("median_simulation_ms")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        failures = sum(row["failed_trials"] for row in report["summary"])
        if failures:
            st.warning(f"{failures} planned trials failed. They remain in every relevant success denominator.")
        st.write(f"Classical trial-division median: {report['classical_baseline']['median_ms']:.6f} ms. "
                 "That times factoring only. Quantum rows measure classical circuit simulation, not quantum hardware.")
        st.warning("A trial is a complete run, not a shot. Small trial counts give wide uncertainty. "
                   "Usable phases are classically verified candidates, not state fidelity or a security score. "
                   "These pilot data cannot establish quantum advantage or a reliable production attack estimate.")
        st.write(report["interpretation"])
        st.download_button("Download controlled study", json.dumps(report, indent=2).encode(),
                           file_name="quantumvault-controlled-study.json", mime="application/json",
                           key="download_study", on_click="ignore")
        st.caption(f"Public research data saved without overwriting earlier runs: quantum_lab/records/{st.session_state['study_saved_name']}")
        with st.expander("Trial records and noise coverage"):
            st.json(report)
