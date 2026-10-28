"""All KPI and segment aggregates are SQL, shared by the app and the saved report."""
import duckdb
import pandas as pd

from .config import DB


def load_orders(path=DB):
    with duckdb.connect(str(path), read_only=True) as connection:
        return connection.execute("SELECT * FROM analytics.fact_orders ORDER BY purchased_at, order_id").fetchdf()


def query(frame, sql, params=None):
    with duckdb.connect() as connection:
        connection.register("cohort", frame)
        return connection.execute(sql, params or []).fetchdf()


def summary(frame):
    return query(frame, """
        SELECT count(*) AS orders,
               count(*) FILTER (WHERE order_status = 'delivered') AS delivered_orders,
               count(*) FILTER (WHERE delivery_eligible) AS eligible_orders,
               count(*) FILTER (WHERE is_late) AS late_orders,
               100.0 * count(*) FILTER (WHERE is_late)
                 / nullif(count(*) FILTER (WHERE delivery_eligible), 0) AS late_rate_pct,
               median(delivery_days) FILTER (WHERE delivery_eligible) AS median_delivery_days,
               sum(item_value_brl::DECIMAL(18,2)) FILTER (WHERE order_status = 'delivered') AS delivered_item_value_brl,
               count(*) FILTER (WHERE seller_count > 1 AND delivery_eligible) AS multi_seller_eligible,
               count(*) FILTER (WHERE delivery_eligible AND is_poor_review IS NOT NULL) AS reviewed_eligible,
               count(*) FILTER (WHERE delivery_eligible AND NOT is_late AND is_poor_review IS NOT NULL) AS on_time_reviewed,
               count(*) FILTER (WHERE delivery_eligible AND is_late AND is_poor_review IS NOT NULL) AS late_reviewed,
               avg(is_poor_review::INTEGER) FILTER (WHERE delivery_eligible AND is_late) * 100 AS late_poor_review_pct,
               avg(is_poor_review::INTEGER) FILTER (WHERE delivery_eligible AND NOT is_late) * 100 AS on_time_poor_review_pct,
               count(*) FILTER (WHERE delivery_eligible AND is_late AND is_poor_review IS NOT NULL
                                 AND review_answered_at >= delivered_at) AS late_post_delivery_reviewed,
               count(*) FILTER (WHERE delivery_eligible AND NOT is_late AND is_poor_review IS NOT NULL
                                 AND review_answered_at >= delivered_at) AS on_time_post_delivery_reviewed,
               avg(is_poor_review::INTEGER) FILTER (WHERE delivery_eligible AND is_late
                                 AND review_answered_at >= delivered_at) * 100 AS late_post_delivery_poor_review_pct,
               avg(is_poor_review::INTEGER) FILTER (WHERE delivery_eligible AND NOT is_late
                                 AND review_answered_at >= delivered_at) * 100 AS on_time_post_delivery_poor_review_pct
        FROM cohort
    """).iloc[0].to_dict()


def monthly(frame):
    return query(frame, """
        SELECT purchase_month, count(*) AS orders,
               count(*) FILTER (WHERE delivery_eligible) AS eligible_orders,
               count(*) FILTER (WHERE is_late) AS late_orders,
               avg(is_late::INTEGER) * 100 AS late_rate_pct,
               median(delivery_days) FILTER (WHERE delivery_eligible) AS median_delivery_days
        FROM cohort GROUP BY purchase_month ORDER BY purchase_month
    """)


def segments(frame, dimension="customer_state", minimum=100):
    if dimension not in {"customer_state", "primary_category"}:
        raise ValueError("Unsupported segment dimension")
    return query(frame, f"""
        SELECT {dimension} AS segment, count(*) AS eligible_orders,
               count(*) FILTER (WHERE is_late) AS late_orders,
               avg(is_late::INTEGER) * 100 AS late_rate_pct,
               median(delivery_days) AS median_delivery_days,
               median(handling_days) AS median_handling_days,
               median(transit_days) AS median_transit_days
        FROM cohort WHERE delivery_eligible
        GROUP BY {dimension} HAVING count(*) >= ?
        ORDER BY late_orders DESC, segment
    """, [minimum])


def review_comparison(frame, post_delivery_only=False):
    timing_filter = "AND review_answered_at >= delivered_at" if post_delivery_only else ""
    return query(frame, f"""
        SELECT CASE WHEN is_late THEN 'Late' ELSE 'On time' END AS delivery,
               count(*) AS eligible_orders, count(is_poor_review) AS reviewed_orders,
               count(*) FILTER (WHERE is_poor_review) AS poor_reviews,
               avg(is_poor_review::INTEGER) * 100 AS poor_review_pct
        FROM cohort WHERE delivery_eligible {timing_filter} GROUP BY is_late ORDER BY is_late
    """)


def sellers(frame, minimum=30):
    return query(frame, """
        WITH eligible AS (
            SELECT * FROM cohort WHERE delivery_eligible AND seller_count = 1
        ), baseline AS (
            SELECT avg(is_late::INTEGER)::DOUBLE AS baseline_rate FROM eligible
        ), grouped AS (
            SELECT sole_seller_id AS seller_id, min(seller_state) AS seller_state,
                   count(*) AS eligible_orders, count(*) FILTER (WHERE is_late) AS late_orders,
                   avg(is_late::INTEGER)::DOUBLE AS late_rate,
                   median(handling_days) AS median_handling_days,
                   median(transit_days) AS median_transit_days
            FROM eligible GROUP BY sole_seller_id HAVING count(*) >= ?
        ), bounds AS (
            SELECT g.*, b.baseline_rate,
                   (late_rate + 1.96*1.96/(2*eligible_orders)
                      - 1.96*sqrt(late_rate*(1-late_rate)/eligible_orders
                                  + 1.96*1.96/(4*eligible_orders*eligible_orders)))
                      / (1 + 1.96*1.96/eligible_orders) AS wilson_lower,
                   (late_rate + 1.96*1.96/(2*eligible_orders)
                      + 1.96*sqrt(late_rate*(1-late_rate)/eligible_orders
                                  + 1.96*1.96/(4*eligible_orders*eligible_orders)))
                      / (1 + 1.96*1.96/eligible_orders) AS wilson_upper
            FROM grouped g CROSS JOIN baseline b
        )
        SELECT *, greatest(late_orders - eligible_orders*baseline_rate, 0) AS excess_late_orders,
               wilson_lower > baseline_rate AS investigate,
               late_rate * 100 AS late_rate_pct,
               wilson_lower * 100 AS wilson_lower_pct,
               wilson_upper * 100 AS wilson_upper_pct,
               baseline_rate * 100 AS baseline_rate_pct
        FROM bounds ORDER BY investigate DESC, excess_late_orders DESC, seller_id
    """, [minimum])


def routes(frame, minimum=100):
    return query(frame, """
        SELECT seller_state, customer_state,
               seller_state || ' -> ' || customer_state AS route,
               count(*) AS eligible_orders, count(*) FILTER (WHERE is_late) AS late_orders,
               avg(is_late::INTEGER) * 100 AS late_rate_pct,
               median(handling_days) AS median_handling_days,
               median(transit_days) AS median_transit_days
        FROM cohort WHERE delivery_eligible AND seller_count = 1
        GROUP BY seller_state, customer_state HAVING count(*) >= ?
        ORDER BY late_orders DESC, route
    """, [minimum])


def matched_review_comparison(frame):
    """Descriptive within-stratum comparison; not a causal adjustment or experiment."""
    return query(frame, """
        WITH strata AS (
            SELECT primary_category, customer_state,
                count(*) FILTER (WHERE is_late AND is_poor_review IS NOT NULL) AS late_reviewed,
                count(*) FILTER (WHERE NOT is_late AND is_poor_review IS NOT NULL) AS on_time_reviewed,
                avg(is_poor_review::INTEGER) FILTER (WHERE is_late) AS late_poor_rate,
                avg(is_poor_review::INTEGER) FILTER (WHERE NOT is_late) AS on_time_poor_rate
            FROM cohort WHERE delivery_eligible GROUP BY primary_category, customer_state
        )
        SELECT *, (late_poor_rate - on_time_poor_rate) * 100 AS difference_pp
        FROM strata WHERE late_reviewed >= 20 AND on_time_reviewed >= 20
        ORDER BY late_reviewed DESC, primary_category, customer_state
    """)


def filter_orders(frame, start, end, states=None, categories=None):
    # Inclusive calendar dates, including orders late on the selected end date.
    start = pd.Timestamp(start)
    end = pd.Timestamp(end) + pd.Timedelta(days=1)
    mask = (frame.purchased_at >= start) & (frame.purchased_at < end)
    if states:
        mask &= frame.customer_state.isin(states)
    if categories:
        mask &= frame.primary_category.isin(categories)
    return frame.loc[mask].copy()
