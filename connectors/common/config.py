import os

from connectors.common.logger import get_logger

logger = get_logger(__name__)

azure_storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
azure_storage_container = os.getenv("AZURE_STORAGE_CONTAINER")

if not azure_storage_connection_string:
    logger.warning("AZURE_STORAGE_CONNECTION_STRING is not set")
if not azure_storage_container:
    logger.warning("AZURE_STORAGE_CONTAINER is not set")
