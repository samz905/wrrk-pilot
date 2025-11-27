"""
Tools for Sales Prospecting.

ACTIVE TOOLS (used by orchestrator):
- LinkedIn (employees, profile detail, company search) - Apify
- Reddit (search and lead extraction) - Apify
- Twitter/X (search) - Apify
- Google/Web (SERP and website scraping) - CrewAI native tools
- Crunchbase (company research) - Apify

LEGACY TOOLS (moved to /backend/legacy/):
- apify_linkedin.py, apify_linkedin_posts.py, apify_linkedin_leads.py
- linkedin_comprehensive.py
- fuzzy_matcher.py, domain_extractor.py, icp_matcher.py, lead_scorer.py
- composite/ folder (intent_signal_hunter, decision_maker_finder, company_trigger_scanner)
"""

# LinkedIn Tools (Apify) - ACTIVE
from .apify_linkedin_employees import LinkedInEmployeesSearchTool, LinkedInEmployeesBatchSearchTool
from .apify_linkedin_post_comments import LinkedInPostCommentsTool
from .apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool
from .apify_linkedin_company_search import LinkedInCompanySearchTool, LinkedInCompanyBatchSearchTool

# Reddit Tools (Apify)
from .apify_reddit import ApifyRedditSearchTool, RedditLeadExtractionTool

# Twitter Tools (Apify)
from .apify_twitter import ApifyTwitterSearchTool

# Google/Web Tools (CrewAI native - replaces Apify)
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

# Crunchbase Tools (Apify)
from .apify_crunchbase import ApifyCrunchbaseTool

# All atomic tools (used by orchestrator)
ATOMIC_TOOLS = [
    # LinkedIn
    LinkedInEmployeesSearchTool,
    LinkedInEmployeesBatchSearchTool,  # PARALLEL employee search
    LinkedInPostCommentsTool,
    ApifyLinkedInProfileDetailTool,
    LinkedInCompanySearchTool,
    LinkedInCompanyBatchSearchTool,
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

__all__ = [
    # LinkedIn
    "LinkedInEmployeesSearchTool",
    "LinkedInEmployeesBatchSearchTool",
    "LinkedInPostCommentsTool",
    "ApifyLinkedInProfileDetailTool",
    "LinkedInCompanySearchTool",
    "LinkedInCompanyBatchSearchTool",
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
    # Tool lists
    "ATOMIC_TOOLS",
]
