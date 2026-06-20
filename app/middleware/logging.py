import logging
import os
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("leetsave")

# Skip routine health/static checks entirely.
SKIP_PATHS = {"/health", "/favicon.ico"}

# Succeed quietly — only log these when something goes wrong.
QUIET_OK_PATHS = {"/api/v1/auth/me", "/api/v1/submissions"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        method = request.method

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error("%s %s ERROR %.0fms", method, path, elapsed_ms, exc_info=True)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        status = response.status_code

        if path in QUIET_OK_PATHS and status < 400:
            return response

        if status >= 500:
            logger.error("%s %s %s %.0fms", method, path, status, elapsed_ms)
        elif status >= 400:
            logger.warning("%s %s %s %.0fms", method, path, status, elapsed_ms)
        else:
            logger.info("%s %s %s %.0fms", method, path, status, elapsed_ms)

        return response


def configure_logging(app_env: str) -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    logging.getLogger("leetsave").setLevel(level)

    for noisy in ("watchfiles", "uvicorn.access", "uvicorn.error", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
