CREATE OR REPLACE TABLE analytics.dim_customers AS SELECT * FROM staging.customers;
CREATE OR REPLACE TABLE analytics.dim_sellers AS SELECT * FROM staging.sellers;
CREATE OR REPLACE TABLE analytics.dim_products AS SELECT * FROM staging.products;

-- Grain: order_id + order_item_id. Never join raw payments or reviews to this fact.
CREATE OR REPLACE TABLE analytics.fact_order_items AS
SELECT i.*, p.category, s.seller_state
FROM staging.items i
LEFT JOIN staging.products p USING (product_id)
LEFT JOIN staging.sellers s USING (seller_id);

-- Aggregate each child table BEFORE joining. This prevents money inflation.
CREATE OR REPLACE TABLE analytics.fact_orders AS
WITH item_totals AS (
    SELECT order_id, count(*) AS item_count, count(DISTINCT seller_id) AS seller_count,
           CASE WHEN count(DISTINCT seller_id) = 1 THEN min(seller_id) END AS sole_seller_id,
           sum(item_value_brl) AS item_value_brl, sum(freight_value_brl) AS freight_value_brl
    FROM staging.items GROUP BY order_id
), payment_totals AS (
    SELECT order_id, count(*) AS payment_count, sum(payment_value_brl) AS payment_value_brl
    FROM staging.payments GROUP BY order_id
), category_values AS (
    SELECT order_id, coalesce(category, 'unknown') AS category, sum(item_value_brl) AS category_value
    FROM analytics.fact_order_items GROUP BY order_id, coalesce(category, 'unknown')
), primary_category AS (
    SELECT order_id, category AS primary_category FROM category_values
    QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY category_value DESC, category) = 1
), assembled AS (
    SELECT o.*, c.customer_unique_id, c.customer_state,
           coalesce(i.item_count, 0) AS item_count, coalesce(i.seller_count, 0) AS seller_count,
           i.sole_seller_id, s.seller_state,
           coalesce(i.item_value_brl, 0) AS item_value_brl,
           coalesce(i.freight_value_brl, 0) AS freight_value_brl,
           p.payment_value_brl, coalesce(p.payment_count, 0) AS payment_count,
           coalesce(k.primary_category, 'unknown') AS primary_category,
           r.review_id, r.review_score, r.review_answered_at,
           date_trunc('month', o.purchased_at)::DATE AS purchase_month,
           (o.order_status = 'delivered' AND o.purchased_at IS NOT NULL
            AND o.delivered_at IS NOT NULL AND o.estimated_at IS NOT NULL
            AND o.delivered_at >= o.purchased_at
            AND o.estimated_at::DATE >= o.purchased_at::DATE) AS delivery_eligible,
           epoch(o.delivered_at - o.purchased_at) / 86400.0 AS delivery_days,
           CASE WHEN o.handed_to_carrier_at >= o.purchased_at
                THEN epoch(o.handed_to_carrier_at - o.purchased_at) / 86400.0 END AS handling_days,
           CASE WHEN o.delivered_at >= o.handed_to_carrier_at
                THEN epoch(o.delivered_at - o.handed_to_carrier_at) / 86400.0 END AS transit_days,
           date_diff('day', o.estimated_at::DATE, o.delivered_at::DATE) AS delay_days
    FROM staging.orders o
    LEFT JOIN staging.customers c USING (customer_id)
    LEFT JOIN item_totals i USING (order_id)
    LEFT JOIN staging.sellers s ON i.sole_seller_id = s.seller_id
    LEFT JOIN payment_totals p USING (order_id)
    LEFT JOIN primary_category k USING (order_id)
    LEFT JOIN staging.reviews r USING (order_id)
)
SELECT *, CASE WHEN delivery_eligible THEN delivered_at::DATE > estimated_at::DATE END AS is_late,
          CASE WHEN review_score BETWEEN 1 AND 5 THEN review_score <= 2 END AS is_poor_review,
          CASE WHEN payment_value_brl IS NOT NULL
               THEN payment_value_brl - item_value_brl - freight_value_brl END AS payment_difference_brl
FROM assembled;

CREATE OR REPLACE TABLE analytics.dim_dates AS
SELECT d::DATE AS date_id, year(d) AS year, month(d) AS month,
       date_trunc('month', d)::DATE AS month_start
FROM generate_series(
    (SELECT min(purchased_at)::DATE FROM analytics.fact_orders),
    (SELECT max(purchased_at)::DATE FROM analytics.fact_orders), INTERVAL 1 DAY
) AS dates(d);

-- Historical purchase cohort, not a current operational alerting system.
CREATE OR REPLACE VIEW analytics.monthly_delivery AS
SELECT purchase_month, count(*) AS orders,
       sum(item_value_brl) AS item_value_brl,
       count(*) FILTER (WHERE delivery_eligible) AS eligible_orders,
       count(*) FILTER (WHERE is_late) AS late_orders,
       100.0 * count(*) FILTER (WHERE is_late)
         / nullif(count(*) FILTER (WHERE delivery_eligible), 0) AS late_rate_pct,
       median(delivery_days) FILTER (WHERE delivery_eligible) AS median_delivery_days
FROM analytics.fact_orders GROUP BY purchase_month;
