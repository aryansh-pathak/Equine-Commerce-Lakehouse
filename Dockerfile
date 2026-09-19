# Image for running the pipeline and the Streamlit dashboard.
FROM python:3.11-slim

# Java runtime for PySpark.
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless make \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src \
    DUCKDB_PATH=/app/data/warehouse/ecl.duckdb

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
# Default: build the warehouse, then serve the dashboard.
CMD ["bash", "-lc", "python pipelines/run_pipeline.py --source synthetic && streamlit run app/dashboard.py --server.address 0.0.0.0"]
