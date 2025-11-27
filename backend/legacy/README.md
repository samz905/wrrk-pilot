# Legacy Code

This folder contains discontinued tools and crews that are no longer used by the orchestrator.

**Archived on:** 2025-11-27

## Why These Were Moved

The prospecting system was refactored from a multi-crew architecture to a single **Orchestrator Agent** with stepped tools. These files are kept for reference but are NOT imported anywhere in the active codebase.

## Contents

### `/crews/` - Discontinued Crews

| Folder | Description | Why Discontinued |
|--------|-------------|------------------|
| `linkedin/` | LinkedIn post search and lead extraction crew | Orchestrator uses LinkedIn tools directly |
| `reddit/` | Reddit search crew | Orchestrator uses stepped Reddit tools |
| `twitter/` | Twitter/X search crew | Strategy de-prioritized |
| `google/` | Google SERP and website crawling crew | Replaced with CrewAI native tools |
| `aggregation/` | Lead deduplication and aggregation | Handled by orchestrator |
| `qualification/` | ICP matching and lead scoring | Handled by orchestrator |

### `/tools/` - Discontinued Atomic Tools

| File | Description | Why Discontinued |
|------|-------------|------------------|
| `apify_linkedin.py` | Basic LinkedIn search | Replaced by more specific tools |
| `apify_linkedin_posts.py` | LinkedIn posts search | Not used by orchestrator |
| `apify_linkedin_leads.py` | Lead extraction from posts | Not used by orchestrator |
| `linkedin_comprehensive.py` | Combined LinkedIn tool | Replaced by atomic tools |
| `domain_extractor.py` | Extract domains from URLs | Only used by aggregation crew |
| `fuzzy_matcher.py` | Fuzzy string matching | Only used by aggregation crew |
| `icp_matcher.py` | ICP matching tool | Only used by qualification crew |
| `lead_scorer.py` | Lead scoring tool | Only used by qualification crew |
| `apify_google_serp.py` | Google SERP via Apify | Replaced by CrewAI SerperDevTool |
| `apify_website_crawler.py` | Website crawling via Apify | Replaced by CrewAI ScrapeWebsiteTool |

### `/tools/stepped/` - Discontinued Stepped Tools

| File | Description | Why Discontinued |
|------|-------------|------------------|
| `g2_tools.py` | G2 competitor review extraction | G2 strategy discontinued |
| `upwork_tools.py` | Upwork job posting extraction | Upwork strategy discontinued |

### `/tools/composite/` - Discontinued Composite Tools

| File | Description | Why Discontinued |
|------|-------------|------------------|
| `intent_signal_hunter.py` | Multi-platform intent signal finder | Replaced by orchestrator |
| `decision_maker_finder.py` | Find decision makers at companies | Replaced by orchestrator |
| `company_trigger_scanner.py` | Company trigger event scanner | Replaced by orchestrator |

## Active Architecture

The current system uses:

1. **OrchestratorCrew** (`/app/crews/orchestrator/`)
   - Single intelligent agent with full tool suite
   - Mandatory two-platform strategy: Reddit + TechCrunch

2. **Stepped Tools** (`/app/tools/stepped/`)
   - `reddit_tools.py` - search → score → extract
   - `techcrunch_tools.py` - fetch → select → extract → decision_makers
   - `filter_sellers.py` - reusable buyer/seller filter

3. **Atomic Tools** (`/app/tools/`)
   - LinkedIn: employees, profile_detail, company_search, post_comments
   - Reddit: search, lead extraction
   - Twitter: search
   - Crunchbase: company research
   - Google/Web: SerperDevTool, ScrapeWebsiteTool (CrewAI native)

See `/backend/TECH_ARCH.md` for full architecture documentation.
