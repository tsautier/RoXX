from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import logging
import os

logger = logging.getLogger("roxx.security.rate_limit")


# Initialize Limiter
# storage_uri will be loaded from env or config. Default to memory for dev, Redis for prod.
# For Phase 5, we want Redis if available.

def get_limiter():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        # Check if Redis is reachable? slowapi does this internally usually
        return Limiter(key_func=get_remote_address, storage_uri=redis_url)
    except Exception as e:
        logger.warning(f"Failed to initialize Redis limiter, falling back to memory: {e}")
        return Limiter(key_func=get_remote_address)

limiter = get_limiter()
