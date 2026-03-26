"""
Legal Disclaimers & Compliance Notices

Purpose: Centralize all legal and regulatory disclaimer text that must appear
in the user interface. This ensures consistent messaging across all endpoints
and pages, and provides clear communication that QuantScope is for analysis
only—not financial advice or professional recommendations.

Components:
  _EN: Main disclaimer explaining that QuantScope is educational/informational,
       not financial advice, and disclaiming liability for losses.
  
  _REG: Regulatory notice clarifying that QuantScope is not registered as an
         investment advisor and does not provide personalized recommendations.
  
  disclaimer(): Function to assemble and return the appropriate disclaimer text
                based on context (with or without regulatory notice).

Why? Financial instruments are heavily regulated. Users must understand that:
  - QuantScope provides data analysis, not advice
  - They must consult licensed advisors before investing
  - Past performance ≠ future results
  - The creators cannot be held liable for financial losses
  - The system is not investment advice or a fiduciary service
"""

# Primary Disclaimer: Educational Purpose & Liability Waiver
# Communicates:
#   1. This is educational/informational use only
#   2. NOT financial advice (critical legal protection)
#   3. Investment risks exist including total loss
#   4. Historical data does not predict future
#   5. Users should consult professionals
#   6. Creators disclaim liability for losses
_EN = (
    "DISCLAIMER: This tool provides quantitative data analysis for "
    "educational and informational purposes only. It does NOT constitute "
    "financial advice, investment advice, or any other professional advice. "
    "All investments carry risk including total loss. Past performance does "
    "not guarantee future results. Consult a licensed financial advisor "
    "before making investment decisions. The creators accept NO liability "
    "for financial losses."
)

# Regulatory Notice: Non-Advisor Status
# Clarifies:
#   1. Not registered with SEC or other regulators as an investment advisor
#   2. Does not provide personalized recommendations (generic analysis only)
#   3. No fiduciary duty to users
_REG = (
    "REGULATORY NOTICE: This system is not registered as an investment "
    "advisor with any regulatory authority. It does not provide "
    "personalized recommendations."
)


def disclaimer(include_regulatory=True):
    """
    Assemble and return the appropriate disclaimer text.
    
    Combines the educational disclaimer with optional regulatory notice.
    Called by:
      - page_routes.py: /about endpoint (include_regulatory=True)
      - api_routes.py: /health endpoint (include_regulatory=True)
      - Other endpoints needing compliance messaging
    
    Args:
        include_regulatory: If True (default), include regulatory notice.
                           If False, return only educational disclaimer.
    
    Returns:
        str: Full disclaimer text with paragraph separations.
    
    Example:
        >>> text = disclaimer()
        >>> # Returns: "DISCLAIMER: This tool provides... \n\n REGULATORY NOTICE: ..."
        
        >>> text = disclaimer(include_regulatory=False)
        >>> # Returns: "DISCLAIMER: This tool provides..."
    """
    # Start with the educational disclaimer (always included).
    parts = [_EN]
    
    # Optionally append the regulatory notice (usually included unless specifically omitted).
    if include_regulatory:
        parts.append(_REG)
    
    # Join all parts with double newlines for clear paragraph separation.
    return "\n\n".join(parts)
