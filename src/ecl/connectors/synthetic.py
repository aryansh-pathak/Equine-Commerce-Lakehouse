"""Synthetic connector -- wraps the data generator as a source.

This is the default source so the whole lakehouse runs end-to-end with zero
credentials. Point the pipeline at `csv` or a live API connector to swap in
real Majestic Ally data without touching downstream code.
"""
from __future__ import annotations

import pandas as pd

from ecl.connectors.base import MarketplaceConnector
from ecl.generate import generate


class SyntheticConnector(MarketplaceConnector):
    name = "synthetic"

    def __init__(self, seed: int | None = None):
        self.seed = seed

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        tables = generate(seed=self.seed)
        self.validate(tables)
        return tables
