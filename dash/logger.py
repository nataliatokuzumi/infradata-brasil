import logging
import os

_configured = False


def get_logger(name: str) -> logging.Logger:
    """Same pattern as connectors/common/logger.py — duplicated instead of
    imported because dash/ is a separately deployed app (its own Dockerfile,
    own requirements.txt, build context is dash/ alone, so connectors/ isn't
    even present in the built image)."""
    global _configured

    if not _configured:
        logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
        _configured = True

    return logging.getLogger(name)
