# Olist Delivery Intelligence

An end-to-end analytics project answering: **Which sellers and delivery routes should an operations team investigate first?**

Built with **Python, SQL, DuckDB, Plotly and Streamlit**. The analytical work lives in readable SQL and Python. Power BI exports are included as an optional next step.

The interface uses bundled **Inter** fonts, readable chart typography, touch-friendly tabs and a collapsible filter drawer. Metric cards and chart panels adapt to the available content width, including narrow browser panels. The standalone HTML report embeds Inter for offline use. Font attribution and the SIL Open Font License are included under `static/fonts/`.

For the full application on a hosting provider, see [deployment setup](docs/hosting.md). A compact, checksum-verified Parquet snapshot supports fresh Streamlit instances without downloading raw files at startup.

## Start here

- **View the results without installing anything:** open [the offline dashboard](reports/dashboard.html). Charts support hover and zoom; this saved snapshot contains all source orders.
- **Read the recommendation:** [business brief](reports/business_brief.md).
- **Explore dates, states, categories and seller thresholds:** run the Streamlit dashboard below.
- **Understand or extend the project:** follow [the project map](docs/project_map.md), then [the metric contract](docs/metric_contract.md).

## Verified results from this build

The original dataset contains 99,441 orders. Of 96,470 eligible completed deliveries, 6,534 arrived after their promised calendar date: **6.77%**. Median delivery time was **10.22 days**.

The poor-review rate was **62.42% for late deliveries versus 9.27% for on-time deliveries** among reviewed eligible orders. Reviewing answer timestamps reveals an important sensitivity: when restricted to reviews answered on/after delivery, the rates become **19.44% versus 9.25%**. This changes the interpretation substantially. The project reports both comparisons and does not infer a causal effect.

There are 79 seller screening flags at a minimum of 30 eligible single-seller deliveries. This is an investigation shortlist, not a finding of seller fault. Numbers above describe the downloaded source snapshot; regenerate the reports if source files change.

## Run locally

Tested with Python 3.12 on Windows. Run these commands from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_project.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The pipeline downloads the original public archive, records source checksums, builds the database, runs quality checks and creates reports. It uses about 45 MB of network transfer on the first run. Existing source CSVs are reused. No paid service or API key was needed for the verified download.

For the exact library versions used here, install `requirements.lock.txt` instead of `requirements.txt`. The project ZIP excludes raw CSVs and the database; `run_project.py` recreates them. The current local project folder already has the built data.

If Kaggle changes its download access, download the original archive from [the dataset page](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), put the eight required CSVs listed in `src/config.py` in `data/raw/`, and run:

```powershell
.\.venv\Scripts\python.exe run_project.py --skip-download
```

For macOS/Linux, use `.venv/bin/python` for the same commands. The one-click `launch_dashboard.ps1` also works in this local workspace using the prepared Python environment.

## What is implemented

| Layer | Implementation |
|---|---|
| Ingestion | Original source download; allowlisted ZIP members; SHA-256 provenance |
| Staging | SQL types, preserved identifiers, translated categories, deterministic review resolution |
| Data model | One row per order and one row per order item; separate payment/item aggregation |
| Analysis | Delivery eligibility, calendar-date SLA, review timing sensitivity, stage and route diagnostics |
| Prioritization | Minimum sample size, pointwise Wilson intervals, volume-based benchmark gaps |
| Dashboard | Cohort filters, executive overview, diagnostics, seller scorecards, quality panel |
| Reporting | Offline interactive HTML, generated business brief, CSV scorecards, machine-readable metrics |
| Validation | 22 build checks plus analytical edge-case and dashboard integration tests |
| BI handoff | Six exported CSV tables and an optional Power BI setup guide |

## Validate

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Analytical unit tests use small, clearly synthetic fixtures. All displayed business findings use original Olist observations. App integration tests require a built database; they are skipped until then. In restricted environments, pass a writable temporary folder with `--basetemp <new-folder>`.

## Repository layout

```text
app.py                    Streamlit application
run_project.py            Download → SQL build → checks → reports
src/                      Pipeline, SQL analytics, charts and reporting
sql/                      Staging, marts and investigation queries
tests/                    Grain, deadline, review, attribution and UI checks
notebooks/                Guided Python/SQL exploration
docs/                     Metric contract, project map and Power BI guide
data/raw/                 Original CSVs (excluded from Git/ZIP)
data/processed/            DuckDB database and BI tables (excluded from Git/ZIP)
reports/                  Verified findings, HTML dashboard and scorecards
```

## Scope and attribution

Source: **Brazilian E-Commerce Public Dataset by Olist**, historical purchases from 2016–2018, [published by Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). This project excludes the large geolocation file because its geographic analysis uses states.

The data does not identify the logistics carrier, provide operating costs, measure profit, or contain a randomized delivery intervention. Seller comparisons are not fully adjusted for route/product mix. Missing reviews, reviews submitted before delivery, and incomplete boundary periods matter.

Original code: MIT license. Source data and derived data/visualizations: **CC BY-NC-SA 4.0**; see [data attribution](DATA_LICENSE.md). No dashboard has been published to an external service.
