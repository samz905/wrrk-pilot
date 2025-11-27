"""
Tools for Sales Prospecting.

This module provides atomic tools that wrap various APIs for:
- LinkedIn (posts, profiles, employees, comments) - Apify
- Reddit (search and lead extraction) - Apify
- Twitter/X (search) - Apify
- Google (SERP and website scraping) - CrewAI native tools
- Crunchbase (company research) - Apify

And processing tools for:
- Fuzzy matching (deduplication)
- Domain extraction
- ICP matching
- Lead scoring
"""

# LinkedIn Tools (Apify)
from .apify_linkedin_posts import ApifyLinkedInPostsSearchTool
from .apify_linkedin_leads import LinkedInLeadExtractionTool
from .apify_linkedin_employees import LinkedInEmployeesSearchTool
from .apify_linkedin_post_comments import LinkedInPostCommentsTool
from .apify_linkedin import ApifyLinkedInSearchTool
from .apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool

# Reddit Tools (Apify)
from .apify_reddit import ApifyRedditSearchTool, RedditLeadExtractionTool

# Twitter Tools (Apify)
from .apify_twitter import ApifyTwitterSearchTool

# Google/Web Tools (CrewAI native - replaces Apify)
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

# Crunchbase Tools (Apify)
from .apify_crunchbase import ApifyCrunchbaseTool

# Processing Tools
from .fuzzy_matcher import FuzzyMatcherTool
from .domain_extractor import DomainExtractorTool
from .icp_matcher import ICPMatcherTool
from .lead_scorer import LeadScorerTool

# All atomic tools
ATOMIC_TOOLS = [
    # LinkedIn
    ApifyLinkedInPostsSearchTool,
    LinkedInLeadExtractionTool,
    LinkedInEmployeesSearchTool,
    LinkedInPostCommentsTool,
    ApifyLinkedInSearchTool,
    ApifyLinkedInProfileDetailTool,
    # Reddit
    ApifyRedditSearchTool,
    RedditLeadExtractionTool,
    # Twitter
    ApifyTwitterSearchTool,
    # Google/Web (CrewAI native)
    SerperDevTool,
    ScrapeWebsiteTool,
    # Crunchbase
    ApifyCrunchbaseTool,
]

# Processing tools
PROCESSING_TOOLS = [
    FuzzyMatcherTool,
    DomainExtractorTool,
    ICPMatcherTool,
    LeadScorerTool,
]

__all__ = [
    # LinkedIn
    "ApifyLinkedInPostsSearchTool",
    "LinkedInLeadExtractionTool",
    "LinkedInEmployeesSearchTool",
    "LinkedInPostCommentsTool",
    "ApifyLinkedInSearchTool",
    "ApifyLinkedInProfileDetailTool",
    # Reddit
    "ApifyRedditSearchTool",
    "RedditLeadExtractionTool",
    # Twitter
    "ApifyTwitterSearchTool",
    # Google/Web (CrewAI native)
    "SerperDevTool",
    "ScrapeWebsiteTool",
    # Crunchbase
    "ApifyCrunchbaseTool",
    # Processing
    "FuzzyMatcherTool",
    "DomainExtractorTool",
    "ICPMatcherTool",
    "LeadScorerTool",
    # Tool lists
    "ATOMIC_TOOLS",
    "PROCESSING_TOOLS",
]
