# Q0007 — Five largest July orders

[Original](../../examples/programs/q0007.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0007.mini) · [Expected output](../../examples/expected/q0007.json)

**Native sample: 2,596 → 2,170 cycles; 426 saved (16.41%).** Three orders qualify, in ID order **10, 14, 5** as ranked by amount. The limit is a maximum, not a required output size. Each row contains ID, amount, and a formatted note/status label, not raw status.

The original builds labels before selecting orders. It sorts by amount descending with NULLs last and then ID ascending with NULLs first. It filters this sorted stream to July 2023, builds positions with `IOTA`, and uses `SLICE` to take at most five. The leading space in `" shipped"` is part of the output: concatenating an empty note, a space, and the status produces it.

**Current rewrite:** removes unused customer and quantity columns, the uppercase display copy, weekday calculation, and unused gathers. It still sorts before filtering. A future rewrite could filter first, apply stable `TOPK` on the qualifying rows, and build only their labels. Taking five rows *before* filtering could discard qualifying orders.

## Step by step

Follow each SQL path separately. `sN` means that path's result from step N. `pos` makes the MiniVM sort permutation visible in SQL.

### Step 1 — Build the display label (`s1`)

```sql
-- Before: include the unused customer, quantity, uppercase note and weekday.
SELECT o_id,o_amt,o_date,o_cust,o_qty,upper(o_note) AS spare_note,
	   (cast(strftime('%w',o_date) AS integer)+6)%7+1 AS weekday,
	   substr(nullif(coalesce(o_note,'')||' '||coalesce(o_status,''),''),1,40) AS label FROM orders;
-- After: keep precisely the same 40-character label, including its separator.
SELECT o_id,o_amt,o_date,
	   substr(nullif(coalesce(o_note,'')||' '||coalesce(o_status,''),''),1,40) AS label FROM orders;
```

### Step 2 — Rank all orders by amount, then ID (`s2`)

```sql
-- Before
SELECT s1.*,row_number() OVER (ORDER BY o_amt DESC NULLS LAST,o_id ASC NULLS FIRST) AS pos FROM s1;
-- After: narrower rows, same sort keys; this is not yet a TOPK plan.
SELECT s1.*,row_number() OVER (ORDER BY o_amt DESC NULLS LAST,o_id ASC NULLS FIRST) AS pos FROM s1;
```

### Step 3 — Filter to July without losing the relative order (`s3`)

```sql
-- Before
SELECT * FROM s2 WHERE strftime('%Y-%m',o_date)='2023-07';
-- After: the date is needed for filtering but not for display.
SELECT pos,o_id,o_amt,label FROM s2 WHERE strftime('%Y-%m',o_date)='2023-07';
```

### Step 4 — Take the first five qualifying positions

```sql
-- Before
SELECT o_id,o_amt,label FROM s3 ORDER BY pos LIMIT 5;
-- After: the limit is still after the filter; only three fixture rows qualify.
SELECT o_id,o_amt,label FROM s3 ORDER BY pos LIMIT 5;
```

### Before SQL — build a wide display row and rank before the July filter

```sql
WITH ranked AS (
	SELECT o_id, o_amt, o_date, o_cust, o_qty, upper(o_note) AS spare_note,
		   (cast(strftime('%w', o_date) AS integer) + 6) % 7 + 1 AS unused_weekday,
		   substr(nullif(coalesce(o_note, '') || ' ' || coalesce(o_status, ''), ''), 1, 40) AS label,
		   row_number() OVER (ORDER BY o_amt DESC NULLS LAST, o_id ASC NULLS FIRST) AS position
	FROM orders
)
SELECT o_id, o_amt, label FROM ranked
WHERE strftime('%Y-%m', o_date) = '2023-07' ORDER BY position LIMIT 5;
```

### After SQL — omit unused displays, retain the same ranking contract

```sql
SELECT o_id, o_amt,
	   substr(nullif(coalesce(o_note, '') || ' ' || coalesce(o_status, ''), ''), 1, 40) AS label
FROM orders
WHERE o_date >= '2023-07-01' AND o_date < '2023-08-01'
ORDER BY o_amt DESC NULLS LAST, o_id ASC NULLS FIRST
LIMIT 5;
```

The half-open interval expresses the plan's year and month tests. SQL describes the top five **among July orders**; it does not mean the current optimizer physically moved the date test or emitted `TOPK`.