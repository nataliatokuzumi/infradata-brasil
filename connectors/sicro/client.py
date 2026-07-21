from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from urllib.parse import urlparse, unquote

import requests
from azure.storage.blob import BlobServiceClient

from database import SicroDownloadsDatabase
from settings import database_path, download_dir, extract_dir


class SicroClient(SicroDownloadsDatabase):

    def __init__(self):
        super().__init__(db_path=database_path)

        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir = Path(extract_dir)
        self.extract_dir.mkdir(parents=True, exist_ok=True) 

        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER")
        self.service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.container_client = self.service_client.get_container_client(self.container_name)


    def _download_to_local_file(self, url: str, filename: str) -> Path:
        destination = self.download_dir / filename
        print(f"[local] downloading: {url} -> {destination}")

        with requests.get(url, timeout=120, stream=True) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)

        print(f"[local] saved: {destination}")
        return destination

    def _extract_archive(self, archive_path: Path, extract_dir: Path, extension: str) -> list[Path]:
        
        if extension == ".zip":
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extract_dir)
        elif extension == ".rar":
            try:
                import rarfile
            except ImportError:
                if shutil.which("unrar") is None:
                    raise RuntimeError("rarfile não está instalado e 'unrar' não está disponível")
                subprocess.run(["unrar", "x", str(archive_path), str(extract_dir)], check=True, capture_output=True, text=True)
            else:
                with rarfile.RarFile(archive_path) as archive:
                    archive.extractall(extract_dir)
        elif extension == ".7z":
            if shutil.which("7z") is None:
                raise RuntimeError("'7z' não está disponível no PATH")
            subprocess.run(["7z", "x", str(archive_path), f"-o{extract_dir}"], check=True, capture_output=True, text=True)
        else:
            return [archive_path]

        return sorted(path for path in extract_dir.rglob("*") if path.is_file())

    def _upload_local_files_to_blob(self, local_files: list[Path], base_dir: Path, blob_prefix: str) -> list[str]:
        uploaded_blob_names = []

        for local_file in local_files:
            relative_path = local_file.relative_to(base_dir).as_posix()
            blob_name = f"{blob_prefix.rstrip('/')}/{relative_path}" if blob_prefix else relative_path
            print(f"[blob] uploading: {local_file} -> {blob_name}")

            with local_file.open("rb") as handle:
                self.container_client.upload_blob(name=blob_name, data=handle, overwrite=True)

            uploaded_blob_names.append(blob_name)

        return uploaded_blob_names

    def _download_extract_and_upload(self, url: str, region: str, state_code: str, year: str, month: str, filename: str, extension: str) -> str | None:

        downloaded_path = self._download_to_local_file(url, filename)

        try:
            extracted_files = self._extract_archive(downloaded_path, extract_dir, extension)
        except Exception as exc:
            print(f"[local] extraction failed: {exc}")
            extracted_files = [downloaded_path]

        if extracted_files == [downloaded_path]:
            base_dir = downloaded_path.parent
            files_to_upload = [downloaded_path]
        else:
            base_dir = extract_dir
            files_to_upload = [path for path in extracted_files if path.is_file()]

        blob_prefix = self._build_blob_name(region, state_code, year, month, archive_name)
        self._upload_local_files_to_blob(files_to_upload, base_dir, blob_prefix)

        return self._calculate_hash(downloaded_path)

    def _calculate_hash(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as handle:
            for byte_block in iter(lambda: handle.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def process_pending_downloads(self, statuses=("pending", "failed"), nfiles: int = None) -> None:
        pending_rows = self.get_pending_downloads(statuses, nfiles)
        print(f"Found {len(pending_rows)} pending downloads in the database.")

        if not pending_rows:
            return

        for row in pending_rows:
            _, region, state_code, year, month, revisado, url, filename, extension, status = row
            downloaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                file_hash = self._download_extract_and_upload(url, region, state_code, year, month, filename)
                if file_hash:
                    self.update_download_by_url(url, status="downloaded", file_hash=file_hash, downloaded_at=downloaded_at)
                    print(f"Downloaded, extracted and uploaded: {url}")
                else:
                    self.update_download_by_url(url, status="failed", downloaded_at=downloaded_at)
                    print(f"Upload failed for {url}")
            except requests.RequestException as exc:
                self.update_download_by_url(url, status="failed", downloaded_at=downloaded_at)
                print(f"Failed to download {url}: {exc}")
            except Exception as exc:
                self.update_download_by_url(url, status="failed", downloaded_at=downloaded_at)
                print(f"Processing failed for {url}: {exc}")


    def main(self) -> None:

        self.process_pending_downloads()


if __name__ == "__main__":
    client = SicroClient()
    client.main()

