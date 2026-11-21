# MiniVM take-home submission

Start in `minivm-takehome`. Use Python 3.12 (standard library only). `./optimize PROGRAM SCHEMA` prints a rewritten program; `./evaluate OPTIMIZER` runs differential tests. Supply your own copy of the assignment's original `bin/` locally to run the evaluator. On Linux/macOS, make the VM launcher and matching binary executable. The optimizer itself does not need the VM.

The ZIP records Unix mode `0755` for both launchers and both evaluator controls. If your extractor drops mode bits, run this from `minivm-takehome` on Linux/macOS:

```sh
chmod +x ./optimize ./evaluate ./GPT6.2-MiniVM/checks/identity ./GPT6.2-MiniVM/checks/drop-duplicate
```

**Benchmark scope:** 60,363 → 51,640 MiniVM cycles, a **14.45% reduction across the eight supplied queries**. This is not a prediction for unseen plans. The reviewer reported 0.67 seconds for the evaluator and 0.035 seconds for the slowest supplied optimizer call on Linux after restoring the Git history; those are elapsed times, not cycle counts.

| Requested material | Location |
|---|---|
| Implementation, tests and scripts | [optimizer](minivm-takehome/GPT6.2-MiniVM/optimize.py), [evaluator](minivm-takehome/GPT6.2-MiniVM/evaluate.py), [tests](minivm-takehome/GPT6.2-MiniVM/test_minivm.py), [reproduction guide](minivm-takehome/docs/analysis/QUICK_REFERENCE.md) |
| Results and verification | [native command checks](minivm-takehome/GPT6.2-MiniVM/verification.md), [eight-query analysis](minivm-takehome/docs/analysis/ALL_QUERIES_SUMMARY.md) |
| Written plan | [Work with a few additional days and unlimited compute/tokens](minivm-takehome/docs/analysis/OPTIMIZATION_PLAN.md) |
| Models and approximate tokens | [AI usage](minivm-takehome/GPT6.2-MiniVM/AI_USAGE.md) |
| Prompts, sessions and logs | [planning prompt](minivm-takehome/skill/minivm-plan.skill); the prepared handoff also includes byte-preserved VS Code originals under `raw-sessions/`, with checksums in `evidence-manifest.json`. The chat journal and transcript contain the prompts. |
| Git history | `history.fi` in the handoff is a **text Git fast-export stream**, not a ZIP, Git bundle, or diff summary. Restore with `git init replay`, `git -C replay fast-import < history.fi`, then `git -C replay switch submission` in a POSIX shell. Filtering out the vendor binaries changes commit hashes; original author, dates, messages and source changes are preserved. |

The original checkout includes vendor binaries in its initial commit: **do not send it or its `.git` directory**. Send only the audited handoff. Nothing is uploaded during preparation. The raw evidence and Git attribution contain local paths and email addresses. A pattern scan is not a confidentiality review: the submitter should read prompts and tool output privately before sharing. If unrelated confidential material is present, ask the interview team how to handle it before modifying or sending the original evidence.