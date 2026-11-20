# Q0001 — Line export for qualifying orders

[Original](../../examples/programs/q0001.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0001.mini) · [Expected output](../../examples/expected/q0001.json)

**Native sample: 13,766 → 11,725 cycles; 2,041 saved (14.83%).** Four rows, each containing order ID, line number, product ID, and a label of at most 40 characters.

The original sorts lines by `(l_order, l_no)`, joins products and categories to build the label, and joins the resulting rows to orders from 2024 whose amount exceeds 750. It then keeps lines with quantity at least 1. The schema declares lines stored in the same ascending order: a stable sort returns the identity permutation. `IOTA` produces those positions without comparisons. Backward liveness also removes price, discount, and other columns that never affect the four output fields.

## Step by step

Read either SQL path from top to bottom. `s1`, `s2`, and `s3` mean the preceding results **on that path**.

### Step 1 — Read lines in report order (`s1`)

```sql
-- Before: sort positions and carry six line columns.
SELECT l_order, l_no, l_prod, l_qty, l_price, l_disc FROM lines ORDER BY l_order, l_no;
-- After: only four columns. MiniVM uses IOTA because storage order matches.
SELECT l_order, l_no, l_prod, l_qty FROM lines ORDER BY l_order, l_no;
```

### Step 2 — Join the product and category; build the label (`s2`)

```sql
-- Before: l.* still includes price and discount.
SELECT l.*, substr(nullif(coalesce(p.p_name,'') || ' / ' || coalesce(k.k_name,''),''),1,40) AS label
FROM s1 AS l JOIN products AS p ON p.p_id=l.l_prod JOIN categories AS k ON k.k_id=p.p_cat;
-- After: same name lookups, but l.* is the narrower Step 1 row.
SELECT l.*, substr(nullif(coalesce(p.p_name,'') || ' / ' || coalesce(k.k_name,''),''),1,40) AS label
FROM s1 AS l JOIN products AS p ON p.p_id=l.l_prod JOIN categories AS k ON k.k_id=p.p_cat;
```

### Step 3 — Join eligible orders and filter quantity (`s3`)

```sql
-- Before
SELECT l.* FROM s2 AS l JOIN orders AS o ON o.o_id=l.l_order
WHERE strftime('%Y',o.o_date)='2024' AND o.o_amt>750 AND l.l_qty>=1;
-- After: same three tests; no filter was removed or pushed down.
SELECT l.* FROM s2 AS l JOIN orders AS o ON o.o_id=l.l_order
WHERE strftime('%Y',o.o_date)='2024' AND o.o_amt>750 AND l.l_qty>=1;
```

### Step 4 — Return the four report columns

```sql
-- Before
SELECT l_order, l_no, l_prod, label FROM s3 ORDER BY l_order, l_no;
-- After: same output order even though Step 1 no longer needs a physical sort.
SELECT l_order, l_no, l_prod, label FROM s3 ORDER BY l_order, l_no;
```

### Before SQL — follow the wide line rows

```sql
WITH sorted_lines AS (
	SELECT l_order, l_no, l_prod, l_qty, l_price, l_disc
	FROM lines ORDER BY l_order, l_no
), labeled AS (
	SELECT l.*, substr(nullif(coalesce(p.p_name, '') || ' / ' ||
		   coalesce(k.k_name, ''), ''), 1, 40) AS label
	FROM sorted_lines AS l JOIN products AS p ON p.p_id = l.l_prod
	JOIN categories AS k ON k.k_id = p.p_cat
)
SELECT l.l_order, l.l_no, l.l_prod, l.label
FROM labeled AS l JOIN orders AS o ON o.o_id = l.l_order
WHERE strftime('%Y', o.o_date) = '2024' AND o.o_amt > 750 AND l.l_qty >= 1
ORDER BY l.l_order, l.l_no;
```

### After SQL — keep only fields needed for the same result

```sql
SELECT l.l_order, l.l_no, l.l_prod,
	   substr(nullif(coalesce(p.p_name, '') || ' / ' || coalesce(k.k_name, ''), ''), 1, 40) AS label
FROM lines AS l
JOIN products AS p ON p.p_id = l.l_prod
JOIN categories AS k ON k.k_id = p.p_cat
JOIN orders AS o ON o.o_id = l.l_order
WHERE strftime('%Y', o.o_date) = '2024' AND o.o_amt > 750 AND l.l_qty >= 1
ORDER BY l.l_order, l.l_no;
```

**Still present:** the quantity mask and early label construction. A further pass could use the declared `not_null` and `check` constraints on `l_qty` to remove the mask after proving its origin. Delaying label construction must preserve both name lookups, NULL substitution, separator, truncation, and line order. The SQL retains `ORDER BY` because output order is required even when a physical sort is not. See the [register walkthrough](ALL_QUERIES_SUMMARY.md#q0001-walkthrough).