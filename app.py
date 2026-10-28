"""Run with: python -m streamlit run app.py"""
import json

import pandas as pd
import streamlit as st

from src import analysis as a
from src.charts import CHART_CONFIG, monthly_chart, review_chart, seller_chart, stage_chart, state_chart
from src.config import DB, REPORTS
from src.deployment import restore_database
from src.ui import apply_styles, hero, review_insight, sidebar_brand

st.set_page_config(page_title="Olist | Delivery Intelligence", page_icon="📦", layout="wide")
apply_styles()
hero()

@st.cache_resource(show_spinner=False)
def prepare_deployment_database():
    return restore_database()


if not DB.exists():
    try:
        with st.spinner("Preparing the validated data snapshot…"):
            prepare_deployment_database()
    except Exception:
        st.error("The data snapshot could not be loaded. Please contact the app owner.")
        st.stop()

if not DB.exists():
    st.info("Build the project first: python run_project.py. The dashboard uses original Olist observations.")
    st.stop()


@st.cache_data(show_spinner=False)
def cached_orders(modified_at):
    return a.load_orders()


orders = cached_orders(DB.stat().st_mtime_ns)
minimum_date, maximum_date = orders.purchased_at.min().date(), orders.purchased_at.max().date()
with st.sidebar:
    sidebar_brand()
    date_range = st.date_input("Purchase dates", value=(minimum_date, maximum_date),
                               min_value=minimum_date, max_value=maximum_date)
    states = st.multiselect("Destination states", sorted(orders.customer_state.dropna().unique()), help="Leave empty to include all destinations.")
    categories = st.multiselect("Primary categories", sorted(orders.primary_category.unique()), help="Leave empty to include all primary categories.")
    minimum_seller = st.slider("Minimum orders per seller", 10, 200, 30, 10,
                               help="Minimum eligible single-seller deliveries required for the seller scorecard.")
    with st.expander("About these metrics"):
        st.caption("Late = delivered after the promised calendar date. Only eligible completed deliveries enter the rate.")
        st.caption("Seller and route views use single-seller orders because the data has one delivery timestamp per order.")
    st.caption("Original Olist public dataset · Historical portfolio study")

if len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()
cohort = a.filter_orders(orders, *date_range, states, categories)
if cohort.empty:
    st.info("No orders match this cohort. Expand the dates or filters.")
    st.stop()

metrics = a.summary(cohort)


def number(value, pattern="{:,.1f}"):
    return "—" if pd.isna(value) else pattern.format(value)


with st.container(key="kpi_grid"):
    columns = st.columns(4)
    columns[0].metric("Orders analyzed", number(metrics["orders"], "{:,.0f}"))
    columns[1].metric("Delivered item value", number(metrics["delivered_item_value_brl"] / 1_000_000, "R$ {:.2f}M"),
                      help="Delivered merchandise value in BRL, excluding freight; this is not profit.")
    columns[2].metric("Late-delivery rate", number(metrics["late_rate_pct"], "{:.1f}%"))
    columns[3].metric("Median delivery time", number(metrics["median_delivery_days"], "{:.1f} days"))
st.caption(
    f"{metrics['eligible_orders']:,.0f} eligible deliveries · {metrics['late_orders']:,.0f} late orders · "
    "Merchandise value excludes freight and is not profit. All metrics follow the selected purchase cohort."
)
if not metrics["eligible_orders"]:
    st.info("This cohort contains no completed deliveries with valid delivery and promise timestamps.")
    st.stop()

seller_data = a.sellers(cohort, minimum_seller)
route_data = a.routes(cohort)
reviews = a.review_comparison(cohort)
flagged = seller_data[seller_data.investigate]

overview, diagnostics, priorities, definitions = st.tabs([
    "Executive overview", "Delivery diagnostics", "Seller priorities", "Definitions & quality"
])
with overview:
    gap = metrics["late_poor_review_pct"] - metrics["on_time_poor_review_pct"]
    post_gap = metrics["late_post_delivery_poor_review_pct"] - metrics["on_time_post_delivery_poor_review_pct"]
    if not pd.isna(gap):
        review_insight(gap, post_gap)
    with st.container(key="overview_charts"):
        left, right = st.columns(2)
        with left.container(border=True, key="monthly_panel"):
            st.plotly_chart(monthly_chart(a.monthly(cohort)), width="stretch", config=CHART_CONFIG)
            st.caption("Purchase months with ≥100 eligible deliveries. Boundary months may be incomplete.")
        with right.container(border=True, key="reviews_panel"):
            st.plotly_chart(review_chart(reviews), width="stretch", config=CHART_CONFIG)
            st.caption("Poor reviews = 1–2 stars. Rates exclude missing reviews; timing sensitivity is shown above.")
    with st.container(key="overview_actions"):
        left, right = st.columns(2)
        with left.container(border=True, key="states_panel"):
            st.plotly_chart(state_chart(a.segments(cohort)), width="stretch", config=CHART_CONFIG)
            st.caption("States with ≥100 eligible deliveries, ranked by late-order volume.")
        with right.container(border=True, key="actions_panel"):
            st.markdown('<div class="priority-kicker">YOUR NEXT INVESTIGATION</div>'
                        f'<div class="priority-count">{len(flagged):,} <span>sellers to review</span></div>', unsafe_allow_html=True)
            st.subheader("Start where the gap is largest")
            st.write("These sellers meet the order threshold and have a Wilson lower bound above the single-seller benchmark.")
            st.write("Inspect route mix and handoff times before assigning responsibility. Then pilot a change on comparable routes and track delivery reliability, reviews, and shipping cost.")
            st.caption("Open Seller priorities for the ranked scorecard and supporting intervals.")

with diagnostics:
    st.subheader("Review timing changes the interpretation")
    st.write("Some reviews were answered before the customer received the order. Compare the full reviewed cohort with the subset answered on or after delivery.")
    timing = pd.concat([
        reviews.assign(review_scope="All eligible reviewed orders"),
        a.review_comparison(cohort, post_delivery_only=True).assign(review_scope="Answered on/after delivery"),
    ], ignore_index=True)
    st.dataframe(timing[["review_scope", "delivery", "eligible_orders", "reviewed_orders", "poor_review_pct"]].round(2), hide_index=True, width="stretch")
    st.caption("Eligible orders in the second scope also satisfy the answer-timing condition. Neither scope removes review-selection bias or establishes causality.")
    st.subheader("Separate the stages before proposing a fix")
    st.plotly_chart(stage_chart(route_data), width="stretch", config=CHART_CONFIG)
    st.caption("Single-seller routes with ≥100 eligible deliveries. Stage medians use valid timestamps for that stage and should not be added together. Source records do not identify the carrier.")
    st.dataframe(route_data.round(2), hide_index=True, width="stretch")
    st.subheader("Product category context")
    st.dataframe(a.segments(cohort, "primary_category").round(2), hide_index=True, width="stretch")
    st.caption("Each order belongs to its highest-merchandise-value category; ties are alphabetical. This keeps category totals additive.")
    st.subheader("Compare reviews within category and destination")
    st.dataframe(a.matched_review_comparison(cohort).round(3), hide_index=True, width="stretch")
    st.caption("Only strata with ≥20 reviewed late and ≥20 reviewed on-time deliveries. This is descriptive stratification, not evidence of causation.")

with priorities:
    st.subheader("Prioritize volume and evidence together")
    if not seller_data.empty:
        st.caption(f"Single-seller baseline in this cohort: {seller_data.baseline_rate_pct.iloc[0]:.2f}%. Recomputed before applying the seller volume threshold.")
    st.plotly_chart(seller_chart(seller_data), width="stretch", config=CHART_CONFIG)
    st.caption("Dots show observed late rates; whiskers show pointwise 95% Wilson intervals. The dotted line is the single-seller cohort benchmark. Sellers sort by screening flag, then excess late orders.")
    fields = ["seller_id", "seller_state", "eligible_orders", "late_orders", "late_rate_pct",
              "wilson_lower_pct", "wilson_upper_pct", "excess_late_orders", "investigate"]
    st.dataframe(seller_data[fields].round(2), hide_index=True, width="stretch", column_config={
        "seller_id": "Seller ID", "seller_state": "State", "eligible_orders": "Eligible orders",
        "late_orders": "Late orders", "late_rate_pct": st.column_config.NumberColumn("Late rate", format="%.2f%%"),
        "wilson_lower_pct": st.column_config.NumberColumn("95% lower bound", format="%.2f%%"),
        "wilson_upper_pct": st.column_config.NumberColumn("95% upper bound", format="%.2f%%"),
        "excess_late_orders": "Excess late orders", "investigate": "Review flag",
    })
    st.download_button("Download seller scorecard", seller_data.to_csv(index=False), "seller_scorecard.csv", "text/csv")
    st.caption("Excess late orders = max(observed late orders − eligible orders × benchmark, 0). This describes a gap; it does not estimate preventable orders or financial savings. Wilson flags are exploratory and are not corrected for multiple comparisons.")

with definitions:
    st.subheader("Metric contract")
    st.markdown("""
    - **Eligible delivery:** status is delivered; purchase, delivery and promise timestamps exist; delivery is not before purchase; promise date is not before purchase date.
    - **Late delivery:** actual delivery calendar date is after the estimated delivery calendar date. A delivery at 9 p.m. on the promise date is on time.
    - **Poor-review rate:** 1–2 star orders divided by reviewed orders within the same delivery group. Latest review per order is retained.
    - **Median delivery time:** elapsed days between purchase and delivery for eligible orders.
    - **Seller attribution:** single-seller orders only. Customer delivery timestamps cannot identify which seller caused a delay on a multi-seller order.
    - **Time and money:** source timestamps have no declared timezone. Values are historical BRL; costs and profit are not available.
    """)
    st.write("The source has historical coverage gaps, missing observations and review-selection effects. Non-delivered orders are reported separately and do not enter the late-delivery denominator.")
    quality_file = REPORTS / "data_quality.json"
    if quality_file.exists():
        quality = json.loads(quality_file.read_text(encoding="utf-8"))
        show_status = st.success if quality["passed"] else st.error
        show_status(f"{sum(c['passed'] for c in quality['checks'])}/{len(quality['checks'])} build checks passed across the full dataset.")
        st.caption("Quality checks and observations below describe the full build, independent of dashboard filters.")
        st.dataframe(pd.DataFrame(quality["checks"]), hide_index=True, width="stretch")
        st.dataframe(pd.DataFrame(quality["observations"].items(), columns=["observation", "orders_or_rows"]), hide_index=True, width="stretch")
    st.link_button("Original dataset and license", "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
