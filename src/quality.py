"""Checks protect analytical grain, denominators, relationships and money totals."""
import json


HARD_CHECKS = {
    "one_fact_row_per_order": "SELECT abs((SELECT count(*) FROM raw.orders) - (SELECT count(*) FROM analytics.fact_orders))",
    "unique_order_ids": "SELECT count(*) - count(DISTINCT order_id) FROM analytics.fact_orders",
    "non_null_order_ids": "SELECT count(*) FROM analytics.fact_orders WHERE order_id IS NULL",
    "unique_item_keys": "SELECT count(*) FROM (SELECT order_id, order_item_id FROM analytics.fact_order_items GROUP BY ALL HAVING count(*) > 1)",
    "unique_customer_keys": "SELECT count(*) - count(DISTINCT customer_id) FROM staging.customers",
    "unique_seller_keys": "SELECT count(*) - count(DISTINCT seller_id) FROM staging.sellers",
    "unique_product_keys": "SELECT count(*) - count(DISTINCT product_id) FROM staging.products",
    "items_have_orders": "SELECT count(*) FROM staging.items i LEFT JOIN staging.orders o USING (order_id) WHERE o.order_id IS NULL",
    "orders_have_customers": "SELECT count(*) FROM staging.orders o LEFT JOIN staging.customers c USING (customer_id) WHERE c.customer_id IS NULL",
    "items_have_products": "SELECT count(*) FROM staging.items i LEFT JOIN staging.products p USING (product_id) WHERE p.product_id IS NULL",
    "items_have_sellers": "SELECT count(*) FROM staging.items i LEFT JOIN staging.sellers s USING (seller_id) WHERE s.seller_id IS NULL",
    "reviews_have_orders": "SELECT count(*) FROM staging.reviews r LEFT JOIN staging.orders o USING (order_id) WHERE o.order_id IS NULL",
    "payments_have_orders": "SELECT count(*) FROM staging.payments p LEFT JOIN staging.orders o USING (order_id) WHERE o.order_id IS NULL",
    "valid_item_money": "SELECT count(*) FROM staging.items WHERE item_value_brl IS NULL OR freight_value_brl IS NULL OR item_value_brl < 0 OR freight_value_brl < 0",
    "valid_payment_money": "SELECT count(*) FROM staging.payments WHERE payment_value_brl IS NULL OR payment_value_brl < 0",
    "valid_purchase_timestamps": "SELECT count(*) FROM staging.orders WHERE purchased_at IS NULL",
    "valid_review_scores": "SELECT count(*) FROM staging.reviews WHERE review_score IS NULL OR review_score NOT BETWEEN 1 AND 5",
    "item_value_reconciles_to_source": "SELECT abs((SELECT sum(item_value_brl) FROM staging.items) - (SELECT sum(item_value_brl) FROM analytics.fact_orders))",
    "freight_reconciles_to_source": "SELECT abs((SELECT sum(freight_value_brl) FROM staging.items) - (SELECT sum(freight_value_brl) FROM analytics.fact_orders))",
    "payments_reconcile_to_source": "SELECT abs((SELECT sum(payment_value_brl) FROM staging.payments) - (SELECT sum(payment_value_brl) FROM analytics.fact_orders))",
    "late_flags_have_valid_denominator": "SELECT count(*) FROM analytics.fact_orders WHERE is_late IS NOT NULL AND NOT delivery_eligible",
    "multi_seller_orders_not_attributed": "SELECT count(*) FROM analytics.fact_orders WHERE seller_count > 1 AND sole_seller_id IS NOT NULL",
}

OBSERVATIONS = {
    "additional_reviews_resolved": "SELECT (SELECT count(*) FROM raw.reviews) - (SELECT count(*) FROM staging.reviews)",
    "delivered_orders_excluded_from_sla": "SELECT count(*) FROM analytics.fact_orders WHERE order_status = 'delivered' AND NOT delivery_eligible",
    "non_delivered_orders": "SELECT count(*) FROM analytics.fact_orders WHERE order_status <> 'delivered'",
    "multi_seller_orders": "SELECT count(*) FROM analytics.fact_orders WHERE seller_count > 1",
    "orders_without_items": "SELECT count(*) FROM analytics.fact_orders WHERE item_count = 0",
    "orders_without_payments": "SELECT count(*) FROM analytics.fact_orders WHERE payment_count = 0",
    "orders_without_reviews": "SELECT count(*) FROM analytics.fact_orders WHERE review_score IS NULL",
    "payment_mismatches_over_5_centavos": "SELECT count(*) FROM analytics.fact_orders WHERE abs(payment_difference_brl) > 0.05",
    "review_answer_before_delivery": "SELECT count(*) FROM analytics.fact_orders WHERE review_answered_at < delivered_at",
    "delivery_before_purchase": "SELECT count(*) FROM analytics.fact_orders WHERE delivered_at < purchased_at",
    "invalid_carrier_sequence": "SELECT count(*) FROM analytics.fact_orders WHERE handed_to_carrier_at < purchased_at OR delivered_at < handed_to_carrier_at",
    "unknown_primary_categories": "SELECT count(*) FROM analytics.fact_orders WHERE primary_category = 'unknown'",
}


def validate(connection, report_path=None):
    checks = []
    for name, sql in HARD_CHECKS.items():
        value = float(connection.execute(sql).fetchone()[0] or 0)
        checks.append({"name": name, "value": value, "passed": value == 0})
    observations = {name: int(connection.execute(sql).fetchone()[0]) for name, sql in OBSERVATIONS.items()}
    report = {"passed": all(c["passed"] for c in checks), "checks": checks, "observations": observations}
    if report_path:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        failed = [check["name"] for check in checks if not check["passed"]]
        raise ValueError(f"Data quality checks failed: {', '.join(failed)}")
    return report
