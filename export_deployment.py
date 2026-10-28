"""Export the validated order mart used by the hosted Streamlit application."""
import json

import duckdb

from src.config import DB, REPORTS, SOURCE
from src.deployment import MANIFEST, SNAPSHOT, checksum


def export():
    if not DB.exists():
        raise FileNotFoundError("Build the original dataset with python run_project.py first.")
    quality = json.loads((REPORTS / "data_quality.json").read_text(encoding="utf-8"))
    if not quality["passed"]:
        raise ValueError("Export requires a validated build.")
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB), read_only=True) as connection:
        connection.execute(
            "COPY (SELECT * FROM analytics.fact_orders ORDER BY order_id) TO ? "
            "(FORMAT PARQUET, COMPRESSION ZSTD)", [str(SNAPSHOT)]
        )
        count = connection.execute("SELECT count(*) FROM analytics.fact_orders").fetchone()[0]
    source_manifest = REPORTS / "source_metadata.json"
    source = json.loads(source_manifest.read_text(encoding="utf-8")) if source_manifest.exists() else {}
    MANIFEST.write_text(json.dumps({
        "source": SOURCE,
        "license": "CC BY-NC-SA 4.0",
        "table": "analytics.fact_orders",
        "row_count": count,
        "sha256": checksum(SNAPSHOT),
        "source_archive_sha256": source.get("archive_sha256"),
        "description": "Validated, typed order mart; no raw review text or original archive is bundled.",
    }, indent=2), encoding="utf-8")
    print(f"Exported {count:,} order facts: {SNAPSHOT.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    export()
