# Q0008 — Count and quantity by order status

[Original](../../examples/programs/q0008.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0008.mini) · [Expected output](../../examples/expected/q0008.json)

**Native sample: 1,524 → 1,249 cycles; 275 saved (18.04%).** Three rows of `(display status, order count, total quantity)`; the first is `["shipped", 10, 67]`.

The quantity filter (`o_qty >= 5`) runs before grouping. The plan applies `NULLIFE` to status and normalizes it with `RTRIM` and `UPPER` for the group key. Within each group, `GMIN` chooses a display spelling from the **pre-normalized** values after `NULLIFE`. `GCOUNT` and `GSUM` supply the two numeric outputs. The final sort is by descending count, then by a key derived from the first ten characters of the chosen spelling, trimmed and uppercased.

**Current rewrite:** only quantity and status need to be loaded. Removing the other five order columns also removes their filtered gathers. The choice of display spelling and the final sort remain live. Replacing the spelling with the normalized key could change both the displayed text and the tie order.

## Step by step

`sN` is the output of step N on the same path. `pos` records fixture insertion order so SQL can reproduce MiniVM's stable ordering.

### Step 1 — Filter orders by quantity (`s1`)

```sql
-- Before: gather the whole order row.
SELECT rowid AS pos,o_id,o_cust,o_date,o_amt,o_qty,o_status,o_note FROM orders WHERE o_qty>=5;
-- After: only quantity and status feed the groups.
SELECT rowid AS pos,o_qty,o_status FROM orders WHERE o_qty>=5;
```

### Step 2 — Separate the display spelling from the grouping key (`s2`)

```sql
-- Before
SELECT pos,o_qty,nullif(o_status,'') AS spelling,upper(rtrim(nullif(o_status,''))) AS k FROM s1;
-- After: do not replace spelling with k; the displayed value can differ.
SELECT pos,o_qty,nullif(o_status,'') AS spelling,upper(rtrim(nullif(o_status,''))) AS k FROM s1;
```

### Step 3 — Group, choose the spelling, count, and sum (`s3`)

```sql
-- Before
SELECT min(spelling COLLATE BINARY) AS rep,count(*) AS n,sum(o_qty) AS qty,min(pos) AS first_pos
FROM s2 GROUP BY k;
-- After: same aggregate inputs after dropping unrelated columns in Step 1.
SELECT min(spelling COLLATE BINARY) AS rep,count(*) AS n,sum(o_qty) AS qty,min(pos) AS first_pos
FROM s2 GROUP BY k;
```

### Step 4 — Sort by count and the display-derived key

```sql
-- Before
SELECT rep,n,qty FROM s3 ORDER BY n DESC,upper(rtrim(substr(rep,1,10))) ASC NULLS FIRST,first_pos;
-- After: first group appearance still breaks ties on both explicit keys.
SELECT rep,n,qty FROM s3 ORDER BY n DESC,upper(rtrim(substr(rep,1,10))) ASC NULLS FIRST,first_pos;
```

### Before SQL — gather the wide order row after filtering

```sql
WITH wide AS (
	SELECT rowid AS input_pos, o_id, o_cust, o_date, o_amt, o_qty, o_status, o_note
	FROM orders WHERE o_qty >= 5
), grouped AS (
	SELECT min(nullif(o_status, '') COLLATE BINARY) AS display_status,
		   count(*) AS n, sum(o_qty) AS total_qty, min(input_pos) AS first_pos
	FROM wide GROUP BY upper(rtrim(nullif(o_status, '')))
)
SELECT display_status, n, total_qty FROM grouped
ORDER BY n DESC, upper(rtrim(substr(display_status, 1, 10))) ASC NULLS FIRST, first_pos;
```

### After SQL — group just the quantity and spelling

```sql
WITH qualifying AS (
	SELECT rowid AS input_pos, nullif(o_status, '') AS spelling, o_qty
	FROM orders WHERE o_qty >= 5
), grouped AS (
	SELECT min(spelling COLLATE BINARY) AS display_status,
		   count(*) AS n, sum(o_qty) AS total_qty, min(input_pos) AS first_pos
	FROM qualifying
	GROUP BY upper(rtrim(spelling))
)
SELECT display_status, n, total_qty FROM grouped
ORDER BY n DESC, upper(rtrim(substr(display_status, 1, 10))) ASC NULLS FIRST, first_pos;
```

MiniVM groups are emitted in first-appearance order and its final sort is stable. Here `rowid` represents fixture insertion order in an ordinary SQLite table. If rows were loaded in another order, use an explicit source ordinal instead.