from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
DB = PROCESSED / "olist.duckdb"
SOURCE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
DOWNLOAD = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
METADATA = "https://www.kaggle.com/api/v1/datasets/view/olistbr/brazilian-ecommerce"
FILES = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translations": "product_category_name_translation.csv",
}

def make_directories():
    for path in (RAW, PROCESSED, REPORTS):
        path.mkdir(parents=True, exist_ok=True)
