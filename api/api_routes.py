"""
API Routes for QuantScope.

This module exposes endpoints used by the frontend and CLI/web clients.
Main responsibilities:
    1. Health and metadata endpoints
    2. Query parsing endpoint
    3. Analysis endpoints (smart query-based and direct symbol-based)
    4. Standardized success/degraded/error responses
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from api.schemas import (
    AnalyzeReq, SmartReq, AnalyzeResp, StockOut,
    ParseOut, HealthResp,
)
from config.markets import EXCHANGES
from config.legal import disclaimer
from core.data_fetcher import FetchError
from core.validator import ValidationError, clean_symbols
from core.query_parser import parse as parse_query
from pipeline import Pipeline
from llm.engine import LLMEngine
from monitor import metrics

logger = logging.getLogger(__name__)
router = APIRouter()

_llm_name = None


def _llm():
    """Resolve active LLM provider once and cache the provider name for reuse."""
    global _llm_name
    if _llm_name is None:
        try:
            _llm_name = LLMEngine().provider
        except Exception:
            # Keep API healthy even when LLM provider is unavailable.
            _llm_name = "none"
    return _llm_name


def _build_results(analyses):
    """Convert internal pipeline dict results into API response schema objects."""
    out = []
    for a in analyses:
        out.append(StockOut(
            symbol=a.get("symbol"), sector=a.get("sector"),
            price=a.get("price"), currency=a.get("currency"),
            composite_score=a.get("composite_score"),
            rsi=a.get("rsi"), signals=a.get("signals"),
            returns=a.get("returns"),
            volatility_annual_pct=a.get("volatility_annual_pct"),
            sharpe_ratio=a.get("sharpe_ratio"),
            max_drawdown_pct=a.get("max_drawdown_pct"),
            risk=a.get("risk"), explanation=a.get("explanation"),
        ))
    return out


@router.get("/health", response_model=HealthResp)
async def health():
    """Lightweight system status endpoint for uptime checks and diagnostics."""
    return HealthResp(
        status="ok", version="1.0.0", llm_provider=_llm(),
        exchanges=len(EXCHANGES), metrics=metrics.snapshot(),
    )


@router.get("/exchanges")
async def exchanges():
    """Return supported exchanges and ticker suffix metadata used by the parser/UI."""
    return {"exchanges": {
        k: {"name": v["name"], "suffix": v["suffix"],
             "currency": v["currency"], "tz": v["tz"]}
        for k, v in EXCHANGES.items()
    }}


@router.post("/parse")
async def parse_input(req: SmartReq):
    """Parse a natural-language query into structured symbols and intent fields."""
    return parse_query(req.query).to_dict()


@router.post("/smart-analyze", response_model=AnalyzeResp)
async def smart_analyze(req: SmartReq):
    """
    Analyze stocks from natural-language input.

    Flow:
      1. Parse text query into symbols
      2. Validate/clean symbols
      3. Run pipeline
      4. Return standard response (ok or degraded)
    """
    # STEP 1: Parse natural language into machine-readable query data.
    parsed = parse_query(req.query)
    if not parsed.symbols:
        raise HTTPException(400,
            "Could not find stock symbols. Try ticker symbols "
            "like AAPL or company names like Apple.")

    # STEP 2: Validate and normalize extracted symbols.
    try:
        ok, bad = clean_symbols(parsed.symbols)
    except ValidationError as e:
        raise HTTPException(400, str(e))

    # STEP 3: Run analysis pipeline for valid symbols.
    try:
        pipe = Pipeline(ok, req.portfolio_value, parsed.query)
        results = pipe.run()
    except FetchError as e:
        # Return degraded response when market data providers are unavailable.
        logger.warning("Market data unavailable: %s", e)
        return AnalyzeResp(
            status="degraded", timestamp=datetime.now().isoformat(),
            query_info=ParseOut(**parsed.to_dict()),
            stocks_analyzed=0,
            stocks_skipped=len(ok) + len(bad),
            portfolio_value=req.portfolio_value,
            llm_provider=_llm(), disclaimer=disclaimer(False),
            results=[],
            portfolio_summary=(
                "Market data unavailable right now. "
                "Check internet/proxy settings and retry."
            ),
            validation_issues=bad + [str(e)],
        )
    except Exception as e:
        # Unexpected pipeline errors map to HTTP 500 with safe message length.
        logger.error("Pipeline: %s", e, exc_info=True)
        raise HTTPException(500, "Analysis failed: " + str(e)[:200])

    # STEP 4: Record metric and return successful API payload.
    metrics.count("analyses_completed")
    return AnalyzeResp(
        status="ok", timestamp=datetime.now().isoformat(),
        query_info=ParseOut(**parsed.to_dict()),
        stocks_analyzed=len(results),
        stocks_skipped=len(ok) - len(results) + len(bad),
        portfolio_value=req.portfolio_value,
        llm_provider=_llm(), disclaimer=disclaimer(False),
        results=_build_results(results),
        portfolio_summary=pipe.portfolio_summary,
        validation_issues=bad,
    )


@router.post("/analyze", response_model=AnalyzeResp)
async def analyze(req: AnalyzeReq):
    """
    Analyze stocks from explicit symbol list.

    This endpoint skips natural-language parsing and directly validates symbols,
    then runs the same core pipeline used by smart-analyze.
    """
    # STEP 1: Validate and normalize user-provided symbols.
    try:
        ok, bad = clean_symbols(req.symbols)
    except ValidationError as e:
        raise HTTPException(400, str(e))

    # STEP 2: Run analysis pipeline and handle degraded provider conditions.
    try:
        pipe = Pipeline(ok, req.portfolio_value)
        results = pipe.run()
    except FetchError as e:
        # Degraded mode keeps API responsive when market data cannot be fetched.
        logger.warning("Market data unavailable: %s", e)
        return AnalyzeResp(
            status="degraded", timestamp=datetime.now().isoformat(),
            stocks_analyzed=0,
            stocks_skipped=len(ok) + len(bad),
            portfolio_value=req.portfolio_value,
            llm_provider=_llm(), disclaimer=disclaimer(False),
            results=[],
            portfolio_summary=(
                "Market data unavailable right now. "
                "Check internet/proxy settings and retry."
            ),
            validation_issues=bad + [str(e)],
        )
    except Exception as e:
        # Unexpected pipeline errors map to HTTP 500 with safe message length.
        logger.error("Pipeline: %s", e, exc_info=True)
        raise HTTPException(500, "Analysis failed: " + str(e)[:200])

    # STEP 3: Record metric and return successful API payload.
    metrics.count("analyses_completed")
    return AnalyzeResp(
        status="ok", timestamp=datetime.now().isoformat(),
        stocks_analyzed=len(results),
        stocks_skipped=len(ok) - len(results) + len(bad),
        portfolio_value=req.portfolio_value,
        llm_provider=_llm(), disclaimer=disclaimer(False),
        results=_build_results(results),
        portfolio_summary=pipe.portfolio_summary,
        validation_issues=bad,
    )