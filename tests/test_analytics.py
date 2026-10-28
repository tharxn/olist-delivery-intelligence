"""Tiny synthetic fixtures test edge cases; project findings use original Olist data."""
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from src import analysis as a
from src.pipeline import load_raw, transform
from src.quality import validate


@pytest.fixture
def warehouse(tmp_path):
    def save(filename, rows, columns=None):
        pd.DataFrame(rows, columns=columns).to_csv(tmp_path / filename, index=False)

    order_rows = []
    for order_id, status, actual, promise in [
        ("a", "delivered", "2018-01-05 21:00:00", "2018-01-05 00:00:00"),
        ("b", "delivered", "2018-01-06 00:01:00", "2018-01-05 00:00:00"),
        ("c", "delivered", "2018-01-04 10:00:00", None),
        ("d", "canceled", None, "2018-01-05 00:00:00"),
    ]:
        order_rows.append({
            "order_id": order_id, "customer_id": "buyer", "order_status": status,
            "order_purchase_timestamp": "2018-01-01 10:00:00", "order_approved_at": "2018-01-01 11:00:00",
            "order_delivered_carrier_date": "2018-01-02 10:00:00" if actual else None,
            "order_delivered_customer_date": actual, "order_estimated_delivery_date": promise,
        })
    save("olist_orders_dataset.csv", order_rows)
    save("olist_customers_dataset.csv", [{"customer_id": "buyer", "customer_unique_id": "person", "customer_zip_code_prefix": "00123", "customer_city": "city", "customer_state": "SP"}])
    save("olist_sellers_dataset.csv", [
        {"seller_id": seller, "seller_zip_code_prefix": "00123", "seller_city": "city", "seller_state": "SP"}
        for seller in ("s1", "s2")
    ])
    save("olist_products_dataset.csv", [{"product_id": "p1", "product_category_name": "category_pt"}])
    save("product_category_name_translation.csv", [{"product_category_name": "category_pt", "product_category_name_english": "category_en"}])
    save("olist_order_items_dataset.csv", [
        {"order_id": order_id, "order_item_id": item_id, "product_id": "p1", "seller_id": seller,
         "shipping_limit_date": "2018-01-03 00:00:00", "price": price, "freight_value": freight}
        for order_id, item_id, seller, price, freight in [
            ("a", 1, "s1", 10, 1), ("a", 2, "s1", 20, 2),
            ("b", 1, "s1", 20, 2), ("b", 2, "s2", 20, 2), ("c", 1, "s2", 10, 1),
        ]
    ])
    save("olist_order_payments_dataset.csv", [
        {"order_id": order_id, "payment_sequential": sequential, "payment_type": "credit_card",
         "payment_installments": 1, "payment_value": value}
        for order_id, sequential, value in [("a", 1, 15), ("a", 2, 18), ("b", 1, 44), ("c", 1, 11)]
    ])
    save("olist_order_reviews_dataset.csv", [
        {"order_id": order_id, "review_id": review, "review_score": score,
         "review_creation_date": "2018-01-06 00:00:00", "review_answer_timestamp": answered}
        for order_id, review, score, answered in [
            ("a", "old", 1, "2018-01-06 12:00:00"),
            ("a", "new", 5, "2018-01-07 12:00:00"),
            ("b", "review_b", 1, "2018-01-07 12:00:00"),
        ]
    ])
    connection = duckdb.connect()
    load_raw(connection, tmp_path)
    transform(connection)
    yield connection
    connection.close()


def frame(connection):
    return connection.execute("SELECT * FROM analytics.fact_orders").fetchdf()


def test_money_does_not_multiply_across_child_tables(warehouse):
    row = warehouse.execute("SELECT item_count, item_value_brl, freight_value_brl, payment_value_brl FROM analytics.fact_orders WHERE order_id='a'").fetchone()
    assert tuple(float(value) for value in row) == (2, 30, 3, 33)
    assert warehouse.execute("SELECT count(*) FROM analytics.fact_orders").fetchone()[0] == 4
    assert validate(warehouse)["passed"]


def test_calendar_day_deadline_and_missing_estimate(warehouse):
    facts = frame(warehouse).set_index("order_id")
    assert not facts.loc["a", "is_late"]  # Delivered at 9 p.m. on the promise date.
    assert facts.loc["b", "is_late"]
    assert not facts.loc["c", "delivery_eligible"]
    assert pd.isna(facts.loc["c", "is_late"])
    assert not facts.loc["d", "delivery_eligible"]
    stats = a.summary(frame(warehouse))
    assert stats["eligible_orders"] == 2
    assert stats["late_rate_pct"] == 50


def test_latest_review_and_review_denominators(warehouse):
    assert warehouse.execute("SELECT review_score FROM analytics.fact_orders WHERE order_id='a'").fetchone()[0] == 5
    comparison = a.review_comparison(frame(warehouse)).set_index("delivery")
    assert comparison.loc["Late", "poor_review_pct"] == 100
    assert comparison.loc["On time", "poor_review_pct"] == 0
    assert comparison.reviewed_orders.sum() == 2


def test_multi_seller_attribution_is_excluded(warehouse):
    assert warehouse.execute("SELECT sole_seller_id FROM analytics.fact_orders WHERE order_id='b'").fetchone()[0] is None
    scorecard = a.sellers(frame(warehouse), minimum=1)
    assert scorecard.eligible_orders.sum() == 1
    assert set(scorecard.seller_id) == {"s1"}


def test_review_timing_sensitivity_excludes_pre_delivery_answers(warehouse):
    orders = frame(warehouse)
    orders.loc[orders.order_id == "b", "review_answered_at"] = pd.Timestamp("2018-01-05 12:00:00")
    full = a.review_comparison(orders)
    after_delivery = a.review_comparison(orders, post_delivery_only=True)
    assert "Late" in full.delivery.values
    assert "Late" not in after_delivery.delivery.values
    metrics = a.summary(orders)
    assert metrics["late_reviewed"] == 1
    assert metrics["late_post_delivery_reviewed"] == 0
    assert pd.isna(metrics["late_post_delivery_poor_review_pct"])


def test_seller_baseline_is_not_changed_by_volume_cutoff():
    rows = []
    for index in range(101):
        rows.append({"delivery_eligible": True, "seller_count": 1,
                     "sole_seller_id": "large" if index < 100 else "small", "seller_state": "SP",
                     "is_late": index < 50, "handling_days": 1.0, "transit_days": 4.0})
    scorecard = a.sellers(pd.DataFrame(rows), minimum=30)
    assert len(scorecard) == 1
    assert scorecard.baseline_rate.iloc[0] == pytest.approx(50 / 101)
    assert scorecard.wilson_lower.iloc[0] < 0.5 < scorecard.wilson_upper.iloc[0]


def test_date_filter_includes_the_whole_end_date(warehouse):
    orders = frame(warehouse)
    assert len(a.filter_orders(orders, "2018-01-01", "2018-01-01")) == 4
    assert a.filter_orders(orders, "2018-01-02", "2018-01-02").empty


def test_invalid_join_dimension_is_rejected(warehouse):
    with pytest.raises(ValueError):
        a.segments(frame(warehouse), "untrusted_column")


def test_quality_checks_catch_an_inflated_order_fact(warehouse):
    warehouse.execute("INSERT INTO analytics.fact_orders SELECT * FROM analytics.fact_orders WHERE order_id='a'")
    with pytest.raises(ValueError, match="one_fact_row_per_order"):
        validate(warehouse)
