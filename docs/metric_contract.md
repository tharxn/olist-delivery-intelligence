# Metric contract and analytical decisions

## Population and grain

`analytics.fact_orders` has exactly one row per `order_id`, including orders that were canceled, unavailable or still in progress in the historical snapshot. `analytics.fact_order_items` has one row per `(order_id, order_item_id)`.

Each source customer record has a `customer_id`; repeat-customer identity is represented separately by `customer_unique_id`. Seller and product dimensions retain original identifiers. Postcode prefixes stay strings so leading zeroes survive ingestion.

Payments and order items are separately aggregated to order grain before joining. A two-item order with two payment records must still contain two items and its original money totals. Joining both child tables directly would create four rows.

## Delivery reliability

An order is eligible when all of these hold:

1. `order_status = 'delivered'`.
2. Purchase, delivery and estimated delivery timestamps are present and parseable.
3. Delivery timestamp is not before purchase timestamp.
4. Estimated delivery calendar date is not before purchase calendar date.

An eligible order is late if `CAST(delivered_at AS DATE) > CAST(estimated_at AS DATE)`. Estimated timestamps are commonly midnight. Comparing full timestamps would incorrectly label deliveries later on the same calendar day as late.

**Late-delivery rate = late eligible orders / eligible orders.** Non-delivered orders and missing timestamps do not count as on time. Their counts remain visible in the quality report.

Delivery time is elapsed seconds from purchase to delivery divided by 86,400. The headline reports the median among eligible orders. Source timestamps have no declared timezone; no timezone conversion is invented.

## Purchase cohorts

Dashboard start and end dates are inclusive calendar dates, based on purchase timestamp. The end boundary is implemented as `< end_date + 1 day`, so purchases at 11 p.m. on the last selected date are included.

All dashboard KPIs follow this cohort and the selected destination states and primary categories. Empty multiselect filters mean all values. Quality observations describe the full database build and are labeled separately.

The monthly trend uses purchase month and shows only months with at least 100 eligible deliveries. The data covers partial boundary periods and gaps. It does not describe current operations or provide a reliable unresolved-order alerting feed.

## Merchandise value, freight and payments

`item_value_brl` is the sum of source item prices. `freight_value_brl` is separate. Delivered merchandise value sums item prices for delivered-status orders, including those missing an SLA timestamp. It is not company revenue recognition, net revenue, margin or profit.

Source money is staged as `DECIMAL(18,2)`. Item totals, freight totals and payment totals reconcile separately to their respective source tables. Payments are not forced to equal item value plus freight: discrepancies greater than R$0.05 are documented as observations. No undocumented correction is applied.

## Reviews

Multiple reviews for an order are reduced to the latest answer timestamp, falling back to creation timestamp, then deterministic review ID and score tie-breaks. The discarded-row count remains in the quality report. Scores of 1–2 are poor; scores of 3–5 are not classified as poor.

**Poor-review rate = reviewed eligible orders with 1–2 stars / reviewed eligible orders** in each delivery group. Unreviewed orders are excluded from this denominator. Rates are shown alongside reviewed-order counts.

Two comparisons are reported:

1. All reviewed eligible deliveries, regardless of when the review was answered.
2. The subset with `review_answered_at >= delivered_at`.

The difference between these results is substantive: pre-delivery reviews are common among late orders. Neither comparison is causal or immune to review-selection effects. The category–destination stratification is a further descriptive check; only strata with at least 20 reviewed orders in each group are included. It uses the full reviewed cohort and does not replace the timing sensitivity.

## Category assignment

Each order is assigned to the category with the largest sum of merchandise value; ties sort alphabetically. This is a primary-category grouping, not a claim that all items in an order share the same category. Unknown categories are retained. Category totals remain additive at order grain.

## Seller and route attribution

The dataset supplies one customer delivery timestamp per order. Only orders with exactly one distinct seller enter seller and seller-state → destination-state comparisons. Multi-seller orders remain in company totals but are not attributed to an individual seller.

Routes require at least 100 eligible deliveries. Seller screening defaults to at least 30 eligible deliveries and can be changed in the app. These are practical screening thresholds, not universal statistical rules.

For each selected cohort:

- Benchmark = late rate across **all** eligible single-seller orders, before applying the minimum seller volume.
- Observed seller rate = seller late orders / seller eligible orders.
- A pointwise 95% Wilson interval is computed with z = 1.96.
- `investigate = Wilson lower bound > benchmark`.
- `excess_late_orders = max(late orders − eligible orders × benchmark, 0)`.

Sellers sort by investigation flag, then excess late-order count. Small samples carry wider intervals. Intervals are exploratory, not corrected for multiple comparisons, and do not quantify uncertainty in an independent external benchmark. They assume independent Bernoulli observations; clustering and historical changes can violate that assumption.

An excess count describes a benchmark gap. It does not estimate preventable orders, recoverable sales or savings. Different route, product and seasonal mixes may explain part of the gap. A flag warrants investigation, not an attribution of fault.

## Delivery stages

- Purchase-to-carrier time uses valid purchase and carrier timestamps with carrier ≥ purchase.
- Carrier-to-customer time uses valid carrier and delivery timestamps with delivery ≥ carrier.
- Each stage median has its own valid-record denominator.

The grouped chart shows these medians separately. Medians are not additive. Purchase-to-carrier time includes payment approval and handling; it is not a pure measure of seller processing. The source does not identify the carrier.

## Reproducibility

`reports/source_metadata.json` records the original archive checksum, source file checksums, source URL, download timestamp and observed license. `reports/data_quality.json` distinguishes enforced checks from retained observations. `reports/metrics.json` contains generated metrics; `src/reporting.py` regenerates the narrative and plots from the same analytical functions used by the dashboard.
