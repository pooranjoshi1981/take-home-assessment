# MiniVM: getting started, walkthrough, and eight-query benchmark

## Getting started

Start in the assignment root. Give the optimizer a **program and schema** to get another program; give MiniVM a **program and data** to get `ncols`, `rows`, and `cycles`. See the [VM overview](../README.md) and [commands for Windows, Linux, and macOS](QUICK_REFERENCE.md). Compare the rows and their order first, then compare cycles on the same input.

Each query below links to its own analysis with a complete SQL example. The SQL describes the result **before and after** optimization: the MiniVM instructions change, not the question being asked. The examples use SQLite syntax on tables with the fixture's column names, numeric affinities for amounts, and ISO dates. SQLite is a reading aid, not the correctness oracle: its decimal arithmetic and built-in Unicode case mapping differ from MiniVM's. For concrete SQL projection changes across all eight plans, see the [optimizer getting-started and comparison guide](../../GPT6.2-MiniVM/OPTIMIZER_GUIDE.md).

## Q0001 walkthrough

The first [expected row](../../examples/expected/q0001.json) is `[25, 1, 1002, "Tent 2 / Garden"]`. Follow it through the [original](../../examples/programs/q0001.mini) and [optimized](../../GPT6.2-MiniVM/optimized-examples/q0001.mini) plans:

| Step | Registers | Before and after |
|---|---|---|
| Establish line order | `r1`, `r2`, `r7` | Before: sort by order ID and line number. After: the [schema](../../examples/schema.json) guarantees that order, so `IOTA` returns exactly the positions a stable sort would produce. |
| Look up names | `r17/r18`, `r30/r31` | Both plans use paired join positions to carry line IDs forward and fetch the matching product and category names. Unused price and discount copies disappear. |
| Build the label | `r43`–`r48` | In both plans, substitute empty strings for NULL names, concatenate with `" / "`, apply `NULLIFE`, and take at most 40 characters. |
| Select orders | `r53`–`r58`, `r60/r61` | Require order year 2024 and amount strictly above 750. The order-ID join keeps eligible lines. |
| Return four columns | `r76`, `r77`, `OUT` | Keep quantity at least 1, then gather order ID, line number, product ID, and label. Both plans return the same four sample rows. |

The label and both name lookups are live because they reach `OUT`. Price does not. This distinction, plus removing the sort comparisons, explains the saving without assuming that any join was removed. See the [full Q0001 SQL](Q0001_DETAILED_ANALYSIS.md).

## Eight-query benchmark

On the [bundled data](../../examples/data.json), the current optimizer saves **8,723 of 60,363 cycles (14.45%)**. Both versions of each plan were run with the Windows x86-64 MiniVM. Column counts and ordered rows matched the bundled expected results, including duplicates. The native counts also agree with the independently [calculated cycle report](../../GPT6.2-MiniVM/optimized-examples/cycles.md). This is a sample benchmark, not a guarantee about unseen data.

| Analysis | What the query returns | Output rows | Original cycles | Optimized cycles | Saved |
|---|---|---:|---:|---:|---:|
| [Q0001](Q0001_DETAILED_ANALYSIS.md) | Labeled lines for eligible orders | 4 | 13,766 | 11,725 | 2,041 |
| [Q0002](Q0002_DETAILED_ANALYSIS.md) | Count of smaller discounted lines per report line | 7 | 3,617 | 3,527 | 90 |
| [Q0003](Q0003_DETAILED_ANALYSIS.md) | Latest four IDs per normalized status | 12 | 8,562 | 8,496 | 66 |
| [Q0004](Q0004_DETAILED_ANALYSIS.md) | Revenue and count for qualifying lines | 1 | 18,442 | 13,582 | 4,860 |
| [Q0005](Q0005_DETAILED_ANALYSIS.md) | Revenue per category for card-paid orders | 2 | 5,518 | 4,723 | 795 |
| [Q0006](Q0006_DETAILED_ANALYSIS.md) | Each eligible order with its status group's maximum quantity | 30 | 6,338 | 6,168 | 170 |
| [Q0007](Q0007_DETAILED_ANALYSIS.md) | Up to five July orders by amount | 3 | 2,596 | 2,170 | 426 |
| [Q0008](Q0008_DETAILED_ANALYSIS.md) | Count and quantity per normalized status | 3 | 1,524 | 1,249 | 275 |
| **Total** | | **62** | **60,363** | **51,640** | **8,723** |

Q0004 accounts for more than half the savings: removing unused columns avoids copying them after successive joins. The four joins themselves remain. By contrast, pruning Q0003 saves only 66 cycles because the live self-join and ranking calculations still dominate. Compare each plan with its own baseline: cost per output row is misleading when a global aggregate deliberately returns one row.
