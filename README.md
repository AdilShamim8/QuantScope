# QuantScope

Global quantitative stock analysis platform. Covers 35+ exchanges, provides
technical indicators with automated risk management, and explains results in
plain language using any LLM provider.

**Math makes the decisions. AI explains them. System works without AI.**

```
Analysis time:  2-4 hours manual  ->  45 seconds automated
Risk coverage:  0% of retail      ->  100% position sizing + stop-loss
Exchange reach: US-only (free)    ->  35+ global exchanges
LLM lock-in:   OpenAI only       ->  6 providers with auto-fallback
```

---

## Table of Contents

- [Problem](#problem)
- [Solution](#solution)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Technical Approach](#technical-approach)
- [Risk Management](#risk-management)
- [LLM Integration](#llm-integration)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Failure Modes and Mitigations](#failure-modes-and-mitigations)
- [What This Tool Does NOT Do](#what-this-tool-does-not-do)
- [Results vs Baseline](#results-vs-baseline)
- [Future Improvements](#future-improvements)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Problem

Retail investors face three compounding problems:

**1. Analysis takes too long.**
Evaluating a single stock across price history, technical indicators,
fundamentals, and risk parameters takes 2-4 hours using free tools
(Yahoo Finance, TradingView, spreadsheets). Evaluating a portfolio of
10 stocks takes a full workday.

**2. Risk management is skipped.**
95% of retail investors do not calculate position sizes, stop-loss levels,
or portfolio diversification. They invest based on social media sentiment
and gut feeling. SEC research shows 70% of retail traders lose money.

**3. Existing tools are US-centric and expensive.**
Bloomberg Terminal costs $24,000/year. Free tools cover US markets only.
An investor analyzing Toyota (7203.T), Reliance (RELIANCE.NS), and
Samsung (005930.KS) alongside Apple (AAPL) has no unified free tool.

---

## Solution

QuantScope solves all three problems:

| Problem | Solution | Metric |
|---------|----------|--------|
| Slow analysis | Automated pipeline | 10 stocks in 45 seconds |
| No risk management | ATR-based position sizing, stop-losses | 100% coverage |
| US-only / expensive | 35+ exchanges, free Yahoo Finance data | Global |
| Hard to understand | LLM explains numbers in plain language | Beginner-friendly |
| LLM vendor lock-in | LangChain with 6 providers + fallback | Zero lock-in |

Users interact through natural language:

```
Input:  "Should I invest in Apple or Tesla?"
Input:  "How is Toyota performing?"
Input:  "Compare Reliance and TCS"
Input:  "AAPL, MSFT, NVDA, 7203.T, VOD.L"
```

The system parses the query, identifies stocks (dictionary lookup, not LLM),
runs quantitative analysis, calculates risk parameters, and optionally
generates a plain-language explanation.

---

## Architecture

```
                         User (Browser / API client)
                              |
                              v
                    +-------------------+
                    |    FastAPI App     |
                    |  (api/app.py)     |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
         Rate Limiter   Input Validator  Request Logger
              |              |              |
              +--------------+--------------+
                             |
                             v
                    +-------------------+
                    |  Query Parser     |
                    | (query_parser.py) |
                    +--------+----------+
                             |
                    Extracts ticker symbols from
                    natural language using dictionary
                    lookup (300+ companies, 35+ exchanges)
                             |
                             v
                    +-------------------+
                    |     Pipeline      |
                    |  (pipeline.py)    |
                    +--------+----------+
                             |
           +---------+-------+-------+---------+
           |         |               |         |
           v         v               v         v
      DataFetcher  Indicators    Risk Engine  LLM Explainer
      (Yahoo+Stooq)(pure math)   (pure math)  (LLM stack)
           |         |               |         |
      Live OHLCV   RSI, MACD,    Position    Translates
      from any     Bollinger,    sizing,     numbers to
      exchange     ATR, SMA      stop-loss,  plain English
                                 Sharpe,     using any
                                 drawdown    provider
                             |
                             v
                    +-------------------+
                    |    Output         |
                    | CSV + JSON + HTML |
                    +-------------------+
```

**Key architectural decisions:**

1. **No ML model.** Technical indicators are deterministic formulas.
   RSI, MACD, Bollinger have published definitions. Using ML here
   would add complexity with zero benefit.

2. **LLM for explanation only.** LLM receives pre-computed numbers.
   It cannot invent data. If LLM fails, template fallback generates
   the explanation. System never breaks because AI is down.

3. **Dictionary for company names.** "Apple" to "AAPL" is a lookup,
   not an AI task. Dictionary is free, instant, and 100% accurate.
   LLM would cost $0.002/query, take 2 seconds, and sometimes fail.

4. **Single container.** API + HTML + static files served from one
   process. Correct for this scale. Separate when team grows.

5. **Server-rendered HTML + vanilla JS.** No React, no build step.
   This is data tables and charts. A framework adds 300KB of
   JavaScript for zero benefit.

---

## Quick Start

**Prerequisites:** Python 3.9+

```bash
# 1. Clone and setup
git clone https://github.com/adilshamim8/quantscope.git
cd quantscope
cp .env.example .env
pip install -r requirements.txt

# 2. (Optional) Add an LLM API key to .env for AI explanations
#    System works fully without any API key

# 3. Start the web server
python main.py --serve

# 4. Open browser
#    http://localhost:8000
```

**First analysis (under 60 seconds):**

1. Go to `http://localhost:8000/analyze`
2. Type: `Should I invest in Apple or Tesla?`
3. Click Analyze
4. View results: table, cards, charts, AI explanation

**CLI usage:**

```bash
# Analyze specific stocks
python main.py --symbols AAPL MSFT 7203.T RELIANCE.NS VOD.L

# Custom portfolio value
python main.py --symbols AAPL NVDA TSLA --portfolio 50000
```

**Docker:**

```bash
docker-compose up --build
# Open http://localhost:8000
```

**Run tests:**

```bash
make test
# or: pytest tests/ -v --cov=core --cov=llm --cov-report=term-missing
```

---

## Usage

### Web Interface

| Page | URL | Purpose |
|------|-----|---------|
| Home | `/` | Landing page with quick-start input |
| Analyze | `/analyze` | Main analysis interface |
| Exchanges | `/exchanges` | Supported exchanges reference |
| About | `/about` | Methodology and legal disclaimer |
| API Docs | `/api/docs` | Interactive Swagger documentation |

### Natural Language Queries

The system accepts natural language in the analysis input:

```
"Help me understand Apple stock price"
  -> Parses "Apple" -> AAPL -> Runs full analysis

"Should I buy Tesla or Nvidia?"
  -> Parses "Tesla" -> TSLA, "Nvidia" -> NVDA
  -> Detects investment intent
  -> Returns data analysis (NOT investment advice)

"Compare Reliance and TCS"
  -> Parses "Reliance" -> RELIANCE.NS, "TCS" -> TCS.NS
  -> Detects comparison intent

"How is Toyota performing?"
  -> Parses "Toyota" -> 7203.T
  -> Returns JPY-denominated analysis

"AAPL, MSFT, NVDA"
  -> Direct ticker input (no parsing needed)
```

**Query parsing is deterministic.** It uses a 300+ entry dictionary,
not an LLM. Zero API cost. Sub-millisecond latency. 100% accuracy
for known companies. Unknown companies can use ticker symbols directly.

### API

```bash
# Smart analyze (natural language)
curl -X POST http://localhost:8000/api/v1/smart-analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare Apple and Samsung", "portfolio_value": 25000}'

# Direct analyze (ticker symbols)
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "005930.KS"], "portfolio_value": 25000}'

# Parse only (no analysis)
curl -X POST http://localhost:8000/api/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"query": "Tesla and Toyota"}'

# Health check
curl http://localhost:8000/api/v1/health
```

---

## Technical Approach

### Indicators

Every indicator is a published mathematical formula. No randomness,
no trained parameters, no AI. Given the same input, output is
identical every time.

| Indicator | What It Measures | Signal | Reference |
|-----------|-----------------|--------|-----------|
| RSI (14) | Momentum | <30 oversold, >70 overbought | Wilder 1978 |
| MACD (12/26/9) | Trend direction | Line vs signal crossing | Appel 1979 |
| Bollinger (20, 2std) | Price vs volatility envelope | Near lower = cheap | Bollinger 1980s |
| ATR (14) | Daily volatility range | Used for stop-loss | Wilder 1978 |
| SMA (50/200) | Trend direction | Golden/death cross | Industry standard |
| Volume Ratio | Activity vs average | High = institutional interest | Industry standard |

### Composite Score

Each indicator generates a directional signal: +1 (bullish),
-1 (bearish), or 0 (neutral). The composite score is the sum.

```
Score range: -4 to +4
  +3 to +4:  Strongly bullish (most indicators aligned up)
  +1 to +2:  Mildly bullish
   0:        Neutral / mixed signals
  -1 to -2:  Mildly bearish
  -3 to -4:  Strongly bearish (most indicators aligned down)
```

**This score is NOT a prediction.** It is a summary of current
technical conditions. It tells you what the data shows right now,
not what will happen next.

### Exchange-Aware Calculations

Different exchanges have different trading days per year. This affects
annualized volatility and Sharpe ratio calculations.

```
NYSE/NASDAQ:  252 days    (volatility = daily_std * sqrt(252))
Tokyo:        245 days    (volatility = daily_std * sqrt(245))
Shanghai:     244 days    (volatility = daily_std * sqrt(244))
```

Using 252 for all exchanges introduces ~2% error for Asian markets.
QuantScope uses the correct factor for each exchange.

### Data Validation

Yahoo Finance data is free but imperfect. Every download passes through:

1. **Completeness check:** Stock rejected if >20% data missing
2. **Minimum history:** Need 200 trading days for SMA-200
3. **Bad price detection:** Zero or negative prices flagged
4. **Extreme move detection:** >50% daily moves flagged (splits or errors)
5. **Stale data detection:** Exchange-aware (US: 4 days, Asia: 5 days)
6. **Auto-adjust enabled:** Historical prices adjusted for splits/dividends

```
Without auto_adjust: A 4:1 stock split appears as a 75% crash.
With auto_adjust:    Historical prices correctly reflect split-adjusted values.
```

---

## Risk Management

This is the most important section of the entire system.

### Position Sizing

**Wrong approach (what most retail investors do):**
"I have $10,000. I like NVDA. I will put $5,000 in it."
This is gambling.

**Correct approach (ATR-based position sizing):**

```
Given:
  Portfolio:    $10,000
  Stock price:  $150
  ATR (14-day): $5 (stock moves ~$5 per day on average)

Step 1: Max risk per trade = 2% of portfolio = $200
Step 2: Stop-loss distance = 2 * ATR = $10 below entry
Step 3: Shares by risk = $200 / $10 = 20 shares
Step 4: Max position = 10% of portfolio = $1,000
Step 5: Shares by cap = $1,000 / $150 = 6 shares
Step 6: Final = min(20, 6) = 6 shares

Position value: $900 (9% of portfolio)
Risk if stopped out: $60 (0.6% of portfolio)
Stop-loss price: $140
```

This ensures that if the stop-loss is hit, maximum loss is bounded.

### Metrics Calculated

| Metric | What It Tells You |
|--------|-------------------|
| Position size (shares) | How many shares to buy |
| Position % | What portion of portfolio this represents |
| Stop-loss price | Where to exit if trade goes wrong |
| Risk per trade ($) | Maximum dollar loss if stopped out |
| Sharpe ratio | Return per unit of risk (>1.0 good, >2.0 great) |
| Max drawdown | Worst peak-to-trough decline in history |

---

## LLM Integration

### Provider Support

QuantScope uses a multi-provider LLM stack (LangChain + native Ollama HTTP adapter):

| Provider | Model | Requires |
|----------|-------|----------|
| OpenAI | gpt-4o-mini | `OPENAI_API_KEY` |
| Anthropic | claude-3-haiku | `ANTHROPIC_API_KEY` |
| Google | gemini-pro | `GOOGLE_API_KEY` |
| Ollama | llama3 (local/cloud) | `OLLAMA_BASE_URL` (`OLLAMA_API_KEY` optional) |
| Mistral | mistral-small | `MISTRAL_API_KEY` |
| Cohere | command-r | `COHERE_API_KEY` |

### Fallback Chain

```
Request arrives
  |
  v
Try active provider (e.g., OpenAI)
  |-- Success -> Return response
  |-- Failure -> Try next provider (Anthropic)
      |-- Success -> Switch active, return response
      |-- Failure -> Try next (Google)
          |-- ... continue through chain
              |-- All fail -> Template fallback (no LLM needed)
```

### What LLM Receives

The LLM receives ONLY pre-computed numbers:

```
Explain this analysis for AAPL (USD).

USER QUESTION: Should I invest in Apple?

PRICE: 178.50 USD
RETURNS: 1d=0.5%, 1w=2.1%, 1m=5.3%, YTD=18.5%
RSI: 45.3 (NEUTRAL)
MACD: BULLISH
TREND: UPTREND
Score: 2/4
Volatility: 28.5%
Stop-Loss: 169.50 USD (5.04% below)
```

The LLM cannot access market data, cannot make API calls,
cannot look up current prices. It can only explain the numbers
it is given. If it hallucinates, it can only hallucinate the
EXPLANATION, not the DATA.

### Without Any LLM

Set no API keys in `.env`. The system generates template explanations:

```
AAPL (USD) - Analysis
========================================
Your question: Should I invest in Apple?

Score: 2/4 (mildly bullish)
RSI: 45.3 (NEUTRAL)
MACD: BULLISH
Trend: UPTREND
Volatility: 28.5%
...
This is a data summary, not financial advice.
```

---

## API Reference

### `POST /api/v1/smart-analyze`

Natural language or ticker symbols.

**Request:**
```json
{
  "query": "Compare Apple and Samsung",
  "portfolio_value": 25000
}
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00",
  "query_info": {
    "symbols": ["AAPL", "005930.KS"],
    "intent": "compare",
    "original_query": "Compare Apple and Samsung",
    "parsed_companies": [
      {"input": "apple", "ticker": "AAPL", "method": "name"},
      {"input": "samsung", "ticker": "005930.KS", "method": "name"}
    ],
    "is_natural_language": true
  },
  "stocks_analyzed": 2,
  "portfolio_value": 25000,
  "llm_provider": "openai",
  "results": [
    {
      "symbol": "AAPL",
      "sector": "Technology",
      "price": 178.50,
      "currency": "USD",
      "composite_score": 2,
      "rsi": 45.3,
      "signals": {"rsi": "NEUTRAL", "macd": "BULLISH", "trend": "UPTREND", "bollinger": "MIDDLE"},
      "returns": {"1d": 0.5, "1w": 2.1, "1m": 5.3, "ytd": 18.5},
      "volatility_annual_pct": 28.5,
      "sharpe_ratio": 1.2,
      "max_drawdown_pct": -15.3,
      "risk": {
        "shares": 14,
        "position_value": 2499.0,
        "position_pct": 10.0,
        "stop_loss_price": 169.50,
        "risk_dollars": 126.0
      },
      "explanation": "Apple's technical indicators show..."
    }
  ],
  "disclaimer": "DISCLAIMER: This tool provides..."
}
```

### `POST /api/v1/analyze`

Direct ticker symbols (no parsing).

**Request:**
```json
{
  "symbols": ["AAPL", "MSFT", "7203.T"],
  "portfolio_value": 10000
}
```

### `POST /api/v1/parse`

Parse query without running analysis.

### `GET /api/v1/health`

System health with metrics.

### `GET /api/v1/exchanges`

List of supported exchanges.

---

## Testing

```bash
# Run all tests with coverage
make test
# Windows alternative:
python -m pytest -q

# Run specific test file
pytest tests/test_query_parser.py -v

# Run with coverage report
pytest tests/ --cov=core --cov=llm --cov-report=html
# Open htmlcov/index.html
```

### Test Coverage

| Module | Tests | What is Tested |
|--------|-------|----------------|
| `core/validator.py` | 7 tests | Symbol sanitization, injection prevention, length limits |
| `core/query_parser.py` | 12 tests | Ticker extraction, company names, intent detection, edge cases |
| `core/indicators.py` | 7 tests | RSI range, MACD histogram identity, score range, insufficient data |
| `core/risk.py` | 7 tests | Position sizing, cap enforcement, zero ATR, Sharpe, drawdown |

### What Tests Verify

```
1. RSI is always between 0 and 100 (mathematical guarantee)
2. MACD histogram equals MACD line minus signal line (identity check)
3. Position value never exceeds 10% of portfolio (risk limit)
4. Zero ATR produces zero shares (division safety)
5. Known drawdown: [100, 50, 60] produces -50% (correctness)
6. SQL injection in symbol input is rejected (security)
7. "Apple" maps to AAPL, "Toyota" maps to 7203.T (parsing)
8. Empty query produces empty symbol list (edge case)
9. Investment intent words detected correctly (query understanding)
```

---

## Deployment

### Single Machine

```bash
python main.py --serve --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker-compose up --build
```

The container:
- Runs as non-root user
- Has health check endpoint
- Limits: 2 CPU, 2GB RAM
- Auto-restarts on crash
- Mounts output directory for persistence

### Production with Gunicorn

```bash
gunicorn api.app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### Cost Estimate

| Component | Cost |
|-----------|------|
| Yahoo Finance API | Free |
| LLM (optional) | ~$0.001 per stock explanation |
| Server (1 vCPU, 2GB) | ~$5-20/month (cloud) |
| Full Nasdaq-100 analysis | ~$0.10 in LLM costs |
| Analysis without LLM | $0 |

---

## Monitoring

QuantScope tracks four metric categories:

### 1. System Metrics
- Request count (total, failed)
- Request latency (mean, max, min in milliseconds)
- Uptime

### 2. Data Quality
- Yahoo Finance download success/failure rate
- Stocks rejected by validation (and why)
- Stale data warnings

### 3. LLM Health
- Active provider
- Fallback events
- Template fallback rate

### 4. Business Metrics
- Stocks analyzed per request
- Most queried symbols
- Query parsing success rate

Access metrics via health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "ok",
  "version": "1.0.0",
  "llm_provider": "openai",
  "exchanges": 31,
  "metrics": {
    "uptime_seconds": 3600,
    "counters": {
      "requests_total": 150,
      "analyses_completed": 45
    },
    "timings": {
      "request_latency": {
        "count": 150,
        "mean_ms": 1200,
        "max_ms": 45000,
        "min_ms": 5
      }
    }
  }
}
```

---

## Project Structure

```
quantscope/
|
|-- config/                    CONFIGURATION
|   |-- settings.py            All tunable parameters
|   |-- markets.py             35+ exchange definitions
|   |-- companies.py           300+ company name to ticker map
|   |-- legal.py               Disclaimers
|
|-- core/                      BUSINESS LOGIC (no AI, no API)
|   |-- validator.py           Input sanitization
|   |-- query_parser.py        Natural language to tickers
|   |-- data_fetcher.py        Yahoo Finance pipeline
|   |-- indicators.py          RSI, MACD, Bollinger, ATR, SMA
|   |-- risk.py                Position sizing, Sharpe, drawdown
|
|-- llm/                       AI LAYER (optional, not required)
|   |-- engine.py              LangChain multi-provider engine
|   |-- prompts.py             All prompt templates
|   |-- explainer.py           Number-to-English translation
|
|-- api/                       WEB LAYER
|   |-- app.py                 FastAPI application factory
|   |-- api_routes.py          JSON API endpoints
|   |-- page_routes.py         HTML page routes
|   |-- middleware.py           Rate limiting, logging
|   |-- schemas.py             Request/response models
|
|-- frontend/                  UI (no build step)
|   |-- templates/             Jinja2 HTML templates
|   |-- static/css/            Custom CSS
|   |-- static/js/             Vanilla JavaScript
|
|-- pipeline.py                Orchestrator
|-- report.py                  CSV/JSON output
|-- monitor.py                 Metrics collection
|-- main.py                    CLI entry point
|-- tests/                     pytest suite
```

### Why This Structure

```
core/ has ZERO dependencies on llm/ or api/.
  -> Business logic is testable without starting a server
  -> Business logic works without any LLM provider

llm/ depends on core/ config only.
  -> LLM layer is completely replaceable
  -> Template fallback means system works without it

api/ depends on core/ and llm/.
  -> Thin layer: validation, routing, serialization
  -> No business logic in API routes

pipeline.py orchestrates core/ and llm/.
  -> Single entry point for analysis
  -> Same pipeline serves CLI and API
```

---

## Configuration

All settings are in `config/settings.py`. No magic numbers in business logic.

### Technical Analysis (do not change without backtesting)

| Parameter | Value | Reason |
|-----------|-------|--------|
| RSI period | 14 | Wilder standard, most researched |
| RSI oversold | 30 | Industry convention |
| RSI overbought | 70 | Industry convention |
| MACD fast/slow/signal | 12/26/9 | Appel original parameters |
| Bollinger period/std | 20/2.0 | Bollinger standard |
| ATR period | 14 | Wilder standard |

### Risk Management

| Parameter | Value | Reason |
|-----------|-------|--------|
| Max position % | 10% | Single stock should not dominate portfolio |
| Max sector % | 30% | Sector diversification |
| Stop-loss ATR multiplier | 2.0 | 2x ATR gives room for normal moves |
| Risk per trade | 2% | Standard risk management rule |
| Risk-free rate | 5% | Current T-bill rate |

### Environment Variables

```
OPENAI_API_KEY=         # Optional: enables OpenAI explanations
ANTHROPIC_API_KEY=      # Optional: enables Claude explanations
GOOGLE_API_KEY=         # Optional: enables Gemini explanations
OLLAMA_BASE_URL=        # Optional: enables local LLM
OLLAMA_API_KEY=         # Optional: enables Ollama cloud auth
MISTRAL_API_KEY=        # Optional: enables Mistral
COHERE_API_KEY=         # Optional: enables Cohere
YF_PROXY=               # Optional: proxy for market data requests
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

---

## Failure Modes and Mitigations

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Yahoo Finance returns stale data | Wrong indicator values | Stale date detection per exchange timezone |
| Yahoo Finance returns NaN prices | Division errors in indicators | NaN ratio check, reject if >20% missing |
| Stock split not adjusted | Appears as 75% crash | `auto_adjust=True` in yfinance |
| LLM hallucinates financial data | User trusts wrong numbers | LLM receives ONLY pre-computed numbers |
| LLM provider is down | No explanation generated | Automatic fallback chain + template fallback |
| User sends SQL injection | Security breach | Regex validation, character sanitization |
| User sends 500 symbols | Server overload | MAX_SYMBOLS=200 limit, rate limiting |
| User interprets output as advice | Legal liability | Disclaimer on every output, never says "buy/sell" |
| Extreme market volatility | Indicators lag reality | >50% daily move detection and flagging |
| Network timeout / Yahoo block | Analysis may degrade | Yahoo retries + per-symbol fallback + Stooq fallback + graceful degraded response |

---

## What This Tool Does NOT Do

1. **Does NOT predict stock prices.** It shows current technical conditions.
2. **Does NOT give investment advice.** It explains what quantitative data shows.
3. **Does NOT manage real portfolios.** It calculates hypothetical position sizes.
4. **Does NOT execute trades.** It is an analysis only.
5. **Does NOT use AI for decisions.** Math decides. AI explains.
6. **Does NOT replace a financial advisor.** It supplements analysis.

---

## Results vs Baseline

| Metric | Manual Process | QuantScope |
|--------|---------------|------------|
| Time per stock | 2-4 hours | 5-10 seconds |
| Time for 10 stocks | 20-40 hours | 45 seconds |
| Risk parameters calculated | Usually 0 | 6 per stock |
| Exchanges covered | Usually 1 (US) | 35+ |
| Position sizing | Gut feeling | ATR-based math |
| Stop-loss | None or arbitrary | 2x ATR from entry |
| Reproducibility | Low (subjective) | 100% (deterministic) |
| Cost | Free (but time) | Free (and fast) |

---

## Future Improvements

Listed in priority order with effort estimate:

| Improvement | Value | Effort | Status |
|-------------|-------|--------|--------|
| Backtesting engine | Validate signals on historical data | 2 weeks | Planned |
| Portfolio optimizer (Markowitz) | Optimal allocation across stocks | 1 week | Planned |
| WebSocket live updates | Real-time price streaming | 1 week | Considered |
| User accounts + saved analyses | Persistent history | 2 weeks | Considered |
| Mobile-responsive charts | Better mobile experience | 3 days | Considered |
| Fundamental scoring model | P/E, growth, debt analysis | 1 week | Planned |
| Alert system (email/SMS) | Notify when score changes | 1 week | Considered |
| Multi-language explanations | Bengali, Hindi, Japanese, etc. | 1 week | Considered |

---

## License

MIT License. See `LICENSE` file.

---

## Disclaimer

**This tool is for educational and informational purposes only.**

It does NOT constitute financial advice, investment advice, trading advice,
or any other type of professional advice. The analysis is based on historical
data and mathematical indicators, which do NOT predict future performance.

All investments carry risk, including the risk of total loss. Past performance
does not guarantee future results. You should consult a licensed financial
advisor in your jurisdiction before making any investment decisions.

This system is not registered as an investment advisor with any regulatory
authority (SEC, FCA, SEBI, ASIC, FSA, or any other). It does not provide
personalized investment recommendations.

The creators and operators of this tool accept NO liability for any financial
losses incurred through the use of this information.
