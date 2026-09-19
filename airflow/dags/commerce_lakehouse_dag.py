"""Airflow DAG: daily orchestration of the commerce lakehouse.

extract_land -> spark_clean -> load_warehouse -> dbt_build -> dq_gate

Each task maps to the same functions the CLI pipeline uses, so local runs and
scheduled runs execute identical code. Scheduled daily; the dq_gate task fails
the run (and alerts) if data quality regresses.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Make the project importable inside the Airflow worker.
REPO_ROOT = Path(os.getenv("ECL_HOME", Path(__file__).resolve().parents[2]))
for p in (REPO_ROOT, REPO_ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

DEFAULT_ARGS = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
}


def _extract_land(**_):
    from ecl.ingest import ingest
    return ingest(os.getenv("ECL_SOURCE", "synthetic"))


def _spark_clean(**_):
    from ecl.spark_clean import clean
    return clean()


def _load_warehouse(**_):
    from ecl.load_duckdb import load
    return load()


def _dq_gate(**_):
    from ecl.quality.suite import run_all
    passed, _ = run_all()
    if not passed:
        raise ValueError("Data-quality gate failed — see data/quality/dq_report.html")


with DAG(
    dag_id="commerce_lakehouse",
    description="Multi-marketplace ELT -> dimensional warehouse -> DQ gate",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",  # daily at 06:00
    catchup=False,
    tags=["ecommerce", "elt", "dbt", "spark"],
) as dag:
    extract_land = PythonOperator(task_id="extract_land", python_callable=_extract_land)
    spark_clean = PythonOperator(task_id="spark_clean", python_callable=_spark_clean)
    load_warehouse = PythonOperator(task_id="load_warehouse", python_callable=_load_warehouse)

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {REPO_ROOT} && DUCKDB_PATH={REPO_ROOT}/data/warehouse/ecl.duckdb "
            f"dbt build --project-dir {REPO_ROOT}/dbt --profiles-dir {REPO_ROOT}/dbt"
        ),
    )
    dq_gate = PythonOperator(task_id="dq_gate", python_callable=_dq_gate)

    extract_land >> spark_clean >> load_warehouse >> dbt_build >> dq_gate
