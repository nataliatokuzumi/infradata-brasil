from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from connectors.blob_storage.client import BlobStorageClient
from connectors.sicro.database import SicroParsedFilesDatabase
from connectors.sicro.parse.classify import BlobClassification, classify_blob
from connectors.sicro.parse.reader import parse_relatorio_sintetico
from connectors.sicro.parse.settings import parsed_dir
from connectors.sicro.parse.writer import build_silver_blob_name, write_silver_parquet
from connectors.sicro.settings import database_path


def _base_record(c: BlobClassification, parsed_at: str) -> dict:
    return {
        "blob_name": c.blob_name,
        "report_type": c.report_type,
        "region": c.region,
        "state_slug": c.state_slug,
        "year": c.year,
        "month": c.month,
        "desonerado": c.desonerado,
        "revisado": c.revisado,
        "archive_stem": c.archive_stem,
        "parsed_at": parsed_at,
    }


class SicroParseClient:

    def __init__(
        self,
        blob_client: BlobStorageClient | None = None,
        tracking_db: SicroParsedFilesDatabase | None = None,
    ):
        self.blob_client = blob_client or BlobStorageClient()
        self.tracking_db = tracking_db or SicroParsedFilesDatabase(db_path=database_path)

        self.parsed_dir = Path(parsed_dir)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)

    def discover_candidates(self) -> list[BlobClassification]:
        blob_names = self.blob_client.list_blobs()

        candidates = [classify_blob(name) for name in blob_names]

        return [c for c in candidates if c is not None]

    def pending_candidates(self) -> list[BlobClassification]:
        return [
            c for c in self.discover_candidates()
            if not self.tracking_db.is_parsed(c.blob_name)
        ]

    def _process_one(self, c: BlobClassification) -> dict:
        parsed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        try:
            xlsx_bytes = self.blob_client.download_blob_bytes(c.blob_name)
            df = parse_relatorio_sintetico(xlsx_bytes)

            local_path = write_silver_parquet(df, c, self.parsed_dir)
            silver_blob_name = build_silver_blob_name(c)
            self.blob_client.upload_file(local_path, silver_blob_name)
            local_path.unlink(missing_ok=True)

            return {
                **_base_record(c, parsed_at),
                "silver_blob_name": silver_blob_name,
                "row_count": len(df),
                "status": "parsed",
                "error": None,
            }

        except Exception as exc:

            print(f"Parsing failed for {c.blob_name}: {exc}")

            return {
                **_base_record(c, parsed_at),
                "silver_blob_name": None,
                "row_count": None,
                "status": "failed",
                "error": str(exc),
            }

    def process_pending(self, max_workers: int = 5) -> None:
        candidates = self.pending_candidates()

        print(
            f"Found {len(candidates)} pending report files to parse."
        )

        if not candidates:
            return

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = [
                executor.submit(self._process_one, c)
                for c in candidates
            ]

            for future in as_completed(futures):
                self.tracking_db.upsert_parsed_file(future.result())

    def main(self) -> None:
        self.process_pending()
