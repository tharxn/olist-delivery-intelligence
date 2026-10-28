"""Restore the validated analytical snapshot for a fresh cloud instance."""
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import duckdb

from .config import DB, ROOT

SNAPSHOT = ROOT / "data" / "deployment" / "orders.parquet"
MANIFEST = SNAPSHOT.with_suffix(".json")


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def restore_database(db_path=DB, snapshot=SNAPSHOT, manifest_path=MANIFEST):
    """Preserve existing databases; verify and atomically restore a missing one."""
    db_path, snapshot, manifest_path = map(Path, (db_path, snapshot, manifest_path))
    if db_path.exists():
        return False
    if not snapshot.exists() or not manifest_path.exists():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if checksum(snapshot) != manifest["sha256"]:
        raise ValueError("The deployment snapshot checksum does not match its manifest.")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = db_path.parent / f"snapshot-{uuid4().hex}.duckdb"
    try:
        with duckdb.connect(str(temporary), config={"memory_limit": "256MB", "threads": 2}) as connection:
            connection.execute("CREATE SCHEMA analytics")
            connection.execute(
                "CREATE TABLE analytics.fact_orders AS SELECT * FROM read_parquet(?)", [str(snapshot)]
            )
            count = connection.execute("SELECT count(*) FROM analytics.fact_orders").fetchone()[0]
            if count != manifest["row_count"]:
                raise ValueError("The deployment snapshot row count does not match its manifest.")
        os.replace(temporary, db_path)
    finally:
        # Only remove this function's own temporary file, never an existing DB.
        if temporary.exists():
            temporary.unlink()
    return True
