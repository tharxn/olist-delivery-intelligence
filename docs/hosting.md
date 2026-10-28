# Streamlit Community Cloud deployment

Live dashboard: https://olist-delivery-intelligence-tharxn.streamlit.app/.

Public project repository: https://github.com/tharxn/olist-delivery-intelligence.

Deployed on 28 October 2026 with Python 3.12. The hosted dashboard was checked against the original analytical build: 99,441 orders, 6.8% displayed late-delivery rate, R$13.22M delivered merchandise value and 10.2-day median delivery time.

The full application runs on a Python server. The local address `http://127.0.0.1:8507/` is available only on this computer; it is not an internet deployment.

The app can run on Streamlit Community Cloud from this repository with:

- Branch: `main`
- Main file: `app.py`
- Python: `3.12`
- Dependencies: `requirements.txt`
- Secrets: none required

On a fresh instance, the app restores its order mart from `data/deployment/orders.parquet`. Its SHA-256 and row count are checked before atomic database creation. Existing databases are preserved. The snapshot uses the original validated Olist data under CC BY-NC-SA 4.0; source attribution is included in the manifest and `DATA_LICENSE.md`.

The deployment snapshot contains the order mart needed by the dashboard. To recreate the raw, staging, item and dimension tables for SQL exploration, run `python run_project.py`. To update the hosted data after rebuilding, run `python export_deployment.py` and commit the resulting Parquet file and manifest together.

The full 161 MB local database and raw CSVs stay excluded from Git. The smaller Parquet snapshot avoids a dependency on Kaggle availability during app startup.

Official deployment guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy.
