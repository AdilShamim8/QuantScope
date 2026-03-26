"""
QuantScope Analysis Pipeline

This file contains the Pipeline class which is the heart of the analysis workflow.
It takes stock symbols and runs them through all analysis steps:
  1. Fetch market and fundamental data
  2. Calculate technical indicators
  3. Compute risk metrics
  4. Generate AI-powered explanations
  5. Save results to CSV/JSON

The pipeline orchestrates all modules (data fetcher, indicators, risk, LLM) 
to produce final ranked stock insights.
"""

import logging
import time
from config import settings
from config.markets import currency_for
from core.data_fetcher import DataFetcher
from core import indicators
from core import risk
from llm import explainer
import report

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Orchestrates the complete analysis workflow for a batch of stock symbols.
    
    This class coordinates:
      - Data fetching (prices, fundamentals)
      - Technical analysis calculations
      - Risk assessment
      - LLM-powered insights
      - Report generation
    """

    def __init__(self, symbols, portfolio_value=10000.0, user_query=""):
        """
        Initialize the pipeline with analysis parameters.
        
        Args:
          symbols: List of stock tickers (e.g., ['AAPL', 'MSFT'])
          portfolio_value: Total investment amount in USD
          user_query: Optional natural language context (e.g., "growth stocks")
        """
        self._symbols = symbols
        self._pv = portfolio_value
        self._query = user_query
        self._results = []  # Will store final analysis for each stock
        self.portfolio_summary = ""  # Text summary of portfolio recommendation

    def run(self):
        """
        Execute the complete analysis pipeline.
        
        What happens:
          1. Fetch all market prices and fundamental data
          2. Process each stock through indicators and risk calculations
          3. Generate AI explanations for top 5 stocks
          4. Save results to files
          5. Return sorted results
        
        Returns: List of analyzed stock dicts, sorted by composite_score (best first)
        """
        t0 = time.time()
        logger.info("Pipeline: %d symbols, $%s", len(self._symbols),
                     "{:,.0f}".format(self._pv))

        # STEP 1: Fetch raw market data from data sources (Yahoo Finance, Stooq, etc.)
        # This includes daily prices, volume, and company fundamentals (sector, currency)
        f = DataFetcher(self._symbols)
        pd_ = f.prices()  # Get all price history for all symbols
        fund = f.fundamentals()  # Get company metadata (sector, currency, etc.)
        
        # Convert fundamentals DataFrame into a dict for faster lookup later
        fm = {}
        if not fund.empty:
            fm = {r["symbol"]: r.to_dict() for _, r in fund.iterrows()}

        # STEP 2: Process each stock individually through the analysis pipeline
        # For each stock, we calculate technical indicators, risk metrics, and scoring
        self._results = []
        skip = 0
        for sym in self._symbols:
            # Get the daily price data for this specific stock
            df = f.stock(sym, pd_)
            if df is None:
                # Skip if data fetch failed for this stock
                skip += 1; continue
            
            # Calculate all technical indicators (RSI, MACD, Bollinger, ATR, etc.)
            # Returns a dict with all computed metrics
            a = indicators.analyze(sym, df)
            if a is None:
                # Skip if indicators could not be computed
                skip += 1; continue
            # Enrich analysis with company metadata (sector, currency)
            fd = fm.get(sym, {})
            a["currency"] = fd.get("currency") or currency_for(sym)
            a["sector"] = fd.get("sector", "Unknown")
            
            # Calculate position sizing: how many shares to buy and where to put stop loss
            # This uses ATR (volatility) to determine risk-appropriate sizing
            a["risk"] = risk.position_size(self._pv, a["price"], a["atr"])
            
            # Calculate risk-adjusted return metric (Sharpe ratio)
            # Higher = better risk-adjusted performance
            dr = df["Close"].pct_change().dropna()
            a["sharpe_ratio"] = risk.sharpe(dr, sym)
            
            # Calculate maximum drawdown: worst peak-to-trough decline in price history
            # Used to assess volatility risk
            dd, ds, de = risk.max_drawdown(df["Close"].dropna())
            a["max_drawdown_pct"] = dd
            
            # Add completed stock analysis to results list
            self._results.append(a)

        # STEP 3: Rank stocks by composite score (best prospects first)
        # Composite score blends momentum, trend, volatility into one comparable number
        self._results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

        # STEP 4: Generate AI explanations for the top 5 stocks
        # The LLM explains why each stock is recommended given its metrics
        for a in self._results[:5]:
            a["explanation"] = explainer.explain(
                a, a.get("risk", {}), self._query)

        # Generate a high-level portfolio recommendation summary
        self.portfolio_summary = explainer.portfolio_summary(self._results)

        # STEP 5: Save all results to output files for archival and reporting
        settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        report.save_csv(self._results, settings.OUTPUT_DIR / "latest.csv")
        report.save_json(self._results, settings.OUTPUT_DIR / "latest.json")

        # Log completion: how many stocks were processed and total time
        logger.info("Done: %d/%d in %.1fs", len(self._results),
                     len(self._symbols), time.time() - t0)
        
        # Return final ranked list (best prospect first)
        return self._results