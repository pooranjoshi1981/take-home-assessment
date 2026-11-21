# Quick reference

Run these commands from the assignment root. Optimizing takes **program + schema**; executing takes **program + data**.

### Windows PowerShell

```powershell
python GPT6.2-MiniVM/optimize.py examples/programs/q0001.mini examples/schema.json
./bin/minivm-windows-x86_64.exe examples/programs/q0001.mini examples/data.json
./bin/minivm-windows-x86_64.exe GPT6.2-MiniVM/optimized-examples/q0001.mini examples/data.json
python -m unittest discover -s GPT6.2-MiniVM -v
python GPT6.2-MiniVM/build_examples.py
python GPT6.2-MiniVM/sample_cycles.py
```

The last two commands regenerate all eight saved plans and then the calculated report. Use the generator rather than redirecting stdout to a program file in Windows PowerShell 5.1, whose default redirection encoding is UTF-16.

### Linux or macOS

```sh
./optimize examples/programs/q0007.mini examples/schema.json > /tmp/q0007.mini
./bin/minivm /tmp/q0007.mini examples/data.json
./evaluate ./optimize
```

The wrappers default to `python3`; set `PYTHON` to an absolute interpreter path if necessary. On Linux/macOS, the VM launcher and matching platform binary must be executable. Under Windows Git Bash, the same wrappers work with `sh` on PATH and the supplied native Windows VM. See the [actual CLI checks](../../GPT6.2-MiniVM/verification.md).

**Interpreting results:** `ncols` checks the output width even when `rows` is empty. Preserve duplicate rows and any specified ordering. `cycles` measures VM work, not elapsed time. See the [CLI and schema contract](../running.md), [instruction index](../instructions/README.md), and [cost table](../cycles.md).

