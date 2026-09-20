import sqlite3
from pathlib import Path

from connectors.common.logger import get_logger
from layers import queries

logger = get_logger(__name__)


database_path = "downloads.db"
database_local_path = Path(__file__).parent / database_path


class SicroTrackingDatabase:

    def __init__(self, db_path: str):

        self.db = Path(__file__).parent / db_path
        self.conn = sqlite3.connect(self.db)
        logger.debug(f"[database] connected: {self.db}")
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute(queries.CREATE_SICRO_DOWNLOADS_TABLE)
            self.conn.execute(queries.CREATE_SICRO_PARSED_FILES_TABLE)

    # --- sicro_downloads (raw layer) ---

    def insert_download(
        self,
        url: str,
        region: str = None,
        state_code: str = None,
        year: str = None,
        month: str = None,
        revisado: bool = None,
        filename: str = None,
        extension: str = None,
        scraped_at: str = None,
        downloaded_at: str = None,
        status: str = None,
        file_hash: str = None
    ):
        with self.conn:
            self.conn.execute(
                queries.INSERT_DOWNLOAD,
                (region, state_code, year, month, revisado, url, filename, extension, scraped_at, downloaded_at, status, file_hash),
            )

    def url_exists(self, url: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(queries.URL_EXISTS, (url,))
        return cursor.fetchone() is not None

    def get_pending_downloads(self, statuses=("pending",), nfiles: int = None):
        placeholders = ",".join("?" for _ in statuses)
        query = queries.GET_PENDING_DOWNLOADS.format(
            placeholders=placeholders,
            limit_clause=f"LIMIT {nfiles}" if nfiles is not None else "",
        )
        cursor = self.conn.cursor()
        cursor.execute(query, statuses)
        return cursor.fetchall()

    def update_download_by_url(
        self,
        downloads: list[dict]
    ) -> None:

        if not downloads:
            return

        rows = [(
            item.get("status"),
            item.get("file_hash"),
            item.get("downloaded_at"),
            item["url"]
        ) for item in downloads
        ]

        with self.conn:
            self.conn.executemany(queries.UPDATE_DOWNLOAD_BY_URL, rows)

    def update_download(
        self,
        state_code: str,
        year: str,
        month: str,
        revisado: bool,
        status: str,
        file_hash: str = None,
        downloaded_at: str = None,
    ):
        with self.conn:
            self.conn.execute(
                queries.UPDATE_DOWNLOAD,
                (status, file_hash, downloaded_at, state_code, year, month, revisado),
            )

    def get_download(self, state_code: str, year: str, month: str, revisado: bool):
        cursor = self.conn.cursor()
        cursor.execute(
            queries.GET_DOWNLOAD,
            (state_code, year, month, revisado),
        )
        return cursor.fetchone()

    # --- sicro_parsed_files (silver layer) ---

    def is_parsed(self, blob_name: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(queries.IS_PARSED, (blob_name,))
        return cursor.fetchone() is not None

    def upsert_parsed_file(self, record: dict) -> None:
        with self.conn:
            self.conn.execute(
                queries.UPSERT_PARSED_FILE,
                (
                    record["blob_name"],
                    record.get("report_type"),
                    record.get("region"),
                    record.get("state_slug"),
                    record.get("year"),
                    record.get("month"),
                    record.get("desonerado"),
                    record.get("revisado"),
                    record.get("archive_stem"),
                    record.get("silver_blob_name"),
                    record.get("row_count"),
                    record.get("status"),
                    record.get("error"),
                    record.get("parsed_at"),
                ),
            )

    def get_failed(self) -> list[tuple]:
        cursor = self.conn.cursor()
        cursor.execute(queries.GET_FAILED)
        return cursor.fetchall()
