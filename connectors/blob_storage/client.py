from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from azure.storage.blob import BlobServiceClient

from connectors.common.config import azure_storage_connection_string, azure_storage_container
from connectors.common.logger import get_logger

logger = get_logger(__name__)


class BlobStorageClient:
    """
    Thin wrapper around a single Azure Blob Storage container.
    """

    def __init__(self, connection_string: str | None = None, container_name: str | None = None):
        self.connection_string = connection_string or azure_storage_connection_string
        self.container_name = container_name or azure_storage_container
        self.service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.container_client = self.service_client.get_container_client(self.container_name)
        logger.debug(f"[blob] connected to container: {self.container_name}")

    def upload_file(self, local_file: Path, blob_name: str) -> str:
        logger.info(f"[blob] uploading: {local_file} -> {blob_name}")

        with local_file.open("rb") as handle:
            self.container_client.upload_blob(
                name=blob_name,
                data=handle,
                overwrite=True,
            )

        return blob_name

    def upload_files(
        self,
        uploads: list[tuple[Path, str]],
        max_workers: int = 8,
    ) -> list[str]:
        logger.info(f"[blob] uploading {len(uploads)} file(s), max_workers={max_workers}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = [
                executor.submit(self.upload_file, local_file, blob_name)
                for local_file, blob_name in uploads
            ]

            return [
                future.result()
                for future in futures
            ]

    def list_blobs(self, name_starts_with: str | None = None) -> list[str]:
        names = [
            blob.name
            for blob in self.container_client.list_blobs(name_starts_with=name_starts_with)
        ]
        logger.debug(f"[blob] listed {len(names)} blob(s), name_starts_with={name_starts_with!r}")
        return names

    def blob_exists(self, blob_name: str) -> bool:
        return self.container_client.get_blob_client(blob_name).exists()

    def download_blob_bytes(self, blob_name: str) -> bytes:
        logger.debug(f"[blob] downloading bytes: {blob_name}")
        return self.container_client.download_blob(blob_name).readall()

    def download_blob_to_file(self, blob_name: str, destination: Path) -> Path:
        logger.info(f"[blob] downloading: {blob_name} -> {destination}")

        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("wb") as handle:
            self.container_client.download_blob(blob_name).readinto(handle)

        return destination
