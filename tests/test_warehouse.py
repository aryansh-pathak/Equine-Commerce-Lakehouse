"""Integration checks against a built warehouse.

Skipped automatically if the pipeline hasn't been run yet (no DuckDB file), so
`pytest` is green on a fresh checkout and meaningful in CI after `make pipeline`.
"""
from pathlib import Path

import duckdb
import pytest
from config.settings import SETTINGS

pytestmark = pytest.mark.skipif(
    not Path(SETTINGS.duckdb_path).exists(),
    reason="warehouse not built yet (run `make pipeline`)",
)


def _con():
    return duckdb.connect(SETTINGS.duckdb_path, read_only=True)


def test_marts_exist_and_are_populated():
    con = _con()
    for model in ("dim_product", "fct_orders", "mart_sku_velocity", "mart_channel_performance"):
        n = con.execute(f"select count(*) from main.{model}").fetchone()[0]
        assert n > 0, f"{model} is empty"
    con.close()


def test_no_orphan_order_lines():
    con = _con()
    orphans = con.execute(
        "select count(*) from main.fct_orders f "
        "left join main.dim_product p on f.sku=p.sku where p.sku is null"
    ).fetchone()[0]
    assert orphans == 0
    con.close()


def test_all_quantities_positive_after_cleaning():
    con = _con()
    bad = con.execute("select count(*) from main.fct_orders where quantity <= 0").fetchone()[0]
    assert bad == 0
    con.close()
