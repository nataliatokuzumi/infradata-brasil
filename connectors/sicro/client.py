from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
import rarfile
import py7zr
from ftfy import fix_text
from urllib.parse import urlparse, unquote

import requests
from azure.storage.blob import BlobServiceClient

from database import SicroDownloadsDatabase
from concurrent.futures import ThreadPoolExecutor, as_completed
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

        self.downloaded = []


    def _download_to_local_file(
        self,
        url: str,
        filename: str,
    ):
        destination = self.download_dir / filename

        sha256 = hashlib.sha256()

        with requests.get(
            url,
            timeout=120,
            stream=True,
        ) as response:

            response.raise_for_status()

            with destination.open("wb") as handle:

                for chunk in response.iter_content(
                    chunk_size=8 * 1024 * 1024
                ):
                    if chunk:
                        handle.write(chunk)
                        sha256.update(chunk)

        return destination, sha256.hexdigest()
    
    
    @staticmethod
    def fix_filename(path: Path) -> Path:
        fixed_name = fix_text(path.name)

        if fixed_name != path.name:
            new_path = path.with_name(fixed_name)
            path.rename(new_path)
            return new_path

        return path
    

    def _extract_archive(self, archive_path: Path, extension: str, filename: str) -> list[Path]:
        
        extract_dir = self.extract_dir / filename

        if extension.lower() == "zip":

            print(f"[extract] extracting ZIP: {archive_path} -> {extract_dir}")

            extract_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(archive_path, "r") as archive:
                print(f"[extract] ZIP contains {len(archive.namelist())} files")
                archive.extractall(extract_dir)

            files = [
                p for p in extract_dir.rglob("*")
                if p.is_file()
            ]

            print(f"[extract] extracted {len(files)} files")
                
        elif extension == "rar":
            with rarfile.RarFile(archive_path) as archive:
                try:
                    archive.extractall(extract_dir)
                except rarfile.RarCannotExec as e:
                    subprocess.run(
                            ["unar", "-output-directory", str(extract_dir), str(archive_path)],
                            check=True,
                            capture_output=True,
                            text=True,
                        )

        elif extension == "7z":
            try:
                with py7zr.SevenZipFile(archive_path, mode="r") as archive:
                    archive.extractall(path=extract_dir)
            except py7zr.exceptions.Bad7zFile:
                subprocess.run(
                    ["7z", "x", str(archive_path), f"-o{extract_dir}"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
    
        extracted_files = sorted(path for path in extract_dir.rglob("*") if path.is_file())
    
        files_to_upload = [self.fix_filename(path) for path in extracted_files if path.is_file()]
        
        return files_to_upload


    def _upload_one_file(
        self,
        local_file: Path,
        region: str,
        state_code: str,
        year: str,
        month: str,
    ) -> str:

        relative_path = local_file.relative_to(
            self.extract_dir
        ).as_posix()

        relative_path = fix_text(relative_path)

        blob_name = (
            f"{region}/"
            f"{state_code}/"
            f"{year}/"
            f"{month}/"
            f"{relative_path}"
        )

        print(
            f"[blob] uploading: "
            f"{local_file} -> {blob_name}"
        )

        with local_file.open("rb") as handle:
            self.container_client.upload_blob(
                name=blob_name,
                data=handle,
                overwrite=True,
            )

        return blob_name


    def _upload_local_files_to_blob(
        self,
        local_files,
        region,
        state_code,
        year,
        month,
        max_workers=8,
    ):

        with ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:

            futures = [
                executor.submit(
                    self._upload_one_file,
                    local_file,
                    region,
                    state_code,
                    year,
                    month,
                )
                for local_file in local_files
            ]

            return [
                future.result()
                for future in futures
            ]
    

    def _process_row(self, row):
        downloaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        _, region, state_code, year, month, url, filename, extension = row

        try:
            downloaded_path, file_hash = self._download_to_local_file(
                url,
                filename
            )

            extracted_files = self._extract_archive(
                downloaded_path,
                extension,
                Path(filename).stem
            )

            self._upload_local_files_to_blob(
                extracted_files,
                region,
                state_code,
                year,
                month
            )

            downloaded_path.unlink(missing_ok=True)

            extract_dir = self.extract_dir / Path(filename).stem
            shutil.rmtree(extract_dir, ignore_errors=True)
        
            return {"url": url,
                "status": "downloaded",
                "file_hash": file_hash,
                "downloaded_at": downloaded_at
            }

        except Exception as exc:

            print(f"Processing failed for {url}: {exc}")

            return {"url": url,
                "status": "failed",
                "downloaded_at": downloaded_at
            }


    def process_pending_downloads(self, nfiles=None, max_workers=5):

        pending_rows = self.get_pending_downloads(
            statuses=("pending", "failed"),
            nfiles=nfiles,
        )

        print(
            f"Found {len(pending_rows)} pending downloads "
            f"in the database."
        )

        if not pending_rows:
            return

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = [
                executor.submit(self._process_row, row)
                for row in pending_rows
            ]

            for future in as_completed(futures):
                self.downloaded.append(future.result())


    def main(self) -> None:

        self.process_pending_downloads(nfiles=40)
        self.update_download_by_url(downloads=self.downloaded)


if __name__ == "__main__":
    client = SicroClient()
    client.main()

