# Validation record

Verified on 28 October 2026 with Python 3.12.14 on Windows. Exact library versions are recorded in `requirements.lock.txt`.

- Original archive downloaded from Olist's Kaggle endpoint; archive and eight CSV SHA-256 hashes recorded in `source_metadata.json`.
- Transactional SQL build completed with 99,441 order facts. All 22 enforced data quality checks passed; retained source anomalies are listed separately in `data_quality.json`.
- Rebuilding with existing source CSVs completed successfully and reproduced the metrics.
- Complete pytest suite: **11 passed**. Coverage includes child-table join inflation, calendar-date deadlines, missing estimates, duplicate reviews, review timing, multi-seller attribution, benchmark denominators, end-date inclusion, bad dimensions, detection of inflated facts, dashboard filters and empty cohorts.
- Streamlit rendered in the browser at a local loopback address; the executive dashboard and charts were visually checked. No browser console warnings or errors were reported at verification.
- Notebook outputs, offline HTML, scorecards and the business brief were generated from the built source data.

The Streamlit tests and live server require local socket access. This machine's network-isolated sandbox blocked Python's event-loop socket pair, so those checks ran with local networking enabled. Analytical tests and the SQL build ran in the restricted environment. No external hosting was used.

Optional Power BI formulas are a documented starting point; they have not been executed inside Power BI. No `.pbix` file is claimed.

## Inter and responsive UI update

- Bundled official Inter 4.1 normal/italic variable WOFF2 files and the SIL Open Font License. The browser confirmed Inter was loaded. The report embeds the normal font and its license for offline use.
- Checked live dashboard layouts at viewport widths of 320, 390, 768, 1024, 1440 and 1920 pixels. Document width matched the viewport at every size; metric text and chart containers did not overflow. Metric cards changed from four columns to two or one, and chart panels stacked as content width narrowed.
- Confirmed that the mobile filter drawer opens and closes, the entire purchase-date range fits, and the seller tab and its horizontally scrollable table remain accessible at 390 pixels.
- Re-ran the two dashboard integration tests after the UI change: **2 passed**. Analytical SQL and metric definitions were unchanged.
- Updated desktop and mobile previews and the project archive.
- Verified the offline report contains the embedded Inter font and font license, with no Google Fonts imports. Browser layout verification covered the live Streamlit interface; the offline report was checked at the generated-file level.

## Hosting preparation

- Added an original-data Parquet snapshot and checksum/row-count manifest for cloud startup. Fresh instances restore a local order mart atomically; existing databases are preserved.
- Full test suite after startup changes: **14 passed**, including cold restoration, corruption rejection and cleanup after a row-count mismatch.
- Verified the full 99,441-row deployment snapshot restores the same dashboard summary metrics and seller screening flags as the analytical build.
