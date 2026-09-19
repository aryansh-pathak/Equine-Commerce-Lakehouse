"""Cleaning / conforming step (PySpark).

Reads the raw landing zone and produces the conformed `clean/` layer:
type-casts, trims whitespace, repairs stringified prices, drops exact
duplicates, and quarantines invalid rows (non-positive quantities, unparseable
prices). This is the heavy-lifting transform and is written in PySpark so it
scales from a laptop to a cluster unchanged.

Emits a small cleaning report (rows in vs out, rows rejected per table).
"""
from __future__ import annotations

from pathlib import Path

from config.settings import SETTINGS
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from ecl.spark_session import get_spark


def _raw(spark, entity: str) -> DataFrame:
    path = f"{SETTINGS.lake_path(SETTINGS.raw_prefix)}/{entity}.parquet"
    return spark.read.parquet(path)


def _write(df: DataFrame, entity: str) -> None:
    path = f"{SETTINGS.lake_path(SETTINGS.clean_prefix)}/{entity}"
    df.write.mode("overwrite").parquet(path)


def clean() -> dict[str, dict[str, int]]:
    spark = get_spark("ecl-clean")
    spark.sparkContext.setLogLevel("ERROR")
    report: dict[str, dict[str, int]] = {}
    try:
        # --- products ---
        p = _raw(spark, "products")
        p_in = p.count()
        products = (
            p.withColumn("sku", F.trim(F.col("sku")))
            .withColumn("msrp", F.col("msrp").cast("double"))
            .withColumn("unit_cost", F.col("unit_cost").cast("double"))
            .dropDuplicates(["sku"])
            .filter(F.col("sku").isNotNull() & (F.col("msrp") > 0))
        )
        _write(products, "products")
        report["products"] = {"in": p_in, "out": products.count()}

        # --- orders ---
        o = _raw(spark, "orders")
        o_in = o.count()
        orders = (
            o.withColumn("order_ts", F.to_timestamp("order_ts"))
            .withColumn("customer_state", F.trim(F.col("customer_state")))
            .withColumn("channel", F.lower(F.trim(F.col("channel"))))
            .dropDuplicates(["order_id"])
            .filter(F.col("order_id").isNotNull() & F.col("order_ts").isNotNull())
        )
        _write(orders, "orders")
        report["orders"] = {"in": o_in, "out": orders.count()}

        # --- order_items --- (the dirtiest table)
        it = _raw(spark, "order_items")
        it_in = it.count()
        parsed = (
            it.withColumn("sku", F.trim(F.col("sku")))
            # strip currency symbols/commas, then cast
            .withColumn(
                "unit_price",
                F.regexp_replace(F.col("unit_price").cast("string"), r"[^0-9.]", "").cast("double"),
            )
            .withColumn("quantity", F.col("quantity").cast("int"))
            .withColumn("discount_pct", F.col("discount_pct").cast("double"))
            .dropDuplicates(["order_id", "sku", "quantity", "unit_price"])
        )
        valid = parsed.filter(
            (F.col("quantity") > 0)
            & F.col("unit_price").isNotNull()
            & (F.col("unit_price") > 0)
            & F.col("sku").isNotNull()
        ).withColumn("line_gross", F.round(F.col("quantity") * F.col("unit_price"), 2))
        _write(valid, "order_items")
        report["order_items"] = {
            "in": it_in,
            "out": valid.count(),
            "rejected": it_in - valid.count(),
        }

        # --- inventory_snapshots ---
        inv = _raw(spark, "inventory_snapshots")
        inv_in = inv.count()
        inventory = (
            inv.withColumn("snapshot_date", F.to_date("snapshot_date"))
            .withColumn("on_hand_units", F.col("on_hand_units").cast("int"))
            .withColumn("reorder_point", F.col("reorder_point").cast("int"))
            .dropDuplicates(["snapshot_date", "sku"])
            .filter(F.col("snapshot_date").isNotNull() & F.col("sku").isNotNull())
        )
        _write(inventory, "inventory_snapshots")
        report["inventory_snapshots"] = {"in": inv_in, "out": inventory.count()}
    finally:
        spark.stop()

    Path(SETTINGS.lake_path(SETTINGS.clean_prefix)).mkdir(parents=True, exist_ok=True)
    return report


if __name__ == "__main__":  # pragma: no cover
    import json

    print(json.dumps(clean(), indent=2))
