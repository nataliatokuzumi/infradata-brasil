import argparse
from pathlib import Path

from connectors.blob_storage.client import BlobStorageClient

# "_state/" is a reserved top-level prefix that doesn't collide with the
# region-name top-level prefixes (sudeste/norte/...) already used for raw
# report files.
TRACKING_DB_BLOB_NAME = "_state/downloads.db"


def restore_tracking_db(local_path: Path, blob_client: BlobStorageClient | None = None) -> None:
    """Downloads the tracking db from Blob Storage to local_path. No-op if
    it doesn't exist yet in blob storage (first run)."""

    blob_client = blob_client or BlobStorageClient()

    if not blob_client.blob_exists(TRACKING_DB_BLOB_NAME):
        print(f"[db_sync] no {TRACKING_DB_BLOB_NAME} in blob storage yet, starting fresh")
        return

    blob_client.download_blob_to_file(TRACKING_DB_BLOB_NAME, local_path)


def persist_tracking_db(local_path: Path, blob_client: BlobStorageClient | None = None) -> None:
    """Uploads the local tracking db to Blob Storage, overwriting the
    previous snapshot."""

    blob_client = blob_client or BlobStorageClient()

    blob_client.upload_file(local_path, TRACKING_DB_BLOB_NAME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Round-trip the SICRO tracking db through Blob Storage (for ephemeral CI runners)."
    )
    parser.add_argument("action", choices=["restore", "persist"])
    parser.add_argument("--db", default="connectors/sicro/downloads.db")
    args = parser.parse_args()

    local_path = Path(args.db)

    if args.action == "restore":
        restore_tracking_db(local_path)
    else:
        persist_tracking_db(local_path)
