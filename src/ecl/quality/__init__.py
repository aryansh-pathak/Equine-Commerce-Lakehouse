"""Data-quality validation framework (dbt tests + Python expectation suites)."""
from __future__ import annotations

from ecl.quality.expectations import Expectation, Result, Suite

__all__ = ["Expectation", "Result", "Suite"]
