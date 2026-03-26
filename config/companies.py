"""
Company Name to Ticker Symbol Mapping

Purpose: Convert natural language company names to stock ticker symbols. Enables
users to say "Apple" instead of "AAPL", "Tesla" instead of "TSLA", etc.

Structure:
  MAP: Dictionary of 300+ company names (keys) to tickers (values)
    - Keys are lowercase for case-insensitive matching
    - Multiple aliases per company (e.g., "facebook" and "meta" both → "META")
    - Global coverage: US, UK, EU, Japan, India, China, Korea, Taiwan, Australia, Brazil, Canada
    - Supports country-specific symbol formats (e.g., "7203.T" for Japan, "0700.HK" for Hong Kong)
  
  lookup(): Fuzzy matching algorithm
    1. Clean input: Strip whitespace, lowercase, remove noise words ("stock", "inc", etc.)
    2. Try exact match in MAP
    3. Try prefix match (if query >= 3 chars and key starts with query)
    4. Try substring match (if key >= 4 chars and appears in input)
    5. Return None if no match found
  
  _NOISE: Common suffixes to strip from company names before matching
"""

MAP = {
    # US TECHNOLOGY (MEGA-CAP)
    "apple": "AAPL", "apple inc": "AAPL",
    "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "nvidia": "NVDA", "meta": "META",
    "facebook": "META", "tesla": "TSLA", "netflix": "NFLX",
    "adobe": "ADBE", "salesforce": "CRM", "intel": "INTC",
    "amd": "AMD", "advanced micro devices": "AMD",
    "qualcomm": "QCOM", "broadcom": "AVGO", "cisco": "CSCO",
    "oracle": "ORCL", "ibm": "IBM", "paypal": "PYPL",
    "uber": "UBER", "airbnb": "ABNB", "spotify": "SPOT",
    "snap": "SNAP", "walmart": "WMT", "costco": "COST",
    "starbucks": "SBUX", "mcdonalds": "MCD", "nike": "NKE",
    "disney": "DIS", "coca cola": "KO", "pepsi": "PEP",
    "johnson johnson": "JNJ", "pfizer": "PFE", "moderna": "MRNA",
    "jpmorgan": "JPM", "jp morgan": "JPM", "goldman sachs": "GS",
    "bank of america": "BAC", "visa": "V", "mastercard": "MA",
    "berkshire": "BRK-B", "exxon": "XOM", "chevron": "CVX",
    "boeing": "BA", "caterpillar": "CAT", "honeywell": "HON",
    "ford": "F", "general motors": "GM", "palantir": "PLTR",
    "snowflake": "SNOW", "crowdstrike": "CRWD", "cloudflare": "NET",
    "datadog": "DDOG", "mongodb": "MDB", "zoom": "ZM",
    "shopify": "SHOP", "block": "SQ", "coinbase": "COIN",
    "robinhood": "HOOD", "rivian": "RIVN", "doordash": "DASH",
    "arm": "ARM", "asml": "ASML", "eli lilly": "LLY",
    "abbvie": "ABBV", "merck": "MRK", "amgen": "AMGN",
    "gilead": "GILD", "regeneron": "REGN", "vertex": "VRTX",
    "at&t": "T", "verizon": "VZ", "comcast": "CMCSA",
    "t mobile": "TMUS",
    
    # UK
    "vodafone": "VOD.L", "hsbc": "HSBA.L", "bp": "BP.L",
    "shell": "SHEL.L", "rio tinto": "RIO.L", "gsk": "GSK.L",
    "unilever": "ULVR.L", "barclays": "BARC.L",
    "rolls royce": "RR.L", "diageo": "DGE.L", "tesco": "TSCO.L",
    
    # GERMANY
    "sap": "SAP.DE", "siemens": "SIE.DE", "volkswagen": "VOW3.DE",
    "bmw": "BMW.DE", "mercedes": "MBG.DE", "adidas": "ADS.DE",
    "bayer": "BAYN.DE", "basf": "BAS.DE", "allianz": "ALV.DE",
    
    # FRANCE
    "lvmh": "MC.PA", "louis vuitton": "MC.PA", "total": "TTE.PA",
    "totalenergies": "TTE.PA", "loreal": "OR.PA", "sanofi": "SAN.PA",
    "airbus": "AIR.PA", "hermes": "RMS.PA",
    
    # JAPAN
    "toyota": "7203.T", "sony": "6758.T", "honda": "7267.T",
    "nintendo": "7974.T", "softbank": "9984.T", "keyence": "6861.T",
    "hitachi": "6501.T", "uniqlo": "9983.T",
    
    # INDIA (NSE - National Stock Exchange)
    "reliance": "RELIANCE.NS", "tcs": "TCS.NS",
    "tata consultancy": "TCS.NS", "infosys": "INFY.NS",
    "wipro": "WIPRO.NS", "hdfc bank": "HDFCBANK.NS", "hdfc": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS", "icici": "ICICIBANK.NS",
    "sbi": "SBIN.NS", "airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS", "bajaj finance": "BAJFINANCE.NS",
    "hindustan unilever": "HINDUNILVR.NS", "maruti": "MARUTI.NS",
    "tata motors": "TATAMOTORS.NS", "tata steel": "TATASTEEL.NS",
    "asian paints": "ASIANPAINT.NS", "sun pharma": "SUNPHARMA.NS",
    "adani": "ADANIENT.NS",
    
    # CHINA / HONG KONG
    "alibaba": "9988.HK", "tencent": "0700.HK", "byd": "1211.HK",
    "xiaomi": "1810.HK", "jd": "9618.HK", "meituan": "3690.HK",
    "baidu": "9888.HK", "nio": "NIO", "li auto": "LI", "xpeng": "XPEV",
    
    # SOUTH KOREA
    "samsung": "005930.KS", "sk hynix": "000660.KS",
    "hyundai": "005380.KS", "kia": "000270.KS",
    "naver": "035420.KS", "kakao": "035720.KS",
    
    # TAIWAN
    "tsmc": "2330.TW", "taiwan semiconductor": "2330.TW",
    "foxconn": "2317.TW", "mediatek": "2454.TW",
    
    # AUSTRALIA
    "bhp": "BHP.AX", "commonwealth bank": "CBA.AX", "csl": "CSL.AX",
    
    # BRAZIL
    "petrobras": "PETR4.SA", "vale": "VALE3.SA",
    "itau": "ITUB4.SA", "nubank": "NU",
    
    # CANADA
    "rbc": "RY.TO", "td bank": "TD.TO",
    
    # ETFS (Major indexes and commodities)
    "s&p 500": "SPY", "spy": "SPY", "sp500": "SPY",
    "nasdaq": "QQQ", "qqq": "QQQ",
    "dow jones": "DIA", "dow": "DIA",
    "gold": "GLD", "oil": "USO", "bitcoin etf": "IBIT",
    "ark": "ARKK",
}

# Common noise words to strip from company names before matching.
# Examples: "Apple Inc." → "Apple", "Microsoft Corp" → "Microsoft"
# This allows flexible matching even when users include common suffixes.
_NOISE = [
    " stock", " share", " shares", " price", " inc", " corp",
    " ltd", " limited", " plc", " ag", " sa", " nv",
    " co", " company", " group", "'s", ".", ",", "?",
]


def lookup(name):
    """
    Convert a company name to a stock ticker symbol using fuzzy matching.
    
    Algorithm:
      1. Clean the input: strip whitespace, lowercase, remove noise words
      2. Try exact match in MAP
      3. If not found, try prefix match (input >= 3 chars, key starts with input)
      4. If not found, try substring match (key >= 4 chars, key appears in input)
      5. Return None if no match found
    
    Examples:
      - lookup("Apple Inc") → "AAPL" (exact match after noise removal)
      - lookup("APPL") → "AAPL" (prefix match: "apple" starts with "appl")
      - lookup("my TSLA holdings") → "TSLA" (substring match: "tsla" in "my tsla holdings")
    
    Args:
        name: Company name or partial name (string)
    
    Returns:
        str: Ticker symbol (e.g., "AAPL"), or None if no match found
    """
    # Return None for empty or None input.
    if not name:
        return None
    
    # Step 1: Clean the input string.
    # Strip leading/trailing whitespace and convert to lowercase for case-insensitive matching.
    c = name.strip().lower()
    
    # Remove common noise words (suffixes like "Inc", "Corp", "Ltd").
    for n in _NOISE:
        c = c.replace(n, "")
    
    # Strip whitespace again after noise removal.
    c = c.strip()
    
    # If the cleaned string is now empty, return None.
    if not c:
        return None
    
    # Step 2: Try exact match. If the cleaned input exactly matches a key in MAP, return the ticker.
    if c in MAP:
        return MAP[c]
    
    # Step 3: Try prefix match. If the user typed "appl" and "apple" is a key, match it.
    # Only do this if user input is >= 3 characters (avoid matching "a" → many results).
    for key, ticker in MAP.items():
        if key.startswith(c) and len(c) >= 3:
            return ticker
    
    # Step 4: Try substring match. If a key appears anywhere in the user's input, match it.
    # Only do this if the key is >= 4 characters (avoid matching short keys like "a" or "t").
    # Useful for queries like "I want to buy some Tesla stock" → matches "tesla" in input.
    for key, ticker in MAP.items():
        if len(key) >= 4 and key in c:
            return ticker
    
    # Step 5: No match found at any level. Return None.
    return None
