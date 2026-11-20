# Q0004 — Revenue and count for Kitchen sales

[Original](../../examples/programs/q0004.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0004.mini) · [Expected output](../../examples/expected/q0004.json)

**Native sample: 18,442 → 13,582 cycles; 4,860 saved (26.35%).** The result is **one row**, `[null, 0]`. No joined rows satisfy the filters, but `GALL` creates one group even over empty input; its sum is NULL and its count is zero.

Four joins attach orders, products, categories, and customers to lines. The original applies an audit sort before testing normalized region `CENTRAL`, order year 2023, and normalized category `KITCHEN`. For surviving rows it computes quantity × price × (1 − discount), then sums revenue and counts rows.

**Current rewrite:** prune unused loads, gathered columns, and display calculations. Removing one unused value can eliminate several copies across successive joins. The saved plan still has all four joins, the audit sort, and late filters: none of the 4,860 cycles should be attributed to filter pushdown. Moving filters before joins is a future experiment; duplicate customer matches must still contribute to both aggregates.

## Step by step

Read each path in sequence: `s1`, `s2`, and `s3` name its intermediate results.

### Step 1 — Join lines to four lookup tables (`s1`)

```sql
-- Before: carry display fields, even though no output uses them.
SELECT l.l_order,l.l_qty,l.l_price,l.l_disc,o.o_date,k.k_name,c.c_region,
			 l.l_no,o.o_status,p.p_name,c.c_name
FROM lines l JOIN orders o ON o.o_id=l.l_order JOIN products p ON p.p_id=l.l_prod
JOIN categories k ON k.k_id=p.p_cat JOIN customers c ON c.c_id=o.o_cust;
-- After: narrower rows, same four joins and multiplicity.
SELECT l.l_order,l.l_qty,l.l_price,l.l_disc,o.o_date,k.k_name,c.c_region
FROM lines l JOIN orders o ON o.o_id=l.l_order JOIN products p ON p.p_id=l.l_prod
JOIN categories k ON k.k_id=p.p_cat JOIN customers c ON c.c_id=o.o_cust;
```

### Step 2 — Apply the audit order (`s2`)

```sql
-- Before: apply the permutation to the wide row.
SELECT * FROM s1 ORDER BY o_date DESC NULLS LAST,l_order ASC NULLS FIRST;
-- After: sort by the same keys; only the live values are gathered.
SELECT l_qty,l_price,l_disc,o_date,k_name,c_region FROM s1
ORDER BY o_date DESC NULLS LAST,l_order ASC NULLS FIRST;
```

### Step 3 — Filter the joined rows and compute revenue (`s3`)

```sql
-- Before
SELECT (l_qty*l_price)*(1-l_disc) AS revenue FROM s2
WHERE upper(rtrim(nullif(c_region,'')))='CENTRAL' AND strftime('%Y',o_date)='2023'
	AND upper(rtrim(nullif(k_name,'')))='KITCHEN';
-- After: predicates remain after the joins; no customer match is deduplicated.
SELECT (l_qty*l_price)*(1-l_disc) AS revenue FROM s2
WHERE upper(rtrim(nullif(c_region,'')))='CENTRAL' AND strftime('%Y',o_date)='2023'
	AND upper(rtrim(nullif(k_name,'')))='KITCHEN';
```

### Step 4 — Sum revenue and count matches

```sql
-- Before
SELECT sum(revenue),count(*) FROM s3;
-- After: still one aggregate row, even when Step 3 returns none.
SELECT sum(revenue),count(*) FROM s3;
```

### Before SQL — carry display fields through the audit stage

```sql
WITH audit AS (
		SELECT l.l_order, l.l_no, l.l_qty, l.l_price, l.l_disc, o.o_date, o.o_status,
					 p.p_name, k.k_name, c.c_name, c.c_region
		FROM lines AS l JOIN orders AS o ON o.o_id = l.l_order
		JOIN products AS p ON p.p_id = l.l_prod
		JOIN categories AS k ON k.k_id = p.p_cat
		JOIN customers AS c ON c.c_id = o.o_cust
		ORDER BY o.o_date DESC NULLS LAST, l.l_order ASC NULLS FIRST
)
SELECT sum((l_qty * l_price) * (1 - l_disc)) AS revenue, count(*) AS line_count
FROM audit WHERE upper(rtrim(nullif(c_region, ''))) = 'CENTRAL'
	AND strftime('%Y', o_date) = '2023' AND upper(rtrim(nullif(k_name, ''))) = 'KITCHEN';
```

### After SQL — express the aggregate using only live inputs

The after SQL omits the intermediate order because it cannot change this result. The optimized **VM** still sorts; the SQL is a result equivalent, not a claim that the optimizer removed the audit step.

```sql
SELECT sum((l.l_qty * l.l_price) * (1 - l.l_disc)) AS revenue, count(*) AS line_count
FROM lines AS l
JOIN orders AS o ON o.o_id = l.l_order
JOIN products AS p ON p.p_id = l.l_prod
JOIN categories AS k ON k.k_id = p.p_cat
JOIN customers AS c ON c.c_id = o.o_cust
WHERE upper(rtrim(nullif(c.c_region, ''))) = 'CENTRAL'
	AND strftime('%Y', o.o_date) = '2023'
	AND upper(rtrim(nullif(k.k_name, ''))) = 'KITCHEN';
```

There is no `GROUP BY`: the aggregate must return one row even if no sale qualifies. The SQL need not express the intermediate audit sort to describe that result.