import pandas as pd
import streamlit as st

from components.data import DATA_ERRORS, load_benchmark
from components.data import ROOT, read_json
from benchmark.file_performance import benchmark_files, save_benchmark, validate_report


def render():
    st.caption("QUANTUMVAULT / PERFORMANCE LAB")
    st.title("Measured here. Compared fairly.")
    st.write("Saved key-establishment measurements from benchmark/results.json.")
    try:
        result = load_benchmark()
    except DATA_ERRORS:
        st.error("Saved benchmark data is missing or invalid. No substitute values are displayed.")
        st.code(".\\.venv\\Scripts\\python.exe -m benchmark.performance > benchmark/results.json", language="powershell")
        return
    entries = result["algorithms"]
    timings = pd.DataFrame({name: data["median_ms"] for name, data in entries.items()})
    timings.index = ["Key generation", "Sender establishment", "Receiver recovery"]
    st.subheader("Median time / milliseconds", divider="violet")
    st.dataframe(timings, width="stretch")
    st.bar_chart(timings, stack=False, y_label="Median milliseconds")
    st.subheader("Measured sizes / bytes", divider="violet")
    sizes = pd.DataFrame({name: data["sizes_bytes"] for name, data in entries.items()})
    st.dataframe(sizes, width="stretch")
    metadata = result["metadata"]
    st.caption(f"Recorded {metadata['measured_at_utc']} · {metadata['repetitions']} repetitions · "
               f"{metadata['warmup_calls_per_operation']} warm-up per operation · {metadata['statistic']}.")
    st.info("X25519 sender establishment includes a fresh ephemeral key, exchange and public-key export. "
            "These timings exclude HKDF, AES-GCM, file I/O and full package creation. "
            "Machine load and backend versions affect results.")
    with st.expander("Measurement configuration"):
        st.json(metadata)
    st.subheader("Whole-file protection measurements", divider="violet")
    if st.button("Run file benchmark", key="run_file_benchmark"):
        st.session_state.pop("file_benchmark", None)
        try:
            with st.spinner("Measuring both algorithms on the same synthetic files…"):
                report = benchmark_files()
                save_benchmark(report)
                st.session_state["file_benchmark"] = report
        except Exception:
            st.error("The file benchmark failed; no new measurement is claimed.")
    report = st.session_state.get("file_benchmark")
    if report is None:
        paths = sorted((ROOT / "benchmark" / "records").glob("files-*.json"), reverse=True)
        if paths:
            try:
                report = validate_report(read_json(paths[0].relative_to(ROOT)))
            except DATA_ERRORS:
                st.warning("Saved whole-file measurements could not be read.")
    if report:
        st.caption(f"Recorded {report['metadata']['measured_at_utc']} · {report['metadata']['repetitions']} repetitions.")
        st.dataframe(pd.DataFrame(report["measurements"]), hide_index=True, width="stretch")
        st.write(report["metadata"]["scope"])
    else:
        st.info("No whole-file run is saved yet. Run the benchmark above to obtain actual measurements.")
