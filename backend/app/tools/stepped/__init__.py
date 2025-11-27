"""
Stepped tools for agent reasoning at each checkpoint.

ACTIVE TOOLS:
- Reddit: search -> score -> extract
- TechCrunch: fetch -> select_articles -> extract_companies -> select_decision_makers
- FilterSellers: reusable seller/buyer filter

LEGACY TOOLS (moved to /backend/legacy/tools/stepped/):
- g2_tools.py (G2 strategy discontinued)
- upwork_tools.py (Upwork strategy discontinued)
"""

from .filter_sellers import FilterSellersTool
from .reddit_tools import RedditSearchSteppedTool, RedditScoreTool, RedditExtractTool
from .techcrunch_tools import (
    TechCrunchFetchTool,
    TechCrunchSelectArticlesTool,
    TechCrunchExtractCompaniesTool,
    TechCrunchSelectDecisionMakersTool
)

__all__ = [
    # Seller filter (reusable)
    "FilterSellersTool",

    # Reddit stepped tools
    "RedditSearchSteppedTool",
    "RedditScoreTool",
    "RedditExtractTool",

    # TechCrunch stepped tools (funding signals)
    "TechCrunchFetchTool",
    "TechCrunchSelectArticlesTool",
    "TechCrunchExtractCompaniesTool",
    "TechCrunchSelectDecisionMakersTool",
]
