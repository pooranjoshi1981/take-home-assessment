# Getting started with the Python optimizer

1. From the assignment root, run `python GPT6.2-MiniVM/build_examples.py` to regenerate the eight plans with the [current optimizer](optimize.py). The [original programs](../examples/programs) are inputs; the rewritten programs go into [optimized-examples](optimized-examples).
2. Pick the same query on both sides and run each program on the **same data** using the [platform-specific commands](../docs/analysis/QUICK_REFERENCE.md). Compare output width, ordered rows, and duplicates before comparing cycles.
3. Run `python GPT6.2-MiniVM/sample_cycles.py` for the [calculated comparison](optimized-examples/cycles.md). The [combined guide](../docs/analysis/ALL_QUERIES_SUMMARY.md) records the separate native VM check. The calculator covers the fixture programs only.

## Before and after, in SQL terms

The optimizer emits MiniVM, not SQL. The SQL pairs below illustrate **intermediate columns read or carried**, not the final result queries. Each heading links to the full executable result SQL. Dropping a column here is valid only because no later predicate, join, sort, or output needs that copy. The cycle numbers are for the complete MiniVM plans, not these SQL fragments.

### [Q0001: labeled order lines](../docs/analysis/Q0001_DETAILED_ANALYSIS.md) — 13,766 → 11,725

```sql
-- Before: read price and discount as well as the four live line columns.
SELECT l_order, l_no, l_prod, l_qty, l_price, l_disc FROM lines ORDER BY l_order, l_no;
-- After: narrower input; the VM uses declared storage order instead of sorting.
SELECT l_order, l_no, l_prod, l_qty FROM lines ORDER BY l_order, l_no;
```

Keep `ORDER BY` in the SQL contract. Only the physical method changes: the saved plan uses `IOTA` for the identity permutation.

### [Q0002: discounted-line counts](../docs/analysis/Q0002_DETAILED_ANALYSIS.md) — 3,617 → 3,527

```sql
-- Before: two reads of discount, only the first feeds a predicate.
SELECT l_disc, l_disc AS unused_discount FROM lines;
-- After
SELECT l_disc FROM lines;
```

The self-join still uses all discounted lines as the comparison population; no date or amount predicate was pushed into that side.

### [Q0003: latest orders per status](../docs/analysis/Q0003_DETAILED_ANALYSIS.md) — 8,562 → 8,496

```sql
-- Before
SELECT o_id, o_cust, o_status FROM orders;
-- After
SELECT o_id, o_status FROM orders;
```

Customer ID is dead. The repeated **order** ID in the final output is not: both positions remain. The ranking still uses a self-join.

### [Q0004: Kitchen revenue and count](../docs/analysis/Q0004_DETAILED_ANALYSIS.md) — 18,442 → 13,582

```sql
-- Before: customer-side inputs to the last join.
SELECT c_id, c_name, c_region FROM customers;
-- After: retain the join key and region predicate input.
SELECT c_id, c_region FROM customers;
```

This is one example of pruning across the four joins; earlier unused columns also stop being copied. All joins, the audit sort, and the final aggregate remain. The saving is not evidence of filter pushdown.

### [Q0005: card-paid line revenue](../docs/analysis/Q0005_DETAILED_ANALYSIS.md) — 5,518 → 4,723

```sql
-- Before
SELECT y_order, y_method, y_amt FROM payments;
-- After
SELECT y_order, y_method FROM payments;
```

Revenue comes from line quantity, price, and discount, not payment amount. Several card payments may match one order; both plans still deduplicate by line key after joining.

### [Q0006: maximum quantity per status](../docs/analysis/Q0006_DETAILED_ANALYSIS.md) — 6,338 → 6,168

```sql
-- Before: gather date as well as the other fields after filtering.
SELECT o_id, o_status, o_qty, o_amt, o_date FROM orders WHERE o_date >= '2023-01-01';
-- After: date is read for the predicate but is not copied into the filtered result.
SELECT o_id, o_status, o_qty, o_amt FROM orders WHERE o_date >= '2023-01-01';
```

The distinction is between using a column and carrying it forward. `GMAX`, the self-join, and the identity gather still execute.

### [Q0007: five July orders](../docs/analysis/Q0007_DETAILED_ANALYSIS.md) — 2,596 → 2,170

```sql
-- Before: two unused input columns in addition to the report inputs.
SELECT o_id, o_cust, o_date, o_amt, o_qty, o_status, o_note FROM orders;
-- After
SELECT o_id, o_date, o_amt, o_status, o_note FROM orders;
```

The unused weekday and uppercase display copy disappear too. The VM still builds the real label and sorts before filtering; it has not replaced the sort with `TOPK`.

### [Q0008: status counts and quantities](../docs/analysis/Q0008_DETAILED_ANALYSIS.md) — 1,524 → 1,249

```sql
-- Before: gather all seven fields for qualifying orders.
SELECT o_id, o_cust, o_date, o_amt, o_qty, o_status, o_note FROM orders WHERE o_qty >= 5;
-- After
SELECT o_qty, o_status FROM orders WHERE o_qty >= 5;
```

Quantity feeds both the filter and sum. Status feeds the normalized group key **and** the display spelling. Neither use can be removed. For experiments beyond these measured changes, see the [optimization plan](../docs/analysis/OPTIMIZATION_PLAN.md).