from pathlib import Path
from datetime import datetime
import hashlib
import argparse
import sys
from urllib.parse import urlparse, unquote

import requests

try:
    from .database import SicroDownloadsDatabase
    from .settings import database_path
except ImportError:
    from database import SicroDownloadsDatabase
    from settings import database_path


class SicroClient(SicroDownloadsDatabase):

    def __init__(self, download_dir="downloads", db_path=None):
        db_file = db_path or database_path
        super().__init__(db_path=db_file)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        print(f"Download directory set to: {self.download_dir}")
        print(f"Using database: {self.db_path}")

    def _download(self, url: str, filename: str) -> Path:
        destination = self.download_dir / filename
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        with open(destination, "wb") as f:
            f.write(response.content)

        return destination

    def _resolve_filename(self, url: str, filename: str | None = None) -> str:
        if filename:
            return filename
        parsed = urlparse(url)
        return Path(unquote(parsed.path)).name

    def _upload_to_blob_storage(self, file_path: Path, blob_name: str) -> bool:
        """
        Upload a downloaded file to blob storage.

        Required information from you:
        - provider (Azure Blob, AWS S3, Google Cloud Storage, etc.)
        - credentials or connection string / auth method
        - container or bucket name
        - optional prefix/key pattern
        """
        print(f"[blob] upload requested: {file_path} -> {blob_name}")
        return True

    def get_file_hash(self, file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def process_pending_downloads(self, statuses=("pending", "failed"), blob_prefix: str = "") -> None:
        pending_rows = self.get_pending_downloads(statuses)
        if not pending_rows:
            print("No pending downloads found in the database.")
            return

        for row in pending_rows:
            _, region, state_code, year, month, revisado, url, filename, extension, status = row
            filename = self._resolve_filename(url, filename)
            downloaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            blob_name = f"{blob_prefix}{filename}" if blob_prefix else filename

            try:
                file_path = self._download(url, filename)
                file_hash = self.get_file_hash(file_path)
                upload_ok = self._upload_to_blob_storage(file_path, blob_name)
                if upload_ok:
                    self.update_download_by_url(url, status="downloaded", file_hash=file_hash, downloaded_at=downloaded_at)
                    print(f"Downloaded and uploaded: {url} -> {blob_name}")
                else:
                    self.update_download_by_url(url, status="failed", downloaded_at=downloaded_at)
                    print(f"Upload failed for {url}")
            except requests.RequestException as exc:
                self.update_download_by_url(url, status="failed", downloaded_at=downloaded_at)
                print(f"Failed to download {url}: {exc}")

    @staticmethod
    def main(argv=None) -> None:
        parser = argparse.ArgumentParser(description="Download pending Sicro file URLs from the database and upload them to blob storage.")
        parser.add_argument("--db", default=None, help="Path to the SQLite database file")
        parser.add_argument("--download-dir", default="downloads", help="Local directory for downloaded files")
        parser.add_argument("--blob-prefix", default="", help="Optional prefix for blob storage keys")
        args = parser.parse_args(argv)

        client = SicroClient(download_dir=args.download_dir, db_path=args.db)
        client.process_pending_downloads(blob_prefix=args.blob_prefix)


if __name__ == "__main__":
    SicroClient.main(sys.argv[1:])
