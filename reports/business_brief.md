# Olist delivery intelligence: business brief

## Decision
Which sellers and delivery routes should operations investigate first?

## Scope and verified findings
- Original Olist data, purchase period 04 Sep 2016 – 17 Oct 2018; 99,441 source orders.
- 96,470 eligible deliveries; 6,534 late (6.77%).
- Median purchase-to-delivery time: 10.22 days.
- Delivered merchandise value: R$ 13,221,498.11, excluding freight; this is not profit.
- Poor-review rate: 62.42% late versus 9.27% on time, a 53.15 percentage-point higher rate among reviewed eligible orders.
- Review-timing sensitivity: after restricting to reviews answered on/after delivery, poor-review rates are 19.44% late (n=1,908) versus 9.25% on time (n=89,263), a 10.19 percentage-point gap. Pre-delivery reviews account for much of the full-cohort difference.
- 79 sellers meet minimum 30 eligible deliveries and a Wilson lower bound above the 6.85% single-seller benchmark.
- The first 5 flagged sellers represent 535 late orders among 4,891 eligible single-seller deliveries. Start with their route and handoff records, then compare equivalent routes and categories.

## Recommendation
Investigate the shortlist, comparing equivalent routes and categories. Examine purchase-to-carrier and carrier-to-customer stages separately. The source cannot identify a carrier or establish responsibility for a delay.

Pilot a concrete process change with comparable control routes if operational data becomes available. Predefine late-delivery rate as the primary metric and review participation, delivery duration and shipping cost as guardrails. Report uncertainty and observed results before scaling.

## Interpretation limits
The late/review relationship is observational. Some reviews were answered before delivery. Seller rankings do not adjust for all route and product differences; pointwise Wilson intervals are exploratory, without multiplicity correction. The benchmark includes all eligible single-seller orders, before the minimum-volume cutoff. Excess late orders describe a benchmark gap, not preventable delays or savings. Multi-seller orders stay in company totals but are excluded from seller/route attribution. Historical boundary periods may be incomplete. Costs, margin and current customer behavior cannot be inferred from these records.

## Validation
22/22 build checks passed. Source hashes: reports/source_metadata.json. Detailed exclusions and observed exceptions: reports/data_quality.json. Definitions: docs/metric_contract.md. Results regenerate from SQL; no findings are hardcoded into the pipeline.

Source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. Data license: CC BY-NC-SA 4.0.
