from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from azure.storage.blob import BlobServiceClient

from connectors.common.config import azure_storage_connection_string, azure_storage_container


class BlobStorageClient:
    """Thin wrapper around a single Azure Blob Storage container.

    Connectors own the blob naming/partitioning convention for their data
    (e.g. SICRO's region/state/year/month layout); this client only knows how
    to upload bytes to a given blob name.
    """

    def __init__(self, connection_string: str | None = None, container_name: str | None = None):
        self.connection_string = connection_string or azure_storage_connection_string
        self.container_name = container_name or azure_storage_container
        self.service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.container_client = self.service_client.get_container_client(self.container_name)

    def upload_file(self, local_file: Path, blob_name: str) -> str:
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

    def upload_files(
        self,
        uploads: list[tuple[Path, str]],
        max_workers: int = 8,
    ) -> list[str]:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = [
                executor.submit(self.upload_file, local_file, blob_name)
                for local_file, blob_name in uploads
            ]

            return [
                future.result()
                for future in futures
            ]
