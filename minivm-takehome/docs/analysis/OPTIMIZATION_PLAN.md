# Optimization plan: next experiments

With a few additional days and unlimited compute and tokens, I would spend day one generating legal counterexamples and building a regression corpus; day two implementing one proven rewrite at a time; and day three running differential tests and per-rule ablations on held-out workloads. Use parallel workers for data and program generation, not to relax the one-second optimizer or two-minute evaluator limits. Ship a rule only if it preserves results across those checks and improves held-out cycle costs enough to justify its worst regressions.

The [current baseline](OPTIMIZER_STATUS.md) is dead-code removal and declared-order sort replacement. The following are **proposals**, not implemented passes or projected cycle savings.

| Priority | Candidate | Proof required before enabling it |
|---|---|---|
| Q0001 | Remove the redundant quantity mask; build labels only after qualifying orders are known. | Trace quantity through gathers to a non-NULL base column with a lower bound of 1. Preserve join multiplicity and line order. |
| Q0007 | Filter by date, apply stable `TOPK` on qualifying positions, then build labels. | Filtering must preserve input order for ties. Keep amount direction, NULL placement, secondary ID key, and original limit. |
| Q0004 | Filter dimensions before joining; investigate eliminating the audit sort. | Retain duplicate customer matches and `[null, 0]` on empty aggregate input. Prove no order-sensitive consumer needs the permutation. |
| Q0002, Q0003, Q0006 | Reduce or avoid pairwise self-joins. | Separate report and comparison populations; preserve zero counts, normalized NULL behavior, tie rules, output spelling, and repeated columns. |
| Q0005, Q0008 | Deduplicate payment keys early; avoid carrying unnecessary display values. | Use the declared line key for revenue multiplicity. For status labels preserve the original `GMIN` representative and its sort key. |

**Implementation order.** Track each register definition and row-position domain separately before moving an operation. Use schema constraints to prove correctness; use cardinalities and histograms only to choose between equivalent plans. Benchmark one change at a time against both the original and the current optimizer.

**Test beyond the fixtures.** Generate small legal programs and tables with empty groups, tied keys, NULLs, repeated join matches, and overwritten registers. Vary data while keeping its schema and old statistics fixed. Run both programs in MiniVM, compare outputs first, and shrink failures by deleting instructions and rows while preserving constraints. Keep minimized cases as regressions. Use held-out plans for cycle and timeout comparisons rather than selecting rules on these eight queries alone.
