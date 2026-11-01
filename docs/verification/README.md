# Verified results on 1 November 2026

| Check | Actual result | Evidence |
| --- | --- | --- |
| Original baseline rerun | 40 tests passed | baseline-40.txt |
| Expanded working environment | 61 tests passed | working-61.txt |
| Expanded fresh installation | 61 tests passed | fresh-61.txt |
| Final fresh suite after saved-data validation | 62 tests passed in 69.050 seconds | fresh-final-62.txt |
| Fresh environment checker | All checks passed | fresh-environment.json |
| Exact installed dependency comparison | Matches requirements-lock.txt | verification.json |
| Dependency consistency | No broken requirements found | verification.json |
| Three original crypto engine SHA-256 values | Match pre-change values | verification.json |
| Extended quantum study | 60 trials, zero execution failures; inconclusive outcomes retained | ../../quantum_lab/records/study-20261101T092636Z-735f0c81.json |

The working `.venv` was preserved. `.venv-verification` was newly created and
installed from the lock file. Its actual application was started on localhost
port 8502 and checked in the browser. Automated fresh-environment verification
does not constitute independent teammate acceptance or independent security review.

The final suite comprises 17 interface tests, 7 protected-key tests, 7 repeated
experiment tests, 3 whole-file benchmark tests, and the preserved 28 crypto,
quantum and assessment tests. It includes real operations; simulator errors are
mocked only in explicit failure tests. Streamlit's bare-mode context warnings in
AppTest logs are not failed assertions. The final log ends with OK.

After clarifying the experiment page's ideal-versus-noisy wording, its real
study-and-benchmark interface test passed again in 15.308 seconds; see
final-ui-label-check.txt. No functionality changed after the complete 62-test run.

The first restricted attempt at the final rerun stalled before completing the
boundary test and was interrupted; no pass was claimed for that attempt. The
completed fresh run shown above was executed with normal local process access.

The browser workflow uses synthetic files and test-only passphrases. Its detailed
outcomes are recorded separately in browser-checks.md. No user file contents,
private keys or passphrases are included in this evidence directory.

The eight-page updated presentation guide was rendered through Word and all
eight page images were visually inspected. No clipped text, overlapping content,
broken headings or blank spill pages were found. Rendering is layout QA, not a
security review.
