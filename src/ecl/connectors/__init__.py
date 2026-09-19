"""Source connectors for the ingestion layer."""
from __future__ import annotations

from ecl.connectors.base import ENTITIES, MarketplaceConnector
from ecl.connectors.csv_connector import CsvExportConnector
from ecl.connectors.synthetic import SyntheticConnector


def get_connector(source: str = "synthetic", **kwargs) -> MarketplaceConnector:
    """Factory: resolve a connector by name.

    'synthetic' -> generated data (default, always runnable)
    'csv'       -> read marketplace CSV exports from a directory
    Live API connectors (amazon/ebay/etsy/walmart/faire) live in api_stubs.py
    and are wired the same way once credentials are provided.
    """
    source = source.lower()
    if source == "synthetic":
        return SyntheticConnector(**kwargs)
    if source == "csv":
        return CsvExportConnector(**kwargs)
    raise ValueError(f"unknown source '{source}'")


__all__ = [
    "ENTITIES",
    "MarketplaceConnector",
    "SyntheticConnector",
    "CsvExportConnector",
    "get_connector",
]
