"""Central configuration for the equine-commerce-lakehouse.

Everything is environment-driven so the same code runs locally (DuckDB + a
local Parquet "lake") or against cloud infrastructure (S3 + Snowflake/BigQuery)
by changing environment variables only -- no code edits.

Read once, imported everywhere.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Repo root = two levels up from this file (config/settings.py -> repo/)
REPO_ROOT = Path(__file__).resolve().parents[1]


def _env_path(name: str, default: Path) -> Path:
    val = os.getenv(name)
    return Path(val).expanduser().resolve() if val else default


@dataclass(frozen=True)
class Settings:
    # --- Storage: local Parquet lake (swap LAKE_URI to s3://... in the cloud) ---
    lake_uri: str = os.getenv("LAKE_URI", str(REPO_ROOT / "data" / "lake"))
    raw_prefix: str = "raw"      # landing zone (as-extracted)
    clean_prefix: str = "clean"  # conformed, typed, deduplicated

    # --- Warehouse: DuckDB locally; set WAREHOUSE_TARGET=snowflake for cloud ---
    warehouse_target: str = os.getenv("WAREHOUSE_TARGET", "duckdb")
    duckdb_path: str = os.getenv(
        "DUCKDB_PATH", str(REPO_ROOT / "data" / "warehouse" / "ecl.duckdb")
    )

    # --- Business parameters (Majestic Ally) ---
    channels: tuple[str, ...] = ("amazon", "walmart", "ebay", "etsy", "faire")
    # Marketplace referral/commission as a fraction of gross sales.
    channel_fee_rate: dict[str, float] = field(
        default_factory=lambda: {
            "amazon": 0.15,
            "walmart": 0.12,
            "ebay": 0.13,
            "etsy": 0.065,
            "faire": 0.15,  # wholesale marketplace take
        }
    )
    # Replenishment lead time in days, used for stockout-risk flags.
    reorder_lead_time_days: int = int(os.getenv("REORDER_LEAD_TIME_DAYS", "21"))

    # --- Synthetic data generation ---
    history_days: int = int(os.getenv("HISTORY_DAYS", "400"))
    random_seed: int = int(os.getenv("RANDOM_SEED", "42"))

    def lake_path(self, layer: str) -> str:
        """Return the URI for a lake layer ('raw' or 'clean')."""
        base = self.lake_uri.rstrip("/")
        return f"{base}/{layer}"


SETTINGS = Settings()
