# Optional Power BI handoff

The working dashboard is Streamlit. No `.pbix` file is included. The pipeline exports six CSV tables under `data/processed/power_bi/` so Power BI can be added later.

## Begin with an order-level model

Import `fact_orders`, `dim_customers`, `dim_sellers` and `dim_dates`. Set identifier fields to Text, timestamps to Date/Time, `date_id` and `purchase_month` to Date, flags to True/False, and money to Fixed Decimal Number.

Add a date-only `purchase_date` column from `purchased_at` in Power Query. Create these one-to-many relationships, filtering from dimension to fact:

| Dimension key | Fact key |
|---|---|
| dim_customers.customer_id | fact_orders.customer_id |
| dim_sellers.seller_id | fact_orders.sole_seller_id |
| dim_dates.date_id | fact_orders.purchase_date |

Mark `dim_dates` as the date table. Build the executive page from order-level measures. Using the seller dimension restricts the fact to single-seller orders, by design; label those pages clearly.

Leave `fact_order_items` and `dim_products` unloaded for the first version. They support a later item-level model. Adding both seller → orders → items and seller → items as active paths can create ambiguous filtering. Design that second model deliberately rather than enabling bidirectional relationships.

## Starting measures

```dax
Orders = COUNTROWS(fact_orders)

Eligible Deliveries =
CALCULATE([Orders], fact_orders[delivery_eligible] = TRUE())

Late Deliveries =
CALCULATE([Orders], fact_orders[is_late] = TRUE())

Late Delivery Rate = DIVIDE([Late Deliveries], [Eligible Deliveries])

Delivered Merchandise Value BRL =
CALCULATE(
    SUM(fact_orders[item_value_brl]),
    fact_orders[order_status] = "delivered"
)

Reviewed Eligible Orders =
CALCULATE(
    [Orders],
    fact_orders[delivery_eligible] = TRUE(),
    NOT ISBLANK(fact_orders[review_score])
)

Poor Reviewed Eligible Orders =
CALCULATE(
    [Orders],
    fact_orders[delivery_eligible] = TRUE(),
    fact_orders[review_score] IN {1, 2}
)

Poor Review Rate =
DIVIDE([Poor Reviewed Eligible Orders], [Reviewed Eligible Orders])
```

Format rates as percentages. A visual grouped by `is_late` then gives the late/on-time review comparison. Preserve the review-timing sensitivity with a separate filter or column for `review_answered_at >= delivered_at`.

Validate the unfiltered model against `reports/metrics.json` before adding slicers. The first version should reproduce the SQL answers. Seller Wilson calculations remain in the exported scorecard until you intentionally implement and validate them in the BI model.
