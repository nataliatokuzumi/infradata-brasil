# infradata-brasil

Data pipeline that ingests **SICRO** (Sistema de Custos Referenciais de Obras), DNIT's reference cost index, and exposes an analytical layer (star schema + views) queryable via DuckDB, with a dashboard on top.

## Architecture

The pipeline follows a raw → silver → gold layering, with each layer implemented in a different technology:

```
DNIT (website)
    │  scraping + download + extraction         (Python)
    ▼
raw/       raw files (xlsx/zip/7z), organized by region/state/year/month
    │  parsing + cleaning/typing                 (Python + pandas)
    ▼
silver/    typed Parquet, 1 row per item per source file
    │  transformation (star schema)              (dbt + DuckDB)
    ▼
gold/      dimensions + facts + exposure views, in Parquet
    │
    ▼
dash/      dashboard (Plotly Dash), reading gold directly from Blob Storage via DuckDB
```

Everything moves through Blob Storage (Azure) between stages — no layer reads from the previous one locally; each one reads/writes Parquet (or raw files) to Blob.

## Running it

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt          # connectors + dbt
pip install -r requirements-dev.txt      # pytest, dev only
```

Required environment variables (connectors + dbt):

```
AZURE_STORAGE_CONNECTION_STRING
AZURE_STORAGE_CONTAINER
```

### Running the pipeline

```bash
# raw: discovers new publications on the DNIT site, downloads, extracts, uploads to Blob
python -m layers.raw.main

# silver: parses pending raw files into typed Parquet
python -m layers.silver.main [optional_limit]

# gold: silver → star schema (dimensions/facts) + exposure views
cd layers/gold_dbt
dbt build
```

### Tests

```bash
pytest tests/
```

### Dashboard

```bash
cd dash
pip install -r requirements.txt
python app.py
```

Additional environment variables: `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER` (reads gold directly from Blob), `DASH_AUTH_USERNAME`/`DASH_AUTH_PASSWORD` (Basic Auth).
