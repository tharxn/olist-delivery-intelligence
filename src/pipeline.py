import duckdb

from .config import DB, FILES, PROCESSED, RAW, REPORTS, ROOT, make_directories
from .download import verify_local_sources
from .quality import validate


def load_raw(connection, raw_dir=RAW):
    for schema in ("raw", "staging", "analytics"):
        connection.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    for table, filename in FILES.items():
        path = raw_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run python run_project.py first.")
        connection.execute(
            f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM read_csv(?, header=true, all_varchar=true)",
            [str(path)],
        )


def transform(connection):
    for filename in ("01_staging.sql", "02_marts.sql"):
        connection.execute((ROOT / "sql" / filename).read_text(encoding="utf-8"))


def export_power_bi(connection, destination):
    destination.mkdir(parents=True, exist_ok=True)
    tables = ("fact_orders", "fact_order_items", "dim_customers", "dim_sellers", "dim_products", "dim_dates")
    for table in tables:
        # Use parameter binding for the output path; SQL object names are a fixed allowlist.
        connection.execute(f"COPY analytics.{table} TO ? (HEADER, DELIMITER ',')", [str(destination / f"{table}.csv")])


def build():
    make_directories()
    missing = [filename for filename in FILES.values() if not (RAW / filename).exists()]
    if missing:
        raise FileNotFoundError(f"Missing source CSVs: {', '.join(missing)}. Run without --skip-download.")
    verify_local_sources()
    # Transactional rebuild: a failed transformation cannot leave half-updated marts.
    with duckdb.connect(str(DB)) as connection:
        connection.execute("BEGIN TRANSACTION")
        try:
            load_raw(connection)
            transform(connection)
            quality = validate(connection, REPORTS / "data_quality.json")
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        export_power_bi(connection, PROCESSED / "power_bi")
        count = connection.execute("SELECT count(*) FROM analytics.fact_orders").fetchone()[0]
    print(f"Built {count:,} order facts; {len(quality['checks'])} data checks passed.", flush=True)
    return quality
