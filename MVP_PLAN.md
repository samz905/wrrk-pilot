# Lead Prospecting MVP: Implementation Plan

## Executive Summary

Building an intent-based lead prospecting tool that finds buyers, not just contacts. Unlike Apollo's stale database approach, we detect real-time buying signals across LinkedIn, Twitter, Reddit, and Google to deliver warm prospects with context.

**Key Differentiator**: Process 50-100 leads at once using breadth-first searches (e.g., "all companies complaining about Salesforce", "all CTOs looking for new CRM") rather than one-at-a-time deep dives.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          NEXT.JS FRONTEND                                   │
│                                                                              │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │      LEFT PANEL: INPUT          │  │   RIGHT PANEL: LIVE RESULTS      │ │
│  │                                  │  │                                   │ │
│  │  🎯 Sales Goal Input             │  │  📊 Progress Bar (0-100%)        │ │
│  │  "Find companies needing new    │  │                                   │ │
│  │   CRM software"                  │  │  🤖 Agent Activity Log           │ │
│  │                                  │  │  ├─ [LinkedIn Agent] Searching...│ │
│  │  🎛️  Filters:                    │  │  ├─ [Twitter Agent] Found 23... │ │
│  │  - Industry                      │  │  └─ [Scorer] Qualifying leads... │ │
│  │  - Company Size                  │  │                                   │ │
│  │  - Location                      │  │  📋 Results Table (Live Update)  │ │
│  │  - Budget Range                  │  │  ┌────────────────────────────┐ │ │
│  │                                  │  │  │Name │ Company │ Score │Email│ │ │
│  │  🚀 [Start Prospecting]          │  │  ├────────────────────────────┤ │ │
│  │                                  │  │  │Sarah│ DataTech│  95%  │ ✓  │ │ │
│  └─────────────────────────────────┘  │  │Mike │CloudFlow│  88%  │ ✓  │ │ │
│                                        │  │James│ RegBank │  99%  │ ✓  │ │ │
│                                        │  └────────────────────────────┘ │ │
│                                        │                                   │ │
│                                        │  💾 [Export CSV] [Export JSON]   │ │
│                                        └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                         ↕ WebSocket/SSE
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                                    │
│                                                                              │
│  API Endpoints:                                                             │
│  POST   /api/v1/prospect/start      → Start prospecting job                │
│  GET    /api/v1/prospect/{job_id}   → Get job status/results               │
│  GET    /api/v1/prospect/stream     → SSE real-time updates                │
│  DELETE /api/v1/prospect/{job_id}   → Cancel job                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CREWAI FLOW ORCHESTRATOR                               │
│                                                                              │
│  State Management (Pydantic):                                               │
│  - total_leads: int                                                         │
│  - qualified_leads: int                                                     │
│  - current_platform: str                                                    │
│  - progress_percentage: float                                               │
│  - agent_activities: List[str]                                              │
│                                                                              │
│  Flow Stages:                                                               │
│  1. [START] → Initialize → Parallel Platform Scraping                      │
│  2. [SCRAPE] → LinkedIn + Twitter + Reddit + Google (async)                │
│  3. [AGGREGATE] → Deduplicate + Merge                                      │
│  4. [QUALIFY] → Score + Prioritize                                         │
│  5. [ENRICH] → Email Pattern Matching + Company Data                       │
│  6. [COMPLETE] → Return Results                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CREWAI MULTI-AGENT SYSTEM                                │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │ LINKEDIN CREW    │  │ TWITTER CREW     │  │ REDDIT CREW      │         │
│  │                  │  │                  │  │                  │         │
│  │ 🧑 Scraper Agent │  │ 🧑 Scraper Agent │  │ 🧑 Scraper Agent │         │
│  │ Role: LinkedIn   │  │ Role: Twitter    │  │ Role: Reddit     │         │
│  │ Intelligence     │  │ Signal Hunter    │  │ Pain Detector    │         │
│  │                  │  │                  │  │                  │         │
│  │ 🛠️  Tools:        │  │ 🛠️  Tools:        │  │ 🛠️  Tools:        │         │
│  │ - Apify LinkedIn │  │ - Apify Twitter  │  │ - Apify Reddit   │         │
│  │ - Profile Search │  │ - Tweet Search   │  │ - Post Search    │         │
│  │ - Job Change     │  │ - User Profiles  │  │ - Comment Search │         │
│  │   Detection      │  │ - Engagement     │  │ - Subreddit Scan │         │
│  │                  │  │   Metrics        │  │                  │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ GOOGLE RESEARCH CREW                                        │           │
│  │                                                              │           │
│  │ 🧑 Research Agent                                            │           │
│  │ Role: Company Intelligence Analyst                          │           │
│  │                                                              │           │
│  │ 🛠️  Tools:                                                   │           │
│  │ - Apify Google Search                                       │           │
│  │ - News Finder (funding, leadership changes)                │           │
│  │ - Competitor Analysis                                       │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
│                              ↓ Results Flow ↓                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ AGGREGATION CREW                                            │           │
│  │                                                              │           │
│  │ 🧑 Deduplication Agent                                       │           │
│  │ Role: Data Consolidation Expert                             │           │
│  │                                                              │           │
│  │ Tasks:                                                       │           │
│  │ - Merge leads from all platforms                           │           │
│  │ - Identify duplicates (name + company matching)            │           │
│  │ - Consolidate intent signals from multiple sources         │           │
│  │ - Create unified prospect profiles                         │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
│                              ↓ Results Flow ↓                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ QUALIFICATION CREW                                          │           │
│  │                                                              │           │
│  │ 🧑 Lead Scorer Agent                                         │           │
│  │ Role: B2B Sales Qualification Expert                       │           │
│  │ Backstory: 15 years in enterprise sales, specialty in      │           │
│  │ identifying high-intent buyers based on behavioral signals │           │
│  │                                                              │           │
│  │ 🧑 Decision Maker Identifier Agent                          │           │
│  │ Role: Organizational Hierarchy Analyst                     │           │
│  │                                                              │           │
│  │ Scoring Factors:                                            │           │
│  │ - Intent Signal Strength (complaint, request, evaluation)  │           │
│  │ - Timing Indicators (recent post, job change, funding)     │           │
│  │ - Decision Authority (title, seniority, department)        │           │
│  │ - Company Fit (size, industry, budget indicators)          │           │
│  │ - Competitive Pressure (evaluating alternatives)           │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
│                              ↓ Results Flow ↓                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ ENRICHMENT CREW                                             │           │
│  │                                                              │           │
│  │ 🧑 Email Enrichment Agent                                    │           │
│  │ Role: Contact Information Specialist                       │           │
│  │                                                              │           │
│  │ 🧑 Company Data Agent                                        │           │
│  │ Role: Firmographic Researcher                              │           │
│  │                                                              │           │
│  │ 🛠️  Tools:                                                   │           │
│  │ - Email Pattern Generator (firstname.lastname@domain)      │           │
│  │ - Domain Finder (company website extraction)               │           │
│  │ - LinkedIn Profile to Email Converter                      │           │
│  │ - Company Data Extractor (size, industry, revenue)         │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL SERVICES                                     │
│                                                                              │
│  🔌 Apify API                                                               │
│  - LinkedIn Profile Scraper (apify/linkedin-profile-scraper)               │
│  - Twitter/X Scraper (apify/twitter-scraper)                               │
│  - Reddit Scraper (trudax/reddit-scraper)                                  │
│  - Google Search (apify/google-search-scraper)                             │
│                                                                              │
│  🧠 Anthropic Claude API                                                    │
│  - Model: claude-sonnet-4-5-20250929                                       │
│  - Used by all CrewAI agents for reasoning                                 │
│                                                                              │
│  💾 PostgreSQL + pgvector                                                   │
│  - Lead storage                                                             │
│  - Job history                                                              │
│  - Agent memory/context                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Design: Personalities & Expertise

### 1. LinkedIn Intelligence Agent

**agents.yaml**:
```yaml
linkedin_scraper:
  role: "LinkedIn Intelligence Analyst"
  goal: "Identify 50-100 decision-makers on LinkedIn showing intent to buy based on job changes, posts, and activity signals"
  backstory: |
    You're a seasoned B2B intelligence specialist with 12 years of experience in LinkedIn prospecting.
    Your expertise is identifying buying signals that others miss: new VP of Sales hiring their stack,
    recently promoted executives with budget authority, and companies posting about specific pain points.
    You understand that a "VP Sales" hired 30 days ago has 90-day budget windows. You know that
    someone commenting on a competitor's product update is evaluating alternatives. You're not just
    finding profiles—you're finding buyers at the perfect moment.
```

**Search Strategies**:
- Job title changes in last 90 days (new authority = new budget)
- Posts mentioning competitor names or pain points
- Companies hiring multiple roles in target department (expansion signal)
- Engagement with solution-related content (likes, comments on relevant topics)

**Tools**:
- `ApifyLinkedInSearchTool`: Search LinkedIn by keywords, location, company
- `ApifyLinkedInProfileTool`: Extract detailed profile data
- `JobChangeDetectorTool`: Identify recent role changes (intent signal)

---

### 2. Twitter Signal Hunter Agent

**agents.yaml**:
```yaml
twitter_hunter:
  role: "Twitter Signal Intelligence Expert"
  goal: "Find 50-100 prospects on Twitter actively complaining about competitors or asking for recommendations"
  backstory: |
    You're a social listening expert who's been monitoring B2B buyer signals on Twitter for 8 years.
    You know that when a CTO tweets "Why is [Competitor] so slow?", they're 2 weeks from evaluating
    alternatives. You specialize in finding complaint threads, recommendation requests, and frustration
    posts that indicate active buying mode. You understand engagement patterns—a thread with 20+ replies
    means multiple prospects, not just one. You're the first to spot trending pain points before they
    become obvious.
```

**Search Strategies**:
- Complaint tweets: "[Competitor] is too expensive/slow/complicated"
- Request tweets: "Does anyone know a good [solution type]?"
- Comparison tweets: "[Product A] vs [Product B] - which should I choose?"
- Event tweets: "Just got promoted to VP Sales, need to build our stack"

**Tools**:
- `ApifyTwitterSearchTool`: Search tweets by keywords, hashtags
- `ApifyTwitterProfileTool`: Extract user profiles
- `EngagementAnalyzerTool`: Measure reply/like/retweet patterns

---

### 3. Reddit Pain Point Detective Agent

**agents.yaml**:
```yaml
reddit_detective:
  role: "Reddit Community Intelligence Specialist"
  goal: "Discover 50-100 prospects on Reddit discussing problems our solution solves in r/entrepreneur, r/startups, r/sales, and industry subreddits"
  backstory: |
    You've spent 10 years analyzing Reddit communities to find authentic buyer intent. You know that
    Redditors are brutally honest—when they say "[Tool] is garbage", they mean it and they're looking
    for alternatives. You specialize in finding long-form complaint threads where multiple prospects
    reveal themselves. You understand subreddit culture: r/entrepreneur has bootstrapped founders,
    r/sales has quota-carrying reps with budget influence. You find the posts where someone says
    "There has to be a better way" because that's a buyer raising their hand.
```

**Search Strategies**:
- Help requests: "Can anyone recommend a [solution]?"
- Complaint threads: "Why is [problem] so hard to solve?"
- Alternative requests: "Cheaper alternative to [expensive competitor]?"
- Success story questions: "How did you solve [specific problem]?"

**Tools**:
- `ApifyRedditSearchTool`: Search posts/comments by keywords
- `SubredditAnalyzerTool`: Identify best subreddits for target audience
- `ThreadContextTool`: Extract full thread for multiple prospects

---

### 4. Google Research Intelligence Agent

**agents.yaml**:
```yaml
google_researcher:
  role: "Company Intelligence & News Analyst"
  goal: "Find 50-100 companies with recent triggers (funding, leadership changes, expansions) that indicate readiness to buy"
  backstory: |
    You're an intelligence analyst with expertise in identifying company-level buying triggers. You know
    that companies announce "Series A funding" and immediately start building their tech stack. When a
    company posts "New CMO hired", that's a 90-day window for rebranding projects. You specialize in
    finding these trigger events at scale using Google News, company blogs, and press releases. You
    understand timing: a company that just opened a new office needs new tools for that team. You're
    not just finding companies—you're finding companies at inflection points.
```

**Search Strategies**:
- Funding announcements: "[Industry] Series A funding"
- Leadership changes: "New [CTO/CMO/VP Sales] hired"
- Expansion news: "Opening new office", "Expanding to [market]"
- Problem announcements: "Company X faces [challenge]", "[Breach/Incident] at [Company]"

**Tools**:
- `ApifyGoogleSearchTool`: Search Google for recent news
- `NewsDateFilterTool`: Filter results to last 30/60/90 days
- `CompanyExtractorTool`: Extract company names from articles

---

### 5. Aggregation & Deduplication Agent

**agents.yaml**:
```yaml
aggregation_specialist:
  role: "Data Consolidation Expert"
  goal: "Merge leads from all platforms, remove duplicates, and consolidate intent signals into unified prospect profiles"
  backstory: |
    You're a data quality specialist who's been cleaning and merging prospect data for 15 years. You
    understand that "John Smith at Acme Corp" on LinkedIn is the same person as "@johnsmith" on Twitter
    complaining about Salesforce. You excel at fuzzy matching, identifying duplicates across platforms,
    and creating a single source of truth. When you find the same prospect on 3 platforms, you combine
    all their intent signals into one high-confidence lead. You're obsessive about data quality because
    you know that duplicate outreach destroys conversion rates.
```

**Deduplication Logic**:
- Name + Company matching (fuzzy)
- Email domain matching
- LinkedIn profile URL matching
- Cross-platform username matching

**Tools**:
- `FuzzyMatcherTool`: Match names/companies with typos/variations
- `DomainExtractorTool`: Extract company domains from various sources
- `SignalConsolidatorTool`: Merge intent signals from multiple platforms

---

### 6. Lead Qualification & Scoring Agent

**agents.yaml**:
```yaml
lead_scorer:
  role: "B2B Sales Qualification Expert"
  goal: "Score all leads 0-100 based on intent strength, timing, decision authority, and company fit"
  backstory: |
    You're a former VP of Sales with 15 years of enterprise sales experience. You've closed thousands
    of deals and you know exactly what a qualified lead looks like. You understand that a VP of Sales
    who posted "Salesforce is killing our budget" 3 days ago is a 95/100 score. You know that a junior
    marketing coordinator who liked a post about CRM tools is a 20/100 score. You're ruthless about
    qualification because you've seen teams waste time on bad leads. You prioritize based on: explicit
    intent signals, timing recency, decision-making authority, budget indicators, and company fit.
    Your scoring has historically predicted 87% of closed deals.
```

**Scoring Algorithm**:

```python
score = (
    intent_signal_strength * 0.35 +      # 0-35 points
    timing_recency * 0.25 +              # 0-25 points
    decision_authority * 0.20 +          # 0-20 points
    company_fit * 0.15 +                 # 0-15 points
    competitive_pressure * 0.05          # 0-5 points
)

# Intent Signal Strength (0-35)
# - Explicit request for help: 35 points
# - Direct competitor complaint: 30 points
# - Evaluating alternatives: 25 points
# - Problem discussion: 20 points
# - Topic engagement: 10 points

# Timing Recency (0-25)
# - Last 7 days: 25 points
# - Last 30 days: 20 points
# - Last 90 days: 15 points
# - Older: 5 points

# Decision Authority (0-20)
# - C-level: 20 points
# - VP level: 18 points
# - Director: 15 points
# - Manager: 10 points
# - IC: 5 points

# Company Fit (0-15)
# - Perfect ICP match: 15 points
# - Good fit: 12 points
# - Acceptable: 8 points
# - Stretch: 4 points

# Competitive Pressure (0-5)
# - Evaluating 3+ alternatives: 5 points
# - Comparing 2 options: 3 points
# - Mentioned competitor: 2 points
```

**Tools**:
- `IntentClassifierTool`: Classify intent signals (request, complaint, evaluation)
- `TitleAuthorityTool`: Determine decision-making authority from job title
- `ICPMatcherTool`: Score company fit against Ideal Customer Profile
- `RecencyCalculatorTool`: Calculate days since signal

---

### 7. Enrichment & Contact Finding Agent

**agents.yaml**:
```yaml
enrichment_specialist:
  role: "Contact Information Specialist"
  goal: "Enrich all qualified leads with verified email addresses and complete company data"
  backstory: |
    You're a contact data expert who's been building prospect databases for 10 years. You understand
    email patterns: tech companies use firstname.lastname@, startups often use first@, enterprises
    might use firstnamel@. You know how to extract company domains from LinkedIn profiles, Twitter bios,
    and Reddit post history. You're skilled at pattern-based email generation and validation. You also
    know that "DataTech Inc." needs to be matched to "datatech.com" or "datatechinc.com"—you try all
    variations. You don't just guess emails; you use multiple signals to build confidence.
```

**Email Pattern Strategies**:

```python
# Common patterns to try:
patterns = [
    "{first}.{last}@{domain}",          # john.smith@company.com
    "{first}@{domain}",                  # john@company.com
    "{first}{last}@{domain}",            # johnsmith@company.com
    "{first}.{last_initial}@{domain}",   # john.s@company.com
    "{first_initial}{last}@{domain}",    # jsmith@company.com
    "{first_initial}.{last}@{domain}",   # j.smith@company.com
]

# Domain extraction logic:
# 1. Check LinkedIn profile for company website
# 2. Google search: "[Company Name] official website"
# 3. Pattern matching: "CompanyName" → "companyname.com"
# 4. Try variations: .com, .io, .co, .ai (for tech companies)
```

**Company Data Enrichment**:
- Company size (employee count from LinkedIn)
- Industry/sector
- Location/HQ
- Recent news (funding, leadership, growth)
- Tech stack (from job postings)

**Tools**:
- `EmailPatternGeneratorTool`: Generate email variations
- `DomainFinderTool`: Extract company domain from multiple sources
- `CompanyDataTool`: Enrich with firmographic data
- `NameParserTool`: Parse full names into first/last components

---

## Tool Specifications

### 1. ApifyLinkedInSearchTool

**Purpose**: Search LinkedIn for profiles matching specific criteria

**Input Schema**:
```python
class LinkedInSearchInput(BaseModel):
    keywords: str = Field(..., description="Search keywords (job titles, skills, pain points)")
    location: Optional[str] = Field(None, description="Geographic location filter")
    company_size: Optional[str] = Field(None, description="Company size (1-10, 11-50, 51-200, etc.)")
    max_results: int = Field(default=100, description="Maximum profiles to return")
```

**Output**: List of LinkedIn profile URLs + basic info (name, title, company)

**Apify Actor**: `apify/linkedin-profile-scraper`

**Implementation**:
```python
from crewai.tools import BaseTool
import httpx
import os

class ApifyLinkedInSearchTool(BaseTool):
    name: str = "LinkedIn Profile Search"
    description: str = """
    Search LinkedIn for professionals matching specific criteria.
    Use this when you need to find decision-makers in target companies or
    people discussing specific topics/pain points. Returns LinkedIn profile
    URLs and basic information (name, title, company).
    """

    def _run(self, keywords: str, location: str = None,
             company_size: str = None, max_results: int = 100) -> str:
        apify_token = os.getenv("APIFY_API_TOKEN")

        # Build search query
        search_input = {
            "startUrls": [],
            "searchKeywords": keywords,
            "maxResults": max_results
        }

        if location:
            search_input["locations"] = [location]

        # Call Apify API
        response = httpx.post(
            f"https://api.apify.com/v2/acts/apify/linkedin-profile-scraper/runs",
            params={"token": apify_token},
            json=search_input,
            timeout=30.0
        )

        # Wait for results and return formatted data
        # ... (polling logic)

        return self._format_results(results)
```

---

### 2. ApifyTwitterSearchTool

**Purpose**: Search Twitter/X for tweets matching keywords

**Input Schema**:
```python
class TwitterSearchInput(BaseModel):
    search_query: str = Field(..., description="Twitter search query (keywords, hashtags, @mentions)")
    max_tweets: int = Field(default=100, description="Maximum tweets to retrieve")
    filter_type: str = Field(default="top", description="Filter: 'top', 'latest', 'people'")
```

**Output**: List of tweets with user info, content, engagement metrics

**Apify Actor**: `apify/twitter-scraper`

---

### 3. ApifyRedditSearchTool

**Purpose**: Search Reddit for posts/comments matching keywords

**Input Schema**:
```python
class RedditSearchInput(BaseModel):
    search_query: str = Field(..., description="Reddit search query")
    subreddit: Optional[str] = Field(None, description="Limit to specific subreddit (or 'all')")
    max_results: int = Field(default=100, description="Maximum posts to retrieve")
    time_filter: str = Field(default="month", description="Time filter: day/week/month/year/all")
```

**Output**: List of Reddit posts with author, content, score, subreddit

**Apify Actor**: `trudax/reddit-scraper`

---

### 4. ApifyGoogleSearchTool

**Purpose**: Search Google for recent news/articles

**Input Schema**:
```python
class GoogleSearchInput(BaseModel):
    query: str = Field(..., description="Google search query")
    max_results: int = Field(default=50, description="Maximum results")
    date_range: str = Field(default="d30", description="Date range: d7, d30, d90")
```

**Output**: List of search results with title, URL, snippet, date

**Apify Actor**: `apify/google-search-scraper`

---

### 5. IntentClassifierTool

**Purpose**: Classify the strength and type of buying intent signal

**Logic**:
```python
class IntentClassifierTool(BaseTool):
    name: str = "Intent Signal Classifier"
    description: str = "Analyze text to determine buying intent type and strength"

    def _run(self, text: str) -> dict:
        # Use Claude to classify intent
        intent_types = {
            "explicit_request": 35,      # "Does anyone know..."
            "competitor_complaint": 30,   # "[Competitor] is terrible"
            "evaluation": 25,             # "Comparing X vs Y"
            "problem_discussion": 20,     # "We're struggling with..."
            "topic_engagement": 10        # Liked/commented on topic
        }

        # Analyze text for intent signals
        # Return: {"intent_type": "explicit_request", "score": 35, "reasoning": "..."}
```

---

### 6. EmailPatternGeneratorTool

**Purpose**: Generate email address patterns from name and domain

**Logic**:
```python
class EmailPatternGeneratorTool(BaseTool):
    name: str = "Email Pattern Generator"
    description: str = "Generate likely email patterns from first name, last name, and company domain"

    def _run(self, first_name: str, last_name: str, domain: str) -> list:
        patterns = [
            f"{first_name.lower()}.{last_name.lower()}@{domain}",
            f"{first_name.lower()}@{domain}",
            f"{first_name.lower()}{last_name.lower()}@{domain}",
            f"{first_name[0].lower()}{last_name.lower()}@{domain}",
            f"{first_name[0].lower()}.{last_name.lower()}@{domain}",
        ]

        return patterns
```

---

## Project Structure

```
wrrk-pilot/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entry point
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── prospecting.py     # Prospecting endpoints
│   │   │   │   └── health.py          # Health check endpoint
│   │   │
│   │   ├── crews/
│   │   │   ├── __init__.py
│   │   │   ├── base_crew.py           # Base crew configuration
│   │   │   │
│   │   │   ├── linkedin/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── crew.py            # LinkedIn crew definition
│   │   │   │   ├── agents.yaml        # Agent configurations
│   │   │   │   └── tasks.yaml         # Task definitions
│   │   │   │
│   │   │   ├── twitter/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── crew.py
│   │   │   │   ├── agents.yaml
│   │   │   │   └── tasks.yaml
│   │   │   │
│   │   │   ├── reddit/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── crew.py
│   │   │   │   ├── agents.yaml
│   │   │   │   └── tasks.yaml
│   │   │   │
│   │   │   ├── google/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── crew.py
│   │   │   │   ├── agents.yaml
│   │   │   │   └── tasks.yaml
│   │   │   │
│   │   │   ├── aggregation/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── crew.py
│   │   │   │   ├── agents.yaml
│   │   │   │   └── tasks.yaml
│   │   │   │
│   │   │   ├── qualification/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── crew.py
│   │   │   │   ├── agents.yaml
│   │   │   │   └── tasks.yaml
│   │   │   │
│   │   │   └── enrichment/
│   │   │       ├── __init__.py
│   │   │       ├── crew.py
│   │   │       ├── agents.yaml
│   │   │       └── tasks.yaml
│   │   │
│   │   ├── flows/
│   │   │   ├── __init__.py
│   │   │   └── prospecting_flow.py    # Main orchestration flow
│   │   │
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── apify_linkedin.py      # LinkedIn Apify tool
│   │   │   ├── apify_twitter.py       # Twitter Apify tool
│   │   │   ├── apify_reddit.py        # Reddit Apify tool
│   │   │   ├── apify_google.py        # Google Search tool
│   │   │   ├── intent_classifier.py   # Intent classification
│   │   │   ├── email_pattern.py       # Email pattern generator
│   │   │   ├── domain_finder.py       # Domain extraction
│   │   │   └── lead_scorer.py         # Lead scoring logic
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py             # Pydantic models (API)
│   │   │   ├── database.py            # SQLAlchemy models
│   │   │   └── state.py               # Flow state models
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Configuration settings
│   │   │   ├── llm_config.py          # LLM configuration
│   │   │   └── database.py            # Database connection
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logging.py             # Logging utilities
│   │       ├── monitoring.py          # Monitoring/metrics
│   │       └── apify_client.py        # Apify API client wrapper
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_tools.py
│   │   ├── test_crews.py
│   │   └── test_api.py
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # Main prospecting page
│   │   │   └── api/
│   │   │       └── proxy/
│   │   │           └── route.ts       # Proxy to FastAPI
│   │   │
│   │   ├── components/
│   │   │   ├── InputPanel.tsx         # Left panel - user input
│   │   │   ├── ResultsPanel.tsx       # Right panel - results
│   │   │   ├── AgentActivityLog.tsx   # Real-time agent activity
│   │   │   ├── LeadsTable.tsx         # Results table
│   │   │   └── ProgressBar.tsx        # Progress indicator
│   │   │
│   │   ├── hooks/
│   │   │   └── useProspecting.ts      # Prospecting API hook
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client
│   │   │   └── types.ts               # TypeScript types
│   │   │
│   │   └── styles/
│   │       └── globals.css
│   │
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
│
├── docs/
│   ├── API.md                         # API documentation
│   ├── AGENTS.md                      # Agent documentation
│   └── DEPLOYMENT.md                  # Deployment guide
│
├── PROSPECTING_STRATEGY.md            # Strategy document (existing)
├── MVP_PLAN.md                        # This file
├── README.md
└── docker-compose.yml                 # Local development setup
```

---

## Breadth-First Processing Strategy

### Problem Statement

Traditional approach: Process one lead deeply at a time
- Search for "Sarah Johnson, CMO at DataTech"
- Research Sarah's background
- Find Sarah's email
- Move to next lead

**This is too slow** for MVP validation.

### Solution: Breadth-First Batch Processing

Process 50-100 leads simultaneously through each stage:

```python
# Stage 1: SCRAPE (parallel across platforms)
linkedin_results = scrape_linkedin("new CMO hired", max_results=100)
twitter_results = scrape_twitter("looking for CRM alternative", max_results=100)
reddit_results = scrape_reddit("Salesforce too expensive", max_results=100)

# Result: ~300 raw leads

# Stage 2: AGGREGATE
all_leads = merge_and_deduplicate([linkedin_results, twitter_results, reddit_results])
# Result: ~200 unique leads (after deduplication)

# Stage 3: QUALIFY (batch scoring)
scored_leads = score_all_leads(all_leads)
qualified_leads = filter_by_score(scored_leads, min_score=60)
# Result: ~100 qualified leads

# Stage 4: ENRICH (batch email generation)
enriched_leads = enrich_all_leads(qualified_leads)
# Result: ~100 enriched leads with emails
```

### Implementation in CrewAI Flow

```python
from crewai import Flow, start, listen, router, and_
from pydantic import BaseModel

class ProspectingState(BaseModel):
    # Input
    search_query: str = ""
    target_industry: str = ""
    target_company_size: str = ""

    # Progress tracking
    total_raw_leads: int = 0
    total_unique_leads: int = 0
    total_qualified_leads: int = 0
    total_enriched_leads: int = 0
    progress_percentage: float = 0.0
    current_stage: str = ""

    # Agent activity log
    agent_activities: List[str] = []

    # Results
    linkedin_leads: List[dict] = []
    twitter_leads: List[dict] = []
    reddit_leads: List[dict] = []
    google_leads: List[dict] = []
    merged_leads: List[dict] = []
    qualified_leads: List[dict] = []
    final_leads: List[dict] = []

class ProspectingFlow(Flow[ProspectingState]):

    @start()
    def initialize(self):
        """Initialize prospecting flow."""
        self.state.current_stage = "Initializing"
        self.state.agent_activities.append("[System] Starting prospecting job")
        return ["linkedin", "twitter", "reddit", "google"]

    @listen("linkedin")
    def scrape_linkedin(self):
        """Scrape LinkedIn in parallel."""
        self.state.current_stage = "Scraping LinkedIn"
        self.state.agent_activities.append("[LinkedIn Agent] Searching for decision-makers...")

        # Execute LinkedIn crew
        linkedin_crew = LinkedInCrew()
        result = linkedin_crew.crew().kickoff({
            "search_query": self.state.search_query,
            "max_results": 100
        })

        self.state.linkedin_leads = result.leads
        self.state.total_raw_leads += len(result.leads)
        self.state.agent_activities.append(f"[LinkedIn Agent] Found {len(result.leads)} prospects")
        self.state.progress_percentage = 15.0

        return "aggregation_gate"

    @listen("twitter")
    def scrape_twitter(self):
        """Scrape Twitter in parallel."""
        self.state.current_stage = "Scraping Twitter"
        self.state.agent_activities.append("[Twitter Agent] Hunting for intent signals...")

        # Execute Twitter crew
        twitter_crew = TwitterCrew()
        result = twitter_crew.crew().kickoff({
            "search_query": self.state.search_query,
            "max_results": 100
        })

        self.state.twitter_leads = result.leads
        self.state.total_raw_leads += len(result.leads)
        self.state.agent_activities.append(f"[Twitter Agent] Found {len(result.leads)} prospects")
        self.state.progress_percentage = 30.0

        return "aggregation_gate"

    @listen("reddit")
    def scrape_reddit(self):
        """Scrape Reddit in parallel."""
        self.state.current_stage = "Scraping Reddit"
        self.state.agent_activities.append("[Reddit Agent] Detecting pain points...")

        # Execute Reddit crew
        reddit_crew = RedditCrew()
        result = reddit_crew.crew().kickoff({
            "search_query": self.state.search_query,
            "max_results": 100
        })

        self.state.reddit_leads = result.leads
        self.state.total_raw_leads += len(result.leads)
        self.state.agent_activities.append(f"[Reddit Agent] Found {len(result.leads)} prospects")
        self.state.progress_percentage = 45.0

        return "aggregation_gate"

    @listen("google")
    def scrape_google(self):
        """Scrape Google News in parallel."""
        self.state.current_stage = "Researching Company Triggers"
        self.state.agent_activities.append("[Google Agent] Finding company triggers...")

        # Execute Google crew
        google_crew = GoogleCrew()
        result = google_crew.crew().kickoff({
            "search_query": self.state.search_query,
            "max_results": 50
        })

        self.state.google_leads = result.leads
        self.state.total_raw_leads += len(result.leads)
        self.state.agent_activities.append(f"[Google Agent] Found {len(result.leads)} companies")
        self.state.progress_percentage = 60.0

        return "aggregation_gate"

    @listen(and_("aggregation_gate", "aggregation_gate", "aggregation_gate", "aggregation_gate"))
    def aggregate_leads(self):
        """Wait for all platform crews, then aggregate."""
        self.state.current_stage = "Aggregating & Deduplicating"
        self.state.agent_activities.append(f"[Aggregation Agent] Processing {self.state.total_raw_leads} leads...")

        # Execute aggregation crew
        aggregation_crew = AggregationCrew()
        result = aggregation_crew.crew().kickoff({
            "linkedin_leads": self.state.linkedin_leads,
            "twitter_leads": self.state.twitter_leads,
            "reddit_leads": self.state.reddit_leads,
            "google_leads": self.state.google_leads
        })

        self.state.merged_leads = result.unique_leads
        self.state.total_unique_leads = len(result.unique_leads)
        self.state.agent_activities.append(
            f"[Aggregation Agent] Merged to {self.state.total_unique_leads} unique prospects"
        )
        self.state.progress_percentage = 70.0

        return "qualify"

    @listen("qualify")
    def qualify_leads(self):
        """Score and qualify all leads."""
        self.state.current_stage = "Qualifying Leads"
        self.state.agent_activities.append(f"[Qualification Agent] Scoring {self.state.total_unique_leads} leads...")

        # Execute qualification crew
        qualification_crew = QualificationCrew()
        result = qualification_crew.crew().kickoff({
            "leads": self.state.merged_leads
        })

        self.state.qualified_leads = result.qualified_leads
        self.state.total_qualified_leads = len(result.qualified_leads)
        self.state.agent_activities.append(
            f"[Qualification Agent] Qualified {self.state.total_qualified_leads} high-intent leads"
        )
        self.state.progress_percentage = 85.0

        return "enrich"

    @listen("enrich")
    def enrich_leads(self):
        """Enrich qualified leads with emails."""
        self.state.current_stage = "Enriching Contact Data"
        self.state.agent_activities.append(
            f"[Enrichment Agent] Finding emails for {self.state.total_qualified_leads} leads..."
        )

        # Execute enrichment crew
        enrichment_crew = EnrichmentCrew()
        result = enrichment_crew.crew().kickoff({
            "leads": self.state.qualified_leads
        })

        self.state.final_leads = result.enriched_leads
        self.state.total_enriched_leads = len(result.enriched_leads)
        self.state.agent_activities.append(
            f"[Enrichment Agent] Enriched {self.state.total_enriched_leads} leads with contact data"
        )
        self.state.progress_percentage = 100.0
        self.state.current_stage = "Complete"

        return result.enriched_leads
```

### Benefits of Breadth-First Approach

1. **Faster validation**: See 100 leads in 5-10 minutes vs 1 lead every 3 minutes
2. **Better quality assessment**: Can evaluate data quality across large sample
3. **Batch efficiency**: One API call for 100 results vs 100 API calls
4. **Cost savings**: Bulk processing is cheaper than individual requests
5. **Real-time demo**: Shows impressive results quickly for MVP testing

---

## Implementation Roadmap

### Week 1: Backend Foundation & Tools

**Days 1-2: Project Setup**
- [ ] Initialize FastAPI project structure
- [ ] Setup PostgreSQL database + pgvector extension
- [ ] Configure environment variables (.env)
- [ ] Install dependencies (CrewAI, FastAPI, SQLAlchemy, etc.)
- [ ] Setup Apify account and get API token
- [ ] Setup Anthropic account and get Claude API key

**Days 3-4: Build Apify Tools**
- [ ] Implement `ApifyLinkedInSearchTool`
- [ ] Implement `ApifyTwitterSearchTool`
- [ ] Implement `ApifyRedditSearchTool`
- [ ] Implement `ApifyGoogleSearchTool`
- [ ] Test all tools with real API calls (validate output format)

**Days 5-7: Build Utility Tools**
- [ ] Implement `IntentClassifierTool`
- [ ] Implement `EmailPatternGeneratorTool`
- [ ] Implement `DomainFinderTool`
- [ ] Implement `LeadScorerTool`
- [ ] Implement `FuzzyMatcherTool` (for deduplication)

### Week 2: Agent System & Orchestration

**Days 8-10: Create Platform Crews**
- [ ] Build LinkedIn Crew (agents.yaml + tasks.yaml + crew.py)
- [ ] Build Twitter Crew
- [ ] Build Reddit Crew
- [ ] Build Google Crew
- [ ] Test each crew independently with sample queries

**Days 11-12: Create Processing Crews**
- [ ] Build Aggregation Crew (deduplication logic)
- [ ] Build Qualification Crew (scoring algorithm)
- [ ] Build Enrichment Crew (email generation)
- [ ] Test each processing crew with sample data

**Days 13-14: Orchestration Flow**
- [ ] Implement `ProspectingFlow` with state management
- [ ] Setup parallel execution for platform crews
- [ ] Setup sequential execution for processing crews
- [ ] Implement progress tracking and activity logging
- [ ] Test end-to-end flow with real query

### Week 3: API, Frontend & Polish

**Days 15-16: FastAPI Backend**
- [ ] Implement `POST /api/v1/prospect/start` endpoint
- [ ] Implement `GET /api/v1/prospect/{job_id}` endpoint
- [ ] Implement `GET /api/v1/prospect/stream` (SSE) endpoint
- [ ] Add background job processing with in-memory queue
- [ ] Add error handling and retry logic
- [ ] Test API endpoints with Postman/curl

**Days 17-19: Next.js Frontend**
- [ ] Setup Next.js project
- [ ] Build `InputPanel` component (left side)
- [ ] Build `ResultsPanel` component (right side)
- [ ] Build `AgentActivityLog` component
- [ ] Build `LeadsTable` component
- [ ] Implement SSE client for real-time updates
- [ ] Connect frontend to FastAPI backend
- [ ] Style UI (Tailwind CSS)

**Days 20-21: Testing & Optimization**
- [ ] End-to-end testing with real prospecting queries
- [ ] Validate lead quality (manually review 50+ leads)
- [ ] Optimize API costs (batch processing, caching)
- [ ] Add monitoring/logging (track costs, errors, timing)
- [ ] Fix bugs and edge cases
- [ ] Polish UI/UX

---

## Configuration Examples

### .env.example

```bash
# Apify
APIFY_API_TOKEN=your_apify_token_here

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/wrrk_pilot

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# CrewAI
CREWAI_STORAGE_DIR=./crew_storage
OPENAI_API_KEY=  # Leave empty if using Claude only

# Rate Limiting (cost control)
MAX_REQUESTS_PER_MINUTE=10
MAX_TOKENS_PER_REQUEST=2048
```

### requirements.txt

```txt
# Core
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-dotenv==1.0.0

# CrewAI
crewai==0.80.0
crewai-tools==0.12.0

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pgvector==0.2.4

# HTTP Client
httpx==0.26.0
aiohttp==3.9.1

# Utilities
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6

# Monitoring
loguru==0.7.2

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
```

### frontend/package.json

```json
{
  "name": "wrrk-pilot-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "next": "14.1.0",
    "typescript": "^5.3.3",
    "@types/react": "^18.2.48",
    "@types/node": "^20.11.5",
    "tailwindcss": "^3.4.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "axios": "^1.6.5",
    "eventsource": "^2.0.2"
  }
}
```

---

## Cost Breakdown & Budget Control

### Monthly Cost Estimate (Target: <$50/month)

#### Apify Costs (Platform Usage)

**Base Plan**: $25/month (after $5 free credit)

**Per-Platform Costs** (for 10,000 leads/month):
- LinkedIn: 10K profiles × $0.003 = **$30**
- Twitter: 10K tweets × $0.0003 = **$3**
- Reddit: 10K posts × $0.002 = **$20**
- Google: 5K searches × $0.002 = **$10**

**Total Apify**: ~$63/month for 10K leads

**Optimization Strategy** (to hit $25-30):
- Start with 3K leads/month during MVP testing
- 3K LinkedIn profiles = $9
- 3K Twitter tweets = $1
- 3K Reddit posts = $6
- 1.5K Google searches = $3
- **Total**: ~$19 + $25 base = **$44/month** ✅

#### Claude API Costs

**Pricing** (Claude Sonnet 4.5):
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens

**Estimated Usage** (for 3K leads):
- Platform scraping: 7 crews × 2K tokens avg = 14K input, 5K output = $0.12
- Aggregation: 1 crew × 10K tokens = 10K input, 3K output = $0.08
- Qualification: 1 crew × 50K tokens (scoring 3K leads) = 50K input, 20K output = $0.45
- Enrichment: 1 crew × 30K tokens = 30K input, 15K output = $0.32

**Total Claude**: ~$1/month for 3K leads, ~$3-5/month for 10K leads

#### Total MVP Budget

**Ultra-Lean** (3K leads/month):
- Apify: $25 base + $19 usage = $44
- Claude API: $1-2
- Hosting: Free (Vercel + Railway free tiers)
- **Total**: **~$45-46/month** ✅

**Scaled** (10K leads/month):
- Apify: $63
- Claude API: $3-5
- Hosting: Free
- **Total**: **~$66-68/month**

### Cost Control Strategies

1. **Batch Processing**: Process leads in batches to reduce API calls
2. **Caching**: Cache Apify results for 24 hours (same query = free)
3. **Rate Limiting**: Set `max_rpm=10` in CrewAI to avoid rate limit charges
4. **Token Limits**: Set `max_tokens=2048` per agent to control Claude costs
5. **Selective Enrichment**: Only enrich leads with score > 70
6. **Platform Prioritization**: Start with LinkedIn + Reddit (cheapest), add Twitter/Google later

---

## Success Metrics for MVP

### Quantitative Metrics

1. **Lead Volume**: 50-100 qualified leads per search query
2. **Lead Quality Score**: Average score > 65/100
3. **Email Accuracy**: >80% valid email patterns
4. **Processing Time**: <10 minutes for 100 leads
5. **Cost per Lead**: <$0.50 per qualified lead

### Qualitative Metrics

1. **Intent Signal Strength**: Leads should show explicit buying signals (not just titles)
2. **Data Freshness**: Intent signals < 30 days old
3. **Decision Maker Accuracy**: >70% of leads are actual decision-makers
4. **Contextual Relevance**: Outreach context makes sense (not generic)

### MVP Validation Questions

- [ ] Do the leads show real buying intent? (manual review of 50 leads)
- [ ] Are the emails valid? (test 20 emails)
- [ ] Would I reach out to these people? (quality check)
- [ ] Is this better than Apollo? (side-by-side comparison)
- [ ] Can we charge $100-200 per 100 leads? (pricing validation)

---

## Next Steps After MVP

### Phase 2: Production Hardening

1. **Database persistence**: Save jobs, leads, history
2. **Redis queue**: Replace in-memory job queue
3. **Email verification**: Integrate Hunter.io or Neverbounce
4. **User authentication**: Add login/signup
5. **Payment integration**: Stripe for lead purchases
6. **Monitoring**: Setup Sentry, LogRocket, or AgentOps

### Phase 3: Advanced Features

1. **CRM integration**: Push leads to Salesforce, HubSpot
2. **Outreach automation**: Generate personalized emails
3. **Lead scoring refinement**: ML-based scoring
4. **Custom search alerts**: Email when new leads found
5. **Team collaboration**: Share leads, assign territories
6. **Analytics dashboard**: ROI tracking, conversion metrics

### Phase 4: Scale & Optimization

1. **Kubernetes deployment**: Auto-scaling for high volume
2. **Multi-region**: Deploy globally for speed
3. **Advanced caching**: Redis for results, embeddings
4. **A/B testing**: Test different agent strategies
5. **Enterprise features**: SSO, audit logs, SLA guarantees

---

## FAQ

### How is this different from Apollo?

**Apollo**: Static database of 275M contacts (mostly outdated)
- Selling contact info with no buying intent
- Same leads given to your competitors
- 2% response rates (cold outreach)

**Our Tool**: Real-time intent detection engine
- Finding people actively looking for solutions RIGHT NOW
- Unique leads based on your specific search
- 10-15% response rates (warm outreach with context)

### Why breadth-first instead of depth-first?

**Depth-first** (traditional):
- 1 lead → research → qualify → enrich → next lead
- Takes 3-5 minutes per lead
- 100 leads = 5-8 hours

**Breadth-first** (our approach):
- Find 100 leads → qualify all → enrich all
- Takes 5-10 minutes for 100 leads
- Better for batch processing and cost optimization

### Can we really hit <$50/month budget?

Yes, by:
- Processing 3K leads/month during MVP (enough to validate)
- Using Apify's pay-per-result model (only pay for what you use)
- Optimizing Claude prompts to reduce token usage
- Caching results to avoid duplicate API calls
- Using free hosting tiers (Vercel, Railway)

Once validated, we can scale to 10K+ leads at ~$70/month.

### How accurate will the emails be?

**Pattern-based emails** (firstname.lastname@domain.com):
- ~60-70% accurate for tech companies
- ~40-50% accurate for enterprises (they use weird patterns)

**To improve**:
- Add email verification API (Hunter.io: $49/month for 1K verifications)
- Try multiple patterns and validate
- Prioritize LinkedIn profiles with email shown

**MVP approach**: Generate patterns, let users verify manually

### What if Apify scraping fails?

**Mitigation strategies**:
1. Retry logic (3 attempts with exponential backoff)
2. Fallback to alternative Apify actors (there are multiple for each platform)
3. Direct API integration (Reddit API, Twitter API) as backup
4. Error tracking and monitoring (log all failures)

**Reality**: Apify has 99%+ success rate for these actors, failures are rare.

---

## Conclusion

This MVP focuses on **speed, cost-efficiency, and lead quality validation**. By using breadth-first processing, we can quickly validate whether intent-based prospecting generates better leads than Apollo's static database approach.

**Key Success Factors**:
1. Agent personalities must produce high-quality intent classification
2. Breadth-first processing must be fast (<10 min for 100 leads)
3. Lead quality must be visibly better than Apollo
4. Cost must stay under $50/month during testing

**MVP Timeline**: 3 weeks to first working version
**Budget**: $45-50/month
**Target**: 50-100 qualified leads per search query

Let's build it! 🚀
