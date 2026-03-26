"""
HTML Page Routes

Purpose: Serve static HTML templates for the web application. These routes
render Jinja2 templates with context data, providing the user-facing pages
that house the analysis forms, exchange listings, and marketing content.

Each route:
  1. Receives an HTTP GET request
  2. Prepares context data (grouping, content, metadata)
  3. Renders a Jinja2 template with that context
  4. Returns HTML to the browser

This layer bridges the API (which returns JSON) and the frontend (which
renders HTML forms and displays results).
"""

from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from config.markets import EXCHANGES
from config.legal import disclaimer

# Resolve the path to the frontend templates directory.
TPL = Path(__file__).parent.parent / "frontend" / "templates"

# Initialize Jinja2 template engine. This loads .html files from the templates
# directory and can render them with context variables.
templates = Jinja2Templates(directory=str(TPL))

# Create FastAPI router for registering page routes. This will be included
# in app.py without a prefix, making these routes available at the root.
router = APIRouter()


@router.get("/")
async def index(request: Request):
    """
    Serve the home page.
    
    Renders index.html with basic metadata (exchange count) to show
    how many markets are supported.
    
    Args:
        request: FastAPI Request object (required for Jinja2 template context)
    
    Returns:
        TemplateResponse rendering index.html with context
    """
    # Pass the Request object (required by Jinja2) and exchange count for display.
    return templates.TemplateResponse("index.html", {
        "request": request, "exchange_count": len(EXCHANGES)})


@router.get("/analyze")
async def analyze_page(request: Request):
    """
    Serve the analysis form page.
    
    Renders analyze.html which contains the form for users to enter
    stock symbols or natural language queries. The form submits to
    /api/v1/analyze or /api/v1/smart-analyze endpoints.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        TemplateResponse rendering analyze.html
    """
    # Render the form page with minimal context (just the request object).
    return templates.TemplateResponse("analyze.html", {"request": request})


@router.get("/exchanges")
async def exchanges_page(request: Request):
    """
    Serve the supported exchanges listing page.
    
    Fetches all supported exchanges from config, groups them by geographic
    region based on timezone (Americas, Europe & Africa, Asia Pacific), and
    renders exchanges.html with the grouped data.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        TemplateResponse rendering exchanges.html with grouped exchange data
    """
    # Step 1: Initialize a dictionary to collect exchanges by region.
    grouped = {}
    
    # Step 2: Iterate through all configured exchanges and group by region.
    for code, info in EXCHANGES.items():
        # Extract the timezone from the exchange info.
        tz = info["tz"]
        
        # Determine region based on timezone geography.
        if "America" in tz: region = "Americas"
        elif "Europe" in tz or "Africa" in tz: region = "Europe & Africa"
        else: region = "Asia Pacific"
        
        # Add this exchange to the appropriate region group.
        grouped.setdefault(region, []).append({"code": code, **info})
    
    # Step 3: Render the exchanges page with grouped data so users see
    # a nicely organized table of supported markets.
    return templates.TemplateResponse("exchanges.html", {
        "request": request, "grouped": grouped})


@router.get("/about")
async def about(request: Request):
    """
    Serve the about/disclaimer page.
    
    Renders about.html with the legal disclaimer text fetched from config.
    This ensures users understand that QuantScope is for analysis, not advice.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        TemplateResponse rendering about.html with disclaimer content
    """
    # Render the about page with the legal disclaimer text injected.
    return templates.TemplateResponse("about.html", {
        "request": request, "disclaimer": disclaimer()})