# SQL used by the classes in layers/database.py

# --- sicro_downloads (SicroTrackingDatabase, raw-layer methods) ---

CREATE_SICRO_DOWNLOADS_TABLE = """
    CREATE TABLE IF NOT EXISTS sicro_downloads (
        id INTEGER PRIMARY KEY,
        region TEXT NULL,
        state_code TEXT NULL,
        year TEXT NULL,
        month TEXT NULL,
        revisado BOOLEAN NULL,
        url TEXT NOT NULL UNIQUE,
        filename TEXT NULL,
        extension TEXT NULL,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        downloaded_at TIMESTAMP NULL,
        status TEXT NULL,
        file_hash TEXT NULL
    );
    """

INSERT_DOWNLOAD = """
    INSERT OR IGNORE INTO sicro_downloads (
        region, state_code, year, month, revisado, url, filename, extension, scraped_at, downloaded_at, status, file_hash
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

URL_EXISTS = """
    SELECT 1 FROM sicro_downloads WHERE url = ? LIMIT 1;
    """

# {placeholders}/{limit_clause} are filled in by get_pending_downloads() —
# the number of statuses and whether a limit applies both vary per call.
GET_PENDING_DOWNLOADS = """
    SELECT id, region, state_code, year, month, url, filename, extension
    FROM sicro_downloads
    WHERE status IN ({placeholders})
    ORDER BY scraped_at ASC, id ASC
    {limit_clause};
    """

UPDATE_DOWNLOAD_BY_URL = """
    UPDATE sicro_downloads
    SET status = ?, file_hash = ?, downloaded_at = COALESCE(?, downloaded_at)
    WHERE url = ?;
    """

UPDATE_DOWNLOAD = """
    UPDATE sicro_downloads
    SET status = ?, file_hash = ?, downloaded_at = COALESCE(?, downloaded_at)
    WHERE state_code = ? AND year = ? AND month = ? AND revisado = ?;
    """

GET_DOWNLOAD = """
    SELECT status, filename, file_hash, downloaded_at
    FROM sicro_downloads
    WHERE state_code = ? AND year = ? AND month = ? AND revisado = ?
    ORDER BY downloaded_at DESC, id DESC
    LIMIT 1;
    """

# --- sicro_parsed_files (SicroTrackingDatabase, silver-layer methods) ---

CREATE_SICRO_PARSED_FILES_TABLE = """
    CREATE TABLE IF NOT EXISTS sicro_parsed_files (
        id INTEGER PRIMARY KEY,
        blob_name TEXT NOT NULL UNIQUE,
        report_type TEXT NULL,
        region TEXT NULL,
        state_slug TEXT NULL,
        year TEXT NULL,
        month TEXT NULL,
        desonerado BOOLEAN NULL,
        revisado BOOLEAN NULL,
        archive_stem TEXT NULL,
        silver_blob_name TEXT NULL,
        row_count INTEGER NULL,
        status TEXT NULL,
        error TEXT NULL,
        parsed_at TIMESTAMP NULL
    );
    """

IS_PARSED = """
    SELECT 1 FROM sicro_parsed_files WHERE blob_name = ? AND status = 'parsed' LIMIT 1;
    """

UPSERT_PARSED_FILE = """
    INSERT INTO sicro_parsed_files (
        blob_name, report_type, region, state_slug, year, month,
        desonerado, revisado, archive_stem, silver_blob_name,
        row_count, status, error, parsed_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(blob_name) DO UPDATE SET
        report_type = excluded.report_type,
        region = excluded.region,
        state_slug = excluded.state_slug,
        year = excluded.year,
        month = excluded.month,
        desonerado = excluded.desonerado,
        revisado = excluded.revisado,
        archive_stem = excluded.archive_stem,
        silver_blob_name = excluded.silver_blob_name,
        row_count = excluded.row_count,
        status = excluded.status,
        error = excluded.error,
        parsed_at = excluded.parsed_at;
    """

GET_FAILED = """
    SELECT blob_name, error FROM sicro_parsed_files WHERE status = 'failed';
    """
