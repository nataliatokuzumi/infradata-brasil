import logging
import os

_configured = False


def get_logger(name: str) -> logging.Logger:
    """Module-level logger, configured once on first call. Level comes from
    LOG_LEVEL (default INFO) so it can be raised to DEBUG per-run without a
    code change."""
    global _configured

    if not _configured:
        logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
        _configured = True

    return logging.getLogger(name)
