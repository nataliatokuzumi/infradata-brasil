import hashlib
from pathlib import Path

import requests


def download_to_file(
    url: str,
    destination: Path,
    timeout: int = 120,
    chunk_size: int = 8 * 1024 * 1024,
) -> tuple[Path, str]:
    """Stream a URL to a local file, hashing the bytes as they're written.

    Returns the destination path and the sha256 hex digest of the downloaded
    content, so callers get download + integrity hash in a single pass over
    the response body instead of re-reading the file afterwards.
    """
    sha256 = hashlib.sha256()

    with requests.get(url, timeout=timeout, stream=True) as response:
        response.raise_for_status()

        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    handle.write(chunk)
                    sha256.update(chunk)

    return destination, sha256.hexdigest()
