FROM python:3.11-slim

# DuckDB's azure/httpfs extensions need a CA bundle to validate HTTPS to
# Blob Storage — see superset/Dockerfile for the full debug history.
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV CURL_CA_INFO=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
# workers=1: gold.py opens one persistent DuckDB catalog file per process
# (CATALOG_PATH) — DuckDB only allows one read-write connection to a given
# database file at a time, so a second worker process would fail to connect.
# threads=4 still gives concurrency across requests within that one process
# (get_connection()/query() are already written to be thread-safe, see
# gold.py's cursor()-per-call comment).
ENTRYPOINT ["gunicorn", "--bind=0.0.0.0:8501", "--workers=1", "--threads=4", "--worker-class=gthread", "app:server"]
