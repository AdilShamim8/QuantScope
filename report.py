"""
Report/export utilities.

This module writes analysis output to disk in two formats:
    1. CSV for spreadsheet-friendly tabular review
    2. JSON for structured machine-readable consumption
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from config.legal import disclaimer

logger = logging.getLogger(__name__)

# Column order for CSV export. Keep stable so downstream tools can rely on layout.
FIELDS = [
    "symbol", "sector", "currency", "price", "composite_score",
    "rsi", "macd_histogram", "bb_position", "atr", "atr_pct",
    "sma_50", "sma_200", "volume_ratio",
    "return_1d", "return_1w", "return_1m", "return_3m", "return_ytd",
    "volatility_annual_pct", "sharpe_ratio", "max_drawdown_pct",
    "shares", "position_value", "position_pct",
    "stop_loss_price", "risk_dollars",
    "signal_rsi", "signal_macd", "signal_trend", "signal_bollinger",
]


def save_csv(analyses, path):
    """Save normalized analysis rows to CSV with fixed column order."""

    # Nothing to write if analysis list is empty.
    if not analyses:
        return

    # Ensure output directory exists before opening file.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build flat row objects from nested analysis structures.
    rows = []
    for a in analyses:
        # Nested sections from pipeline output.
        s = a.get("signals", {})
        r = a.get("returns", {})
        k = a.get("risk", {})

        # Flatten nested values into one tabular record per symbol.
        rows.append({
            "symbol": a.get("symbol"), "sector": a.get("sector"),
            "currency": a.get("currency"), "price": a.get("price"),
            "composite_score": a.get("composite_score"),
            "rsi": a.get("rsi"), "macd_histogram": a.get("macd_histogram"),
            "bb_position": a.get("bb_position"), "atr": a.get("atr"),
            "atr_pct": a.get("atr_pct"), "sma_50": a.get("sma_50"),
            "sma_200": a.get("sma_200"), "volume_ratio": a.get("volume_ratio"),
            "return_1d": r.get("1d"), "return_1w": r.get("1w"),
            "return_1m": r.get("1m"), "return_3m": r.get("3m"),
            "return_ytd": r.get("ytd"),
            "volatility_annual_pct": a.get("volatility_annual_pct"),
            "sharpe_ratio": a.get("sharpe_ratio"),
            "max_drawdown_pct": a.get("max_drawdown_pct"),
            "shares": k.get("shares"), "position_value": k.get("position_value"),
            "position_pct": k.get("position_pct"),
            "stop_loss_price": k.get("stop_loss_price"),
            "risk_dollars": k.get("risk_dollars"),
            "signal_rsi": s.get("rsi"), "signal_macd": s.get("macd"),
            "signal_trend": s.get("trend"), "signal_bollinger": s.get("bollinger"),
        })

    # Write CSV file with header + data rows.
    with open(str(path), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    logger.info("CSV: %s (%d rows)", path, len(rows))


def save_json(analyses, path):
    """Save full analysis payload as JSON including metadata and disclaimer."""

    # Ensure output directory exists before writing.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve complete nested result structure for API-like consumption.
    out = {
        "generated": datetime.now().isoformat(),
        "count": len(analyses),
        "disclaimer": disclaimer(False),
        "results": analyses,
    }

    # Write pretty-printed JSON for readability.
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    logger.info("JSON: %s", path)