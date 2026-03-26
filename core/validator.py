"""
Input validation helpers for stock symbols.

This module ensures user input is safe and well-formed before analysis:
    1. Validate one symbol (`clean_symbol`)
    2. Validate list of symbols (`clean_symbols`)
    3. Reject unsafe characters and invalid formats
"""

import logging
import re
from config import settings

logger = logging.getLogger(__name__)

# Allowed symbol format examples:
# - AAPL
# - MSFT
# - 7203.T
# - RELIANCE.NS
_PAT = re.compile(r"^[A-Za-z0-9]{1,10}(\.[A-Za-z]{1,4})?$")

# Characters blocked for security/shell-injection hardening.
_BAD = re.compile(r"[;&|`$(){}[\]!<>\\'\"]")


class ValidationError(Exception):
    """Validation exception carrying optional field name for API error mapping."""

    def __init__(self, message, field=None):
        self.field = field
        super().__init__(message)


def clean_symbol(s):
    """Normalize and validate a single symbol string."""

    # STEP 1: Basic type/empty checks.
    if not s or not isinstance(s, str):
        raise ValidationError("Symbol empty.", "symbol")

    # STEP 2: Canonical form used throughout app (trim + uppercase).
    c = s.strip().upper()

    # STEP 3: Enforce configured max length.
    if len(c) > settings.SYMBOL_MAX_LEN:
        raise ValidationError("Symbol too long: " + c, "symbol")

    # STEP 4: Security filter for unsafe characters.
    if _BAD.search(c):
        logger.warning("SECURITY: bad input: %s", s[:50])
        raise ValidationError("Invalid characters.", "symbol")

    # STEP 5: Format check against ticker regex.
    if not _PAT.match(c):
        raise ValidationError("Invalid format: " + c, "symbol")

    # Valid symbol in canonical form.
    return c


def clean_symbols(raw_list):
    """
    Validate a list of symbols.

    Returns:
      (ok, bad)
      - ok: validated unique symbols
      - bad: rejected raw entries
    """

    # STEP 1: List-level guard checks.
    if not raw_list:
        raise ValidationError("No symbols.", "symbols")
    if len(raw_list) > settings.MAX_SYMBOLS:
        raise ValidationError(
            "Too many: {}. Max: {}.".format(len(raw_list), settings.MAX_SYMBOLS),
            "symbols",
        )

    # STEP 2: Validate each symbol and deduplicate while preserving input order.
    ok, bad = [], []
    seen = set()
    for r in raw_list:
        try:
            c = clean_symbol(r)
            if c not in seen:
                ok.append(c)
                seen.add(c)
        except ValidationError:
            # Keep raw rejected value for user feedback/logging.
            bad.append(r)

    # STEP 3: If nothing valid remains, fail fast.
    if not ok:
        raise ValidationError("No valid symbols.", "symbols")

    # Log a short rejection summary (first few only).
    if bad:
        logger.info("Rejected %d: %s", len(bad), bad[:10])
    return ok, bad