import logging
import io
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from config import settings

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Raised when all data download strategies fail and no price data is available."""
    pass


class DataFetcher:
    """
    Fetches market data and fundamentals for a list of symbols.

    This class uses a layered strategy:
      1. Try Yahoo batch download (fastest)
      2. Retry Yahoo single-thread mode
      3. Retry symbol-by-symbol from Yahoo
      4. Fallback to Stooq when Yahoo is unavailable

    It also performs basic data quality checks and keeps a short in-memory cache.
    """

    def __init__(self, symbols):
        # Validate input early so downstream methods can assume symbols exist.
        if not symbols:
            raise ValueError("No symbols.")
        # Use unique symbols only to avoid duplicate network calls.
        self._symbols = list(set(symbols))
        # Cache stores last successful price DataFrame for short-lived reuse.
        self._cache = None
        self._cache_at = None
        # Issues stores validation warnings (missing data, extreme moves, etc.).
        self._issues = []

    @property
    def issues(self):
        # Return a copy so callers cannot mutate internal state.
        return list(self._issues)

    def prices(self):
        """Download price history using retries/fallbacks, validate it, and cache it."""
        # Reuse recent cached data to reduce API calls and improve response time.
        if self._fresh():
            logger.info("Using cached prices.")
            return self._cache

        logger.info("Downloading %d symbols...", len(self._symbols))
        # Proxy support allows users to run behind corporate or local proxy settings.
        proxy = (
            os.environ.get("YF_PROXY")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
        )

        # Attempt 1: Yahoo batch download with threads (fast path).
        raw = self._download_batch(proxy, threads=True)
        # Attempt 2: Same batch request but single-thread in case threaded mode fails.
        if raw.empty:
            logger.warning("Threaded batch download returned empty; retrying single-thread.")
            raw = self._download_batch(proxy, threads=False)
        # Attempt 3: Fetch each symbol one by one from Yahoo.
        if raw.empty:
            logger.warning("Batch download failed; retrying per-symbol fallback.")
            raw = self._download_per_symbol(proxy)
        # Attempt 4: Last fallback to Stooq if Yahoo is unavailable.
        if raw.empty:
            logger.warning("Yahoo fallback failed; trying Stooq fallback.")
            raw = self._download_stooq()

        # If all strategies fail, surface a clear actionable error.
        if raw.empty:
            raise FetchError(
                "Empty download from Yahoo Finance. Check internet/proxy settings and try again."
            )

        # Normalize single-symbol output to MultiIndex format used by downstream code.
        if len(self._symbols) == 1 and not isinstance(raw.columns, pd.MultiIndex):
            raw = pd.concat({self._symbols[0]: raw}, axis=1)

        # Validate data quality and record issues for diagnostics/UI reporting.
        self._validate(raw)
        self._cache = raw
        self._cache_at = datetime.now()

        logger.info(
            "Prices ready. %s to %s",
            raw.index[0].strftime("%Y-%m-%d"),
            raw.index[-1].strftime("%Y-%m-%d"),
        )
        return raw

    def _download_batch(self, proxy, threads):
        """Download all symbols in one Yahoo request."""
        try:
            return yf.download(
                tickers=self._symbols,
                period=settings.PRICE_PERIOD,
                interval=settings.PRICE_INTERVAL,
                group_by="ticker",
                auto_adjust=True,
                threads=threads,
                progress=False,
                proxy=proxy,
            )
        except Exception as e:
            # Keep moving through fallback chain instead of failing the whole pipeline.
            logger.warning("Batch download failed (threads=%s): %s", threads, e)
            if self._cache is not None:
                # If we have stale cache, prefer degraded data over total failure.
                logger.warning("Using stale in-memory cache after batch failure.")
                return self._cache
            return pd.DataFrame()

    def _download_per_symbol(self, proxy):
        """Fallback: download each symbol individually from Yahoo."""
        out = {}
        for sym in self._symbols:
            try:
                df = yf.Ticker(sym).history(
                    period=settings.PRICE_PERIOD,
                    interval=settings.PRICE_INTERVAL,
                    auto_adjust=True,
                    proxy=proxy,
                )
                if df is not None and not df.empty:
                    out[sym] = df
                else:
                    logger.warning("%s fallback history returned empty.", sym)
            except Exception as e:
                logger.warning("%s fallback history failed: %s", sym, e)
            # Small delay to reduce chance of rate limits.
            time.sleep(0.1)

        if not out:
            return pd.DataFrame()
        return pd.concat(out, axis=1)

    def _download_stooq(self):
        """Last-resort fallback: download daily CSV data from Stooq."""
        out = {}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        timeout = 20

        for sym in self._symbols:
            try:
                code = self._to_stooq_symbol(sym)
                url = "https://stooq.com/q/d/l/?s={}&i=d".format(code)
                r = requests.get(url, headers=headers, timeout=timeout)
                r.raise_for_status()
                txt = (r.text or "").strip()
                if not txt or "No data" in txt:
                    logger.warning("%s Stooq returned no data.", sym)
                    continue
                df = pd.read_csv(
                    io.StringIO(txt),
                    parse_dates=["Date"],
                )
                if df.empty:
                    continue
                df = df.rename(columns={
                    "Date": "Date",
                    "Open": "Open",
                    "High": "High",
                    "Low": "Low",
                    "Close": "Close",
                    "Volume": "Volume",
                })
                df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
                df = df.dropna(subset=["Date", "Close"]).set_index("Date").sort_index()
                out[sym] = df
            except Exception as e:
                logger.warning("%s Stooq fallback failed: %s", sym, e)

        if not out:
            return pd.DataFrame()
        return pd.concat(out, axis=1)

    def _to_stooq_symbol(self, sym):
        """Convert standard ticker to Stooq naming convention."""
        s = (sym or "").strip().lower()
        if "." in s:
            return s
        return s + ".us"

    def fundamentals(self):
        """Fetch company metadata used to enrich analysis output."""
        logger.info("Fetching fundamentals...")
        rows, failed = [], []
        for sym in self._symbols:
            try:
                info = yf.Ticker(sym).info or {}
                time.sleep(0.15)
                rows.append({
                    "symbol": sym,
                    "name": info.get("shortName", sym),
                    "sector": info.get("sector", "Unknown"),
                    "industry": info.get("industry", "Unknown"),
                    "currency": info.get("currency", ""),
                    "market_cap": info.get("marketCap", np.nan),
                    "pe_ratio": info.get("trailingPE", np.nan),
                    "forward_pe": info.get("forwardPE", np.nan),
                    "dividend_yield": info.get("dividendYield", 0) or 0,
                    "beta": info.get("beta", np.nan),
                    "current_price": info.get(
                        "currentPrice", info.get("regularMarketPrice", np.nan)
                    ),
                })
            except Exception as e:
                logger.warning("%s fundamentals failed: %s", sym, e)
                failed.append(sym)
        logger.info("Fundamentals: %d ok, %d failed.", len(rows), len(failed))
        return pd.DataFrame(rows)

    def stock(self, symbol, price_data):
        """Return cleaned price history for one symbol if minimum data is available."""
        try:
            if symbol not in price_data.columns.get_level_values(0):
                return None
            df = price_data[symbol].copy().dropna(subset=["Close"])
            return df if len(df) >= settings.MIN_DAYS else None
        except Exception:
            return None

    def _validate(self, df):
        """Run quality checks across all symbols and collect validation issues."""
        self._issues = []
        for sym in self._symbols:
            err = self._check(df, sym)
            if err:
                self._issues.append("{}: {}".format(sym, err))
        if self._issues:
            for i in self._issues[:20]:
                logger.info("  %s", i)

    def _check(self, df, sym):
        """Validate one symbol: presence, missingness, sample size, and outlier moves."""
        try:
            if sym not in df.columns.get_level_values(0):
                return "No data"
            close = df[sym]["Close"]
            if close.isna().mean() > settings.MAX_NAN:
                return "{:.0%} missing".format(close.isna().mean())
            if close.dropna().shape[0] < settings.MIN_DAYS:
                return "Only {} days".format(close.dropna().shape[0])
            bad = (close.dropna() <= 0).sum()
            if bad:
                self._issues.append("{}: {} bad prices".format(sym, bad))
            extreme = close.pct_change().dropna()
            extreme = extreme[extreme.abs() > settings.EXTREME_MOVE]
            if len(extreme) > 2:
                self._issues.append("{}: {} extreme moves".format(sym, len(extreme)))
            return None
        except Exception as e:
            return str(e)

    def _fresh(self):
        """Return True when in-memory cache is still within configured freshness window."""
        if self._cache is None or self._cache_at is None:
            return False
        return datetime.now() - self._cache_at < timedelta(minutes=settings.CACHE_MINUTES)