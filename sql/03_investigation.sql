-- Interview exercises: run these against data/processed/olist.duckdb.
-- 1. How much money would naive child-table joins duplicate?
SELECT 'correct' AS method, sum(item_value_brl) AS item_value_brl FROM analytics.fact_order_items
UNION ALL
SELECT 'naive_items_x_payments', sum(i.item_value_brl)
FROM staging.items i JOIN staging.payments p USING (order_id);

-- 2. Cohort comparisons: calendar-date promise, reviewed orders in denominator.
SELECT is_late, count(*) AS eligible_orders,
       count(is_poor_review) AS reviewed_orders,
       avg(is_poor_review::INTEGER) * 100 AS poor_review_pct
FROM analytics.fact_orders WHERE delivery_eligible GROUP BY is_late;

-- 3. Which destination states contain the most late orders?
SELECT customer_state, count(*) AS eligible_orders, count(*) FILTER (WHERE is_late) AS late_orders,
       avg(is_late::INTEGER) * 100 AS late_rate_pct,
       median(delivery_days) AS median_delivery_days
FROM analytics.fact_orders WHERE delivery_eligible
GROUP BY customer_state HAVING count(*) >= 100 ORDER BY late_orders DESC;

-- 4. Is the late/poor-review association consistent within category and state?
SELECT primary_category, customer_state,
       count(*) FILTER (WHERE is_late AND is_poor_review IS NOT NULL) AS late_reviewed,
       count(*) FILTER (WHERE NOT is_late AND is_poor_review IS NOT NULL) AS on_time_reviewed,
       avg(is_poor_review::INTEGER) FILTER (WHERE is_late) * 100 AS late_poor_review_pct,
       avg(is_poor_review::INTEGER) FILTER (WHERE NOT is_late) * 100 AS on_time_poor_review_pct
FROM analytics.fact_orders WHERE delivery_eligible
GROUP BY primary_category, customer_state
HAVING count(*) FILTER (WHERE is_late AND is_poor_review IS NOT NULL) >= 20
   AND count(*) FILTER (WHERE NOT is_late AND is_poor_review IS NOT NULL) >= 20
ORDER BY late_reviewed DESC;
