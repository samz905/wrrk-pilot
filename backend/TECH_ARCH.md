# Technical Architecture Documentation

> **Last Updated:** 2025-11-27
> **Version:** 2.0 (Single Orchestrator Agent Architecture)

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

---

## Architecture Overview

### Current Architecture (v2)

The system uses a **single intelligent Orchestrator Agent** that:
- Reasons about quality after each tool call
- Adapts strategy based on results
- Follows a mandatory two-platform approach (Reddit + TechCrunch)
- Filters sellers/promoters from all leads

```
┌─────────────────────────────────────────────────────────┐
│              ProspectingFlowV2 (Event-Driven)           │
│  └─ OrchestratorCrew                                    │
│     └─ Single Orchestrator Agent (GPT-4o)               │
│        ├─ Reddit Strategy                               │
│        │  └─ search → score → extract → filter_sellers  │
│        └─ TechCrunch Strategy                           │
│           └─ fetch → select → extract → linkedin_batch  │
│              → employees → decision_makers → filter     │
│        └─ Own Creative Strategies                       │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Agent Decides**: Tools provide data + recommendations, agent reasons and chooses next action
2. **Pure Stepped Tools**: Each tool does ONE thing, no internal tool calls
3. **Mandatory Seller Filtering**: Every platform runs `filter_sellers` before leads are finalized
4. **Clear State Communication**: Tool outputs include `done`, `next`, and `warning` fields

---

## Directory Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py              # Environment configuration
│   │
│   ├── crews/
│   │   └── orchestrator/          # PRIMARY - Single agent crew
│   │       ├── crew.py            # OrchestratorCrew class
│   │       ├── agents.yaml        # Agent role, goal, backstory
│   │       └── tasks.yaml         # Task definitions
│   │
│   ├── flows/
│   │   └── prospecting_flow_v2.py # Event-driven flow orchestration
│   │
│   ├── tools/
│   │   ├── stepped/               # Multi-step tools with agent reasoning
│   │   │   ├── reddit_tools.py    # ACTIVE: search, score, extract
│   │   │   ├── techcrunch_tools.py# ACTIVE: fetch, select, extract, decision_makers
│   │   │   ├── filter_sellers.py  # ACTIVE: LLM buyer/seller classification
│   │   │   ├── g2_tools.py        # DISCONTINUED: G2 reviews
│   │   │   └── upwork_tools.py    # DISCONTINUED: Upwork jobs
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
│   │   └── lead_exporter.py       # JSON/CSV export
│   │
│   └── api/
│       └── v1/
│           └── prospect.py        # FastAPI endpoints
│
├── legacy/                        # All discontinued code
│
├── test_output/                   # Test execution artifacts
│
└── TECH_ARCH.md                   # This file
```

---

## Core Components

### 1. ProspectingFlowV2 (`flows/prospecting_flow_v2.py`)

Event-driven flow using CrewAI Flow decorators:

```python
class ProspectingFlowV2(Flow[ProspectingState]):
    @start()
    def initialize(self): ...

    @listen(initialize)
    def run_orchestrator_with_retries(self): ...

    @router(run_orchestrator_with_retries)
    def route_to_finalize(self): ...

    @listen("success")
    def finalize_success(self): ...
```

**State Model:**
```python
class ProspectingState(BaseModel):
    query: str
    product_description: str
    target_leads: int = 100
    icp_criteria: Dict[str, Any] = {}
    status: ProspectingStatus
    leads: List[Dict]
    hot_leads: int      # score >= 80
    warm_leads: int     # score 60-79
    platforms_searched: List[str]
    strategies_used: List[str]
```

### 2. OrchestratorCrew (`crews/orchestrator/`)

Single intelligent agent with full tool suite:

**Agent Configuration (`agents.yaml`):**
- Role: Senior Sales Prospecting Strategist
- Model: GPT-4o (better reasoning)
- Temperature: 0.3
- Mandatory: Must use BOTH Reddit AND TechCrunch

**Task Configuration (`tasks.yaml`):**
- Detailed step-by-step workflow
- Quality checkpoints after each tool
- Seller filtering requirements

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

### TechCrunch Stepped Tools

```python
# Step 1: Fetch funding articles
class TechCrunchFetchTool:
    """Scrapes TechCrunch for funding announcements"""

# Step 2: Select relevant articles
class TechCrunchSelectArticlesTool:
    """LLM selects articles matching query"""

# Step 3: Extract companies (NO internal LinkedIn call!)
class TechCrunchExtractCompaniesTool:
    """Returns companies WITHOUT LinkedIn URLs"""
    # next: "Call linkedin_company_batch_search"

# Step 4: Select decision makers
class TechCrunchSelectDecisionMakersTool:
    """Picks founders/CEOs/CTOs from employee lists"""
    # warning: "APPLY filter_sellers BEFORE using!"
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

### Pattern 1: OpenAI Beta Parse API (Preferred)

```python
from openai import OpenAI
from pydantic import BaseModel

class LeadClassification(BaseModel):
    name: str
    is_seller: bool
    reason: str

class ClassificationsList(BaseModel):
    classifications: List[LeadClassification]

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.beta.chat.completions.parse(
    model="gpt-5-nano",
    messages=[
        {"role": "system", "content": "Classify leads as buyer or seller"},
        {"role": "user", "content": f"Classify: {leads}"}
    ],
    response_format=ClassificationsList,
    temperature=0.2
)

result = response.choices[0].message.parsed  # Returns Pydantic model
```

### Pattern 2: JSON Schema (Alternative)

```python
json_schema = {
    "name": "lead_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "leads": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "intent_score": {"type": "integer"}
                    }
                }
            }
        },
        "required": ["leads"]
    }
}

response = client.chat.completions.create(
    model="gpt-5-nano",
    messages=[...],
    response_format={"type": "json_schema", "json_schema": json_schema}
)

result = json.loads(response.choices[0].message.content)
```

### Structured Output Models Reference

| Model | File | Purpose | Temperature |
|-------|------|---------|-------------|
| `ClassificationsList` | filter_sellers.py | Buyer/seller classification | 0.2 |
| `FundingArticlesList` | techcrunch_tools.py | Extract funding articles | 0.2 |
| `SelectedCompaniesList` | techcrunch_tools.py | Select relevant companies | 0.3 |
| `DecisionMakersList` | techcrunch_tools.py | Select decision makers | 0.3 |
| `CompanyMatchList` | apify_linkedin_company_search.py | Match company to LinkedIn | 0.2 |
| `PostScore` | apify_reddit.py | Score Reddit posts | 0.3 |

**Temperature Guidelines:**
- **0.2**: Classification, matching (deterministic)
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
| `kaitoeasyapi/twitter-x-scraper` | Twitter/X search |

---

## Configuration

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
    ├─────────────────────────────────────────────┐
    │         REDDIT STRATEGY (~50%)              │
    │  ┌──────────────────────────────────────┐   │
    │  │ reddit_search(query)                 │   │
    │  │    ↓ Agent reviews quality           │   │
    │  │ reddit_score(posts)                  │   │
    │  │    ↓ Agent reviews scores            │   │
    │  │ reddit_extract(posts)                │   │
    │  │    ↓ WARNING: May include sellers!   │   │
    │  │ filter_sellers(leads)                │   │
    │  │    → BUYER leads only                │   │
    │  └──────────────────────────────────────┘   │
    │                                             │
    ├─────────────────────────────────────────────┐
    │       TECHCRUNCH STRATEGY (~50%)            │
    │  ┌──────────────────────────────────────┐   │
    │  │ techcrunch_fetch()                   │   │
    │  │    ↓                                 │   │
    │  │ techcrunch_select_articles()         │   │
    │  │    ↓                                 │   │
    │  │ techcrunch_extract_companies()       │   │
    │  │    ↓ Returns companies (NO LinkedIn) │   │
    │  │ linkedin_company_batch_search()      │   │
    │  │    ↓ Agent gets LinkedIn URLs        │   │
    │  │ linkedin_employees_search() [x N]    │   │
    │  │    ↓                                 │   │
    │  │ techcrunch_select_decision_makers()  │   │
    │  │    ↓ WARNING: Apply filter!          │   │
    │  │ filter_sellers(leads)                │   │
    │  │    → BUYER leads only                │   │
    │  └──────────────────────────────────────┘   │
    │                                             │
    ▼
Merge + Final filter_sellers() + Score + Rank
    │
    ▼
Export: JSON, CSV, Execution Log
```

---

## Active vs Discontinued Features

### ACTIVE (Current)

| Component | Status | Notes |
|-----------|--------|-------|
| **Orchestrator Crew** | ACTIVE | Primary architecture |
| **Reddit Tools** | ACTIVE | search, score, extract |
| **TechCrunch Tools** | ACTIVE | fetch, select, extract, decision_makers |
| **Filter Sellers** | ACTIVE | Critical for all leads |
| **LinkedIn Tools** | ACTIVE | company_search, employees_search |
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

1. **Duplicate API Calls**
   - Cause: Tool internally calling another tool
   - Fix: Remove internal calls, update `next` recommendation

2. **Agent Skipping Platform**
   - Cause: Weak prompts in agents.yaml
   - Fix: Add "MANDATORY" language, explicit execution order

3. **Sellers in Final Leads**
   - Cause: Missing `filter_sellers` call
   - Fix: Add `warning` field to tool output

4. **Agent Confusion**
   - Cause: Vague recommendation messages
   - Fix: Use clear `done`/`next` format

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-11-27 | Single Orchestrator Agent, stepped tools refactored, G2/Upwork discontinued |
| 1.0 | 2025-11 | Initial multi-crew architecture |
