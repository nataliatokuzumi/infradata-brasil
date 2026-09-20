from connectors.common.db_sync import persist_tracking_db, restore_tracking_db
from connectors.common.logger import get_logger
from layers.database import database_local_path
from sources.sicro.download import run as run_sicro

logger = get_logger(__name__)

RAW_SOURCES = [run_sicro]

if __name__ == "__main__":
    logger.info(f"[raw] starting run for {len(RAW_SOURCES)} source(s)")
    restore_tracking_db(database_local_path)
    try:
        for run_source in RAW_SOURCES:
            logger.info(f"[raw] running source: {run_source.__module__}")
            run_source()
    finally:
        persist_tracking_db(database_local_path)
    logger.info("[raw] run complete")
