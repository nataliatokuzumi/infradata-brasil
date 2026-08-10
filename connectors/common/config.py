import os

# Shared across connectors: every connector uploads its extracted files to the
# same Azure Blob Storage account, so the connection is configured once here
# instead of being re-read per connector. Source-specific config (base URLs,
# region/state maps, ...) stays in each connector's own settings.py.
azure_storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
azure_storage_container = os.getenv("AZURE_STORAGE_CONTAINER")
