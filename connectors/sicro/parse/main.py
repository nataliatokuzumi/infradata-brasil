from connectors.common.db_sync import persist_tracking_db, restore_tracking_db
from connectors.sicro.parse.client import SicroParseClient
from connectors.sicro.settings import database_local_path

if __name__ == "__main__":
    restore_tracking_db(database_local_path)
    try:
        client = SicroParseClient()
        client.main()
    finally:
        persist_tracking_db(database_local_path)
