import pandas as pd

from ecl.connectors.base import ENTITIES
from ecl.generate import generate


def test_generate_returns_all_entities():
    tables = generate(seed=7)
    assert set(ENTITIES).issubset(tables.keys())
    for name in ENTITIES:
        assert isinstance(tables[name], pd.DataFrame)


def test_products_match_catalog_size():
    tables = generate(seed=7)
    assert len(tables["products"]) == 143


def test_orders_and_items_are_populated():
    tables = generate(seed=7)
    assert len(tables["orders"]) > 100
    assert len(tables["order_items"]) > 100


def test_raw_data_contains_injected_defects():
    # The generator deliberately injects dirt for the cleaning layer to handle.
    items = generate(seed=7)["order_items"]
    orders = generate(seed=7)["orders"]
    # whitespace-polluted SKUs exist
    assert (items["sku"].astype(str).str.strip() != items["sku"].astype(str)).any()
    # some null customer_state values exist
    assert orders["customer_state"].isna().any()


def test_generation_is_deterministic():
    a = generate(seed=99)["order_items"]
    b = generate(seed=99)["order_items"]
    assert len(a) == len(b)
