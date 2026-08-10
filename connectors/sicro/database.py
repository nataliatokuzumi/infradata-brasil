import sqlite3
from pathlib import Path


class SicroDownloadsDatabase:

    def __init__(self, db_path: str):
        
        self.db = Path(__file__).parent / db_path
        self.conn = sqlite3.connect(self.db)
        self.create_table()

    def create_table(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sicro_downloads (
                    id INTEGER PRIMARY KEY,
                    region TEXT NULL,
                    state_code TEXT NULL,
                    year TEXT NULL,
                    month TEXT NULL,
                    revisado BOOLEAN NULL,
                    url TEXT NOT NULL UNIQUE,
                    filename TEXT NULL,
                    extension TEXT NULL,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    downloaded_at TIMESTAMP NULL,
                    status TEXT NULL,
                    file_hash TEXT NULL
                );
                """
            )

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
                """
                INSERT OR IGNORE INTO sicro_downloads (
                    region, state_code, year, month, revisado, url, filename, extension, scraped_at, downloaded_at, status, file_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (region, state_code, year, month, revisado, url, filename, extension, scraped_at, downloaded_at, status, file_hash),
            )

    def url_exists(self, url: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT 1 FROM sicro_downloads WHERE url = ? LIMIT 1;
            """,
            (url,)
        )
        return cursor.fetchone() is not None

    def get_pending_downloads(self, statuses=("pending",), nfiles: int = None):
        placeholders = ",".join("?" for _ in statuses)
        query = f"""
            SELECT id, region, state_code, year, month, url, filename, extension
            FROM sicro_downloads
            WHERE status IN ({placeholders})
            and region in ('norte')
            ORDER BY scraped_at ASC, id ASC
            {f"LIMIT {nfiles}" if nfiles is not None else ""};
            """
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
            self.conn.executemany(
                """
                UPDATE sicro_downloads
                SET status = ?, file_hash = ?, downloaded_at = COALESCE(?, downloaded_at)
                WHERE url = ?;
                """,
                rows,
            )

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
                """
                UPDATE sicro_downloads
                SET status = ?, file_hash = ?, downloaded_at = COALESCE(?, downloaded_at)
                WHERE state_code = ? AND year = ? AND month = ? AND revisado = ?;
                """,
                (status, file_hash, downloaded_at, state_code, year, month, revisado),
            )

    def get_download(self, state_code: str, year: str, month: str, revisado: bool):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT status, filename, file_hash, downloaded_at
            FROM sicro_downloads
            WHERE state_code = ? AND year = ? AND month = ? AND revisado = ?
            ORDER BY downloaded_at DESC, id DESC
            LIMIT 1;
            """,
            (state_code, year, month, revisado),
        )
        return cursor.fetchone()
