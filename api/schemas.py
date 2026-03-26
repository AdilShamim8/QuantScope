"""
Pydantic Request and Response Schemas

Purpose: Define the API contract using Pydantic models for automatic
validation, serialization, and OpenAPI documentation. Schemas ensure that
requests have required fields and valid types before reaching route handlers,
and define the exact structure of JSON responses returned to clients.

Structure:
  Request Models: Specify what clients must send
    - AnalyzeReq: Direct symbol list with portfolio value
    - SmartReq: Natural language query with portfolio value
  
  Response Models: Specify what clients receive
    - StockOut: Single stock analysis result (symbol, price, metrics, explanation)
    - ParseOut: Query parsing breakdown (symbols found, intent, fragments)
    - AnalyzeResp: Complete analysis response (status, results, portfolio summary)
    - HealthResp: API health check (version, LLM provider, metrics)
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# REQUEST MODELS
# ============================================================================

class AnalyzeReq(BaseModel):
    """
    Request model for direct symbol analysis endpoint (/api/v1/analyze).
    
    Fields:
        symbols: List of stock ticker symbols (1-200 symbols per request)
        portfolio_value: Total portfolio size in USD (default $10,000, max $1 trillion)
    
    Used by: POST /api/v1/analyze
    """
    # List of stock symbols to analyze (e.g., ["AAPL", "MSFT", "TSLA"]).
    # Must have at least 1 symbol and at most 200 (to prevent server overload).
    symbols: List[str] = Field(..., min_length=1, max_length=200)
    
    # Total portfolio value in USD for position sizing calculations and risk metrics.
    # Default is $10,000 if not provided. Max is $1 trillion (prevents nonsense inputs).
    portfolio_value: float = Field(default=10000.0, gt=0, le=1e12)


class SmartReq(BaseModel):
    """
    Request model for natural language query endpoint (/api/v1/smart-analyze).
    
    Fields:
        query: Free-form natural language question or symbol list (1-500 chars)
        portfolio_value: Total portfolio size in USD (default $10,000, max $1 trillion)
    
    Used by: POST /api/v1/smart-analyze
    """
    # Natural language query (e.g., "Compare tech stocks" or "How is Apple doing?").
    # The query_parser will extract symbols and detect intent from this text.
    # Limited to 500 characters to prevent abuse.
    query: str = Field(..., min_length=1, max_length=500)
    
    # Total portfolio value in USD. Same constraints as AnalyzeReq.
    portfolio_value: float = Field(default=10000.0, gt=0, le=1e12)


# RESPONSE MODELS
# ============================================================================

class StockOut(BaseModel):
    """
    Single stock analysis result within an AnalyzeResp.
    
    Represents all calculated metrics for one stock symbol: price, technical indicators,
    risk metrics, position sizing, and LLM-generated explanation.
    
    All fields are Optional because analysis may fail for individual symbols
    (e.g., invalid ticker, insufficient data) but the overall response continues.
    """
    # Stock ticker symbol (e.g., "AAPL")
    symbol: Optional[str] = None
    
    # Industry sector classification (e.g., "Technology", "Healthcare")
    sector: Optional[str] = None
    
    # Current market price
    price: Optional[float] = None
    
    # Currency code (e.g., "USD", "EUR")
    currency: Optional[str] = None
    
    # Composite technical score from 0-4 (0=very bearish, 4=very bullish)
    composite_score: Optional[int] = None
    
    # Relative Strength Index (RSI): 0-100 (below 30=oversold, above 70=overbought)
    rsi: Optional[float] = None
    
    # Technical signals dict (e.g., {"RSI": "overbought", "MACD": "bullish", "Trend": "up"})
    signals: Optional[Dict[str, str]] = None
    
    # Returns over different time periods (e.g., {"1d": 1.5, "1w": -0.3, "1m": 2.1, "ytd": 5.0})
    returns: Optional[Dict[str, Optional[float]]] = None
    
    # Annualized volatility percentage (historical price fluctuation)
    volatility_annual_pct: Optional[float] = None
    
    # Sharpe ratio: risk-adjusted return (higher = better returns per unit of risk)
    sharpe_ratio: Optional[float] = None
    
    # Maximum drawdown percentage: largest peak-to-trough decline historically
    max_drawdown_pct: Optional[float] = None
    
    # Risk metrics dict (e.g., {"position_size_pct": 5.0, "stop_loss": 145.50, "risk_dollars": 500})
    risk: Optional[Dict] = None
    
    # LLM-generated explanation of the analysis in plain English
    explanation: Optional[str] = None


class ParseOut(BaseModel):
    """
    Query parsing breakdown returned in AnalyzeResp.query_info.
    
    Shows what the query_parser extracted from the natural language input:
    which symbols were found, what intent was detected, and what couldn't be parsed.
    """
    # List of stock symbols extracted from the query (e.g., ["AAPL", "MSFT"])
    symbols: List[str]
    
    # Detected intent: "compare", "investment_question", or "analyze"
    intent: str
    
    # Original user query text (unchanged)
    original_query: str
    
    # Company data found by name matching (e.g., [{"name": "Apple", "symbol": "AAPL", "sector": "Tech"}])
    parsed_companies: List[Dict]
    
    # Text fragments from the query that couldn't be matched to any symbol or company
    unparsed_fragments: List[str]
    
    # Boolean: True if query contains natural language (not just symbol list)
    is_natural_language: bool


class AnalyzeResp(BaseModel):
    """
    Complete analysis response from both /api/v1/analyze and /api/v1/smart-analyze.
    
    Contains metadata about the request (status, timestamp, LLM provider), analysis
    results for each stock, and a portfolio-level summary generated by the LLM.
    """
    # Status of the analysis: "success" or "degraded" (partial data due to API limits)
    status: str
    
    # ISO timestamp when analysis completed
    timestamp: str
    
    # Query parsing details (only populated for smart-analyze requests)
    query_info: Optional[ParseOut] = None
    
    # Count of successfully analyzed stocks
    stocks_analyzed: int
    
    # Count of stocks that failed analysis (invalid ticker, no data, etc.)
    stocks_skipped: int
    
    # Portfolio value used for position sizing calculations
    portfolio_value: float
    
    # LLM provider used for explanations (e.g., "openai", "anthropic", "google")
    llm_provider: str
    
    # Legal disclaimer text
    disclaimer: str
    
    # List of StockOut results (one per analyzed symbol)
    results: List[StockOut]
    
    # LLM-generated portfolio summary (grouping stocks by outlook: bullish/neutral/bearish)
    portfolio_summary: str
    
    # List of validation issues encountered (e.g., ["Invalid symbol: XYZ", "Rate limited on AAPL"])
    validation_issues: List[str] = []


class HealthResp(BaseModel):
    """
    Health check response from GET /api/v1/health.
    
    Indicates API readiness, LLM provider availability, and environment status.
    """
    # Status: "healthy" (all services OK), "degraded" (LLM unavailable), or "error"
    status: str
    
    # API version string
    version: str
    
    # Active LLM provider (e.g., "openai", "anthropic", "ollama")
    llm_provider: str
    
    # Number of supported stock exchanges
    exchanges: int
    
    # Optional metrics dict (request count, uptime, latency percentiles)
    metrics: Optional[Dict] = None