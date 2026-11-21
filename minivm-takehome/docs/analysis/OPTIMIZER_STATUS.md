# Optimizer status

The [optimizer entry point](../../optimize) calls one [Python implementation](../../GPT6.2-MiniVM/optimize.py). It does not choose a rewrite by query ID.

| Implemented rule | When it applies | What it leaves alone |
|---|---|---|
| Declared-order sort replacement | All keys are `ASC NF`, are direct loads from one table, and match a prefix of that table's declared `sorted` columns. Emit `IOTA` over the first key. | Descending keys, other NULL placement, computed keys, and order inferred only from statistics. |
| Backward liveness | Start at `OUT`; keep instructions producing needed registers and follow their inputs. Track both join destinations. | The pass conservatively retains writes to multiply assigned registers: overwriting can release memory before later VM budget checks. |

Unknown opcodes and unrecognized plan shapes fall back to the input. The optimizer does **not** currently push filters through joins, merge duplicate gathers, implement groupwise top-N, or move label formatting after a limit.

**Verification:** all eight saved original/optimized pairs matched the golden sample rows on the native Windows VM. Total cost fell from 60,363 to 51,640; see [per-query results](ALL_QUERIES_SUMMARY.md). This verifies the bundled input, not equivalence for every legal dataset.

The [evaluator](../../GPT6.2-MiniVM/evaluate.py) tests eight examples and four edge fixtures. It distinguishes reference errors from candidate failures and cycle regressions from wrong answers. The [unit tests](../../GPT6.2-MiniVM/test_minivm.py) cover comparison, failure handling, timeouts, and rewrite guards; their mocked driver cases are not native measurements.

