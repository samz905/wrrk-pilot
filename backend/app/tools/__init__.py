"""
Apify Tools for Sales Prospecting.

This module provides atomic tools that wrap Apify actors for:
- LinkedIn (posts, profiles, employees, comments)
- Reddit (search and lead extraction)
- Twitter/X (search)
- Google (SERP and website crawler)
- Crunchbase (company research)

And processing tools for:
- Fuzzy matching (deduplication)
- Domain extraction
- ICP matching
- Lead scoring
"""

# LinkedIn Tools
from .apify_linkedin_posts import ApifyLinkedInPostsSearchTool
from .apify_linkedin_leads import LinkedInLeadExtractionTool
from .apify_linkedin_employees import LinkedInEmployeesSearchTool
from .apify_linkedin_post_comments import LinkedInPostCommentsTool
from .apify_linkedin import ApifyLinkedInSearchTool
from .apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool

# Reddit Tools
from .apify_reddit import ApifyRedditSearchTool, RedditLeadExtractionTool

# Twitter Tools
from .apify_twitter import ApifyTwitterSearchTool

# Google Tools
from .apify_google_serp import ApifyGoogleSERPTool
from .apify_website_crawler import ApifyWebsiteCrawlerTool

# Crunchbase Tools
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
    # Google
    ApifyGoogleSERPTool,
    ApifyWebsiteCrawlerTool,
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
    # Google
    "ApifyGoogleSERPTool",
    "ApifyWebsiteCrawlerTool",
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
