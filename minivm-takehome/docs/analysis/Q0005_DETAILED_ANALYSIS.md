# Q0005 — Revenue from orders with a card payment

[Original](../../examples/programs/q0005.mini) · [Optimized](../../GPT6.2-MiniVM/optimized-examples/q0005.mini) · [Expected output](../../examples/expected/q0005.json)

**Native sample: 5,518 → 4,723 cycles; 795 saved (14.41%).** Two rows: `Tools` with `64127.7480`, then `Garden` with `31081.8260`. The final ordering is by category ID, not display name or revenue.

The payment filter tests the normalized method against `CARD`. Joining qualifying payments to lines can repeat a line if its order has several card payments. The plan sorts and groups by `(line order ID, line number)` and uses `GFIRST` to take one representative. It then attaches product category, calculates discounted line revenue, sums by category ID, and looks up the category name.

**Current rewrite:** remove unused payment amounts and intermediate gathers. The join, sort, and line-key deduplication still execute. A possible next rewrite is to deduplicate the **qualifying payment order IDs** before joining. The declared composite line key is what permits one contribution per line; deduplicating only by order on the line side would lose revenue from distinct lines.

## Step by step

Each `sN` names the result of step N on the same SQL path. `pay_pos` models payment input order for the stable first-match selection.

### Step 1 — Filter card payments (`s1`)

```sql
-- Before
SELECT rowid AS pay_pos,y_order,y_method,y_amt FROM payments
WHERE upper(rtrim(nullif(y_method,'')))='CARD';
-- After: the method decides eligibility, but only the qualifying order IDs are needed.
SELECT rowid AS pay_pos,y_order FROM payments WHERE upper(rtrim(nullif(y_method,'')))='CARD';
```

### Step 2 — Join payments to lines and keep one match per line (`s2`)

```sql
-- Before: payment details travel with the selected line.
SELECT * FROM (SELECT l.*,y.y_method,y.y_amt,
	row_number() OVER (PARTITION BY l.l_order,l.l_no ORDER BY y.pay_pos) AS pick
	FROM lines l JOIN s1 y ON y.y_order=l.l_order) WHERE pick=1;
-- After: keep the same first match but gather only line fields needed downstream.
SELECT l_prod,l_qty,l_price,l_disc FROM (SELECT l.*,
	row_number() OVER (PARTITION BY l.l_order,l.l_no ORDER BY y.pay_pos) AS pick
	FROM lines l JOIN s1 y ON y.y_order=l.l_order) WHERE pick=1;
```

### Step 3 — Join products and sum revenue by category (`s3`)

```sql
-- Before
SELECT p.p_cat,sum((l.l_qty*l.l_price)*(1-l.l_disc)) AS revenue FROM s2 l
JOIN products p ON p.p_id=l.l_prod GROUP BY p.p_cat;
-- After: line price, quantity and discount still determine revenue, not payment amount.
SELECT p.p_cat,sum((l.l_qty*l.l_price)*(1-l.l_disc)) AS revenue FROM s2 l
JOIN products p ON p.p_id=l.l_prod GROUP BY p.p_cat;
```

### Step 4 — Attach category names and order by category ID

```sql
-- Before
SELECT k.k_name,t.revenue FROM s3 t JOIN categories k ON k.k_id=t.p_cat ORDER BY k.k_id;
-- After: order by ID, not display name.
SELECT k.k_name,t.revenue FROM s3 t JOIN categories k ON k.k_id=t.p_cat ORDER BY k.k_id;
```

### Before SQL — join payment details, then keep one match per line

```sql
WITH matched AS (
	SELECT l.*, y.y_amt, y.y_method,
		   row_number() OVER (PARTITION BY l.l_order, l.l_no ORDER BY y.rowid) AS pick
	FROM lines AS l JOIN payments AS y ON y.y_order = l.l_order
	WHERE upper(rtrim(nullif(y.y_method, ''))) = 'CARD'
), totals AS (
	SELECT p.p_cat, sum((m.l_qty * m.l_price) * (1 - m.l_disc)) AS revenue
	FROM matched AS m JOIN products AS p ON p.p_id = m.l_prod
	WHERE m.pick = 1 GROUP BY p.p_cat
)
SELECT k.k_name, t.revenue FROM totals AS t
JOIN categories AS k ON k.k_id = t.p_cat ORDER BY k.k_id;
```

### After SQL — deduplicate line fields without carrying payment details

```sql
WITH paid_lines AS (
	SELECT DISTINCT l.l_order, l.l_no, l.l_prod, l.l_qty, l.l_price, l.l_disc
	FROM lines AS l JOIN payments AS y ON y.y_order = l.l_order
	WHERE upper(rtrim(nullif(y.y_method, ''))) = 'CARD'
), totals AS (
	SELECT p.p_cat, sum((l.l_qty * l.l_price) * (1 - l.l_disc)) AS revenue
	FROM paid_lines AS l JOIN products AS p ON p.p_id = l.l_prod
	GROUP BY p.p_cat
)
SELECT k.k_name, t.revenue FROM totals AS t
JOIN categories AS k ON k.k_id = t.p_cat ORDER BY k.k_id;
```

`DISTINCT` includes the line key: two different lines with the same price and quantity must still contribute twice. Payment amount is neither a filter nor part of the revenue formula.