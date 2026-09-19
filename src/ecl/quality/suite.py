"""Concrete data-quality suites run against the modeled warehouse.

Three suites cover the "Catalog Data-Quality" surface and the fact tables:
  * catalog   -> dim_product integrity (the SKU master)
  * sales     -> fct_orders integrity + referential integrity to the catalog
  * inventory -> fct_inventory_snapshot sanity

Run after dbt builds. Writes a JSON + HTML report to data/quality/ and exits
non-zero if any error-severity expectation fails -- so it can gate a pipeline
or a CI job.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import duckdb
from config.settings import SETTINGS

from ecl.catalog import CATEGORIES
from ecl.quality.expectations import Result, Suite

REPORT_DIR = Path(SETTINGS.duckdb_path).resolve().parents[1] / "quality"


def _catalog_suite(con) -> Suite:
    return (
        Suite("catalog", con)
        .expect_row_count_at_least("main.dim_product", 100)
        .expect_not_null("main.dim_product", "sku")
        .expect_unique("main.dim_product", ["sku"])
        .expect_positive("main.dim_product", "msrp")
        .expect_positive("main.dim_product", "unit_cost")
        .expect_in_set("main.dim_product", "category", CATEGORIES)
        .expect_range("main.dim_product", "gross_margin", 0.20, 0.80, severity="warn")
    )


def _sales_suite(con) -> Suite:
    return (
        Suite("sales", con)
        .expect_row_count_at_least("main.fct_orders", 1000)
        .expect_not_null("main.fct_orders", "order_line_key")
        .expect_unique("main.fct_orders", ["order_line_key"])
        .expect_positive("main.fct_orders", "quantity")
        .expect_positive("main.fct_orders", "unit_price")
        .expect_in_set("main.fct_orders", "channel", list(SETTINGS.channels))
        .expect_foreign_key("main.fct_orders", "sku", "main.dim_product", "sku")
    )


def _inventory_suite(con) -> Suite:
    return (
        Suite("inventory", con)
        .expect_not_null("main.fct_inventory_snapshot", "snapshot_date")
        .expect_range("main.fct_inventory_snapshot", "on_hand_units", 0, 100000, severity="error")
        .expect_foreign_key("main.fct_inventory_snapshot", "sku", "main.dim_product", "sku")
    )


def run_all() -> tuple[bool, list[Result]]:
    con = duckdb.connect(str(SETTINGS.duckdb_path))
    all_results: list[Result] = []
    try:
        for builder in (_catalog_suite, _sales_suite, _inventory_suite):
            all_results.extend(builder(con).run())
    finally:
        con.close()

    hard_failures = [r for r in all_results if not r.success and r.severity == "error"]
    passed = len(hard_failures) == 0
    _write_report(all_results, passed)
    return passed, all_results


def _write_report(results: list[Result], passed: bool) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "passed": passed,
        "total": len(results),
        "failed": sum(1 for r in results if not r.success),
        "results": [r.as_dict() for r in results],
    }
    (REPORT_DIR / "dq_report.json").write_text(json.dumps(payload, indent=2))

    rows = "\n".join(
        f"<tr class='{'ok' if r.success else r.severity}'>"
        f"<td>{'PASS' if r.success else 'FAIL'}</td><td>{r.name}</td>"
        f"<td>{r.severity}</td><td>{r.violations}</td></tr>"
        for r in results
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Data Quality Report</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;margin:2rem;color:#1a2b1a}}
h1{{margin-bottom:.2rem}} .status{{font-size:1.2rem;font-weight:700}}
table{{border-collapse:collapse;margin-top:1rem;width:100%}}
th,td{{border:1px solid #d5dcd5;padding:.4rem .6rem;text-align:left}}
th{{background:#2f5233;color:#fff}}
tr.ok td:first-child{{color:#2f5233;font-weight:700}}
tr.error td:first-child{{color:#b00020;font-weight:700}}
tr.warn td:first-child{{color:#b8860b;font-weight:700}}
</style></head><body>
<h1>Equine Commerce Lakehouse — Data Quality</h1>
<p class="status">Overall: {'✅ PASSED' if passed else '❌ FAILED'} &nbsp;
({sum(1 for r in results if r.success)}/{len(results)} expectations passed)</p>
<table><tr><th>Result</th><th>Expectation</th><th>Severity</th><th>Violations</th></tr>
{rows}</table></body></html>"""
    (REPORT_DIR / "dq_report.html").write_text(html)


if __name__ == "__main__":  # pragma: no cover
    import sys

    ok, results = run_all()
    for r in results:
        mark = "PASS" if r.success else f"FAIL({r.severity})"
        print(f"  [{mark}] {r.name} — {r.violations} violations")
    print(f"\nData quality: {'PASSED' if ok else 'FAILED'}  (report: {REPORT_DIR}/dq_report.html)")
    sys.exit(0 if ok else 1)
