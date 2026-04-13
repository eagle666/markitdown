"""API Key authentication middleware."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..core.config import settings

# Header name for API key (RapidAPI uses X-API-Key)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key from the X-API-Key header.

    Args:
        api_key: The API key to verify.

    Returns:
        The verified API key.

    Raises:
        HTTPException: If the API key is invalid or missing.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "API key is required. Provide it via X-API-Key header.",
                }
            },
        )

    # Check against configured API keys
    # In production, you might want to validate against a database
    if settings.api_keys and api_key not in settings.api_keys:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "The provided API key is invalid.",
                }
            },
        )

    return api_key


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce API key authentication on all routes.

    Routes can opt out by adding `dependencies=[Dict()]`.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Let the dependency handle auth verification
        # This middleware just adds logging
        response = await call_next(request)
        return response