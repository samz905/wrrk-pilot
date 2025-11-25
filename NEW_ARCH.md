# Sales Prospecting Agent Architecture

> A truly agentic, autonomous lead prospecting system that reasons, reflects, adapts, and self-corrects.

---

## Table of Contents
1. [Design Philosophy](#design-philosophy)
2. [Architecture Overview](#architecture-overview)
3. [Apify Actors Reference](#apify-actors-reference)
4. [Agent Configuration](#agent-configuration)
5. [State Management](#state-management)
6. [Tool Hierarchy](#tool-hierarchy)
7. [Agentic Behavior Patterns](#agentic-behavior-patterns)
8. [Example Scenarios](#example-scenarios)
9. [Implementation Guide](#implementation-guide)

---

## Design Philosophy

### Core Principles

1. **Truly Agentic** - The agent reasons about results, reflects on quality, and dynamically decides next steps
2. **Self-Correcting** - If a tool returns empty results, try different queries or alternative approaches
3. **Adaptive Strategy** - Choose platforms and tactics based on the specific query, not a fixed pipeline
4. **Quality Over Volume** - 500 high-intent leads > 2000 cold contacts
5. **Simple Implementation, Powerful Behavior** - Leverage CrewAI's built-in capabilities

### What "Truly Agentic" Means

```
CURRENT (Pipeline):
Query → LinkedIn → Reddit → Twitter → Google → Aggregate → Score → Done
       (fixed sequence, no adaptation)

NEW (Agentic):
Query → Agent Reasons → Tries LinkedIn → Reviews Results
                       ↓
                       "Only 5 results, let me try different keywords"
                       ↓
                       Tries LinkedIn with new query → Better results
                       ↓
                       "Now let me check Reddit for the same topic"
                       ↓
                       Reviews Reddit → "Found companies, let me find decision makers"
                       ↓
                       Uses Company Employees tool → Enriches leads
                       ↓
                       Scores and reflects → "These 3 are hot, these 10 are warm"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROSPECTING FLOW (Event-Driven)                      │
│  Uses Pydantic State for type-safe state management                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    ORCHESTRATOR AGENT                                │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │  reasoning: true           # Plans before executing         │    │    │
│  │  │  max_reasoning_attempts: 3 # Reflects up to 3 times        │    │    │
│  │  │  max_iter: 50              # Can iterate extensively        │    │    │
│  │  │  max_retry_limit: 3        # Retries on tool failures      │    │    │
│  │  │  memory: true              # Maintains context              │    │    │
│  │  │  allow_delegation: false   # Single agent simplicity        │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                                                                      │    │
│  │  TOOLS: All atomic + workflow tools available                       │    │
│  │                                                                      │    │
│  │  BEHAVIOR:                                                          │    │
│  │  1. Reason about query → Plan which tools to use                   │    │
│  │  2. Execute tool → Review results                                   │    │
│  │  3. If poor results → Reflect → Try different approach             │    │
│  │  4. If good results → Continue to next logical step                │    │
│  │  5. Aggregate and score leads                                       │    │
│  │  6. Return only leads meeting quality threshold                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Apify Actors Reference

### LinkedIn Actors

#### 1. LinkedIn Posts Search
```python
# Actor: apimaestro/linkedin-posts-search-scraper-no-cookies
# Actor ID: 5QnEH5N71IK2mFLrP

run_input = {
    "keyword": str,           # Required: Search keywords (e.g., "coding")
    "sort_type": str,         # "relevance" (default) or "date"
    "page_number": int,       # Pagination (default: 1)
    "date_filter": str,       # Optional date filter
    "limit": int              # Max posts to return (default: 50)
}

# Example:
run_input = {
    "keyword": "frustrated with Salesforce",
    "sort_type": "relevance",
    "page_number": 1,
    "date_filter": "",
    "limit": 50
}

# Returns: Post content, author info, engagement metrics, post URL
```

#### 2. LinkedIn Post Comments/Engagements Scraper
```python
# Actor: apimaestro/linkedin-post-comments-replies-engagements-scraper-no-cookies

run_input = {
    "postIds": List[str],     # Post IDs or full URLs
    "page_number": int,       # Pagination (default: 1)
    "sortOrder": str,         # "most recent" or "most relevant"
    "limit": int              # Max comments (default: 100)
}

# Example:
run_input = {
    "postIds": [
        "7289521182721093633",
        "https://www.linkedin.com/posts/satyanadella_big-day-..."
    ],
    "page_number": 1,
    "sortOrder": "most recent",
    "limit": 100
}

# Returns: Comments, reactions, replies, commenter profiles
```

#### 3. LinkedIn Profile Scraper (Mass URLs)
```python
# Actor: dev_fusion/linkedin-profile-scraper

run_input = {
    "profileUrls": List[str]  # List of profile URLs
}

# Example:
run_input = {
    "profileUrls": [
        "https://www.linkedin.com/in/williamhgates",
        "http://www.linkedin.com/in/jeannie-wyrick-b4760710a"
    ]
}

# Returns: Full profile, work history, education, email (if available), phone
```

#### 4. LinkedIn Company Employees Scraper
```python
# Actor: apimaestro/linkedin-company-employees-scraper-no-cookies
# Actor ID: cIdqlEvw6afc1do1p

run_input = {
    "identifier": str,        # Company URL (full LinkedIn company page URL)
    "max_employees": int,     # Max employees to return (default: 100)
    "job_title": str          # Filter by job title (optional, empty = all)
}

# Example:
run_input = {
    "identifier": "https://www.linkedin.com/company/google/",
    "max_employees": 100,
    "job_title": "VP Sales"   # Or "" for all employees
}

# Returns: Employee name, title, profile URL
```

### Reddit Actor

```python
# Actor: fatihtahta/reddit-scraper-search-fast
# Actor ID: TwqHBuZZPHJxiQrTU

run_input = {
    "queries": List[str],     # Search queries
    "sort": str,              # "relevance", "hot", "top", "new", "comments"
    "timeframe": str,         # "hour", "day", "week", "month", "year", "all"
    "maxPosts": int,          # Max posts to return (default: 100)
    "maxComments": int,       # Comments per post (default: 100)
    "scrapeComments": bool,   # Whether to scrape comments
    "includeNsfw": bool       # Include NSFW content
}

# Example:
run_input = {
    "queries": [
        "CRM software recommendations",
        "Salesforce alternative"
    ],
    "sort": "relevance",
    "timeframe": "month",
    "maxPosts": 100,
    "maxComments": 50,
    "scrapeComments": True,
    "includeNsfw": False
}

# Returns: Post title, body, author, subreddit, engagement, comments
```

### Twitter/X Actor

```python
# Actor: apidojo/tweet-scraper

run_input = {
    # Multiple input modes - use ONE of these:
    "startUrls": List[str],       # Direct URLs to scrape
    "searchTerms": List[str],     # Search keywords
    "twitterHandles": List[str],  # Specific users to scrape
    "conversationIds": List[str], # Specific threads

    # Common parameters:
    "maxItems": int,              # Max tweets (default: 1000)
    "sort": str,                  # "Latest" or "Top"
    "tweetLanguage": str,         # Language filter (e.g., "en")

    # Advanced filters:
    "author": str,                # Filter by author
    "inReplyTo": str,             # Filter by reply target
    "mentioning": str,            # Filter by mentions
    "minimumRetweets": int,       # Min retweet threshold
    "minimumFavorites": int,      # Min likes threshold
    "minimumReplies": int,        # Min replies threshold
    "start": str,                 # Start date "YYYY-MM-DD"
    "end": str                    # End date "YYYY-MM-DD"
}

# Example - Search mode:
run_input = {
    "searchTerms": [
        "CRM recommendations",
        "Salesforce frustrating"
    ],
    "maxItems": 100,
    "sort": "Latest",
    "tweetLanguage": "en",
    "minimumReplies": 2
}

# Returns: Tweet text, author info, engagement, timestamp
```

### Google Actors

#### 1. Google SERP Search
```python
# Actor: apify/google-search-scraper

run_input = {
    "queries": str,               # Newline-separated queries
    "resultsPerPage": int,        # Results per page (default: 100)
    "maxPagesPerQuery": int,      # Pages to scrape (default: 1)
    "aiMode": str,                # "aiModeOff" (default)
    "searchLanguage": str,        # Language code (optional)
    "languageCode": str,          # Country-specific results
    "forceExactMatch": bool,      # Exact phrase matching
    "wordsInTitle": List[str],    # Required words in title
    "wordsInText": List[str],     # Required words in text
    "wordsInUrl": List[str],      # Required words in URL
    "mobileResults": bool,        # Mobile search results
    "saveHtml": bool,             # Save raw HTML
    "includeIcons": bool          # Include favicons
}

# Example:
run_input = {
    "queries": "CRM software reviews\nSalesforce alternatives 2024",
    "resultsPerPage": 50,
    "maxPagesPerQuery": 1,
    "aiMode": "aiModeOff",
    "forceExactMatch": False
}

# Returns: Title, URL, description snippet, position
```

#### 2. Website Content Crawler
```python
# Actor: apify/website-content-crawler

run_input = {
    "startUrls": List[dict],          # [{"url": "https://..."}]
    "maxCrawlDepth": int,             # How deep to crawl (default: 20)
    "maxCrawlPages": int,             # Max pages total
    "maxConcurrency": int,            # Parallel threads (default: 200)

    # Content extraction:
    "crawlerType": str,               # "playwright:adaptive" (recommended)
    "htmlTransformer": str,           # "readableText" for clean text
    "readableTextCharThreshold": int, # Min chars for content (default: 100)
    "saveMarkdown": bool,             # Save as markdown (recommended: True)
    "saveHtml": bool,                 # Also save HTML

    # Performance:
    "blockMedia": bool,               # Skip images/videos (recommended: True)
    "removeCookieWarnings": bool,     # Remove cookie banners (True)
    "dynamicContentWaitSecs": int,    # Wait for JS (default: 10)

    # Filtering:
    "includeUrlGlobs": List[str],     # URL patterns to include
    "excludeUrlGlobs": List[str],     # URL patterns to exclude
    "removeElementsCssSelector": str  # CSS selectors to remove
}

# Example:
run_input = {
    "startUrls": [{"url": "https://www.g2.com/categories/crm"}],
    "maxCrawlPages": 50,
    "crawlerType": "playwright:adaptive",
    "saveMarkdown": True,
    "blockMedia": True,
    "removeCookieWarnings": True,
    "maxConcurrency": 10
}

# Returns: Markdown content, title, URL, content length
```

### Crunchbase Actor

```python
# Actor: curious_coder/crunchbase-scraper

run_input = {
    "keyword": str,           # Search keyword (e.g., "AI startup")
    "sort_type": str,         # "relevance" (default)
    "page_number": int,       # Pagination (default: 1)
    "date_filter": str,       # Optional date filter
    "limit": int              # Max results (default: 50)
}

# Example:
run_input = {
    "keyword": "Series A SaaS",
    "sort_type": "relevance",
    "page_number": 1,
    "date_filter": "",
    "limit": 50
}

# Returns: Company name, funding info, industry, employee count, founders
```

---

## Agent Configuration

### Orchestrator Agent Definition

```python
from crewai import Agent
from langchain_openai import ChatOpenAI

# GPT-4 for planning/reasoning, GPT-4o-mini for execution
planning_llm = ChatOpenAI(model="gpt-4", temperature=0.3)
execution_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)

orchestrator = Agent(
    role="Senior Sales Prospecting Strategist",
    goal="""
    Find {target_leads} high-intent leads for: {product_description}

    You are an autonomous prospecting agent. Think strategically about:
    1. Which platforms will yield the best leads for this specific product
    2. What search queries will find people with genuine buying intent
    3. How to validate and enrich leads once found

    CRITICAL: Review your results after each tool call. If results are poor:
    - Try different keywords
    - Try a different platform
    - Try a different strategy (intent signals vs company triggers)

    Only return leads with intent score >= 60.
    """,
    backstory="""
    You are an expert B2B sales strategist who has personally prospected for
    multiple successful startups. You understand that the best leads come from
    identifying pain points, not just matching job titles.

    Your superpower is knowing when to pivot strategies. If LinkedIn isn't
    yielding results, you try Reddit. If intent signals are weak, you switch
    to company trigger research. You never give up with poor results - you
    adapt and find another way.
    """,

    # Agentic behavior parameters
    reasoning=True,                    # Plan before executing
    max_reasoning_attempts=3,          # Reflect up to 3 times
    max_iter=50,                       # Allow extensive iteration
    max_retry_limit=3,                 # Retry failed tool calls
    memory=True,                       # Maintain context across calls
    allow_delegation=False,            # Single agent for simplicity

    # Resource management
    max_rpm=10,                        # Prevent API throttling
    max_execution_time=900,            # 15 minute max
    respect_context_window=True,       # Auto-summarize if needed

    # Tools
    tools=[
        # Intent signal tools
        LinkedInPostsSearchTool(),
        RedditSearchTool(),
        TwitterSearchTool(),

        # Company research tools
        GoogleSERPTool(),
        WebsiteCrawlerTool(),
        CrunchbaseTool(),

        # Lead enrichment tools
        LinkedInCompanyEmployeesTool(),
        LinkedInProfileEnrichTool(),

        # Scoring tool
        LeadScoringTool()
    ],

    verbose=True
)
```

---

## State Management

### Pydantic State Model

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime

class LeadPriority(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DISQUALIFIED = "disqualified"

class Lead(BaseModel):
    """Individual lead with all enrichment data."""
    name: str
    title: str
    company: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Intent signals
    intent_signal: str = Field(description="Quote showing buying intent")
    intent_score: int = Field(ge=0, le=100)
    intent_type: str = Field(description="recommendation_request, complaint, evaluation, etc.")

    # Source tracking
    source_platforms: List[str] = []
    source_urls: List[str] = []

    # Enrichment data
    company_size: Optional[str] = None
    company_funding: Optional[str] = None
    company_industry: Optional[str] = None

    # Final scoring
    priority: LeadPriority = LeadPriority.COLD
    final_score: int = 0
    scoring_reasoning: str = ""

class ToolAttempt(BaseModel):
    """Track each tool call for reflection."""
    tool_name: str
    query_used: str
    results_count: int
    quality_assessment: str  # "good", "poor", "empty"
    timestamp: datetime = Field(default_factory=datetime.now)

class ProspectingState(BaseModel):
    """Full state for prospecting flow."""

    # Input
    query: str = ""
    product_description: str = ""
    icp_criteria: Dict[str, Any] = {}
    target_leads: int = 100

    # Progress tracking
    status: str = "initializing"  # initializing, researching, enriching, scoring, completed, failed
    current_strategy: str = ""    # "intent_signals", "company_triggers", "hybrid"

    # Results accumulation
    raw_leads: List[Lead] = []
    qualified_leads: List[Lead] = []

    # Tool tracking (for reflection)
    tool_attempts: List[ToolAttempt] = []
    platforms_searched: List[str] = []
    strategies_tried: List[str] = []

    # Agent reasoning log
    reasoning_log: List[str] = []

    # Error tracking
    errors: List[str] = []
    retries: int = 0
```

### Flow with State

```python
from crewai.flow.flow import Flow, listen, start, router
from crewai.flow.persistence import persist

@persist()  # Auto-save state after each step
class ProspectingFlow(Flow[ProspectingState]):
    """
    Event-driven prospecting flow with agentic decision-making.
    """

    @start()
    def initialize(self):
        """Parse input and determine initial strategy."""
        self.state.status = "initializing"
        self.emit_event("thought", f"Analyzing query: {self.state.query}")

        # Agent determines best initial approach
        self.state.current_strategy = self._determine_initial_strategy()
        self.state.status = "researching"

        return self.state

    @listen(initialize)
    def run_orchestrator(self, state):
        """Execute the main prospecting agent."""
        orchestrator = create_orchestrator_agent()

        result = orchestrator.crew().kickoff(inputs={
            "product_description": state.product_description,
            "target_leads": state.target_leads,
            "icp_criteria": state.icp_criteria
        })

        # Parse structured output
        state.qualified_leads = result.pydantic.leads
        state.status = "completed"

        return state

    @router(run_orchestrator)
    def check_results(self, state):
        """Route based on result quality."""
        if len(state.qualified_leads) >= state.target_leads * 0.5:
            return "success"
        elif state.retries < 3:
            return "retry"
        else:
            return "partial_success"

    @listen("retry")
    def retry_with_new_strategy(self, state):
        """Try alternative strategy if results are insufficient."""
        state.retries += 1
        state.reasoning_log.append(
            f"Retry {state.retries}: Only {len(state.qualified_leads)} leads found, trying new strategy"
        )

        # Switch strategy
        if state.current_strategy == "intent_signals":
            state.current_strategy = "company_triggers"
        else:
            state.current_strategy = "intent_signals"

        return self.run_orchestrator(state)

    @listen("success")
    def finalize_success(self, state):
        """Complete with full results."""
        self.emit_event("completed", {
            "leads": [lead.dict() for lead in state.qualified_leads],
            "total": len(state.qualified_leads)
        })
        return state

    @listen("partial_success")
    def finalize_partial(self, state):
        """Complete with partial results after retries exhausted."""
        self.emit_event("completed", {
            "leads": [lead.dict() for lead in state.qualified_leads],
            "total": len(state.qualified_leads),
            "warning": "Target not reached after retries"
        })
        return state
```

---

## Tool Hierarchy

### Layer 1: Atomic Tools (Direct API Wrappers)

These wrap individual Apify actors with consistent interfaces:

| Tool | Actor | Purpose |
|------|-------|---------|
| `LinkedInPostsSearchTool` | 5QnEH5N71IK2mFLrP | Find posts with intent signals |
| `LinkedInCommentsScrapeTool` | Comments actor | Get post engagers |
| `LinkedInProfileEnrichTool` | dev_fusion | Enrich profiles with email/phone |
| `LinkedInCompanyEmployeesTool` | cIdqlEvw6afc1do1p | Find decision makers at company |
| `RedditSearchTool` | TwqHBuZZPHJxiQrTU | Find discussions |
| `RedditLeadExtractionTool` | Same + LLM | Extract users from threads |
| `TwitterSearchTool` | pzMmk1t7AZ8OKJhfU | Find tweets |
| `GoogleSERPTool` | 563JCPLOqM1kMmbbP | Search Google |
| `WebsiteCrawlerTool` | aYG0l9s7dbB7j3gbS | Extract article content |
| `CrunchbaseTool` | curious_coder | Find company info |

### Layer 2: Composite Tools (Multi-Step Workflows)

These chain multiple atomic tools for common patterns:

```python
class IntentSignalHunterTool(BaseTool):
    """
    Search for intent signals across LinkedIn, Reddit, and Twitter IN PARALLEL.

    Input: topic, keywords
    Output: Unified list of people showing buying intent

    Internal flow:
    1. Generate platform-specific queries
    2. ThreadPoolExecutor: LinkedIn + Reddit + Twitter simultaneously
    3. Merge and deduplicate results
    4. Return unified lead list
    """

class CompanyTriggerScannerTool(BaseTool):
    """
    Find companies with buying triggers using Google + Crunchbase.

    Input: industry, signals (funding, hiring, growth)
    Output: List of companies with trigger details

    Internal flow:
    1. Google SERP: funding announcements, hiring signals
    2. Crunchbase: recent funding, growth metrics
    3. Merge and enrich company data
    4. Return company list with triggers
    """

class DecisionMakerFinderTool(BaseTool):
    """
    Given companies, find relevant decision makers.

    Input: companies list, target titles
    Output: Decision makers with profiles

    Internal flow:
    1. For each company (parallel batches)
    2. LinkedInCompanyEmployeesTool with title filter
    3. Score by title relevance
    4. Return top decision makers
    """

class LeadScoringTool(BaseTool):
    """
    Score leads against ICP and intent signals.

    Input: leads list, icp_criteria
    Output: Scored leads with priority

    Scoring formula:
    - Intent strength: 35%
    - Title/seniority: 25%
    - Company fit: 20%
    - Platform multiplicity: 10%
    - Contact completeness: 10%
    """
```

---

## Agentic Behavior Patterns

### Pattern 1: Reflect and Retry

```python
# In agent task description:
"""
After each tool call, REFLECT on the results:

1. QUANTITY CHECK:
   - Got 0 results? Try different keywords or different platform
   - Got < 5 results? Broaden the search or try synonyms
   - Got > 20 results? Good, proceed to next step

2. QUALITY CHECK:
   - Are results relevant to the query?
   - Do people show genuine buying intent?
   - Are these the right job titles?

3. ADAPT if needed:
   - "These LinkedIn results are mostly sellers, let me try Reddit"
   - "Query 'CRM software' is too broad, let me try 'Salesforce alternative'"
   - "Not finding intent signals, switching to company trigger approach"

4. NEVER accept empty results as final:
   - Always try at least 2 different queries per platform
   - Always try at least 2 different platforms
   - Document what you tried in your reasoning
"""
```

### Pattern 2: Dynamic Tool Selection

```python
# In agent backstory:
"""
You choose tools strategically based on the query:

PRODUCT TYPE → BEST PLATFORMS:
- B2B SaaS → LinkedIn (decision makers) + Reddit (honest discussions)
- Developer tools → Reddit + Twitter (dev communities)
- Enterprise → LinkedIn + Google (company research)
- SMB → Reddit + Twitter (direct users)

STRATEGY SELECTION:
- "Looking for CRM" → Intent signals first (LinkedIn/Reddit posts)
- "Recently funded startups" → Company triggers first (Crunchbase/Google)
- Generic query → Hybrid approach

FALLBACK LOGIC:
- LinkedIn empty? → Try Reddit with same keywords
- Reddit empty? → Try Twitter with hashtags
- All empty? → Broaden keywords or try company trigger approach
"""
```

### Pattern 3: Iterative Enrichment

```python
# In task description:
"""
ENRICHMENT FLOW (do this for top leads only):

1. Got person from post/discussion
   → Check if we have company name

2. Have company name?
   YES → Use LinkedInCompanyEmployeesTool to verify/enrich
   NO → Skip enrichment for now

3. Have LinkedIn URL?
   YES → Use LinkedInProfileEnrichTool for email/phone
   NO → Search for profile if person seems high-intent

4. SCORING THRESHOLD:
   - Only enrich leads with intent_score >= 70
   - Don't waste API calls on weak leads
   - Quality > Quantity
"""
```

---

## Example Scenarios

### Scenario 1: Design Agent for Founders

```
QUERY: "Find leads for our AI design agent that helps startups ship UI faster"

AGENT REASONING:

Step 1: Analyze query
- Product: AI design tool for startups
- Target: Founders, Head of Product, Design leads
- Best signals: Design bottleneck discussions

Step 2: Plan approach
"This is a B2B SaaS for startups. I'll start with intent signals on LinkedIn
and Reddit, then enrich with decision maker data."

Step 3: Execute LinkedIn Posts Search
- Query: "frustrated with design" "hiring designers" "design bottleneck"
- Results: 15 posts found
- Reflection: "Good results, several founders complaining about Figma workflows"

Step 4: Execute Reddit Search
- Query: "design agency recommendations" in r/startups, r/SaaS
- Results: 8 discussions found
- Reflection: "Found several founders asking for design help"

Step 5: Extract leads from discussions
- From LinkedIn: 12 people with intent signals
- From Reddit: 6 users asking for recommendations
- Total: 18 raw leads

Step 6: Enrich top leads
- For leads with intent_score >= 70: Get LinkedIn profiles
- For leads with company names: Find decision makers
- Result: 15 enriched leads

Step 7: Score and filter
- HOT (score >= 80): 5 leads - explicit design problems + right title
- WARM (score 60-79): 7 leads - relevant discussions + decent titles
- Return: 12 qualified leads
```

### Scenario 2: CRM Competitor Displacement

```
QUERY: "Find sales leaders frustrated with Salesforce pricing"

AGENT REASONING:

Step 1: Analyze query
- Product: CRM (competitor to Salesforce)
- Target: VP Sales, RevOps, CRO
- Best signals: Salesforce complaints, pricing discussions

Step 2: Plan approach
"This is a competitor displacement play. I'll focus on complaint signals
on LinkedIn and Reddit, targeting specific Salesforce pain points."

Step 3: Execute LinkedIn Posts Search
- Query: "Salesforce too expensive" "CRM alternatives"
- Results: 3 posts found
- Reflection: "Low results. Let me try different keywords."

Step 4: Retry with different query
- Query: "switching from Salesforce" "CRM migration"
- Results: 11 posts found
- Reflection: "Better! Found several migration discussions."

Step 5: Execute Reddit Search
- Query: "Salesforce pricing" in r/sales, r/salesforce
- Results: 14 discussions found
- Reflection: "Excellent results - lots of pricing complaints"

Step 6: Try company trigger approach
- Google: "companies hiring Salesforce Admin"
- Results: 25 job postings → 25 companies with CRM budget
- Reflection: "These companies are investing in CRM, potential targets"

Step 7: Find decision makers at companies
- Use LinkedInCompanyEmployeesTool for top 10 companies
- Filter: VP Sales, Head of RevOps
- Result: 18 decision makers found

Step 8: Combine and score
- From intent signals: 20 leads with complaints
- From company triggers: 18 decision makers at companies with CRM budget
- Total after dedup: 35 leads
- After scoring: 28 qualified leads (score >= 60)
```

### Scenario 3: Code Review Tool for Engineering Teams

```
QUERY: "Find engineering managers who need faster code review"

AGENT REASONING:

Step 1: Analyze query
- Product: Code review tool
- Target: Engineering Manager, VP Eng, Director of Eng
- Best signals: PR bottleneck, code review discussions

Step 2: Plan approach
"Developer tools sell best through community signals. I'll prioritize
Reddit and Twitter where devs discuss honestly, then enrich with LinkedIn."

Step 3: Execute Reddit Search
- Query: "code review bottleneck" "PR review time" in r/programming
- Results: 22 discussions found
- Reflection: "Great results - many specific pain points about review delays"

Step 4: Execute Twitter Search
- Query: "code review" "PR backlog"
- Results: 15 tweets found
- Reflection: "Found some good discussions, mostly from engineers"

Step 5: Extract leads
- From Reddit: 18 users complaining about review bottlenecks
- From Twitter: 10 users discussing code review pain
- Reflection: "Reddit users are better leads - more detailed pain points"

Step 6: LinkedIn search for decision makers
- Focus on Engineering Managers at mid-size tech companies
- Query: "Engineering Manager" at companies from Crunchbase (50-500 employees)
- Results: 25 potential decision makers

Step 7: Cross-reference and enrich
- Match Reddit/Twitter users to LinkedIn profiles where possible
- Enrich with company size and tech stack info
- Result: 30 enriched leads

Step 8: Final scoring
- HOT: 8 leads - Engineering managers who complained about review time
- WARM: 15 leads - At right companies with right titles
- Return: 23 qualified leads
```

---

## Implementation Guide

### File Structure

```
backend/app/
├── crews/
│   └── orchestrator/
│       ├── __init__.py
│       ├── crew.py           # Single orchestrator crew
│       ├── agents.yaml       # Agent definition
│       └── tasks.yaml        # Task with multi-shot examples
├── tools/
│   ├── atomic/
│   │   ├── apify_linkedin_posts.py
│   │   ├── apify_linkedin_employees.py
│   │   ├── apify_linkedin_profile.py
│   │   ├── apify_reddit.py
│   │   ├── apify_twitter.py
│   │   ├── apify_google_serp.py
│   │   ├── apify_website_crawler.py
│   │   └── apify_crunchbase.py
│   └── composite/
│       ├── intent_signal_hunter.py
│       ├── company_trigger_scanner.py
│       ├── decision_maker_finder.py
│       └── lead_scoring.py
├── flows/
│   └── prospecting_flow.py   # Simplified flow with router
├── models/
│   └── state.py              # Pydantic state models
└── utils/
    └── parallel.py           # ThreadPoolExecutor helpers
```

### Implementation Order

1. **Phase 1: Refactor Atomic Tools**
   - Add consistent error handling with retries
   - Add result quality metadata (count, quality_assessment)
   - Ensure all tools return structured data

2. **Phase 2: Create Composite Tools**
   - IntentSignalHunterTool (parallel LinkedIn + Reddit + Twitter)
   - CompanyTriggerScannerTool (Google + Crunchbase)
   - DecisionMakerFinderTool (batch company employee search)
   - LeadScoringTool (ICP matching + scoring)

3. **Phase 3: Build Orchestrator Agent**
   - Single agent with all tools
   - Enable reasoning=True for planning
   - Add comprehensive task description with examples
   - Test with each scenario

4. **Phase 4: Simplify Flow**
   - Replace 6 crews with single orchestrator
   - Add router for retry logic
   - Implement state persistence

5. **Phase 5: Test & Optimize**
   - Run all 3 example scenarios
   - Benchmark performance
   - Tune agent parameters

---

## Sources

- [CrewAI Agents Documentation](https://docs.crewai.com/en/concepts/agents)
- [Mastering Flow State Management](https://docs.crewai.com/en/guides/flows/mastering-flow-state)
- [Build Agents to be Dependable](https://blog.crewai.com/build-agents-to-be-dependable/)
- [Agentic Flows in CrewAI](https://www.analyticsvidhya.com/blog/2024/11/agentic-flows-in-crewai/)
- [CrewAI Patterns: Conditional Tasks and Structured Outputs](https://medium.com/neural-engineer/crewai-patterns-conditional-tasks-and-structured-outputs-for-email-analysis-498a5048a8c9)
- [Building Multi-Agent Systems With CrewAI](https://www.firecrawl.dev/blog/crewai-multi-agent-systems-tutorial)
