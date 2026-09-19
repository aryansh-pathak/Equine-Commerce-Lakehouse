"""End-to-end pipeline entrypoint.

extract -> land (Parquet) -> clean (PySpark) -> load (DuckDB) ->
model (dbt) -> validate (data-quality gate).

Runs the whole lakehouse locally with one command:

    python pipelines/run_pipeline.py --source synthetic

Exits non-zero if the data-quality gate fails, so it is CI-safe.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from config.settings import SETTINGS  # noqa: E402

from ecl.ingest import ingest  # noqa: E402
from ecl.load_duckdb import load  # noqa: E402
from ecl.spark_clean import clean  # noqa: E402


def _step(msg: str) -> float:
    print(f"\n=== {msg} ===", flush=True)
    return time.time()


def _done(t0: float) -> None:
    print(f"    ...done in {time.time() - t0:.1f}s", flush=True)


def run_dbt() -> None:
    env = os.environ.copy()
    env["DUCKDB_PATH"] = str(Path(SETTINGS.duckdb_path).resolve())
    # Use the dbt installed next to this interpreter (works without activating the venv).
    dbt_bin = Path(sys.executable).parent / "dbt"
    cmd = [
        str(dbt_bin) if dbt_bin.exists() else "dbt", "build",
        "--project-dir", str(REPO_ROOT / "dbt"),
        "--profiles-dir", str(REPO_ROOT / "dbt"),
    ]
    subprocess.run(cmd, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the commerce lakehouse pipeline.")
    parser.add_argument("--source", default="synthetic", choices=["synthetic", "csv"])
    parser.add_argument("--csv-dir", default=None, help="directory of CSV exports (source=csv)")
    args = parser.parse_args()

    connector_kwargs = {"directory": args.csv_dir} if args.source == "csv" else {}

    t = _step(f"1/5 Extract + land raw ({args.source})")
    written = ingest(args.source, **connector_kwargs)
    print(f"    landed: {', '.join(Path(p).name for p in written.values())}")
    _done(t)

    t = _step("2/5 Clean + conform (PySpark)")
    report = clean()
    for entity, stats in report.items():
        print(f"    {entity:22s} in={stats['in']:>7} out={stats['out']:>7}"
              + (f" rejected={stats['rejected']}" if "rejected" in stats else ""))
    _done(t)

    t = _step("3/5 Load clean -> DuckDB warehouse (raw schema)")
    counts = load()
    print("    " + "  ".join(f"{k}={v}" for k, v in counts.items()))
    _done(t)

    t = _step("4/5 Transform + test (dbt build: models + native tests)")
    run_dbt()
    _done(t)

    t = _step("5/5 Data-quality gate (expectation suites)")
    from ecl.quality.suite import run_all  # imported late (after warehouse exists)
    passed, results = run_all()
    for r in results:
        mark = "PASS" if r.success else f"FAIL[{r.severity}]"
        print(f"    [{mark}] {r.name} ({r.violations} violations)")
    _done(t)

    print("\n" + ("PIPELINE OK ✅" if passed else "PIPELINE FAILED — data-quality gate ❌"))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
