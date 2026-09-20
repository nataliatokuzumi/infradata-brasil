import sys

from connectors.common.db_sync import persist_tracking_db, restore_tracking_db
from connectors.common.logger import get_logger
from layers.database import database_local_path
from sources.sicro.parse import run as run_sicro

logger = get_logger(__name__)

SILVER_SOURCES = [run_sicro]


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    logger.info(f"[silver] starting run for {len(SILVER_SOURCES)} source(s), limit={limit}")
    restore_tracking_db(database_local_path)
    try:
        for run_source in SILVER_SOURCES:
            logger.info(f"[silver] running source: {run_source.__module__}")
            run_source(limit=limit)
    finally:
        persist_tracking_db(database_local_path)
    logger.info("[silver] run complete")
