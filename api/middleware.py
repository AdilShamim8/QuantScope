"""
API middleware utilities.

This module provides cross-cutting request behavior:
    1. Request logging (method/path/client)
    2. Latency measurement and response timing header
    3. Success/failure counters for monitoring
    4. Rate-limiter instance used by API routes
"""

import logging
import time
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from monitor import metrics

logger = logging.getLogger(__name__)

# Rate limiter identifies clients by remote IP address.
limiter = Limiter(key_func=get_remote_address)


async def log_requests(request: Request, call_next):
    """
    Middleware hook that logs each request and records latency metrics.

    Adds `X-Time-Ms` response header on successful requests.
    """

    # STEP 1: Capture request start time and basic request identity.
    t0 = time.time()
    ip = request.client.host if request.client else "?"
    logger.info("-> %s %s from %s", request.method, request.url.path, ip)
    metrics.count("requests_total")

    try:
        # STEP 2: Execute downstream route handler / middleware chain.
        resp = await call_next(request)

        # STEP 3: Record latency metrics and append timing header.
        dt = time.time() - t0
        metrics.time("request_latency", dt)
        logger.info("<- %s %s %d (%.0fms)", request.method, request.url.path,
                     resp.status_code, dt * 1000)
        resp.headers["X-Time-Ms"] = str(round(dt * 1000))
        return resp
    except Exception as e:
        # STEP 4: Record failure metric, log error, and re-raise.
        metrics.count("requests_failed")
        logger.error("!! %s %s error: %s", request.method, request.url.path, e)
        raise