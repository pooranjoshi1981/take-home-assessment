# Q0002 — Count smaller discounted lines

[Original](../../examples/programs/q0002.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0002.mini) · [Expected output](../../examples/expected/q0002.json)

**Native sample: 3,617 → 3,527 cycles; 90 saved (2.49%).** Seven rows of `(order ID, line number, count)`, ordered by order ID then line number.

The `GT` on discount and subsequent gathers select discounted lines. The self-join pairs each such line with every discounted line of the same product. The plan compares their quantities, converts each comparison to 1 or 0, and sums by the left row position. Counting the comparisons rather than filtering away false ones keeps lines whose count is zero. Only after counting does the report retain orders from 2023 with amount above 300.

**Current rewrite:** drop the second, unused discount load (`t5_l_d`). The self-join and sort remain. A future pass may filter the **left/report** side earlier, but filtering the right side to eligible orders would silently undercount smaller lines from other orders.

## Step by step

Follow **Before** or **After** from top to bottom; each `sN` names that path's result from step N.

### Step 1 — Load and filter discounted lines (`s1`)

```sql
-- Before: the second discount register has no reader.
SELECT l_order, l_no, l_prod, l_qty, l_disc AS unused_discount FROM lines WHERE l_disc>0;
-- After: still read discount for the predicate; do not load a second copy.
SELECT l_order, l_no, l_prod, l_qty FROM lines WHERE l_disc>0;
```

### Step 2 — Self-join on product (`s2`)

```sql
-- Before
SELECT a.l_order, a.l_no, a.l_qty AS report_qty, b.l_qty AS peer_qty
FROM s1 AS a JOIN s1 AS b ON b.l_prod=a.l_prod;
-- After: the same peers, including discounted lines outside the report's year.
SELECT a.l_order, a.l_no, a.l_qty AS report_qty, b.l_qty AS peer_qty
FROM s1 AS a JOIN s1 AS b ON b.l_prod=a.l_prod;
```

### Step 3 — Count smaller peers per left line (`s3`)

```sql
-- Before
SELECT l_order, l_no, sum(CASE WHEN peer_qty<report_qty THEN 1 ELSE 0 END) AS n
FROM s2 GROUP BY l_order, l_no;
-- After: keep the zero counts; do not filter out false comparisons.
SELECT l_order, l_no, sum(CASE WHEN peer_qty<report_qty THEN 1 ELSE 0 END) AS n
FROM s2 GROUP BY l_order, l_no;
```

### Step 4 — Filter report orders and sort the output

```sql
-- Before
SELECT c.l_order, c.l_no, c.n FROM s3 AS c JOIN orders AS o ON o.o_id=c.l_order
WHERE strftime('%Y',o.o_date)='2023' AND o.o_amt>300 ORDER BY c.l_order,c.l_no;
-- After: the order filter still applies to the reported line, not its peers.
SELECT c.l_order, c.l_no, c.n FROM s3 AS c JOIN orders AS o ON o.o_id=c.l_order
WHERE strftime('%Y',o.o_date)='2023' AND o.o_amt>300 ORDER BY c.l_order,c.l_no;
```

### Before SQL — the duplicate discount read

```sql
WITH loaded AS (
	SELECT l_order, l_no, l_prod, l_qty, l_disc, l_disc AS unused_discount FROM lines
), discounted AS (
	SELECT l_order, l_no, l_prod, l_qty FROM loaded WHERE l_disc > 0
), counts AS (
	SELECT a.l_order, a.l_no,
		   sum(CASE WHEN b.l_qty < a.l_qty THEN 1 ELSE 0 END) AS smaller_count
	FROM discounted AS a JOIN discounted AS b ON a.l_prod = b.l_prod
	GROUP BY a.l_order, a.l_no
)
SELECT c.l_order, c.l_no, c.smaller_count
FROM counts AS c JOIN orders AS o ON o.o_id = c.l_order
WHERE strftime('%Y', o.o_date) = '2023' AND o.o_amt > 300
ORDER BY c.l_order, c.l_no;
```

### After SQL — read the discount once; count the same peers

```sql
WITH discounted AS (
	SELECT l_order, l_no, l_prod, l_qty FROM lines WHERE l_disc > 0
), counts AS (
	SELECT a.l_order, a.l_no,
		   sum(CASE WHEN b.l_qty < a.l_qty THEN 1 ELSE 0 END) AS smaller_count
	FROM discounted AS a JOIN discounted AS b ON b.l_prod = a.l_prod
	GROUP BY a.l_order, a.l_no
)
SELECT c.l_order, c.l_no, c.smaller_count
FROM counts AS c JOIN orders AS o ON o.o_id = c.l_order
WHERE strftime('%Y', o.o_date) = '2023' AND o.o_amt > 300
ORDER BY c.l_order, c.l_no;
```

The declared line key identifies the left row. `ELSE 0` matters: a line can match its own product but have no smaller peer.