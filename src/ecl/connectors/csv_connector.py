"""CSV export connector.

Reads marketplace report exports from a directory -- the realistic "mix" path
when there is no API access: you export Orders/Inventory reports from Amazon
Seller Central, eBay, Etsy, Walmart, Faire, drop the CSVs in one folder, and
the pipeline ingests them on a schedule.

Expected files (any subset; missing entities fall back to empty frames with
the right columns): products.csv, orders.csv, order_items.csv,
inventory_snapshots.csv
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ecl.connectors.base import ENTITIES, MarketplaceConnector

_COLUMNS = {
    "products": ["sku", "category", "product_line", "title", "color", "size", "msrp", "unit_cost"],
    "orders": ["order_id", "order_ts", "channel", "customer_state", "ship_country"],
    "order_items": ["order_id", "sku", "quantity", "unit_price", "discount_pct"],
    "inventory_snapshots": ["snapshot_date", "sku", "on_hand_units", "reorder_point"],
}


class CsvExportConnector(MarketplaceConnector):
    name = "csv"

    def __init__(self, directory: str):
        self.directory = Path(directory).expanduser().resolve()

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        tables: dict[str, pd.DataFrame] = {}
        for entity in ENTITIES:
            path = self.directory / f"{entity}.csv"
            if path.exists():
                tables[entity] = pd.read_csv(path)
            else:
                tables[entity] = pd.DataFrame(columns=_COLUMNS[entity])
        self.validate(tables)
        return tables
