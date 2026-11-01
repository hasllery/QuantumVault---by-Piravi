# Teammate installation and acceptance checklist

Status: **Not yet completed by a teammate.** Automated fresh-environment results
are separate evidence and do not fill in this checklist. Abeed, Vismai or Riya
should complete it without Hassan operating their computer.

Tester name: ____________________

Computer and operating system: ____________________

Date and Python version: ____________________

## Independent installation

- [ ] Obtain the project and read the current README.
- [ ] Install Python 3.11 from its official source if needed.
- [ ] Create a new environment, without copying Hassan's `.venv`.
- [ ] Install `requirements-lock.txt` using that environment's Python.
- [ ] Run `environment_check.py`; every check passes.
- [ ] Run `python -m pip check`; no dependency conflicts are reported.
- [ ] Run `python -m unittest discover -v`; record the actual count and result.
- [ ] Launch `python -m streamlit run app.py` and open the local address.

Use the explicit `.venv\Scripts\python.exe` path rather than changing PowerShell
execution policy. The README documents the full-path fallback if `py` is missing.

## Key backup and file recovery

- [ ] Generate ML-KEM keys and save the public key.
- [ ] Prepare/download a protected private backup with a non-demo passphrase.
- [ ] Supply a recipient fingerprint through a trusted separate channel and show a match.
- [ ] Explain why copying the displayed fingerprint alone does not prove identity.
- [ ] Encrypt a non-sensitive text file and download its package.
- [ ] Clear the session or reload the browser.
- [ ] Recover the file by uploading the protected backup and supplying its passphrase.
- [ ] Open the recovered file and compare the original contents.
- [ ] Try an incorrect passphrase and verify no recovered download is offered.
- [ ] Try a modified package and verify rejection.
- [ ] Try a different expected fingerprint and verify encryption is blocked.
- [ ] Repeat the successful workflow with X25519.
- [ ] Explain the legacy raw-import warning and avoid raw export for new keys.

## Investigation and evidence

- [ ] Run the single base-2 investigation and inspect actual counts and factors.
- [ ] Apply its migration decision and confirm ML-KEM is selected in Secure Vault.
- [ ] Encrypt a demo file and download the receipt; explain that it is unsigned.
- [ ] Run the small controlled study and inspect ideal versus noisy results.
- [ ] Explain why shots differ from trials and why the intervals are wide.
- [ ] Inspect gate/noise coverage and the classical factoring comparison.
- [ ] Run the whole-file benchmark and distinguish it from the old KEM timings.
- [ ] Confirm original evidence was not overwritten by new runs.

## Presentation ownership

Hassan owns implementation details and recovery troubleshooting. Abeed owns the
user journey and this independent-installation check. Vismai owns experimental
design, uncertainty and the quantum limitations. Riya owns the evidence inventory,
claims, timing and outstanding external-review items.

Actual result and problems found: ____________________

Hassan assistance needed, if any: ____________________

Independent security reviewer and review outcome: **Not yet arranged or completed.**
