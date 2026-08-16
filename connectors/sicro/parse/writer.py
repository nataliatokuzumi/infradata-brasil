import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from connectors.sicro.parse.classify import BlobClassification
from connectors.sicro.parse.settings import silver_prefix


def _file_id(blob_name: str) -> str:
    # Deterministic per source blob, so re-parsing the same blob overwrites
    # the same silver file instead of accumulating duplicates.
    return hashlib.sha1(blob_name.encode("utf-8")).hexdigest()[:16]


def build_silver_blob_name(c: BlobClassification) -> str:
    return (
        f"{silver_prefix}/"
        f"report_type={c.report_type}/"
        f"desonerado={str(c.desonerado).lower()}/"
        f"year={c.year}/month={c.month}/state_slug={c.state_slug}/"
        f"{_file_id(c.blob_name)}.parquet"
    )


def write_silver_parquet(df: pd.DataFrame, c: BlobClassification, local_dir: Path) -> Path:
    enriched = df.copy()
    enriched["blob_name"] = c.blob_name
    enriched["region"] = c.region
    enriched["state_slug"] = c.state_slug
    enriched["year"] = c.year
    enriched["month"] = c.month
    enriched["report_type"] = c.report_type
    enriched["desonerado"] = c.desonerado
    enriched["revisado"] = c.revisado
    enriched["archive_stem"] = c.archive_stem
    enriched["parsed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / f"{_file_id(c.blob_name)}.parquet"

    enriched.to_parquet(local_path, engine="pyarrow", index=False)

    return local_path
