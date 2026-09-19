"""Marketplace connector interface.

Every source (synthetic generator, CSV export, or a live marketplace API)
implements the same contract, so the ingestion layer never knows or cares
where the rows came from. Swapping data sources is a config change.
"""
from __future__ import annotations

import abc

import pandas as pd

# The four raw entities every connector must be able to supply.
ENTITIES = ("products", "orders", "order_items", "inventory_snapshots")


class MarketplaceConnector(abc.ABC):
    """Abstract source connector."""

    name: str = "base"

    @abc.abstractmethod
    def fetch_all(self) -> dict[str, pd.DataFrame]:
        """Return a mapping of entity name -> raw DataFrame."""
        raise NotImplementedError

    def validate(self, tables: dict[str, pd.DataFrame]) -> None:
        missing = [e for e in ENTITIES if e not in tables]
        if missing:
            raise ValueError(f"{self.name}: connector missing entities {missing}")
