import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from config import settings
from config.markets import trading_days

logger = logging.getLogger(__name__)


def rsi(prices, period=None):
    """Compute Relative Strength Index (RSI) where low values can indicate oversold conditions."""
    # Use configured default if caller does not provide a custom period.
    p = period or settings.RSI_PERIOD
    # Price changes between consecutive rows.
    d = prices.diff()
    # Keep only positive and negative moves separately.
    g = d.where(d > 0, 0.0)
    l = (-d).where(d < 0, 0.0)
    # Exponential moving averages of gains and losses.
    ag = g.ewm(com=p - 1, min_periods=p).mean()
    al = l.ewm(com=p - 1, min_periods=p).mean()
    rs = ag / al.replace(0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # Handle edge cases for monotonic/no-move series to avoid NaN outputs.
    out = out.mask((al == 0) & (ag > 0), 100.0)
    out = out.mask((ag == 0) & (al > 0), 0.0)
    out = out.mask((ag == 0) & (al == 0), 50.0)
    return out


def macd(prices, fast=None, slow=None, sig=None):
    """Compute MACD line, signal line, and histogram for momentum direction."""
    f = fast or settings.MACD_FAST
    s = slow or settings.MACD_SLOW
    g = sig or settings.MACD_SIGNAL
    # Fast EMA reacts quicker than slow EMA.
    ef = prices.ewm(span=f, adjust=False).mean()
    es = prices.ewm(span=s, adjust=False).mean()
    line = ef - es
    signal = line.ewm(span=g, adjust=False).mean()
    return line, signal, line - signal


def bollinger(prices, period=None, nstd=None):
    """Compute Bollinger upper/middle/lower bands around rolling mean and volatility."""
    p = period or settings.BOLLINGER_PERIOD
    n = nstd or settings.BOLLINGER_STD
    mid = prices.rolling(p).mean()
    std = prices.rolling(p).std()
    return mid + n * std, mid, mid - n * std


def atr(high, low, close, period=None):
    """Compute Average True Range (ATR), a common volatility measure."""
    p = period or settings.ATR_PERIOD
    prev = close.shift(1)
    # True range = largest of intraday range and overnight gap moves.
    tr = pd.concat([
        high - low, (high - prev).abs(), (low - prev).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(p).mean()


def analyze(symbol, ohlcv):
    """
    Analyze one symbol using OHLCV history and return structured metrics.

    Output includes indicator values, signal labels, composite score,
    multi-horizon returns, and annualized volatility.
    """
    try:
        # STEP 1: Extract core market columns used by indicators.
        c = ohlcv["Close"]
        h = ohlcv["High"]
        lo = ohlcv["Low"]
        v = ohlcv["Volume"]

        # Require enough history so long-window indicators are meaningful.
        if c.dropna().shape[0] < settings.MIN_DAYS:
            return None

        # STEP 2: Calculate technical indicators.
        r = rsi(c)
        ml, ms, mh = macd(c)
        bu, bm, bl = bollinger(c)
        a = atr(h, lo, c)
        s50 = c.rolling(settings.SMA_SHORT).mean()
        s200 = c.rolling(settings.SMA_LONG).mean()

        # Keep latest snapshot values only (current market state).
        vals = {
            "c": c.iloc[-1], "r": r.iloc[-1],
            "ml": ml.iloc[-1], "ms": ms.iloc[-1], "mh": mh.iloc[-1],
            "bu": bu.iloc[-1], "bl": bl.iloc[-1],
            "a": a.iloc[-1], "s50": s50.iloc[-1], "s200": s200.iloc[-1],
        }
        # Abort if any required metric is invalid/NaN.
        for val in vals.values():
            if pd.isna(val):
                return None

        # STEP 3: Convert raw values into human-readable signal labels and score.
        signals = {}
        score = 0

        if vals["r"] < settings.RSI_OVERSOLD:
            signals["rsi"] = "OVERSOLD"; score += 1
        elif vals["r"] > settings.RSI_OVERBOUGHT:
            signals["rsi"] = "OVERBOUGHT"; score -= 1
        else:
            signals["rsi"] = "NEUTRAL"

        if vals["ml"] > vals["ms"] and vals["mh"] > 0:
            signals["macd"] = "BULLISH"; score += 1
        elif vals["ml"] < vals["ms"] and vals["mh"] < 0:
            signals["macd"] = "BEARISH"; score -= 1
        else:
            signals["macd"] = "NEUTRAL"

        if vals["c"] > vals["s200"] and vals["s50"] > vals["s200"]:
            signals["trend"] = "UPTREND"; score += 1
        elif vals["c"] < vals["s200"] and vals["s50"] < vals["s200"]:
            signals["trend"] = "DOWNTREND"; score -= 1
        else:
            signals["trend"] = "SIDEWAYS"

        # Bollinger position normalized between lower and upper band.
        bw = vals["bu"] - vals["bl"]
        bp = (vals["c"] - vals["bl"]) / bw if bw > 0 else 0.5
        if bp < 0.2:
            signals["bollinger"] = "NEAR_LOWER"; score += 1
        elif bp > 0.8:
            signals["bollinger"] = "NEAR_UPPER"; score -= 1
        else:
            signals["bollinger"] = "MIDDLE"

        # Volume regime relative to rolling average volume.
        avg_v = v.rolling(settings.VOLUME_AVG_PERIOD).mean().iloc[-1]
        vr = v.iloc[-1] / avg_v if avg_v > 0 else 1.0
        signals["volume"] = "HIGH" if vr > 1.5 else ("LOW" if vr < 0.5 else "NORMAL")

        # STEP 4: Compute returns across common horizons.
        rets = {}
        for label, days in [("1d", 1), ("1w", 5), ("1m", 21), ("3m", 63)]:
            if len(c) > days:
                rets[label] = round((c.iloc[-1] / c.iloc[-days - 1] - 1) * 100, 2)
        # YTD is computed from first trading day in current calendar year.
        current_year = c.index[-1].year
        ytd_series = c[c.index.year == current_year].dropna()
        if not ytd_series.empty:
            rets["ytd"] = round((c.iloc[-1] / ytd_series.iloc[0] - 1) * 100, 2)
        else:
            rets["ytd"] = round((c.iloc[-1] / c.iloc[0] - 1) * 100, 2)

        # STEP 5: Estimate annualized volatility using market-specific trading days.
        td = trading_days(symbol)
        vol = c.pct_change().dropna().std() * np.sqrt(td) * 100

        # Final structured output consumed by API and UI layers.
        return {
            "symbol": symbol,
            "price": round(vals["c"], 4),
            "rsi": round(vals["r"], 1),
            "macd_histogram": round(vals["mh"], 4),
            "bb_position": round(bp, 2),
            "atr": round(vals["a"], 4),
            "atr_pct": round(vals["a"] / vals["c"] * 100, 2),
            "sma_50": round(vals["s50"], 4),
            "sma_200": round(vals["s200"], 4),
            "volume_ratio": round(vr, 2),
            "signals": signals,
            "composite_score": score,
            "returns": rets,
            "volatility_annual_pct": round(vol, 2),
        }
    except Exception as e:
        # Keep pipeline resilient; one symbol failure should not crash full run.
        logger.error("%s analysis failed: %s", symbol, e)
        return None