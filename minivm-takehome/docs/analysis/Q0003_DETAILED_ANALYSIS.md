# Q0003 — Four latest orders per normalized status

[Original](../../examples/programs/q0003.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0003.mini) · [Expected output](../../examples/expected/q0003.json)

**Native sample: 8,562 → 8,496 cycles; 66 saved (0.77%).** Twelve rows sorted by ascending order ID. The three output columns are `(ID, original status, ID)`; the repeated ID is intentional.

The plan applies `NULLIFE`, `RTRIM`, and `UPPER` before self-joining on status. The join has no `NULLEQ`, so NULL keys do not match. For each left order, the plan counts better right-side matches and keeps orders with fewer than four. It uses normalized status for matching but gathers the unmodified status for display. A global `TOPK 4` would choose four orders overall, not four per status.

**Current rewrite:** removes the unused customer column and its gathers. The duplicated ID gathers, pairwise ranking, and final sort remain. A grouped rewrite would need to preserve the ranking comparisons, NULL behavior, original spelling, and both ID output positions.

## Step by step

Each `sN` below is the result of step N in the corresponding Before or After path.

### Step 1 — Load orders and normalize status (`s1`)

```sql
-- Before
SELECT o_id,o_cust,o_status,upper(rtrim(nullif(o_status,''))) AS k FROM orders;
-- After: customer ID is unused; keep the original spelling as well as the key.
SELECT o_id,o_status,upper(rtrim(nullif(o_status,''))) AS k FROM orders;
```

### Step 2 — Join orders that share a non-NULL status (`s2`)

```sql
-- Before
SELECT a.*, b.o_id AS peer FROM s1 AS a JOIN s1 AS b ON b.k=a.k;
-- After: a.* no longer carries customer ID. The join population is unchanged.
SELECT a.*, b.o_id AS peer FROM s1 AS a JOIN s1 AS b ON b.k=a.k;
```

### Step 3 — Count better peers and keep ranks one through four (`s3`)

```sql
-- Before
SELECT o_id,o_status,o_cust FROM s2 GROUP BY o_id,o_status,o_cust
HAVING sum(CASE WHEN peer>o_id OR (peer=o_id AND peer<o_id) THEN 1 ELSE 0 END)<4;
-- After: customer ID drops out; the VM still performs the same comparisons.
SELECT o_id,o_status FROM s2 GROUP BY o_id,o_status
HAVING sum(CASE WHEN peer>o_id OR (peer=o_id AND peer<o_id) THEN 1 ELSE 0 END)<4;
```

### Step 4 — Sort by ID and display the original spelling

```sql
-- Before
SELECT o_id,o_status,o_id FROM s3 ORDER BY o_id;
-- After: the repeated output ID is intentional, unlike the unused customer input.
SELECT o_id,o_status,o_id FROM s3 ORDER BY o_id;
```

### Before SQL — carry customer ID through selection

```sql
WITH keyed AS (
	SELECT o_id, o_cust, o_status, upper(rtrim(nullif(o_status, ''))) AS k FROM orders
), selected AS (
	SELECT a.o_id, a.o_cust, a.o_status
	FROM keyed AS a JOIN keyed AS b ON a.k = b.k
	GROUP BY a.o_id, a.o_cust, a.o_status
	HAVING sum(CASE WHEN b.o_id > a.o_id OR
			  (b.o_id = a.o_id AND b.o_id < a.o_id) THEN 1 ELSE 0 END) < 4
)
SELECT o_id, o_status, o_id FROM selected ORDER BY o_id;
```

### After SQL — drop the customer field, not the repeated output ID

```sql
WITH keyed AS (
	SELECT o_id, o_status, upper(rtrim(nullif(o_status, ''))) AS status_key FROM orders
)
SELECT a.o_id, a.o_status, a.o_id
FROM keyed AS a JOIN keyed AS b ON b.status_key = a.status_key
GROUP BY a.o_id, a.o_status
HAVING sum(CASE WHEN b.o_id > a.o_id THEN 1 ELSE 0 END) < 4
ORDER BY a.o_id;
```

The additional tie branch in the MiniVM compares the same ID pair for both equality and strict inequality; it cannot add a better match. The SQL simplifies that predicate, not the physical self-join.