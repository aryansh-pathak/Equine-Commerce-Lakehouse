"""A small, dependency-light expectations engine (Great Expectations style).

Each expectation compiles to a SQL query that counts violating rows against the
DuckDB warehouse; zero violations passes. Suites collect results and can gate a
pipeline (severity="error") or merely warn (severity="warn"). Kept intentionally
small and transparent -- swap for Great Expectations in a cloud deployment; the
suite definitions in `suite.py` translate directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb


@dataclass
class Result:
    name: str
    success: bool
    violations: int
    severity: str
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "expectation": self.name,
            "success": self.success,
            "violations": self.violations,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class Expectation:
    name: str
    sql_violations: str  # SELECT count(*) of violating rows
    severity: str = "error"  # "error" gates the pipeline; "warn" does not
    detail: str = ""


@dataclass
class Suite:
    name: str
    con: duckdb.DuckDBPyConnection
    expectations: list[Expectation] = field(default_factory=list)

    # ---- builder helpers (compose SQL for common checks) ----
    def expect_not_null(self, table: str, column: str, severity: str = "error") -> Suite:
        self.expectations.append(
            Expectation(
                f"{table}.{column} not null",
                f"SELECT count(*) FROM {table} WHERE {column} IS NULL",
                severity,
            )
        )
        return self

    def expect_unique(self, table: str, columns: list[str], severity: str = "error") -> Suite:
        cols = ", ".join(columns)
        self.expectations.append(
            Expectation(
                f"{table} unique on ({cols})",
                f"SELECT count(*) FROM (SELECT {cols} FROM {table} "
                f"GROUP BY {cols} HAVING count(*) > 1)",
                severity,
            )
        )
        return self

    def expect_positive(self, table: str, column: str, severity: str = "error") -> Suite:
        self.expectations.append(
            Expectation(
                f"{table}.{column} > 0",
                f"SELECT count(*) FROM {table} WHERE {column} IS NULL OR {column} <= 0",
                severity,
            )
        )
        return self

    def expect_in_set(self, table: str, column: str, allowed: list[str], severity: str = "error") -> Suite:
        vals = ", ".join(f"'{v}'" for v in allowed)
        self.expectations.append(
            Expectation(
                f"{table}.{column} in set",
                f"SELECT count(*) FROM {table} WHERE {column} NOT IN ({vals})",
                severity,
            )
        )
        return self

    def expect_range(self, table: str, column: str, lo: float, hi: float, severity: str = "warn") -> Suite:
        self.expectations.append(
            Expectation(
                f"{table}.{column} in [{lo}, {hi}]",
                f"SELECT count(*) FROM {table} WHERE {column} < {lo} OR {column} > {hi}",
                severity,
            )
        )
        return self

    def expect_foreign_key(
        self, child: str, child_col: str, parent: str, parent_col: str, severity: str = "error"
    ) -> Suite:
        self.expectations.append(
            Expectation(
                f"{child}.{child_col} -> {parent}.{parent_col}",
                f"SELECT count(*) FROM {child} c LEFT JOIN {parent} p "
                f"ON c.{child_col} = p.{parent_col} WHERE p.{parent_col} IS NULL",
                severity,
            )
        )
        return self

    def expect_row_count_at_least(self, table: str, minimum: int, severity: str = "error") -> Suite:
        self.expectations.append(
            Expectation(
                f"{table} row count >= {minimum}",
                f"SELECT CASE WHEN count(*) >= {minimum} THEN 0 ELSE 1 END FROM {table}",
                severity,
            )
        )
        return self

    # ---- execution ----
    def run(self) -> list[Result]:
        results: list[Result] = []
        for exp in self.expectations:
            violations = self.con.execute(exp.sql_violations).fetchone()[0]
            results.append(
                Result(
                    name=exp.name,
                    success=violations == 0,
                    violations=int(violations),
                    severity=exp.severity,
                    detail=exp.detail,
                )
            )
        return results
