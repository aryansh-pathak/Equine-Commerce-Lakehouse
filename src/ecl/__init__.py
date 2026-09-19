"""equine-commerce-lakehouse (ecl).

A marketplace-agnostic ELT / lakehouse for a real e-commerce catalog:
extract -> land (Parquet) -> clean (PySpark) -> model (dbt dimensional) ->
validate (data-quality suites) -> serve (analytics app).
"""

__version__ = "0.1.0"
