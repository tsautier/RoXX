"""Same-origin checks for cookie-authenticated browser requests."""

from __future__ import annotations

import os
from urllib.parse import urlsplit


def _origin(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or host is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return None
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def is_trusted_origin(origin: str | None, request_url) -> bool:
    """Match a browser Origin against this endpoint or configured proxy origins."""
    if not origin:
        return False
    candidate = _origin(origin)
    if candidate is None:
        return False
    scheme = "https" if request_url.scheme in {"https", "wss"} else "http"
    configured = os.getenv("ROXX_ALLOWED_ORIGINS", "").strip()
    allowed = (
        {
            value for entry in configured.split(",")
            if (value := _origin(entry.strip())) is not None
        }
        if configured else {f"{scheme}://{request_url.netloc}".lower()}
    )
    return candidate in allowed


def is_trusted_referer(referer: str | None, request_url) -> bool:
    """Use Referer only when Origin is absent; paths are ignored after parsing."""
    if not referer:
        return False
    try:
        parsed = urlsplit(referer)
    except ValueError:
        return False
    if not parsed.scheme or not parsed.netloc or parsed.username or parsed.password:
        return False
    return is_trusted_origin(f"{parsed.scheme}://{parsed.netloc}", request_url)
