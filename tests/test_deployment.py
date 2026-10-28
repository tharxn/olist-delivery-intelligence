import json

import duckdb
import pytest

from src.deployment import checksum, restore_database


@pytest.fixture
def snapshot(tmp_path):
    parquet = tmp_path / "orders.parquet"
    manifest = tmp_path / "orders.json"
    database = tmp_path / "output" / "olist.duckdb"
    with duckdb.connect() as connection:
        connection.execute("CREATE TABLE sample (order_id VARCHAR, value_brl DECIMAL(18,2), purchased_at TIMESTAMP)")
        connection.execute("INSERT INTO sample VALUES ('sample', 10.25, '2018-01-01 10:00:00')")
        connection.execute("COPY sample TO ? (FORMAT PARQUET)", [str(parquet)])
    manifest.write_text(json.dumps({"sha256": checksum(parquet), "row_count": 1}), encoding="utf-8")
    return database, parquet, manifest


def test_cold_start_restores_exact_values(snapshot):
    database, parquet, manifest = snapshot
    assert restore_database(database, parquet, manifest)
    with duckdb.connect(str(database), read_only=True) as connection:
        row = connection.execute("SELECT * FROM analytics.fact_orders").fetchone()
    assert row[0] == "sample"
    assert str(row[1]) == "10.25"
    assert row[2].year == 2018
    assert not restore_database(database, parquet, manifest)


def test_corrupted_snapshot_is_rejected_before_restoring(snapshot):
    database, parquet, manifest = snapshot
    parquet.write_bytes(parquet.read_bytes() + b"modified")
    with pytest.raises(ValueError, match="checksum"):
        restore_database(database, parquet, manifest)
    assert not database.exists()


def test_wrong_count_does_not_leave_a_partial_database(snapshot):
    database, parquet, manifest = snapshot
    manifest.write_text(json.dumps({"sha256": checksum(parquet), "row_count": 2}), encoding="utf-8")
    with pytest.raises(ValueError, match="row count"):
        restore_database(database, parquet, manifest)
    assert not database.exists()
    assert not list(database.parent.glob("snapshot-*.duckdb"))
