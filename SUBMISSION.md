# MiniVM take-home submission

Start in `minivm-takehome`. Use Python 3.12 (standard library only). `./optimize PROGRAM SCHEMA` prints a rewritten program; `./evaluate OPTIMIZER` runs differential tests. Supply your own copy of the assignment's original `bin/` locally to run the evaluator. On Linux/macOS, make the VM launcher and matching binary executable. The optimizer itself does not need the VM.

| Requested material | Location |
|---|---|
| Implementation, tests and scripts | [optimizer](minivm-takehome/GPT6.2-MiniVM/optimize.py), [evaluator](minivm-takehome/GPT6.2-MiniVM/evaluate.py), [tests](minivm-takehome/GPT6.2-MiniVM/test_minivm.py), [reproduction guide](minivm-takehome/docs/analysis/QUICK_REFERENCE.md) |
| Results and verification | [native command checks](minivm-takehome/GPT6.2-MiniVM/verification.md), [eight-query analysis](minivm-takehome/docs/analysis/ALL_QUERIES_SUMMARY.md) |
| Written plan | [Work with a few additional days and unlimited compute/tokens](minivm-takehome/docs/analysis/OPTIMIZATION_PLAN.md) |
| Models and approximate tokens | [AI usage](minivm-takehome/GPT6.2-MiniVM/AI_USAGE.md) |
| Prompts, sessions and logs | [planning prompt](minivm-takehome/skill/minivm-plan.skill); the prepared handoff also includes byte-preserved VS Code originals under `raw-sessions/`, with checksums in `evidence-manifest.json`. The chat journal and transcript contain the prompts. |
| Git history | `history.fi` in the handoff is a **text Git fast-export stream**, not a ZIP, Git bundle, or diff summary. Restore with `git init replay`, `git -C replay fast-import < history.fi`, then `git -C replay switch submission` in a POSIX shell. Filtering out the vendor binaries changes commit hashes; original author, dates, messages and source changes are preserved. |

The original checkout includes vendor binaries in its initial commit: **do not send it or its `.git` directory**. Send only the contents of the audited handoff. No remote upload is part of preparation. Raw originals may contain local paths, account identifiers and user-entered text; review them privately before sharing. Capture again if additional project work occurs after the snapshot.