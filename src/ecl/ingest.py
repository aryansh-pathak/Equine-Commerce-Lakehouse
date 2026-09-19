"""Ingestion (Extract + Land).

Pulls raw tables from a connector and lands them, unmodified in spirit, as
Parquet in the lake's `raw/` layer -- the landing zone. Adds lightweight
lineage columns (_extracted_at, _source). No business logic here: the raw
layer preserves what the source gave us (including dirtiness) so extraction is
replayable and auditable.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from config.settings import SETTINGS

from ecl.connectors import get_connector


def _arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce object columns to nullable strings so mixed-type raw columns
    (e.g. a unit_price exported as both 12.30 and "$12.30") land losslessly."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda v: None if pd.isna(v) else str(v))
    return out


def ingest(source: str = "synthetic", **connector_kwargs) -> dict[str, str]:
    """Extract from `source` and land raw Parquet. Returns {entity: path}."""
    connector = get_connector(source, **connector_kwargs)
    tables = connector.fetch_all()

    raw_dir = Path(SETTINGS.lake_path(SETTINGS.raw_prefix))
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted_at = dt.datetime.now(dt.timezone.utc).isoformat()

    written: dict[str, str] = {}
    for entity, df in tables.items():
        df = _arrow_safe(df)
        df["_extracted_at"] = extracted_at
        df["_source"] = connector.name
        path = raw_dir / f"{entity}.parquet"
        df.to_parquet(path, index=False)
        written[entity] = str(path)
    return written


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else "synthetic"
    print(json.dumps(ingest(src), indent=2))
