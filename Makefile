.PHONY: help setup pipeline dbt dq test lint dashboard docs clean

export PYTHONPATH := $(CURDIR):$(CURDIR)/src
export DUCKDB_PATH ?= $(CURDIR)/data/warehouse/ecl.duckdb

# Prefer a project-local virtualenv and JDK (./.venv, ./.tools/jdk) when present,
# so targets work without activating anything. Otherwise fall back to PATH.
ifneq ($(wildcard $(CURDIR)/.venv/bin/python),)
PYTHON ?= $(CURDIR)/.venv/bin/python
DBT ?= $(CURDIR)/.venv/bin/dbt
else
PYTHON ?= python
DBT ?= dbt
endif
ifneq ($(wildcard $(CURDIR)/.tools/jdk/Contents/Home),)
export JAVA_HOME ?= $(CURDIR)/.tools/jdk/Contents/Home
export PATH := $(JAVA_HOME)/bin:$(PATH)
endif

help:
	@echo "Targets:"
	@echo "  setup      install Python dependencies"
	@echo "  pipeline   run full ELT: extract -> spark clean -> load -> dbt -> DQ gate"
	@echo "  dbt        run dbt build only (models + tests)"
	@echo "  dq         run the data-quality suites only"
	@echo "  test       run pytest"
	@echo "  lint       run ruff"
	@echo "  dashboard  launch the Streamlit app"
	@echo "  docs       generate & serve dbt docs"
	@echo "  clean      remove generated data/warehouse artifacts"

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) pipelines/run_pipeline.py --source synthetic

dbt:
	cd dbt && $(DBT) build --project-dir . --profiles-dir .

dq:
	$(PYTHON) -m ecl.quality.suite

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src pipelines app tests

dashboard:
	$(PYTHON) -m streamlit run app/dashboard.py

docs:
	cd dbt && $(DBT) docs generate --project-dir . --profiles-dir . && $(DBT) docs serve --project-dir . --profiles-dir .

clean:
	rm -rf data/lake data/warehouse data/quality dbt/target dbt/logs
