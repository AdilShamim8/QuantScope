"""
LLM Prompt Templates

Purpose: Define the system and user prompt templates that guide the language
model's responses. These templates enforce constraints (no investment advice,
use clear language, always include disclaimer) and structure the financial
data context that flows into each LLM invocation.

The prompts are used by explainer.py to generate narratives for individual
stocks and portfolio summaries. Each prompt is a template that accepts
format parameters (e.g., {symbol}, {price}, {score}) to inject live data
at the time of LLM invocation.

Templates:
  - SYSTEM: Sets role and constraints (analyst, never recommend, always disclaim)
  - STOCK: Prompts LLM to explain stock metrics for a given user question
"""


# SYSTEM PROMPT
# Role and constraints for all LLM invocations. This instructs the model to:
#   1. Act as a financial data analyst (not a financial advisor)
#   2. Explain what metrics mean (interpretation, not prediction)
#   3. NEVER give investment recommendations (buy/sell advice)
#   4. Always end responses with a legal disclaimer
# This ensures output is educational and compliant with financial regulations.
SYSTEM = (
    "You are a financial data analyst who explains quantitative metrics "
    "in clear language. You NEVER give investment advice. You NEVER "
    "recommend buying or selling. You explain what numbers mean. "
    "You always end with: 'This is a data summary, not financial advice.'"
)

# STOCK PROMPT
# User-facing prompt for generating individual stock narratives.
# Format parameters (enclosed in {braces}) are injected at runtime with live data:
#   {symbol}: Ticker symbol (e.g., AAPL)
#   {currency}: Trading currency (e.g., USD)
#   {query}: User's natural language question about the stock
#   {price}: Current price
#   {r1d}, {r1w}, {r1m}, {rytd}: Returns for 1-day, 1-week, 1-month, year-to-date
#   {rsi}, {rsi_sig}: Relative Strength Index and its interpretation signal
#   {macd_sig}: MACD trend signal (bullish/bearish/neutral)
#   {trend_sig}: Overall trend direction
#   {bb}: Bollinger Band position (0=at lower band, 1=at upper band)
#   {score}: Composite score out of 4 (technical health indicator)
#   {vol}: Historical volatility percentage
#   {sharpe}: Sharpe ratio (risk-adjusted return)
#   {dd}: Maximum drawdown percentage from peak
#   {pos}: Recommended position size as % of portfolio
#   {stop}: Stop-loss price
#   {stop_pct}: Stop-loss distance as percentage below current price
#
# Instruction guidelines:
#   - 3-4 paragraphs of clear narrative
#   - Use "the data suggests" framing (not "you should")
#   - Interpret metrics for the user's specific question
#   - End with mandatory disclaimer
STOCK = (
    "Explain this analysis for {symbol} ({currency}).\n\n"
    "USER QUESTION: {query}\n\n"
    "Address the user's question using ONLY the data below.\n\n"
    "PRICE: {price} {currency}\n"
    "RETURNS: 1d={r1d}%, 1w={r1w}%, 1m={r1m}%, YTD={rytd}%\n"
    "RSI: {rsi} ({rsi_sig})\n"
    "MACD: {macd_sig}\n"
    "TREND: {trend_sig}\n"
    "Bollinger: {bb} (0=lower, 1=upper)\n"
    "Score: {score}/4\n"
    "Volatility: {vol}%\n"
    "Sharpe: {sharpe}\n"
    "Max Drawdown: {dd}%\n"
    "Position: {pos}% of portfolio\n"
    "Stop-Loss: {stop} {currency} ({stop_pct}% below)\n\n"
    "Write 3-4 paragraphs. Use 'the data suggests' not 'you should'. "
    "End with: 'This is a data summary, not financial advice.'"
)
