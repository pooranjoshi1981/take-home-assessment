# Q0006 — Maximum status-group quantity for each order

[Original](../../examples/programs/q0006.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0006.mini) · [Expected output](../../examples/expected/q0006.json)

**Native sample: 6,338 → 6,168 cycles; 170 saved (2.68%).** There are **30 rows and three columns**: `(order ID, order amount, maximum quantity for its status)`. The first row is `[1, "892.43", 9]`. Individual order quantity participates in the maximum but is not a fourth output column.

The date mask keeps orders on or after 2023-01-01. The plan normalizes their status, self-joins the filtered population by that key, groups by **left row position**, and takes `GMAX` over matched right-side quantities. This produces a maximum for each matched order, rather than one output row per status. The final sort orders rows by ID.

**Current rewrite:** removes unused gathers, including the filtered date copy. The self-join and `IOTA r28, r20` / `GATHER r29, r20, r28` identity copy remain. A grouped maximum mapped back to each eligible order could avoid producing pairs, but must exclude NULL normalized status just as the original join does and retain each order's own amount.

## Step by step

Use each step's result as `sN` in the next step, following Before and After separately.

### Step 1 — Filter eligible dates and prepare status keys (`s1`)

```sql
-- Before: gather the date and raw spelling too.
SELECT o_id,o_amt,o_qty,o_date,o_status,upper(rtrim(nullif(o_status,''))) AS k
FROM orders WHERE o_date>='2023-01-01';
-- After: the date predicate stays even though its filtered output column goes away.
SELECT o_id,o_amt,o_qty,upper(rtrim(nullif(o_status,''))) AS k
FROM orders WHERE o_date>='2023-01-01';
```

### Step 2 — Join each eligible order to peers of the same status (`s2`)

```sql
-- Before
SELECT a.*,b.o_qty AS peer_qty FROM s1 a JOIN s1 b ON b.k=a.k;
-- After: the same status matches, without carrying the left order's display candidates.
SELECT a.o_id,a.o_amt,b.o_qty AS peer_qty FROM s1 a JOIN s1 b ON b.k=a.k;
```

### Step 3 — Find the maximum per left order (`s3`)

```sql
-- Before: extra left-row fields survive as display candidates.
SELECT o_id,o_amt,o_date,o_status,o_qty,max(peer_qty) AS mx FROM s2
GROUP BY o_id,o_amt,o_date,o_status,o_qty;
-- After: the order ID is a key; removing unused fields does not merge orders.
SELECT o_id,o_amt,max(peer_qty) AS mx FROM s2 GROUP BY o_id,o_amt;
```

### Step 4 — Sort and return ID, amount, and maximum

```sql
-- Before
SELECT o_id,o_amt,mx FROM s3 ORDER BY o_id;
-- After: use the left order's amount, not the amount of the maximum-quantity peer.
SELECT o_id,o_amt,mx FROM s3 ORDER BY o_id;
```

### Before SQL — carry the filtered date and unused display fields

```sql
WITH eligible AS (
	SELECT o_id, o_amt, o_qty, o_date, o_status, upper(rtrim(nullif(o_status, ''))) AS k
	FROM orders WHERE o_date >= '2023-01-01'
), per_order AS (
	SELECT a.o_id, a.o_amt, a.o_date, a.o_status, a.o_qty, max(b.o_qty) AS status_max_qty
	FROM eligible AS a JOIN eligible AS b ON a.k = b.k
	GROUP BY a.o_id, a.o_amt, a.o_date, a.o_status, a.o_qty
)
SELECT o_id, o_amt, status_max_qty FROM per_order ORDER BY o_id;
```

### After SQL — keep the date test without carrying the date

```sql
WITH eligible AS (
	SELECT o_id, o_amt, o_qty, upper(rtrim(nullif(o_status, ''))) AS status_key
	FROM orders WHERE o_date >= '2023-01-01'
)
SELECT a.o_id, a.o_amt, max(b.o_qty) AS status_max_qty
FROM eligible AS a JOIN eligible AS b ON b.status_key = a.status_key
GROUP BY a.o_id, a.o_amt ORDER BY a.o_id;
```

The date filter applies to both sides; a larger quantity from an older order cannot set the maximum. Grouping by the left order keeps one output per matched order, not one per status.