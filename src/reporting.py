"""Produce an offline interactive snapshot and evidence-based business brief."""
import base64
import html
import json
from datetime import datetime, timezone

import pandas as pd

from . import analysis as a
from .charts import CHART_CONFIG, monthly_chart, review_chart, seller_chart, state_chart
from .config import DB, REPORTS, ROOT, SOURCE


def create_reports():
    orders = a.load_orders()
    metrics = a.summary(orders)
    seller_data = a.sellers(orders)
    flagged = seller_data[seller_data.investigate]
    top = flagged.head(5)
    states = a.segments(orders)
    routes = a.routes(orders)
    matched = a.matched_review_comparison(orders)
    quality = json.loads((REPORTS / "data_quality.json").read_text(encoding="utf-8"))
    gap = metrics["late_poor_review_pct"] - metrics["on_time_poor_review_pct"]
    post_gap = metrics["late_post_delivery_poor_review_pct"] - metrics["on_time_post_delivery_poor_review_pct"]
    direction = "higher" if gap >= 0 else "lower"
    top_late = int(top.late_orders.sum())
    top_eligible = int(top.eligible_orders.sum())
    baseline = float(seller_data.baseline_rate_pct.iloc[0])
    if not top.empty:
        top_sentence = (
            f"The first {len(top)} flagged sellers represent {top_late:,} late orders "
            f"among {top_eligible:,} eligible single-seller deliveries. Start with their route "
            "and handoff records, then compare equivalent routes and categories."
        )
    else:
        top_sentence = "No sellers met the current screening criteria. Inspect route-level patterns before changing the thresholds."
    period = f"{orders.purchased_at.min():%d %b %Y} – {orders.purchased_at.max():%d %b %Y}"
    checks_passed = sum(check["passed"] for check in quality["checks"])
    metrics.update({
        "purchase_period": period,
        "flagged_sellers_minimum_30": len(flagged),
        "single_seller_baseline_pct": baseline,
        "top_5_flagged_sellers_late_orders": top_late,
        "top_5_flagged_sellers_eligible_orders": top_eligible,
        "review_gap_pp": gap,
        "post_delivery_review_gap_pp": post_gap,
        "matched_strata": len(matched),
        "matched_strata_with_higher_late_poor_review_rate": int((matched.difference_pp > 0).sum()),
    })
    (REPORTS / "metrics.json").write_text(
        json.dumps(metrics, indent=2, default=lambda value: value.item()), encoding="utf-8"
    )
    seller_data.to_csv(REPORTS / "seller_scorecard.csv", index=False)
    routes.to_csv(REPORTS / "route_scorecard.csv", index=False)
    matched.to_csv(REPORTS / "review_strata.csv", index=False)
    states.to_csv(REPORTS / "state_scorecard.csv", index=False)
    a.monthly(orders).to_csv(REPORTS / "monthly_delivery.csv", index=False)

    chart_html = []
    for index, figure in enumerate((
        monthly_chart(a.monthly(orders)), review_chart(a.review_comparison(orders)),
        state_chart(states), seller_chart(seller_data),
    )):
        chart_html.append(figure.to_html(
            full_html=False, include_plotlyjs=(index == 0),
            config=CHART_CONFIG, div_id=f"chart-{index}",
        ))
    table_fields = ["seller_id", "seller_state", "eligible_orders", "late_orders", "late_rate_pct", "excess_late_orders"]
    shortlist = top[table_fields].copy()
    shortlist.columns = ["Seller ID", "State", "Eligible orders", "Late orders", "Late rate (%)", "Excess vs benchmark"]
    shortlist_html = shortlist.to_html(index=False, border=0, float_format=lambda value: f"{value:,.1f}")
    observations_html = pd.DataFrame(
        quality["observations"].items(), columns=["Full-dataset observation", "Orders / rows"]
    ).to_html(index=False, border=0)
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    # Embed the exact bundled typeface so the single-file snapshot remains offline.
    font_data = base64.b64encode((ROOT / "static/fonts/InterVariable.woff2").read_bytes()).decode("ascii")
    font_license = (ROOT / "static/fonts/LICENSE.txt").read_text(encoding="utf-8")
    report = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Olist | Delivery Intelligence</title>
<style>
@font-face{{font-family:Inter;font-style:normal;font-weight:100 900;font-display:swap;src:url(data:font/woff2;base64,{font_data}) format('woff2')}}
*{{box-sizing:border-box}}body{{margin:0;background:#f5f7fa;color:#182b42;font:15px/1.7 Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'cv11','ss01'}}
main{{max-width:1400px;margin:auto;padding:48px clamp(16px,4vw,52px)}}.kicker{{color:#157b74;letter-spacing:1.7px;font-weight:650;font-size:11px}}
h1{{font-size:clamp(30px,3.7vw,42px);font-weight:650;letter-spacing:-.045em;line-height:1.15;margin:14px 0}}h2{{font-size:22px;letter-spacing:-.03em;font-weight:600;margin:0 0 10px}}h3{{font-size:17px;font-weight:600;margin:0 0 8px}}
.subtitle,.note{{color:#607184}}.subtitle{{max-width:72ch}}.note{{font-size:12px;line-height:1.7}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin:22px 0}}
.metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:30px 0 20px}}
.card{{background:#fff;border:1px solid #e3e9ef;border-radius:14px;padding:24px;min-width:0}}
.label{{color:#607184;font-size:11px;font-weight:500;letter-spacing:.5px}}.value{{font-size:clamp(25px,2.5vw,32px);font-weight:600;letter-spacing:-.04em;line-height:1.4;margin-top:7px;font-variant-numeric:tabular-nums}}
.callout{{background:#edf5f3;border:1px solid #d7e9e3;padding:22px 24px;margin:22px 0;border-radius:14px}}
.insight-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:18px 0}}.insight-label{{color:#456b63;font-size:12px}}.insight-value{{font-size:28px;font-weight:600;letter-spacing:-.04em;font-variant-numeric:tabular-nums}}.insight-value span{{font-size:13px;font-weight:400;letter-spacing:0}}
table{{border-collapse:collapse;width:100%;min-width:600px;font-size:12px}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #e4e9ef;overflow-wrap:anywhere}}th{{font-weight:500;color:#607184}}
.table-wrap{{overflow-x:auto;max-width:100%;scrollbar-width:thin}}a{{color:#126c67}}a:focus-visible,summary:focus-visible{{outline:2px solid #157b74;outline-offset:3px}}
.tag{{display:inline-block;background:#fff;border:1px solid #e3e9ef;color:#607184;padding:4px 10px;border-radius:999px;font-size:11px}}
.foot{{font-size:12px;color:#607184;margin-top:28px;overflow-wrap:anywhere}}details{{margin-top:22px}}summary{{cursor:pointer;font-weight:600}}
@media(max-width:1000px){{.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:850px){{main{{padding-top:30px}}.grid{{grid-template-columns:minmax(0,1fr)}}.card{{padding:18px}}}}
@media(max-width:480px){{.metrics{{gap:10px}}.card{{padding:16px}}.value{{font-size:25px}}.label{{font-size:10px}}.callout{{padding:18px}}.insight-grid{{gap:12px}}.insight-value{{font-size:25px}}}}
@media(max-width:350px){{.metrics,.insight-grid{{grid-template-columns:minmax(0,1fr)}}}}
</style><script type="text/plain" id="inter-font-license">{font_license}</script></head><body><main>
<div class="kicker">OLIST / OPERATIONS ANALYTICS</div>
<h1>Deliver better. Know where to start.</h1>
<p class="subtitle">An evidence-based investigation of delivery reliability and customer reviews. Which sellers and routes should an operations team investigate first?</p>
<span class="tag">Historical study · {html.escape(period)}</span>
<div class="metrics">
<div class="card"><div class="label">ORDERS ANALYZED</div><div class="value">{metrics['orders']:,.0f}</div></div>
<div class="card"><div class="label">DELIVERED MERCHANDISE VALUE</div><div class="value">R$ {metrics['delivered_item_value_brl']/1_000_000:.2f}M</div></div>
<div class="card"><div class="label">LATE-DELIVERY RATE</div><div class="value">{metrics['late_rate_pct']:.2f}%</div></div>
<div class="card"><div class="label">MEDIAN DELIVERY TIME</div><div class="value">{metrics['median_delivery_days']:.1f} days</div></div>
</div>
<p class="note">{metrics['eligible_orders']:,.0f} eligible deliveries · {metrics['late_orders']:,.0f} late orders. Merchandise value excludes freight and is not profit.</p>
<section class="callout"><h3>Review timing changes the story</h3><div class="insight-grid"><div><div class="insight-label">All reviewed deliveries</div><div class="insight-value">{gap:.1f} <span>pp gap</span></div></div><div><div class="insight-label">Reviews answered after delivery</div><div class="insight-value">{post_gap:.1f} <span>pp gap</span></div></div></div><p class="note">Poor-review rate for late minus on-time deliveries. Some reviews were submitted before delivery; both comparisons are observational.</p></section>
<div class="grid"><section class="card">{chart_html[0]}<p class="note">Purchase months with ≥100 eligible deliveries. Boundary periods may be incomplete.</p></section>
<section class="card">{chart_html[1]}<p class="note">Denominators: {metrics['on_time_reviewed']:,.0f} reviewed on-time orders; {metrics['late_reviewed']:,.0f} reviewed late orders. Missing reviews excluded.</p></section></div>
<div class="grid"><section class="card">{chart_html[2]}<p class="note">States with ≥100 eligible deliveries, ranked by late-order count.</p></section>
<section class="card">{chart_html[3]}<p class="note">Minimum 30 eligible single-seller deliveries. Dots: observed rate. Whiskers: pointwise 95% Wilson intervals. Benchmark: {baseline:.2f}%.</p></section></div>
<section class="card"><h2>Turn the shortlist into an investigation</h2>
<p>{len(flagged):,} sellers have a Wilson lower bound above the single-seller cohort benchmark. {html.escape(top_sentence)}</p>
<div class="table-wrap">{shortlist_html}</div>
<p class="note">Excess = max(late orders − eligible orders × benchmark, 0). It is a descriptive gap, not a forecast of preventable delays. Screening intervals are not corrected for multiple comparisons, and seller route/product mix differs.</p></section>
<div class="grid"><section class="card"><h3>Recommended next actions</h3><ol>
<li>Review the highest-volume flagged sellers alongside their destination mix and handoff timing.</li>
<li>Separate purchase-to-carrier time from carrier-to-customer time before choosing an intervention.</li>
<li>Pilot a change on comparable routes. Track delivery reliability, review participation and shipping cost before expanding.</li>
</ol></section><section class="card"><h3>What the evidence supports</h3>
<p><strong>Timing sensitivity:</strong> among reviews answered on/after delivery, the poor-review rate is {metrics['late_post_delivery_poor_review_pct']:.2f}% for late orders (n={metrics['late_post_delivery_reviewed']:,.0f}) and {metrics['on_time_post_delivery_poor_review_pct']:.2f}% for on-time orders (n={metrics['on_time_post_delivery_reviewed']:,.0f}). The gap is much smaller than in the full reviewed cohort.</p>
<p>{len(matched):,} category–destination strata have at least 20 reviewed deliveries in each group; {int((matched.difference_pp > 0).sum()):,} show a higher poor-review rate among late deliveries.</p>
<p class="note">This is descriptive stratification. The records do not identify carriers, randomize delivery times, provide operating costs, or establish the effect of a proposed change.</p></section></div>
<section class="card"><h2>Metric contract</h2><p><strong>Eligible delivery:</strong> delivered status, valid purchase/delivery/promise timestamps, delivery not before purchase, promise date not before purchase date. <strong>Late:</strong> actual delivery calendar date after the promise calendar date. <strong>Poor review:</strong> latest review per order scores 1–2.</p>
<p><strong>Attribution:</strong> seller and route rankings use single-seller orders. Category views use each order's highest-value category. Payments and item values are aggregated separately before joining to orders.</p>
<p class="note">Historical coverage, incomplete boundary periods, missing reviews, differing route mixes, and reviews answered before delivery limit interpretation. Values are nominal BRL; timestamps have no declared timezone.</p>
<details><summary>Data quality: {checks_passed}/{len(quality['checks'])} build checks passed</summary><p>Checks protect unique keys, referential integrity, valid values, delivery denominators, and reconciliation of source item, freight and payment totals. Observations below are retained and documented.</p><div class="table-wrap">{observations_html}</div></details></section>
<p class="foot">Source: <a href="{SOURCE}">Brazilian E-Commerce Public Dataset by Olist</a> · Data license: CC BY-NC-SA 4.0 · Generated {built_at}. This snapshot includes all source orders. For cohort filters and CSV exports, run the included Streamlit app.</p>
</main></body></html>"""
    (REPORTS / "dashboard.html").write_text(report, encoding="utf-8")
    brief = f"""# Olist delivery intelligence: business brief

## Decision
Which sellers and delivery routes should operations investigate first?

## Scope and verified findings
- Original Olist data, purchase period {period}; {metrics['orders']:,.0f} source orders.
- {metrics['eligible_orders']:,.0f} eligible deliveries; {metrics['late_orders']:,.0f} late ({metrics['late_rate_pct']:.2f}%).
- Median purchase-to-delivery time: {metrics['median_delivery_days']:.2f} days.
- Delivered merchandise value: R$ {metrics['delivered_item_value_brl']:,.2f}, excluding freight; this is not profit.
- Poor-review rate: {metrics['late_poor_review_pct']:.2f}% late versus {metrics['on_time_poor_review_pct']:.2f}% on time, a {abs(gap):.2f} percentage-point {direction} rate among reviewed eligible orders.
- Review-timing sensitivity: after restricting to reviews answered on/after delivery, poor-review rates are {metrics['late_post_delivery_poor_review_pct']:.2f}% late (n={metrics['late_post_delivery_reviewed']:,.0f}) versus {metrics['on_time_post_delivery_poor_review_pct']:.2f}% on time (n={metrics['on_time_post_delivery_reviewed']:,.0f}), a {post_gap:.2f} percentage-point gap. Pre-delivery reviews account for much of the full-cohort difference.
- {len(flagged)} sellers meet minimum 30 eligible deliveries and a Wilson lower bound above the {baseline:.2f}% single-seller benchmark.
- {top_sentence}

## Recommendation
Investigate the shortlist, comparing equivalent routes and categories. Examine purchase-to-carrier and carrier-to-customer stages separately. The source cannot identify a carrier or establish responsibility for a delay.

Pilot a concrete process change with comparable control routes if operational data becomes available. Predefine late-delivery rate as the primary metric and review participation, delivery duration and shipping cost as guardrails. Report uncertainty and observed results before scaling.

## Interpretation limits
The late/review relationship is observational. Some reviews were answered before delivery. Seller rankings do not adjust for all route and product differences; pointwise Wilson intervals are exploratory, without multiplicity correction. The benchmark includes all eligible single-seller orders, before the minimum-volume cutoff. Excess late orders describe a benchmark gap, not preventable delays or savings. Multi-seller orders stay in company totals but are excluded from seller/route attribution. Historical boundary periods may be incomplete. Costs, margin and current customer behavior cannot be inferred from these records.

## Validation
{checks_passed}/{len(quality['checks'])} build checks passed. Source hashes: reports/source_metadata.json. Detailed exclusions and observed exceptions: reports/data_quality.json. Definitions: docs/metric_contract.md. Results regenerate from SQL; no findings are hardcoded into the pipeline.

Source: {SOURCE}. Data license: CC BY-NC-SA 4.0.
"""
    (REPORTS / "business_brief.md").write_text(brief, encoding="utf-8")
    print("Saved the offline dashboard, business brief and analytical scorecards.", flush=True)
