# Project map

## Read or present the result

Open `reports/dashboard.html`, then read `reports/business_brief.md`. The Streamlit app adds cohort filters and CSV downloads. Both use the same SQL-based metric functions.

## Trace a number to the source

1. `src/config.py` lists the eight required original source files.
2. `src/download.py` downloads and fingerprints the source archive.
3. `src/pipeline.py` loads raw text columns and executes the SQL stages in a transaction.
4. `sql/01_staging.sql` creates typed source tables and resolves duplicate reviews.
5. `sql/02_marts.sql` creates order/item facts and dimensions with explicit grains.
6. `src/quality.py` validates keys, relationships, money and SLA eligibility.
7. `src/analysis.py` calculates KPI and segment aggregates in SQL.
8. `src/charts.py` visualizes aggregates; `src/reporting.py` generates saved results.
9. `app.py` adds the interactive filter and presentation layer.

## Explore with Python and SQL

Start with `notebooks/explore_olist.ipynb`, or connect directly:

```python
import duckdb
connection = duckdb.connect("data/processed/olist.duckdb", read_only=True)
connection.sql("SELECT * FROM analytics.monthly_delivery ORDER BY purchase_month").df()
```

`sql/03_investigation.sql` contains four interview-friendly queries: join inflation, late versus on-time review rates, destination-state priorities, and within-category/state comparisons.

## Suggested five-minute walkthrough

1. **Decision:** prioritize an operations investigation with limited time.
2. **Data model:** explain grain and why item/payment aggregation must happen before joining.
3. **Metric choice:** show why midnight promise timestamps require a calendar-date comparison.
4. **Finding:** compare late deliveries and poor reviews, then reveal how review timing changes the gap.
5. **Action:** present a seller/route shortlist with volume and uncertainty, then propose a measurable operational pilot.

Describe only the work you understand and can reproduce. No operational savings or business experiment results have been claimed or measured.

## Extend after the baseline

- Compare seller rankings within matched route, category and purchase-month groups.
- Add a documented missing-review sensitivity analysis.
- Rebuild selected views in Power BI using the included exports.
- Measure refresh performance and add a scheduled workflow if fresh operational data becomes available.

An ML model is optional. The baseline project already demonstrates SQL, data modeling, validation, statistics, BI and business interpretation.
