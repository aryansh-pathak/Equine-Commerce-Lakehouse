"""SparkSession factory.

Centralizes the JVM flags needed to run Spark 3.5 on modern JDKs (17/21),
so every Spark job in the project starts a session the same way.
"""
from __future__ import annotations

import os

from pyspark.sql import SparkSession

# Required for Spark 3.5 on Java 17+ (strong encapsulation / module access).
_JAVA_OPTS = " ".join(
    [
        "--add-opens=java.base/java.lang=ALL-UNNAMED",
        "--add-opens=java.base/java.util=ALL-UNNAMED",
        "--add-opens=java.base/java.nio=ALL-UNNAMED",
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
        "--add-opens=java.base/java.io=ALL-UNNAMED",
        "--add-opens=java.base/java.net=ALL-UNNAMED",
    ]
)


def get_spark(app_name: str = "ecl", cores: str = "local[*]") -> SparkSession:
    # Local mode: bind to loopback so startup doesn't depend on hostname/network/VPN.
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    return (
        SparkSession.builder.master(cores)
        .appName(app_name)
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.extraJavaOptions", _JAVA_OPTS)
        .config("spark.executor.extraJavaOptions", _JAVA_OPTS)
        .getOrCreate()
    )
