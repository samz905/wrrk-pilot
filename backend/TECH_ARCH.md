# Technical Architecture Documentation

> **Last Updated:** 2025-11-30
> **Version:** 3.6 (Compensation Agent + LLM Decision Maker Selection)

This document serves as the canonical reference for the prospecting system architecture, patterns, and design decisions.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Core Components](#core-components)
4. [Tool Design Patterns](#tool-design-patterns)
5. [Stepped Tools Pattern](#stepped-tools-pattern)
6. [Structured Output Patterns](#structured-output-patterns)
7. [External Services](#external-services)
8. [Configuration](#configuration)
9. [Data Flow](#data-flow)
10. [Active vs Discontinued Features](#active-vs-discontinued-features)
11. [Version History](#version-history)
12. [Test Results & Quality Observations](#test-results--quality-observations)

---

## Architecture Overview

### Current Architecture (v3.6)

The system uses a **Supervisor Orchestrator with Parallel Workers + Compensation Agent** architecture:
- 1 LLM orchestrator that plans, reviews, and fixes
- 3 Python worker classes running in PARALLEL via ThreadPoolExecutor
- Workers execute deterministic steps, orchestrator handles intelligence
- **LLM Compensation Agent** decides what to run when target not met
- **LLM Decision Maker Selection** finds role-appropriate contacts (not just founders)
- ~5-9 min execution depending on target size

```
┌─────────────────────────────────────────────────────────────────┐
│                 SupervisorOrchestrator v3.5                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Phase 1: PLAN STRATEGY (LLM Agent)                         │ │
│  │  - Analyze product description                               │ │
│  │  - Generate Reddit queries (actual search strings!)          │ │
│  │  - Identify competitors                                      │ │
│  │  - Set TechCrunch industry focus                            │ │
│  │  → Output: StrategyPlan                                      │ │
│  └─────────────────────┬───────────────────────────────────────┘ │
│                        │                                         │
│  ┌─────────────────────▼───────────────────────────────────────┐ │
│  │  Phase 2: PARALLEL WORKERS (ThreadPoolExecutor)             │ │
│  │                                                              │ │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │ │
│  │   │RedditWorker │  │TechCrunch   │  │CompetitorWorker │     │ │
│  │   │  (Python)   │  │  Worker     │  │   (Python)      │     │ │
│  │   │             │  │  (Python)   │  │                 │     │ │
│  │   │ search →    │  │ fetch_par → │  │ identify →      │     │ │
│  │   │ score →     │  │ select →    │  │ scrape_posts →  │     │ │
│  │   │ extract →   │  │ extract →   │  │ extract_engagers│     │ │
│  │   │ filter      │  │ SERP_dm →   │  │ → filter        │     │ │
│  │   │             │  │ filter      │  │                 │     │ │
│  │   └──────┬──────┘  └──────┬──────┘  └────────┬────────┘     │ │
│  │          │                │                  │               │ │
│  │          └────────────────┼──────────────────┘               │ │
│  │                           ▼                                  │ │
│  │     ┌─────────────────────────────────────────────────────┐  │ │
│  │     │ INTRA-STEP REVIEW (Orchestrator reviews each step)  │  │ │
│  │     │ - Approve good results                              │  │ │
│  │     │ - Retry failed steps                                │  │ │
│  │     │ - Skip if repeated failures                         │  │ │
│  │     └─────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Phase 3: AGGREGATE                                         │ │
│  │  - Combine leads from all workers                           │ │
│  │  - Deduplicate by username                                  │ │
│  │  - Sort by intent_score (warmest first)                     │ │
│  │  - Return top N leads                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Orchestrator Only Orchestrates**: No atomic work - just plan, review, fix
2. **Parallel Execution**: Workers run concurrently via ThreadPoolExecutor
3. **Deterministic Workers**: Python classes with predictable step execution
4. **Intra-Step Review**: Orchestrator reviews each step before proceeding
5. **Mandatory Seller Filtering**: Every platform runs `filter_sellers` before leads are finalized
6. **Strict Mode**: Never accept empty/bad results - retry or skip
7. **Field Mapping**: Tools use `intent_signal`/`source_platform`, exporter maps to CSV fields

---

## Directory Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py              # Environment configuration
│   │
│   ├── supervisor_orchestrator.py # PRIMARY v3.5 - Orchestrator with parallel workers
│   │
│   ├── workers/                   # NEW v3.5 - Python worker classes
│   │   ├── reddit_worker.py       # RedditWorker (search → score → extract → filter)
│   │   ├── techcrunch_worker.py   # TechCrunchWorker (fetch → select → extract → SERP_dm)
│   │   └── competitor_worker.py   # CompetitorWorker (identify → scrape → extract)
│   │
│   ├── crews/
│   │   └── orchestrator/          # LEGACY - CrewAI crew (replaced by supervisor)
│   │       ├── crew.py            # OrchestratorCrew class
│   │       ├── agents.yaml        # Agent role, goal, backstory
│   │       └── tasks.yaml         # Task definitions
│   │
│   ├── flows/
│   │   └── prospecting_flow_v2.py # LEGACY - Event-driven flow orchestration
│   │
│   ├── tools/
│   │   ├── stepped/               # Multi-step tools (used by workers)
│   │   │   ├── reddit_tools.py    # ACTIVE: search, score, extract
│   │   │   ├── techcrunch_tools.py# ACTIVE: fetch, fetch_parallel, select, extract, serp_dm
│   │   │   ├── competitor_tools.py# ACTIVE v3.4: identify, scrape competitor posts
│   │   │   ├── filter_sellers.py  # ACTIVE: LLM buyer/seller classification
│   │   │   ├── g2_tools.py        # DISCONTINUED: G2 reviews
│   │   │   └── upwork_tools.py    # DISCONTINUED: Upwork jobs
│   │   │
│   │   ├── serp_decision_makers.py# ACTIVE v3.4: SERP-based decision maker finder
│   │   ├── apify_linkedin_company_posts.py  # ACTIVE v3.4: LinkedIn company posts
│   │   ├── utility_tools.py       # NEW v3.5: DeduplicateLeadsTool, ValidateLeadsTool
│   │   │
│   │   ├── composite/             # Parallel execution tools
│   │   │   ├── intent_signal_hunter.py
│   │   │   ├── company_trigger_scanner.py
│   │   │   └── decision_maker_finder.py
│   │   │
│   │   ├── legacy/                # Deprecated tools (kept for reference)
│   │   │   ├── apify_google_serp.py
│   │   │   └── apify_website_crawler.py
│   │   │
│   │   └── [root level tools]     # Apify integrations, scoring, utilities
│   │
│   ├── utils/
│   │   ├── agent_logger.py        # Execution trace logging
│   │   └── lead_exporter.py       # JSON/CSV export (with field mapping)
│   │
│   └── api/
│       └── v1/
│           └── prospect.py        # FastAPI endpoints
│
├── legacy/                        # All discontinued code
│
├── test_output/                   # Test execution artifacts
│
├── test_supervisor.py             # NEW v3.5 - Test harness for supervisor
│
└── TECH_ARCH.md                   # This file
```

---

## Core Components

### 1. SupervisorOrchestrator (`app/supervisor_orchestrator.py`) - PRIMARY v3.5

The main orchestrator that coordinates all prospecting work:

```python
class SupervisorOrchestrator:
    """
    LLM-based orchestrator that supervises Python workers.
    - Plans strategy (LLM decides queries, competitors, focus)
    - Launches 3 workers in PARALLEL (ThreadPoolExecutor)
    - Reviews each worker's output
    - Retries or fixes issues
    - Aggregates and deduplicates final leads
    """

    def run(self, product_description: str, target_leads: int = 50) -> OrchestratorResult:
        # Phase 1: Plan strategy
        strategy = self._plan_strategy(product_description, target_leads)

        # Phase 2: Run workers in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(reddit_worker.run, ...): "reddit",
                executor.submit(techcrunch_worker.run, ...): "techcrunch",
                executor.submit(competitor_worker.run, ...): "competitor",
            }

        # Phase 3: Aggregate results
        return self._aggregate_results(all_leads)
```

**Output Model:**
```python
@dataclass
class OrchestratorResult:
    success: bool = False
    leads: List[Dict] = field(default_factory=list)
    total_leads: int = 0
    hot_leads: int = 0      # score >= 80
    warm_leads: int = 0     # score 60-79
    reddit_leads: int = 0
    techcrunch_leads: int = 0
    competitor_leads: int = 0
    sellers_removed: int = 0
    duplicates_removed: int = 0
    platforms_searched: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)
```

### 2. Python Workers (`app/workers/`) - NEW v3.5

Workers are Python classes that execute deterministic step sequences:

| Worker | Steps | Target |
|--------|-------|--------|
| `RedditWorker` | search → score → extract → filter_sellers | ~33% of leads |
| `TechCrunchWorker` | fetch_parallel → select → extract → serp_dm → filter | ~33% of leads |
| `CompetitorWorker` | identify → scrape_posts → extract_engagers → filter | ~33% of leads |

**Worker Interface:**
```python
@dataclass
class WorkerResult:
    success: bool = False
    data: Any = None
    error: Optional[str] = None
    step: str = ""
    step_number: int = 0
    leads_count: int = 0
    trace: List[str] = field(default_factory=list)

class RedditWorker:
    def run(self, queries: List[str], target: int, product_context: str) -> WorkerResult:
        # Step 1: Search
        step1_result = self.step_search(queries[0])
        # Step 2: Score
        step2_result = self.step_score(posts, query)
        # Step 3: Extract
        step3_result = self.step_extract(high_quality_posts, query)
        # Step 4: Filter sellers
        step4_result = self.step_filter(leads)
        return WorkerResult(success=True, data=leads)
```

### 3. Strategy Planning (LLM)

The orchestrator uses a CrewAI Agent for strategy planning:

```python
class StrategyPlan(BaseModel):
    product_category: str = Field(description="Type of product")
    competitors: List[str] = Field(description="Likely competitors")
    reddit_queries: List[str] = Field(description="ACTUAL search query strings")
    techcrunch_focus: str = Field(description="Industry focus for TechCrunch")
    target_titles: List[str] = Field(description="Decision maker titles")
```

**IMPORTANT:** Reddit queries must be actual search strings:
- ✅ Good: `["best ML observability tools", "how to monitor ML models"]`
- ❌ Bad: `["direct", "pain_based", "alternative"]` (category labels, not queries!)

### 4. LEGACY: OrchestratorCrew (`crews/orchestrator/`)

Multi-agent crew with 5 focused agents and task chaining:

**Agents (`agents.yaml`):**

| Agent | Role | Tools |
|-------|------|-------|
| `strategy_planner` | Analyze product, create plan | None (reasoning only) |
| `reddit_specialist` | Execute Reddit workflow | reddit_search, reddit_score, reddit_extract, filter_sellers |
| `techcrunch_specialist` | Execute TechCrunch workflow (SERP-based) | techcrunch_*, serp_decision_makers, linkedin_*, filter_sellers |
| `competitor_specialist` | Execute competitor displacement | competitor_identify, competitor_scrape, filter_sellers |
| `lead_aggregator` | Combine, filter, sort leads | filter_sellers |

**Tasks (`tasks.yaml`):**

| Task | Agent | Context | Output Model |
|------|-------|---------|--------------|
| `plan_strategy` | strategy_planner | (input) | `StrategyPlan` |
| `reddit_prospecting` | reddit_specialist | plan_strategy | `RedditLeads` |
| `techcrunch_prospecting` | techcrunch_specialist | plan_strategy | `TechCrunchLeads` |
| `competitor_prospecting` | competitor_specialist | plan_strategy | `CompetitorLeads` |
| `aggregate_leads` | lead_aggregator | reddit + techcrunch + competitor | `ProspectingOutput` |

**Pydantic Output Models (`crew.py`):**
```python
class StrategyPlan(BaseModel):
    product_category: str
    competitors: List[str]
    reddit_queries: List[str]
    techcrunch_focus: str
    target_titles: List[str]
    lead_distribution: str

class RedditLeads(BaseModel):
    leads: List[Lead]
    count: int
    queries_used: List[str]
    workflow_trace: str

class TechCrunchLeads(BaseModel):
    leads: List[Lead]
    count: int
    companies_found: List[str]
    workflow_trace: str

class CompetitorLeads(BaseModel):  # v3.4
    leads: List[Lead]
    count: int
    competitors_scraped: List[str]
    workflow_trace: str

class ProspectingOutput(BaseModel):
    leads: List[Lead]  # SORTED by intent_score (warmest first)
    total_leads: int
    hot_leads: int
    warm_leads: int
    reddit_leads_count: int
    techcrunch_leads_count: int
    competitor_leads_count: int  # v3.4
    sellers_removed: int
    duplicates_removed: int
    platforms_searched: List[str]
    strategies_used: List[str]
    summary: str
```

---

## Tool Design Patterns

### Input Schema Pattern

All tools use Pydantic for strict input validation:

```python
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(default=50, description="Max results")
    optional_param: Optional[str] = Field(default=None, description="Optional filter")

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = """Tool description shown to agent"""
    args_schema: Type[BaseModel] = MyToolInput

    def _run(self, query: str, limit: int = 50, optional_param: str = None) -> str:
        # Implementation
        return json.dumps(result)
```

### Output Structure Pattern

All tools return JSON with consistent structure:

```python
{
    # Data
    "results": [...],
    "count": N,

    # State communication
    "done": "What was completed",
    "next": "What agent should do next",
    "warning": "Important caveats (optional)",

    # Quality indicators
    "quality": "HIGH" | "LOW",
    "error": "Error message if failed (optional)"
}
```

### Recommendation Pattern

Tools guide agent with `recommendation` or `next` field:

```python
# Success case
"next": "Proceed to reddit_score with these posts"

# Retry case
"next": "Try different query like 'frustrated with [competitor]'"

# Skip case
"next": "Skip to TechCrunch strategy"

# Complete case
"next": "Leads ready for outreach"
```

---

## Stepped Tools Pattern

Stepped tools expose multi-step processes so agent can reason after each step.

### Architecture Principle

```
┌─────────────────────────────────────────────────────────────┐
│  WRONG: Tool internally calls other tools                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ extract_companies():                                    ││
│  │   companies = extract(articles)                         ││
│  │   linkedin_urls = LinkedInBatchSearch(companies)  ← BAD ││
│  │   return companies_with_urls                            ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  RIGHT: Each tool does ONE thing, agent calls next          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Agent calls: extract_companies(articles)                ││
│  │   → returns companies, next="Call linkedin_batch_search"││
│  │                                                         ││
│  │ Agent calls: linkedin_batch_search(companies)           ││
│  │   → returns urls, next="Call linkedin_employees_search" ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Reddit Stepped Tools

```python
# Step 1: Search
class RedditSearchSteppedTool:
    """Returns posts + quality assessment"""
    # Agent decision: Continue? Retry with different query? Skip?

# Step 2: Score
class RedditScoreTool:
    """Scores posts for buying intent (0-100)"""
    # Agent decision: Enough high scores? Proceed or retry?

# Step 3: Extract
class RedditExtractTool:
    """Extracts leads from scored posts"""
    # WARNING: Must run filter_sellers next!
```

### TechCrunch Stepped Tools (v3.4 - SERP-based)

```python
# Step 1: Fetch funding articles (parallel for speed)
class TechCrunchFetchParallelTool:
    """Fetches multiple TechCrunch pages in parallel"""
    # pages=[1,2] fetches 2 pages concurrently

# Step 2: Select relevant articles
class TechCrunchSelectArticlesTool:
    """LLM selects articles matching query"""

# Step 3: Extract companies
class TechCrunchExtractCompaniesTool:
    """Returns companies ready for decision maker search"""

# Step 4: SERP-based decision makers (PREFERRED - FAST!)
class TechCrunchSerpDecisionMakersTool:
    """
    Finds ALL founders via Google SERP (~30-60s total!)
    Replaces slow LinkedIn employee search (was 6-8 min).
    Searches: Founders, Co-founders, CEO + role-specific titles.
    """
    # next: "Call filter_sellers"

# FALLBACK: linkedin_employees_batch_search (slow)
```

### Competitor Displacement Tools (v3.4)

```python
# Step 1: Identify competitor LinkedIn pages
class CompetitorIdentifyTool:
    """Converts competitor names to LinkedIn URLs"""
    # Uses competitors from strategy plan

# Step 2: Scrape competitor posts and extract engagers
class CompetitorScrapeTool:
    """
    Uses harvestapi/linkedin-company-posts Apify actor.
    Extracts commenters/likers from competitor posts.
    These people are interested in this space!
    """
    # Returns leads with name, title, linkedin_url
    # warning: "Apply filter_sellers before final output!"
```

### Filter Sellers Tool

Critical tool that must run on ALL leads:

```python
class FilterSellersTool:
    """
    LLM classifies each lead as BUYER or SELLER.

    BUYER signals: "Looking for", "Need help", "Frustrated with"
    SELLER signals: "I built", "Check out my", "Introducing"

    Returns: buyer_leads, sellers_removed
    """
```

---

## Structured Output Patterns

### Pattern 1: JSON Schema Response (Preferred for gpt-4o-mini)

```python
from openai import OpenAI
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# gpt-4o-mini supports full json_schema response format
json_schema = {
    "name": "classification_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "classifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"enum": ["BUYER", "SELLER"]}
                    },
                    "required": ["name", "type"]
                }
            }
        },
        "required": ["classifications"]
    }
}

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Classify leads as BUYER or SELLER."},
        {"role": "user", "content": f"Classify: {leads}"}
    ],
    response_format={"type": "json_schema", "json_schema": json_schema},
    max_completion_tokens=2000
)

result = json.loads(response.choices[0].message.content)
```

### Pattern 2: Retry with Fallback (For resilience)

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        response = client.chat.completions.create(
            model=settings.TOOL_MODEL,
            messages=[...],
            max_completion_tokens=4000
        )

        result_text = response.choices[0].message.content
        if not result_text or result_text.strip() == "":
            print(f"[WARNING] Empty response on attempt {attempt + 1}, retrying...")
            continue

        # Parse and validate JSON
        scores_array = json.loads(result_text.strip())
        return scores_array

    except json.JSONDecodeError as e:
        print(f"[WARNING] JSON parse error on attempt {attempt + 1}: {e}")
        continue

# Fallback: keyword-based scoring if all retries fail
return fallback_scoring(data)
```

### Pattern 3: Simple JSON (Legacy fallback)

```python
# Use this only if json_schema causes issues with a specific model
# gpt-4o-mini works great with json_schema, so prefer Pattern 1

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Always respond with valid JSON only."},
        {"role": "user", "content": f"Extract leads: {data}"}
    ],
    max_completion_tokens=2000
)

result_text = response.choices[0].message.content.strip()
# Clean markdown if present
result_text = result_text.replace("```json", "").replace("```", "").strip()
result = json.loads(result_text)
```

### Structured Output Standardization (v3.3)

All LLM calls now use OpenAI's `response_format` with `json_schema` for guaranteed valid JSON:

| File | Method | Schema Name |
|------|--------|-------------|
| `apify_reddit.py` | `_batch_score_posts` | `post_scores` |
| `apify_reddit.py` | `_calculate_intent_score_llm` | `intent_score` |
| `apify_reddit.py` | `_extract_leads_from_discussion` | `lead_extraction` |
| `apify_linkedin_employees.py` | `_score_employees` | `employee_scores` |
| `filter_sellers.py` | `_run` | `ClassificationsList` (Pydantic) |
| `techcrunch_tools.py` | Multiple | Pydantic models |
| `apify_linkedin_company_search.py` | Multiple | Pydantic models |

**Note:** `_classify_commenters_batch` and complex `_extract_leads_from_discussion_v2` removed in v3.4 (Reddit Relaxation).

**Benefits:**
- No JSON parsing errors - OpenAI guarantees schema compliance
- No retry logic needed for malformed JSON
- No markdown cleanup (`\`\`\`json` stripping)
- Simpler, cleaner code

### Structured Output Models Reference

| Model | File | Purpose | Temperature |
|-------|------|---------|-------------|
| `ClassificationsList` | filter_sellers.py | Buyer/seller classification | 0.2 |
| `FundingArticlesList` | techcrunch_tools.py | Extract funding articles | 0.2 |
| `SelectedCompaniesList` | techcrunch_tools.py | Select relevant companies | 0.3 |
| `DecisionMakersList` | techcrunch_tools.py | Select decision makers | 0.3 |
| `CompanyMatchList` | apify_linkedin_company_search.py | Match company to LinkedIn | 0.2 |
| `PostScore` | apify_reddit.py | Score Reddit posts | 0.3 |
| `employee_scores` | apify_linkedin_employees.py | Score decision makers | 0.2 |

**Temperature Guidelines:**
- **0.2**: Classification, matching, scoring (deterministic)
- **0.3**: Selection, extraction (some variation OK)

---

## External Services

| Service | Integration | Purpose | Auth |
|---------|-------------|---------|------|
| **Apify** | `ApifyClient` | LinkedIn, Reddit, Twitter scraping | `APIFY_API_TOKEN` |
| **OpenAI** | `OpenAI` client | LLM reasoning, structured outputs | `OPENAI_API_KEY` |
| **TechCrunch** | CrewAI `ScrapeWebsiteTool` | Funding announcements | Public |
| **Google SERP** | CrewAI `SerperDevTool` | Company triggers | `SERPER_API_KEY` |

### Apify Actors Used

| Actor | Purpose |
|-------|---------|
| `apify/reddit-scraper-search-fast` | Reddit post search |
| `M2FMdjRVeF1HPGFcc` | LinkedIn profile search |
| `5QnEH5N71IK2mFLrP` | LinkedIn post search |
| `apimaestro/linkedin-companies-search-scraper` | Company LinkedIn URL lookup |
| `harvestapi/linkedin-company-posts` | Competitor posts + engagers (v3.4) |
| `kaitoeasyapi/twitter-x-scraper` | Twitter/X search |

---

## Configuration

### Model Configuration (`app/core/config.py`)

```python
# Agent model - used for orchestrator agent reasoning (needs strong reasoning)
AGENT_MODEL: str = "gpt-4o-mini"  # Best for agentic tasks, tool selection
AGENT_TEMPERATURE: float = 0.3

# Tool model - used for tool LLM calls (structured outputs)
TOOL_MODEL: str = "gpt-4o-mini"  # Same as agent - reliable structured outputs
TOOL_TEMPERATURE: float = 0.2
```

**Model Selection Rationale:**
| Model | Use Case | Notes |
|-------|----------|-------|
| `gpt-4o-mini` | Agent reasoning + Tool calls | Unified model, reliable JSON schema support |
| `gpt-5-mini` | **AVOID for tools** | Structured output issues, empty responses |
| `gpt-5-nano` | **AVOID** | Returns empty responses frequently |

**Why Unified gpt-4o-mini:**
- Consistent behavior across agent reasoning and tool calls
- Full `response_format={"type": "json_schema", ...}` support
- Reliable structured outputs without retry/fallback complexity
- Cost difference minimal for this use case

**Known Issues with gpt-5 models:**
- `gpt-5-nano`: Returns empty `message.content` for batch scoring
- `gpt-5-mini`: Inconsistent with `response_format` json_schema
- Both: Require retry logic and fallback scoring patterns

### Environment Variables

```bash
# Required
APIFY_API_TOKEN=<token>
OPENAI_API_KEY=<key>

# Optional
ANTHROPIC_API_KEY=<key>      # For Claude alternative
SERPER_API_KEY=<key>         # For Google SERP
CRUNCHBASE_COOKIE=<cookie>   # For Crunchbase data

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

### YAML Configuration

**agents.yaml** - Agent personality and instructions:
```yaml
orchestrator:
  role: "Senior Sales Prospecting Strategist"
  goal: |
    Find {target_leads} high-intent BUYER leads...
    MANDATORY: USE BOTH REDDIT AND TECHCRUNCH
  backstory: |
    Expert in finding BUYING INTENT...
  verbose: true
```

**tasks.yaml** - Task workflow definition:
```yaml
prospect_leads:
  description: |
    REQUIRED EXECUTION ORDER:
    1. Reddit strategy (search → score → extract → filter)
    2. TechCrunch strategy (fetch → select → extract → linkedin → filter)
  expected_output: |
    {target_leads} qualified BUYER leads...
  agent: orchestrator
```

---

## Data Flow

```
User Request
    │
    ▼
ProspectingFlowV2.initialize()
    │
    ▼
OrchestratorCrew.kickoff()
    │
    ├────────────────────────────────────────────────────────────────────┐
    │                                                                    │
    │  ┌────────────────────┐ ┌───────────────────┐ ┌─────────────────┐ │
    │  │  REDDIT (~33%)     │ │ TECHCRUNCH (~33%) │ │COMPETITOR (~33%)│ │
    │  │                    │ │                   │ │                 │ │
    │  │ reddit_search()    │ │ tc_fetch_parallel │ │ comp_identify() │ │
    │  │    ↓               │ │    ↓              │ │    ↓            │ │
    │  │ reddit_score()     │ │ tc_select_arts()  │ │ comp_scrape()   │ │
    │  │    ↓               │ │    ↓              │ │ (LinkedIn posts)│ │
    │  │ reddit_extract()   │ │ tc_extract_cos()  │ │    ↓            │ │
    │  │ (ALL engagers)     │ │    ↓              │ │ extract_engagers│ │
    │  │    ↓               │ │ SERP_dm() (FAST!) │ │    ↓            │ │
    │  │ filter_sellers()   │ │    ↓              │ │ filter_sellers()│ │
    │  │    → BUYER leads   │ │ filter_sellers()  │ │    → BUYER leads│ │
    │  └─────────┬──────────┘ │    → BUYER leads  │ └────────┬────────┘ │
    │            │            └─────────┬─────────┘          │          │
    │            │                      │                    │          │
    │            └──────────────────────┼────────────────────┘          │
    │                                   ▼                               │
    │        ┌──────────────────────────────────────────────────┐       │
    │        │  AGGREGATION                                     │       │
    │        │  1. Final filter_sellers() (safety check)        │       │
    │        │  2. Deduplicate (keep higher score)              │       │
    │        │  3. SORT by intent_score (warmest first!)        │       │
    │        │  4. Return top N leads                           │       │
    │        └──────────────────────────────────────────────────┘       │
    │                                                                    │
    └────────────────────────────────────────────────────────────────────┘
    │
    ▼
Export: JSON, CSV, Execution Log (sorted warmest→coldest)
```

---

## Active vs Discontinued Features

### ACTIVE (Current - v3.4)

| Component | Status | Notes |
|-----------|--------|-------|
| **Orchestrator Crew** | ACTIVE | 5 agents, task chaining |
| **Reddit Tools** | ACTIVE | search, score, extract (relaxed - no classification) |
| **TechCrunch Tools** | ACTIVE | fetch_parallel, select, extract, SERP_decision_makers |
| **Competitor Tools** | ACTIVE v3.4 | identify, scrape_posts (competitor displacement) |
| **SERP Decision Makers** | ACTIVE v3.4 | Fast founder lookup via Google SERP |
| **Filter Sellers** | ACTIVE | Critical for all leads |
| **LinkedIn Tools** | ACTIVE | company_search, employees_search, company_posts |
| **Composite Tools** | ACTIVE | intent_hunter, trigger_scanner |

### DISCONTINUED

| Component | Status | Replacement | Location |
|-----------|--------|-------------|----------|
| **G2 Tools** | DISCONTINUED | N/A | `tools/stepped/g2_tools.py` |
| **Upwork Tools** | DISCONTINUED | N/A | `tools/stepped/upwork_tools.py` |
| **Crunchbase Flow** | DISCONTINUED | TechCrunch | N/A |
| **Google SERP Tool** | DISCONTINUED | CrewAI SerperDevTool | `tools/legacy/` |
| **Website Crawler** | DISCONTINUED | CrewAI ScrapeWebsiteTool | `tools/legacy/` |
| **Legacy Crews** | DISCONTINUED | OrchestratorCrew | `crews/reddit/`, etc. |

### EXPERIMENTAL (Not in production)

| Component | Status | Notes |
|-----------|--------|-------|
| Twitter integration | EXPERIMENTAL | Pay-per-result, expensive |
| Crunchbase integration | EXPERIMENTAL | Requires cookie auth |

---

## Adding New Tools

### Checklist for New Stepped Tools

1. **Single Responsibility**: Tool does ONE thing only
2. **No Internal Tool Calls**: Never call other tools internally
3. **Pydantic Input Schema**: Define with `Field` descriptions
4. **Structured Output**: Return JSON with `done`, `next`, `warning`
5. **Seller Filter Reminder**: Add warning if output contains leads
6. **Update YAML**: Add to agent backstory and task description

### Template

```python
from typing import Type, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json

class MyToolInput(BaseModel):
    """Input schema with clear descriptions for agent."""
    data: List[dict] = Field(..., description="Data from previous step")
    query: str = Field(..., description="Original query for context")

class MyTool(BaseTool):
    """
    One-line description of what this tool does.
    Does NOT do X - agent must call Y separately.
    """

    name: str = "my_tool"
    description: str = """
    Detailed description for agent.

    Parameters:
    - data: Data from previous_tool
    - query: Original search query

    Returns processed data. Next: call next_tool.
    """
    args_schema: Type[BaseModel] = MyToolInput

    def _run(self, data: List[dict], query: str) -> str:
        if not data:
            return json.dumps({
                "results": [],
                "count": 0,
                "done": "No data to process",
                "next": "Try previous_tool first"
            })

        # Process data...
        results = self._process(data)

        return json.dumps({
            "results": results,
            "count": len(results),
            "done": f"Processed {len(results)} items",
            "next": "Call next_tool with these results",
            "warning": "APPLY filter_sellers before using!"  # If applicable
        })
```

---

## Troubleshooting

### Common Issues

1. **Empty CSV Fields (buying_signal, platform)**
   - Cause: Field name mismatch between tools and exporter
   - Fix: Tools use `intent_signal`, `source_platform`. Exporter maps them in `lead_exporter.py`

2. **Strategy Generates Category Labels Instead of Queries**
   - Cause: Prompt not explicit about needing actual search strings
   - Fix: Strategy prompt includes examples: "Good: 'best ML tools', Bad: 'direct'"

3. **Worker Parameter Mismatch**
   - Cause: Worker passes wrong param name to tool (e.g., `industry` vs `query`)
   - Fix: Check tool's `args_schema` and match parameter names exactly

4. **Sellers in Final Leads**
   - Cause: Missing `filter_sellers` call in worker
   - Fix: Every worker must call `step_filter()` as final step

5. **Slow Execution (29+ min)**
   - Cause: Sequential execution in v3.4
   - Fix: v3.5 uses ThreadPoolExecutor for parallel worker execution (~6 min)

6. **TechCrunch Returns 0 Leads**
   - Cause: TechCrunch companies filtered as "sellers"
   - Fix: TechCrunch decision makers skip seller filter (they're pre-qualified)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.6 | 2025-11-29 | **Compensation Agent + LLM Decision Makers**: (1) **LLM Compensation Agent** - Replaced heuristic `_decide_compensations()` with `_ask_compensation_agent()` that reasons about what worked/failed. Agent tracks `round_history` and makes intelligent decisions. (2) **LLM Decision Maker Selection** - `serp_decision_makers.py` now asks LLM "who would BUY this product?" to find role-appropriate contacts (VP Sales for sales tools, CTOs for dev tools) instead of always prioritizing founders. (3) **Target-Aware Loop** - Compensation loop runs up to 3 rounds until target met. Priority: TechCrunch → Competitors → Reddit. (4) **ProspectingContext** - Tracks pages fetched, queries used, competitors scraped to avoid duplicate work. (5) **Bug Fix** - Fixed numbered prefix bug ("1. Groove" → "Groove") in competitor generation. |
| 3.5 | 2025-11-28 | **Supervisor Orchestrator**: (1) **New Architecture** - Single LLM orchestrator with 3 parallel Python workers (RedditWorker, TechCrunchWorker, CompetitorWorker). (2) **Parallel Execution** - Workers run via ThreadPoolExecutor (~6 min vs 29+ min). (3) **Intra-Step Review** - Orchestrator reviews each worker step, retries failures. (4) **Strategy Fix** - Strategy planner now generates actual search queries (not category labels like "direct", "pain_based"). (5) **Field Mapping Fix** - `lead_exporter.py` maps tool fields (`intent_signal`, `source_platform`) to CSV columns (`buying_signal`, `platform`). |
| 3.4 | 2025-11-28 | **Major Update**: (1) **Reddit Relaxation** - Removed `_classify_commenters_batch()`, simplified to extract ALL engagers, uses `filter_sellers` at end only. (2) **TechCrunch SERP** - Added `TechCrunchFetchParallelTool` and `TechCrunchSerpDecisionMakersTool` for ~30-60s decision maker lookup (was 6-8 min). (3) **Competitor Displacement** - New strategy using `harvestapi/linkedin-company-posts` actor to find leads from competitor post engagers. (4) **Final Sorting** - Leads sorted by intent_score descending (warmest first). Now 5 agents, 5 tasks. |
| 3.3 | 2025-11-28 | **Structured Output Standardization**: All tool LLM calls now use `response_format` with `json_schema`. Removed retry/fallback complexity for JSON parsing. Updated: `apify_reddit.py`, `apify_linkedin_employees.py`. |
| 3.2 | 2025-11-28 | Unified gpt-4o-mini: Both AGENT_MODEL and TOOL_MODEL now use gpt-4o-mini for reliable structured outputs. Removed gpt-5-mini due to JSON schema issues. |
| 3.1 | 2025-11-28 | Model fix: TOOL_MODEL changed to gpt-5-mini (gpt-5-nano returned empty responses). Added retry/fallback patterns for batch scoring. |
| 3.0 | 2025-11-27 | Multi-Task Sequential Architecture: 4 agents, task chaining via context, Pydantic outputs per task |
| 2.0 | 2025-11-27 | Single Orchestrator Agent, stepped tools refactored, G2/Upwork discontinued |
| 1.0 | 2025-11 | Initial multi-crew architecture |

---

## Test Results & Quality Observations

### Latest Test Run v3.6 (2025-11-30)

**Query:** "an AI-powered customer support platform for SaaS companies"
**Target:** 100 leads
**Duration:** ~11.2 minutes (674.2s)
**Result:** 100 leads (100% of target) ✅

| Metric | Value |
|--------|-------|
| Total Leads | 100 |
| Hot Leads | 3 |
| Warm Leads | 97 |
| Reddit Leads | 16 |
| TechCrunch Leads | 55 |
| Competitor Leads | 29 |
| Duplicates Removed | 23 |

**Compensation Loop in Action:**
```
Initial:  34/100 (34%) → shortfall detected
Round 1:  47/100 (47%) → techcrunch only (+13)
Round 2:  84/100 (84%) → techcrunch + competitor (+12 TC, +25 Comp)
Round 3: 100/100 (100%) → techcrunch + competitor (+15 TC, +24 Comp)
```

**LLM Decision Maker Selection:**
```
Product: "AI-powered customer support platform"
LLM identified roles: ['Chief Customer Officer', 'Director of Customer Experience', 'Head of Customer Support']
```
→ Correctly finds customer success roles, not generic founders!

**Competitors Generated by LLM:**
- Initial: Zendesk, Intercom, Freshdesk, Drift, Help Scout
- Round 2: Ada, Tidio, LivePerson, Zoho Desk, HappyFox
- Round 3: Gorgias, Kayako, Crisp, Front, ServiceTitan

### Previous Test Run v3.6 (2025-11-29)

**Query:** "Sales engagement platform for outbound sales teams"
**Target:** 100 leads
**Duration:** ~8.8 minutes
**Result:** 98 leads (98% of target)

| Metric | Value |
|--------|-------|
| Total Leads | 98 |
| Hot Leads | 2 |
| Warm Leads | 96 |
| Reddit Leads | 21 |
| TechCrunch Leads | 57 |
| Competitor Leads | 20 |

**Compensation Loop in Action:**
```
Initial:  56/100 (56%) → shortfall detected
Round 1:  68/100 (68%) → TC pages 3-4 + competitors
Round 2:  83/100 (83%) → TC pages 5-6
Round 3:  98/100 (98%) → TC pages 7-8
```

### Previous Test Run v3.6 (2025-11-29)

**Query:** "Open source vector database"
**Target:** 50 leads
**Duration:** ~5.5 minutes
**Result:** 49 leads (98% of target)

| Metric | Value |
|--------|-------|
| Total Leads | 49 |
| Reddit Leads | 8 |
| TechCrunch Leads | 15 |
| Competitor Leads | 26 |

**LLM Decision Maker Selection:**
```
Product: "open source vector database"
LLM identified roles: ['Chief Technology Officer', 'Data Engineering Manager', 'Head of Data Science']
```

### Key Fixes in v3.6

1. **LLM Compensation Agent** ✅ NEW
   - Replaced heuristic-based `_decide_compensations()` with LLM agent
   - Agent sees full round history (what worked/failed)
   - Makes intelligent decisions based on context

2. **LLM Decision Maker Selection** ✅ NEW
   - `serp_decision_makers.py` asks LLM who would BUY the product
   - Sales tools → VP Sales, Head of Revenue
   - Dev tools → CTO, VP Engineering
   - Cached per product (1 LLM call per run, not per company)

3. **Numbered Prefix Bug** ✅ FIXED
   - LLM was generating "1. Groove" instead of "Groove"
   - Fixed with regex cleanup in `_generate_more_competitors()`

### Key Fixes in v3.5

1. **Strategy Query Fix** ✅ RESOLVED
   - v3.4 Issue: Strategy planner generated category labels ("direct", "pain_based")
   - v3.5 Fix: Now generates actual search queries ("best ML observability tools", "how to monitor ML models")

2. **Field Mapping Fix** ✅ RESOLVED
   - v3.4 Issue: CSV had empty `buying_signal`, `fit_reasoning`, `platform` columns
   - v3.5 Fix: `lead_exporter.py` maps `intent_signal` → `buying_signal`, `source_platform` → `platform`

3. **Parallel Execution** ✅ RESOLVED
   - v3.4 Issue: Sequential agent execution took 29+ minutes
   - v3.5 Fix: ThreadPoolExecutor runs workers in parallel (~6 min)

4. **Parameter Mismatches** ✅ RESOLVED
   - v3.4 Issue: TechCrunch `industry` param vs tool's `query` param
   - v3.5 Fix: Workers use correct parameter names matching tool signatures

### Field Mapping Reference

Tools use these field names internally:
```
intent_signal      → buying_signal (CSV)
scoring_reasoning  → fit_reasoning (CSV)
source_platform    → platform (CSV)
```

The mapping is done in `lead_exporter.py` (lines 126-134):
```python
if 'intent_signal' in row and not row.get('buying_signal'):
    row['buying_signal'] = row.get('intent_signal', '')
if 'scoring_reasoning' in row and not row.get('fit_reasoning'):
    row['fit_reasoning'] = row.get('scoring_reasoning', '')
if 'source_platform' in row and not row.get('platform'):
    row['platform'] = row.get('source_platform', '')
```
