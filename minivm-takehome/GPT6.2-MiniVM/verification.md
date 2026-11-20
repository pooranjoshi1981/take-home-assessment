# Verification log — 2026-11-20

Windows x86-64, Python 3.12.10, Git Bash, supplied native Windows MiniVM. Commands below are relative to the assignment root. `PYTHON` was set to the absolute interpreter path because `python3` on this machine resolves to a Windows Store alias. This is not a Linux/macOS certification.

| Check | Observed outcome | Elapsed |
|---|---|---:|
| `python -m unittest discover -s GPT6.2-MiniVM -v` | 10 passed | 1.769 s (test runner) |
| `./evaluate ./optimize` | exit 0; 12 passed, 0 skipped; 8,723 cycles saved | 4.047 s |
| `./evaluate ./GPT6.2-MiniVM/checks/identity` | exit 0; 12 passed, 0 skipped; 0 saved | 2.442 s |
| `./evaluate ./GPT6.2-MiniVM/checks/drop-duplicate` | exit 1; `join-bag candidate: expected 3 rows, got 2` | 2.063 s |

Individual `./optimize` calls on Q0001 through Q0008 respectively took **462, 456, 414, 454, 405, 412, 461, 405 ms**, including the outer shell and comparison to saved output. All emitted the expected rewritten plans. On the supplied data all eight produced the reference rows in order and reduced cycles from 60,363 to 51,640. The four edge cases test correctness, not additional gains.

Control development note: the first duplicate-loss control timed out launching an external utility; a shell-only variant initially failed to match a CRLF line. Neither run was counted as detecting duplicate loss. The reported negative control passed only after the actual row-count diagnostic was observed.

These are sample measurements, not universal proofs. A native Linux/macOS run with the reviewer-supplied VM and benchmarking on unseen plans remain useful independent checks.

**Subsequent checks.** The reviewer reported that the restored source passed the ten unit tests and twelve evaluator cases on Linux, rejected the duplicate-loss control, and took 0.67 s for the evaluator and at most 0.035 s for a supplied optimizer input. This run used restored Git modes, not a direct ZIP extraction.

Separately, `python GPT6.2-MiniVM/check_generated.py` passed six seeded native Windows VM checks: three declared-sorted datasets, two nonempty datasets without that declaration, and an empty table. These exercise stable ties, NULLs, a dead string expression, and reused register names. These are variations of a single generated plan shape, not six new workload families. They are outside the evaluator's 12 cases and outside the 14.45% sample benchmark.