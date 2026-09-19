"""Load the clean layer into the warehouse (DuckDB).

Materializes each conformed Parquet dataset as a table in the `raw` schema of
the DuckDB warehouse. dbt then reads these as sources. In the cloud, this step
is a COPY INTO Snowflake / load job into BigQuery -- same contract, different
target (see WAREHOUSE_TARGET in config).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
from config.settings import SETTINGS

from ecl.connectors.base import ENTITIES


def load() -> dict[str, int]:
    db_path = Path(SETTINGS.duckdb_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    clean_base = SETTINGS.lake_path(SETTINGS.clean_prefix)

    con = duckdb.connect(str(db_path))
    counts: dict[str, int] = {}
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        for entity in ENTITIES:
            glob = f"{clean_base}/{entity}/*.parquet"
            con.execute(
                f"CREATE OR REPLACE TABLE raw.{entity} AS "
                f"SELECT * FROM read_parquet('{glob}');"
            )
            counts[entity] = con.execute(
                f"SELECT count(*) FROM raw.{entity}"
            ).fetchone()[0]
    finally:
        con.close()
    return counts


if __name__ == "__main__":  # pragma: no cover
    import json

    print(json.dumps(load(), indent=2))
