"""
Risk utilities for portfolio sizing and performance diagnostics.

This module provides:
    1. Position sizing based on ATR stop distance and portfolio constraints
    2. Sharpe ratio calculation from daily returns
    3. Maximum drawdown calculation with peak/trough dates
"""

import logging
import numpy as np
import pandas as pd
from config import settings
from config.markets import trading_days

logger = logging.getLogger(__name__)


def position_size(portfolio, price, atr_val):
    """
    Compute recommended position size using risk-per-trade and max-position limits.

    Returns a dict with shares, exposure, risk dollars, and stop-loss details.
    """

    # Guard invalid inputs and return a fully zeroed structure.
    if price <= 0 or atr_val <= 0 or portfolio <= 0:
        return {"shares": 0, "position_value": 0, "position_pct": 0,
                "risk_dollars": 0, "risk_pct": 0,
                "stop_loss_price": 0, "stop_distance_pct": 0}

    # Max dollars allowed to lose on this trade.
    max_risk = portfolio * settings.RISK_PER_TRADE_PCT
    # Stop distance in price units derived from volatility (ATR).
    stop_dist = atr_val * settings.STOP_LOSS_ATR_MULT

    # Shares allowed by risk budget.
    by_risk = int(max_risk / stop_dist)
    # Shares allowed by position-cap rule.
    by_cap = int(portfolio * settings.MAX_POSITION_PCT / price)

    # Final shares respect both constraints.
    shares = max(min(by_risk, by_cap), 0)
    val = shares * price

    # Return rounded user-facing risk plan fields.
    return {
        "shares": shares,
        "position_value": round(val, 2),
        "position_pct": round(val / portfolio * 100, 2),
        "risk_dollars": round(shares * stop_dist, 2),
        "risk_pct": round(shares * stop_dist / portfolio * 100, 2),
        "stop_loss_price": round(max(price - stop_dist, 0), 4),
        "stop_distance_pct": round(stop_dist / price * 100, 2),
    }


def sharpe(daily_returns, symbol=""):
    """Compute annualized Sharpe ratio from daily return series."""

    # Need enough observations for a stable estimate.
    if daily_returns.empty or len(daily_returns) < 20:
        return 0.0

    # Use exchange-aware trading days when symbol is known.
    td = trading_days(symbol) if symbol else 252
    ann_ret = daily_returns.mean() * td
    ann_vol = daily_returns.std() * np.sqrt(td)

    # Protect against divide-by-zero for flat return series.
    if ann_vol == 0:
        return 0.0

    # Sharpe = excess annual return over annual volatility.
    return round((ann_ret - settings.RISK_FREE_RATE) / ann_vol, 3)


def max_drawdown(prices):
    """
    Compute worst peak-to-trough decline in a price series.

    Returns:
      (drawdown_percent, peak_date, trough_date)
    """

    # Need at least two points to define a drawdown.
    if prices.empty or len(prices) < 2:
        return (0.0, None, None)

    # Running peak and drawdown series relative to that peak.
    peak = prices.expanding(min_periods=1).max()
    dd = (prices - peak) / peak

    # Worst drawdown and associated trough timestamp.
    worst = dd.min()
    trough = dd.idxmin()
    # Peak date is the highest price observed before (or at) trough.
    peak_date = prices.loc[:trough].idxmax()

    # Date formatter supports pandas timestamps or plain values.
    fmt = lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
    return (round(worst * 100, 2), fmt(peak_date), fmt(trough))