"""
LLM explanation helpers.

This module turns analysis metrics into human-readable narratives:
    1. Build prompt payload from computed indicators/risk data
    2. Ask active LLM provider for explanation
    3. Fallback to deterministic template when LLM is unavailable
    4. Build portfolio-level scan summary text
"""

import logging
from config.markets import currency_for
from config.legal import disclaimer
from llm import prompts

logger = logging.getLogger(__name__)
_engine = None


def _get():
    """Lazily create and cache a shared LLM engine instance."""

    global _engine
    if _engine is None:
        from llm.engine import LLMEngine
        _engine = LLMEngine()
    return _engine


def explain(analysis, risk_data, query=""):
    """
    Build a single-stock explanation using LLM when available.

    Falls back to template output if provider is unavailable or invocation fails.
    """

    # STEP 1: Collect core fields used in prompt/template output.
    engine = _get()
    sym = analysis.get("symbol", "?")
    sig = analysis.get("signals", {})
    ret = analysis.get("returns", {})
    cur = analysis.get("currency") or currency_for(sym)
    q = query or "Explain the technical analysis for this stock."

    # STEP 2: If no live LLM is available, return deterministic template summary.
    if not engine.available:
        return _template(analysis, risk_data, cur, q)

    # STEP 3: Build structured user prompt from analysis fields.
    user = prompts.STOCK.format(
        symbol=sym, currency=cur, query=q,
        price=analysis.get("price", "N/A"),
        r1d=ret.get("1d", "N/A"), r1w=ret.get("1w", "N/A"),
        r1m=ret.get("1m", "N/A"), rytd=ret.get("ytd", "N/A"),
        rsi=analysis.get("rsi", "N/A"), rsi_sig=sig.get("rsi", "N/A"),
        macd_sig=sig.get("macd", "N/A"), trend_sig=sig.get("trend", "N/A"),
        bb=analysis.get("bb_position", "N/A"),
        score=analysis.get("composite_score", "N/A"),
        vol=analysis.get("volatility_annual_pct", "N/A"),
        sharpe=analysis.get("sharpe_ratio", "N/A"),
        dd=analysis.get("max_drawdown_pct", "N/A"),
        pos=risk_data.get("position_pct", "N/A"),
        stop=risk_data.get("stop_loss_price", "N/A"),
        stop_pct=risk_data.get("stop_distance_pct", "N/A"),
    )

    # STEP 4: Invoke LLM and fallback to template if response is empty.
    result = engine.invoke(prompts.SYSTEM, user)
    return result if result else _template(analysis, risk_data, cur, q)


def _template(a, r, cur, q):
    """Generate deterministic explanation text when LLM is not used."""

    # Convert numeric composite score into simple outlook label.
    score = a.get("composite_score", 0)
    if score >= 3: outlook = "strongly bullish"
    elif score >= 1: outlook = "mildly bullish"
    elif score <= -3: outlook = "strongly bearish"
    elif score <= -1: outlook = "mildly bearish"
    else: outlook = "neutral"

    sig = a.get("signals", {})
    ret = a.get("returns", {})
    sep = "=" * 40

    # Assemble a compact multi-line report for one stock.
    return "\n".join([
        "{} ({}) - Analysis".format(a.get("symbol", "?"), cur),
        sep,
        "Your question: {}".format(q),
        "",
        "Score: {}/4 ({})".format(score, outlook),
        "RSI: {} ({})".format(a.get("rsi", "-"), sig.get("rsi", "-")),
        "MACD: {}".format(sig.get("macd", "-")),
        "Trend: {}".format(sig.get("trend", "-")),
        "Volatility: {}%".format(a.get("volatility_annual_pct", "-")),
        "Sharpe: {}".format(a.get("sharpe_ratio", "-")),
        "Max Drawdown: {}%".format(a.get("max_drawdown_pct", "-")),
        "",
        "Returns: 1d={}% | 1w={}% | 1m={}% | YTD={}%".format(
            ret.get("1d", "-"), ret.get("1w", "-"),
            ret.get("1m", "-"), ret.get("ytd", "-")),
        "",
        "Position: {}% | Stop: {} {} | Risk: ${}".format(
            r.get("position_pct", 0), r.get("stop_loss_price", 0),
            cur, r.get("risk_dollars", 0)),
        "",
        "This is a data summary, not financial advice.",
    ])


def portfolio_summary(analyses):
    """Build scan-level summary grouping symbols into bullish/bearish/neutral buckets."""

    if not analyses:
        return "No stocks analyzed."

    # Group by composite score bands for fast at-a-glance readout.
    bull = sorted([a for a in analyses if a.get("composite_score", 0) >= 2],
                  key=lambda x: x.get("composite_score", 0), reverse=True)
    bear = sorted([a for a in analyses if a.get("composite_score", 0) <= -2],
                  key=lambda x: x.get("composite_score", 0))
    neut = len(analyses) - len(bull) - len(bear)

    # Build line-by-line terminal-friendly summary report.
    lines = ["=" * 60, "SCAN: {} stocks".format(len(analyses)), "=" * 60, "",
             "Bullish ({}):".format(len(bull))]
    for a in bull[:10]:
        lines.append("  {:<10} {}/4 | RSI {} | YTD {}% | {}".format(
            a["symbol"], a.get("composite_score", 0), a.get("rsi", "-"),
            a.get("returns", {}).get("ytd", "-"), a.get("currency", "")))
    lines.append("\nBearish ({}):".format(len(bear)))
    for a in bear[:10]:
        lines.append("  {:<10} {}/4 | RSI {} | YTD {}% | {}".format(
            a["symbol"], a.get("composite_score", 0), a.get("rsi", "-"),
            a.get("returns", {}).get("ytd", "-"), a.get("currency", "")))
    lines.append("\nNeutral: {}".format(neut))
    lines.append("\n" + disclaimer(False))
    return "\n".join(lines)