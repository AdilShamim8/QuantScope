"""
Stock Exchange Configuration

Purpose: Define global stock exchanges, their trading metadata, and helper functions
for determining market-specific properties from ticker symbols.

Structure:
  EXCHANGES: Dictionary of 30+ exchanges mapping exchange codes to metadata:
    - name: Human-readable exchange name (e.g., "NYSE/NASDAQ", "Tokyo")
    - suffix: Ticker suffix for that exchange (e.g., ".T" for Tokyo, ".L" for London)
    - currency: Trading currency (e.g., "USD", "JPY", "GBP")
    - tz: Timezone (IANA format) for market hours calculation
    - days: Average trading days per year (accounts for holidays)
    - stale: Days before data considered stale (varies by exchange update frequency)
  
  Helper functions:
    - exchange_for(symbol): Determine exchange from ticker suffix
    - trading_days(symbol): Get trading days/year for a symbol's exchange
    - currency_for(symbol): Get trading currency for a symbol's exchange

Why? Each exchange has different trading days, holidays, currencies, and data
freshness requirements. This centralizes that metadata for use by data_fetcher,
indicators (annualized volatility), and reports.
"""

# GLOBAL EXCHANGES METADATA
# ============================================================================
# Structure for each exchange:
#   "CODES": {
#       "name": "Exchange Name",          # Human-readable name
#       "suffix": ".CODE",                # Suffix appended to tickers (e.g., AAPL vs AAPL.L)
#       "currency": "XXX",                # ISO 4217 currency code
#       "tz": "Timezone/Name",            # IANA timezone for market hours
#       "days": 252,                      # Average trading days per year
#       "stale": 4,                       # Data considered stale after N days
#   }
#
# Note: Two-letter codes (US, TO, L, PA) match yfinance/Stooq conventions when
# combined with ticker symbols (e.g., AAPL + US = AAPL, AAPL + L = AAPL.L).

EXCHANGES = {
    # AMERICAS
    # --------
    # US: NYSE and NASDAQ (no suffix needed; default exchange)
    "US": {"name": "NYSE/NASDAQ", "suffix": "", "currency": "USD",
           "tz": "America/New_York", "days": 252, "stale": 4},
    "TO": {"name": "Toronto", "suffix": ".TO", "currency": "CAD",
           "tz": "America/Toronto", "days": 250, "stale": 4},
    
    # EUROPE
    # ------
    # UK: London Stock Exchange
    "L":  {"name": "London", "suffix": ".L", "currency": "GBP",
           "tz": "Europe/London", "days": 253, "stale": 4},
    # France: Euronext Paris
    "PA": {"name": "Euronext Paris", "suffix": ".PA", "currency": "EUR",
           "tz": "Europe/Paris", "days": 253, "stale": 4},
    # Germany: XETRA Frankfurt
    "DE": {"name": "XETRA Frankfurt", "suffix": ".DE", "currency": "EUR",
           "tz": "Europe/Berlin", "days": 253, "stale": 4},
    # Netherlands: Euronext Amsterdam
    "AS": {"name": "Euronext Amsterdam", "suffix": ".AS", "currency": "EUR",
           "tz": "Europe/Amsterdam", "days": 253, "stale": 4},
    # Italy: Borsa Italiana
    "MI": {"name": "Borsa Italiana", "suffix": ".MI", "currency": "EUR",
           "tz": "Europe/Rome", "days": 252, "stale": 4},
    # Spain: Bolsa de Madrid
    "MC": {"name": "Bolsa de Madrid", "suffix": ".MC", "currency": "EUR",
           "tz": "Europe/Madrid", "days": 252, "stale": 4},
    # Switzerland: SIX Swiss Exchange
    "SW": {"name": "SIX Swiss", "suffix": ".SW", "currency": "CHF",
           "tz": "Europe/Zurich", "days": 252, "stale": 4},
    # Sweden: Nasdaq Stockholm
    "ST": {"name": "Nasdaq Stockholm", "suffix": ".ST", "currency": "SEK",
           "tz": "Europe/Stockholm", "days": 251, "stale": 4},
    # Norway: Oslo Bors
    "OL": {"name": "Oslo Bors", "suffix": ".OL", "currency": "NOK",
           "tz": "Europe/Oslo", "days": 250, "stale": 4},
    # Finland: Nasdaq Helsinki
    "HE": {"name": "Nasdaq Helsinki", "suffix": ".HE", "currency": "EUR",
           "tz": "Europe/Helsinki", "days": 251, "stale": 4},
    # Denmark: Nasdaq Copenhagen
    "CO": {"name": "Nasdaq Copenhagen", "suffix": ".CO", "currency": "DKK",
           "tz": "Europe/Copenhagen", "days": 251, "stale": 4},
    
    # ASIA-PACIFIC
    # ------------
    # Japan: Tokyo Stock Exchange (TSE)
    "T":  {"name": "Tokyo", "suffix": ".T", "currency": "JPY",
           "tz": "Asia/Tokyo", "days": 245, "stale": 5},
    # Hong Kong: Hong Kong Stock Exchange (HKEX)
    "HK": {"name": "Hong Kong", "suffix": ".HK", "currency": "HKD",
           "tz": "Asia/Hong_Kong", "days": 247, "stale": 5},
    # China: Shanghai Stock Exchange (SSE)
    "SS": {"name": "Shanghai", "suffix": ".SS", "currency": "CNY",
           "tz": "Asia/Shanghai", "days": 244, "stale": 5},
    # China: Shenzhen Stock Exchange (SZSE)
    "SZ": {"name": "Shenzhen", "suffix": ".SZ", "currency": "CNY",
           "tz": "Asia/Shanghai", "days": 244, "stale": 5},
    # South Korea: Korea Exchange (KRX) KOSPI
    "KS": {"name": "Korea KOSPI", "suffix": ".KS", "currency": "KRW",
           "tz": "Asia/Seoul", "days": 248, "stale": 5},
    # Taiwan: Taiwan Stock Exchange (TWSE)
    "TW": {"name": "Taiwan", "suffix": ".TW", "currency": "TWD",
           "tz": "Asia/Taipei", "days": 246, "stale": 5},
    # Singapore: Singapore Exchange (SGX)
    "SI": {"name": "Singapore", "suffix": ".SI", "currency": "SGD",
           "tz": "Asia/Singapore", "days": 248, "stale": 5},
    # India: National Stock Exchange (NSE)
    "NS": {"name": "NSE India", "suffix": ".NS", "currency": "INR",
           "tz": "Asia/Kolkata", "days": 248, "stale": 5},
    # India: Bombay Stock Exchange (BSE)
    "BO": {"name": "BSE India", "suffix": ".BO", "currency": "INR",
           "tz": "Asia/Kolkata", "days": 248, "stale": 5},
    # Indonesia: Indonesia Stock Exchange (IDX)
    "JK": {"name": "Jakarta", "suffix": ".JK", "currency": "IDR",
           "tz": "Asia/Jakarta", "days": 240, "stale": 5},
    # Thailand: Stock Exchange of Thailand (SET)
    "BK": {"name": "Thailand", "suffix": ".BK", "currency": "THB",
           "tz": "Asia/Bangkok", "days": 244, "stale": 5},
    # Australia: Australian Securities Exchange (ASX)
    "AX": {"name": "ASX Australia", "suffix": ".AX", "currency": "AUD",
           "tz": "Australia/Sydney", "days": 251, "stale": 4},
    # New Zealand: NZX Main Board
    "NZ": {"name": "NZX", "suffix": ".NZ", "currency": "NZD",
           "tz": "Pacific/Auckland", "days": 249, "stale": 5},
    
    # MIDDLE EAST & AFRICA
    # --------------------
    # Israel: Tel Aviv Stock Exchange (TASE)
    "TA": {"name": "Tel Aviv", "suffix": ".TA", "currency": "ILS",
           "tz": "Asia/Jerusalem", "days": 245, "stale": 5},
    # Saudi Arabia: Saudi Tadawul Exchange
    "SR": {"name": "Saudi Tadawul", "suffix": ".SR", "currency": "SAR",
           "tz": "Asia/Riyadh", "days": 245, "stale": 5},
    # South Africa: Johannesburg Stock Exchange (JSE)
    "JO": {"name": "Johannesburg", "suffix": ".JO", "currency": "ZAR",
           "tz": "Africa/Johannesburg", "days": 250, "stale": 4},
    
    # SOUTH AMERICA
    # -------
    # Brazil: B3 (Bolsa de Valores de São Paulo)
    "SA": {"name": "B3 Brazil", "suffix": ".SA", "currency": "BRL",
           "tz": "America/Sao_Paulo", "days": 249, "stale": 5},
    # Mexico: Mexican Stock Exchange (BMV)
    "MX": {"name": "Mexico", "suffix": ".MX", "currency": "MXN",
           "tz": "America/Mexico_City", "days": 247, "stale": 5},
}


def exchange_for(symbol):
    """
    Determine the exchange metadata for a given stock symbol.
    
    Logic:
      1. If symbol contains a dot (e.g., "AAPL.L"), extract the suffix after the dot
      2. Search EXCHANGES for a matching suffix
      3. If found, return that exchange's metadata
      4. If no dot or no match found, default to US (NYSE/NASDAQ)
    
    Examples:
      - exchange_for("AAPL") → EXCHANGES["US"] (no suffix, default to US)
      - exchange_for("AAPL.L") → EXCHANGES["L"] (London suffix found)
      - exchange_for("0700.HK") → EXCHANGES["HK"] (Hong Kong suffix found)
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "AAPL.L", "0700.HK")
    
    Returns:
        dict: Exchange metadata (name, currency, timezone, trading days, etc.)
    """
    # Step 1: Check if symbol has a dot (suffix indicator).
    if "." in symbol:
        # Extract the suffix: "AAPL.L" → ".L", then "L" for lookups.
        suffix = "." + symbol.rsplit(".", 1)[1]
        
        # Step 2: Search for an exchange matching this suffix.
        for code, ex in EXCHANGES.items():
            if ex["suffix"] == suffix:
                return ex
    
    # Step 3: No dot or no match found; default to US (NYSE/NASDAQ).
    # This handles symbols like "AAPL", "MSFT", "TSLA" with no exchange suffix.
    return EXCHANGES["US"]


def trading_days(symbol):
    """
    Get the average trading days per year for a symbol's exchange.
    
    Used for annualizing volatility and Sharpe ratio calculations.
    Example: If a stock trades on NYSE (252 days/year), daily volatility
    of 1% annualizes to 1% * sqrt(252) ≈ 15.87%.
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        int: Average trading days per year (typically 240-253)
    """
    return exchange_for(symbol)["days"]


def currency_for(symbol):
    """
    Get the trading currency for a symbol's exchange.
    
    Used for displaying prices and reports in the appropriate currency.
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        str: ISO 4217 currency code (e.g., "USD", "GBP", "JPY")
    """
    return exchange_for(symbol)["currency"]
