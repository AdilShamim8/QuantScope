"""
FastAPI Application Bootstrap

Purpose: Initialize and configure the FastAPI application instance, including
route registration, middleware setup, CORS configuration, static file serving,
exception handling, and startup/shutdown hooks.

Flow:
  1. Create FastAPI app with metadata (title, version, docs URL)
  2. Mount frontend static files (JS, CSS)
  3. Register CORS middleware (allow all origins for open API)
  4. Attach rate limiter to app state
  5. Add exception handler for rate limit exceeded responses
  6. Register request logging/latency middleware
  7. Include API routes at /api/v1 prefix
  8. Include HTML page routes at root
  9. Attach startup hook to initialize settings and logging

Result: A fully configured FastAPI app ready to accept HTTP requests.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.api_routes import router as api_router
from api.page_routes import router as page_router
from api.middleware import limiter, log_requests
from config import settings

# Resolve the path to the frontend/static directory containing CSS, JS, and other assets.
STATIC = Path(__file__).parent.parent / "frontend" / "static"


def create():
    """
    Factory function to create and configure the FastAPI application.
    
    Returns a fully configured FastAPI app with all routes, middleware, exception
    handlers, and startup hooks registered. This factory pattern allows clean
    app instantiation and makes testing easier.
    
    Returns:
        FastAPI: Configured application instance ready to accept requests.
    """
    # Step 1: Instantiate FastAPI with metadata for auto-generated documentation.
    # title, version, and docs_url make the /api/docs and /api/redoc endpoints available.
    app = FastAPI(
        title="QuantScope",
        description="Global Stock Analysis",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # Step 2: Mount the frontend static directory so browsers can load CSS and JS files.
    # Requests to /static/* are served directly from the filesystem.
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
    
    # Step 3: Add CORS middleware to allow cross-origin requests from any origin.
    # This enables the frontend (if hosted separately) to call the API without
    # browser security restrictions. In production, restrict allow_origins to specific domains.
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=True, allow_methods=["*"],
                       allow_headers=["*"])
    
    # Step 4: Attach the rate limiter instance to app.state so middleware can access it.
    # This enables per-IP request throttling defined in middleware.py.
    app.state.limiter = limiter
    
    # Step 5: Register an exception handler that returns a 429 Too Many Requests response
    # when a client exceeds their rate limit. This is caught and formatted nicely by slowapi.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Step 6: Register the HTTP middleware that logs all requests/responses and measures latency.
    # This adds the X-Time-Ms header to responses so clients can see processing time.
    app.middleware("http")(log_requests)
    
    # Step 7: Include the API router at /api/v1 prefix. This registers all endpoints like
    # /api/v1/health, /api/v1/analyze, /api/v1/smart-analyze, etc.
    app.include_router(api_router, prefix="/api/v1")
    
    # Step 8: Include the page router for HTML templates. This registers routes like
    # / (home), /analyze, /exchanges, /about, etc. that serve HTML to browsers.
    app.include_router(page_router)

    # Step 9: Attach an event handler that runs when the server starts up.
    # This initializes logging and validates all configuration settings.
    @app.on_event("startup")
    async def startup():
        settings.setup_logging()
        settings.validate()

    return app


# Create the global app instance used by uvicorn or the test client.
