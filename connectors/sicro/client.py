from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

from ftfy import fix_text

from connectors.blob_storage.client import BlobStorageClient
from connectors.common.archive import extract_archive
from connectors.common.http import download_to_file
from connectors.sicro.database import SicroDownloadsDatabase
from connectors.sicro.settings import database_path, download_dir, extract_dir


def build_blob_name(
    local_file: Path,
    extract_dir: Path,
    region: str,
    state_code: str,
    year: str,
    month: str,
) -> str:
    relative_path = local_file.relative_to(extract_dir).as_posix()
    relative_path = fix_text(relative_path)

    return (
        f"{region}/"
        f"{state_code}/"
        f"{year}/"
        f"{month}/"
        f"{relative_path}"
    )


class SicroClient(SicroDownloadsDatabase):

    def __init__(self):
        super().__init__(db_path=database_path)

        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir = Path(extract_dir)
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        self.blob_client = BlobStorageClient()

        self.downloaded = []


    def _download_to_local_file(
        self,
        url: str,
        filename: str,
    ):
        destination = self.download_dir / filename

        return download_to_file(url, destination)


    def _extract_archive(self, archive_path: Path, extension: str, filename: str) -> list[Path]:

        extract_dir = self.extract_dir / filename

        return extract_archive(archive_path, extension, extract_dir)


    def _upload_one_file(
        self,
        local_file: Path,
        region: str,
        state_code: str,
        year: str,
        month: str,
    ) -> str:

        blob_name = build_blob_name(
            local_file, self.extract_dir, region, state_code, year, month
        )

        return self.blob_client.upload_file(local_file, blob_name)


    def _upload_local_files_to_blob(
        self,
        local_files,
        region,
        state_code,
        year,
        month,
        max_workers=8,
    ):

        uploads = [
            (
                local_file,
                build_blob_name(local_file, self.extract_dir, region, state_code, year, month),
            )
            for local_file in local_files
        ]

        return self.blob_client.upload_files(uploads, max_workers=max_workers)


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
