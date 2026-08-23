import sys

from connectors.common.db_sync import persist_tracking_db, restore_tracking_db
from connectors.sicro.parse.client import SicroParseClient
from connectors.sicro.settings import database_local_path

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    restore_tracking_db(database_local_path)
    try:
        client = SicroParseClient()
        client.main(limit=limit)
    finally:
        persist_tracking_db(database_local_path)
