
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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

def rate_limit_custom_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom error handler for rate limits
    """
    # Verify if it's an API request or HTML request to return appropriate response
    if request.url.path.startswith("/api") or request.url.path.startswith("/auth"):
        return JSONResponse(
            {"success": False, "detail": f"Rate limit exceeded: {exc.detail}"}, 
            status_code=429
        )
    else:
        # For HTML pages, maybe a template? For now simple text
        return HTMLResponse(
            content=f"<h1>429 Too Many Requests</h1><p>Please try again later.</p>", 
            status_code=429
        )
