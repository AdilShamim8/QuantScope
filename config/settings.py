"""
Application Settings & Configuration

Purpose: Centralize all hardcoded configuration values, environment-based settings,
and initialization logic. This module loads environment variables via .env, defines
technical indicator parameters, risk thresholds, API settings, and LLM configuration.

Responsibilities:
  1. Load .env file for secrets and environment-specific values
  2. Define project paths (root directory, output, logs)
  3. Define technical analysis indicator parameters
  4. Define risk management thresholds
  5. Define data fetching constraints
  6. Define LLM provider selection and model mappings
  7. Define API server settings
  8. Validate all critical settings at startup
  9. Initialize logging with file and console handlers

Why centralize? Makes configuration changes testable, traceable, and prevents magic
numbers scattered throughout the codebase. All constants in one place = one source of truth.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if present).
# This allows local development to override settings via .env without code changes.
load_dotenv()

# PROJECT STRUCTURE
# Initialize paths relative to this file's location. PROJECT_ROOT is the quantscope/ directory.
PROJECT_ROOT = Path(__file__).parent.parent
# Output directory for CSV exports, JSON reports, and logs.
OUTPUT_DIR = PROJECT_ROOT / "output"
# Logs directory for application log files.
LOG_DIR = OUTPUT_DIR / "logs"


# TECHNICAL ANALYSIS PARAMETERS
# Standard indicator periods used in technical analysis. These values are industry standard
# and have been validated through backtesting by the financial community. Do not change
# without extensive backtesting.
# 
# RSI (Relative Strength Index): Momentum oscillator measuring speed and magnitude of price changes.
RSI_PERIOD = 14              # Number of candles/periods for RSI calculation
RSI_OVERSOLD = 30            # RSI below this = oversold signal (potential bounce)
RSI_OVERBOUGHT = 70          # RSI above this = overbought signal (potential pullback)

# SMA (Simple Moving Average): Average price over N periods. Used for trend identification.
SMA_SHORT = 50               # Short-term trend (50-day SMA)
SMA_LONG = 200               # Long-term trend (200-day SMA, golden cross)

# MACD (Moving Average Convergence Divergence): Trend-following momentum indicator.
MACD_FAST = 12               # Fast EMA period
MACD_SLOW = 26               # Slow EMA period
MACD_SIGNAL = 9              # Signal line EMA period

# Bollinger Bands: Volatility bands around a moving average.
BOLLINGER_PERIOD = 20        # Period for middle band (20-day SMA)
BOLLINGER_STD = 2.0          # Number of standard deviations for upper/lower bands

# ATR (Average True Range): Volatility measurement (used for position sizing and stops).
ATR_PERIOD = 14              # Number of periods for ATR calculation
VOLUME_AVG_PERIOD = 20       # Volume averaging period


# RISK MANAGEMENT PARAMETERS
# Position sizing, leverage limits, and stop-loss rules to protect portfolio.
MAX_POSITION_PCT = 0.10      # Max position size = 10% of portfolio (no single stock > 10%)
MAX_SECTOR_PCT = 0.30        # Max sector exposure = 30% of portfolio (no sector > 30%)
STOP_LOSS_ATR_MULT = 2.0     # Stop loss = current price - (ATR × 2.0) = 2 ATRs below price
RISK_PER_TRADE_PCT = 0.02    # Risk per trade = 2% of portfolio (conservative)
RISK_FREE_RATE = 0.05        # Assumed risk-free return for Sharpe ratio (5% = typical T-bills)


# DATA FETCHING PARAMETERS
# Controls how much historical data to fetch, how long to cache, and data quality thresholds.
PRICE_PERIOD = "1y"          # Fetch 1 year of historical data
PRICE_INTERVAL = "1d"        # Fetch daily OHLCV candles (not hourly or minute)
CACHE_MINUTES = 15           # Cache data for 15 minutes before re-fetching
MIN_DAYS = 200               # Minimum days of data required for valid analysis
MAX_NAN = 0.20               # Max allowed missing data = 20% of rows
EXTREME_MOVE = 0.50          # Flag moves > 50% as potential data errors
STALE_DAYS = 5               # Consider data stale if older than 5 days


# LLM (LANGUAGE MODEL) CONFIGURATION
# Provider selection, fallback order, model selection, and generation parameters.
LLM_TEMP = 0.3               # Temperature for LLM output (0=deterministic, 1=creative; 0.3=balanced)
LLM_TOKENS = 800             # Max tokens in LLM response (keep narratives concise)
LLM_TIMEOUT = 30             # Timeout for LLM calls in seconds
# Provider fallback order: try OpenAI first, then Anthropic, then Google, then local Ollama, etc.
# This allows graceful degradation if a provider is unavailable.
LLM_ORDER = ["openai", "anthropic", "google", "ollama", "mistral", "cohere"]
# Model selection per provider (must match provider's available models).
LLM_MODELS = {
    "openai": "gpt-4o-mini",                      # Fast, cheap GPT-4 variant
    "anthropic": "claude-3-haiku-20240307",       # Claude 3 Haiku (fast, cost-effective)
    "google": "gemini-pro",                       # Google Gemini Pro
    "ollama": "llama3",                           # Local Llama 3 model via Ollama
    "mistral": "mistral-small-latest",            # Mistral Small
    "cohere": "command-r",                        # Cohere Command R
}


# API SERVER CONFIGURATION
# FastAPI server settings and endpoint constraints.
API_HOST = "0.0.0.0"         # Listen on all network interfaces (Docker-friendly)
API_PORT = 8000              # Standard port for development (override with PORT env var)
MAX_SYMBOLS = 200            # Maximum symbols per analyze request (prevent abuse)
SYMBOL_MAX_LEN = 15          # Max length of a single symbol string (sanity check)
QUERY_MAX_LEN = 500          # Max length of natural language query (prevent spam)


# LOGGING CONFIGURATION
# Set log level from environment variable (default to INFO if not set).
# Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


def validate():
    """
    Validate critical configuration values at startup.
    
    Checks that risk parameters are within acceptable ranges and enforces
    minimum data requirements. Called from main.py during initialization.
    If validation fails, logs errors and exits with code 1 (failure).
    
    Validated constraints:
      - RISK_PER_TRADE_PCT: Must be between 0.01% and 10% (sanity check on risk)
      - MAX_POSITION_PCT: Must be between 0% and 50% (reasonable position limit)
      - MIN_DAYS: Must be at least 200 days (require sufficient historical data)
    """
    # Collect all validation errors.
    errors = []
    
    # Check: Risk per trade should be positive and not exceed 10% (too much risk).
    if not (0 < RISK_PER_TRADE_PCT <= 0.10):
        errors.append("RISK_PER_TRADE_PCT invalid")
    
    # Check: Max position should be positive and not exceed 50% (don't allow >50% in one stock).
    if not (0 < MAX_POSITION_PCT <= 0.50):
        errors.append("MAX_POSITION_PCT invalid")
    
    # Check: Minimum days must be at least 200 for statistically valid analysis.
    if MIN_DAYS < 200:
        errors.append("MIN_DAYS must be >= 200")
    
    # If any errors found, log them and exit.
    if errors:
        for e in errors:
            logging.error("CONFIG: %s", e)
        sys.exit(1)


def setup_logging():
    """
    Initialize logging system with file and console handlers.
    
    Creates the output and logs directories if they don't exist, then configures
    Python's logging module with a consistent format for both file and console output.
    Called from main.py during startup.
    
    Logging output format:
      2024-03-26 14:32:15 | INFO     | module.name | Message text
    
    Logs are written to:
      - File: output/logs/app.log
      - Console: stdout (for Docker/container logs)
    """
    # Step 1: Create output and logs directories if they don't exist.
    # parents=True creates intermediate dirs; exist_ok=True doesn't fail if dir exists.
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 2: Configure Python logging with a consistent format across all handlers.
    logging.basicConfig(
        # Log level: only log messages at this level or higher (e.g., INFO captures INFO, WARNING, ERROR).
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        # Format string: timestamp | level | module name | message.
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        # Date/time format for the %(asctime)s placeholder.
        datefmt="%Y-%m-%d %H:%M:%S",
        # Handlers: where logs are sent.
        handlers=[
            # File handler: write logs to output/logs/app.log (persisted for debugging).
            logging.FileHandler(str(LOG_DIR / "app.log"), encoding="utf-8"),
            # Stream handler: write logs to stdout (visible in terminal/Docker logs).
            logging.StreamHandler(sys.stdout),
        ],
    )
