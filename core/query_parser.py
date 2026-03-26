"""
Natural-language query parser.

This module converts user text into structured analysis input:
    1. Detects direct ticker lists (e.g., "AAPL MSFT")
    2. Extracts tickers from free-form text
    3. Maps company names to tickers using configured company map
    4. Detects user intent (compare vs investment question vs analyze)
    5. Captures unmatched fragments for debugging/UX hints
"""

import logging
import re
from config import companies
from config import settings

logger = logging.getLogger(__name__)

# Matches common ticker styles:
# - US style (AAPL, MSFT, TSLA)
# - Exchange-suffixed tickers (7203.T, RELIANCE.NS)
_TICKER_RE = re.compile(
    r"\b([A-Z]{1,5}(?:\.[A-Z]{1,4})?)\b"
    r"|"
    r"\b(\d{4,6}\.[A-Z]{1,4})\b"
)

_COMPARE = {"compare", "versus", "vs", "against", "between", "or", "better"}
_INTENT = {"buy", "sell", "invest", "should", "worth", "safe", "recommend"}
# Words ignored when inferring symbols from natural language.
_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "do", "does", "did", "will", "would", "could", "should",
    "can", "may", "might", "i", "me", "my", "we", "you", "your",
    "it", "its", "they", "them", "this", "that", "what", "which",
    "how", "why", "when", "where", "and", "but", "or", "not", "no",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "stock", "stocks", "share", "shares", "price", "market",
    "trading", "invest", "help", "understand", "explain", "tell",
    "please", "thanks", "hi", "hello", "want", "need", "like",
    "know", "look", "looking", "good", "bad", "best", "top",
    "right", "now", "today", "going", "doing", "performing",
    "about", "think", "up", "down",
}


class Parsed:
    """Container for parser output returned to API and frontend."""

    def __init__(self):
        self.symbols = []
        self.intent = "analyze"
        self.query = ""
        self.companies = []
        self.unmatched = []
        self.is_nl = False

    def to_dict(self):
        """Serialize parsed output as plain dict for API responses."""
        return {
            "symbols": self.symbols,
            "intent": self.intent,
            "original_query": self.query,
            "parsed_companies": self.companies,
            "unparsed_fragments": self.unmatched,
            "is_natural_language": self.is_nl,
        }


def parse(raw):
    """Parse raw user text into symbols, intent, and unmatched fragments."""

    r = Parsed()
    # Gracefully handle empty or non-string input.
    if not raw or not isinstance(raw, str):
        return r

    # Normalize and cap length to avoid excessive processing.
    text = raw.strip()[:settings.QUERY_MAX_LEN]
    r.query = text

    # STEP 1: Fast path for direct ticker list input.
    if _is_ticker_list(text):
        r.is_nl = False
        for t in _split_tickers(text):
            r.symbols.append(t)
            r.companies.append({"input": t, "ticker": t, "method": "direct"})
        return r

    # STEP 2: Natural-language mode.
    r.is_nl = True
    r.intent = _intent(text)

    seen = set()
    # STEP 3: Extract explicit ticker-like tokens directly from text.
    for m in _TICKER_RE.finditer(text):
        t = m.group(1) or m.group(2)
        if t and len(t) >= 2 and t.lower() not in _STOP and t not in seen:
            seen.add(t)
            r.symbols.append(t)
            r.companies.append({"input": t, "ticker": t, "method": "ticker"})

    # STEP 4: Match known company names and map them to configured tickers.
    lower = text.lower()
    # Longest names first to reduce partial/short-name collisions.
    sorted_names = sorted(companies.MAP.keys(), key=len, reverse=True)
    matched_spans = []
    for name in sorted_names:
        idx = lower.find(name)
        if idx == -1:
            continue
        end = idx + len(name)
        overlap = any(idx < er and end > sr for sr, er in matched_spans)
        if overlap:
            continue
        ticker = companies.MAP[name]
        if ticker not in seen:
            seen.add(ticker)
            r.symbols.append(ticker)
            r.companies.append({"input": name, "ticker": ticker, "method": "name"})
        matched_spans.append((idx, end))

    # STEP 5: Build unmatched fragments after removing recognized names + stop words.
    # Useful for diagnostics and UI hints about unparsed query parts.
    remain = lower
    for _, _, name in [(None, None, c["input"]) for c in r.companies]:
        remain = remain.replace(name.lower(), "")
    for w in _STOP:
        remain = re.sub(r"\b" + w + r"\b", "", remain)
    remain = re.sub(r"[^a-z0-9\s]", "", remain).strip()
    r.unmatched = [w for w in remain.split() if len(w) > 2]

    logger.info("Parsed '%s' -> %s (intent=%s)", text[:60], r.symbols, r.intent)
    return r


def _is_ticker_list(text):
    """Return True when input looks like a pure ticker list, not natural language."""
    parts = re.split(r"[,\s]+", text.strip())
    parts = [p for p in parts if p]
    if not parts:
        return False
    return all(re.match(r"^[A-Z0-9]{1,10}(\.[A-Z]{1,4})?$", p) for p in parts)


def _split_tickers(text):
    """Split ticker list text, normalize case, and remove duplicates while preserving order."""
    parts = re.split(r"[,\s]+", text.strip())
    seen = set()
    out = []
    for p in parts:
        c = p.strip().upper()
        if c and c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _intent(text):
    """Infer high-level user intent from keyword presence."""
    low = text.lower()
    # Compare intent has priority if compare keywords are present.
    for w in _COMPARE:
        if w in low:
            return "compare"
    # Investment question intent for recommendation-like wording.
    for w in _INTENT:
        if w in low:
            return "investment_question"
    return "analyze"