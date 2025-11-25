# Reddit Crew Documentation

> **Template Playbook**: This README serves as a reference implementation for all CrewAI crews in this project. Follow the patterns documented here for consistency.

---

## Overview

The Reddit Crew discovers intent signals and extracts leads from Reddit discussions using a two-task sequential workflow:

1. **Task 1**: Find top N discussions for a search query
2. **Task 2**: Extract users with buying intent from those discussions

**Key Features**:
- Structured outputs using Pydantic models
- Explicit context passing between tasks
- Parallel processing for performance
- Debug logging for troubleshooting

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RedditProspectingCrew                     │
├─────────────────────────────────────────────────────────────────┤
│  Inputs: search_query, desired_results                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Task 1: search_reddit_discussions                         │   │
│  │ Agent: reddit_intelligence_agent                          │   │
│  │ Tool: ApifyRedditSearchTool                               │   │
│  │ Output: Task1Output (Pydantic)                            │   │
│  │   └── discussions: List[DiscussionResult]                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼ context                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Task 2: extract_reddit_leads                              │   │
│  │ Agent: lead_extraction_agent                              │   │
│  │ Tool: RedditLeadExtractionTool                            │   │
│  │ Output: Task2Output (Pydantic)                            │   │
│  │   └── leads: List[LeadResult]                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Final Output: Task2Output (JSON)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## CrewAI Best Practices (IMPORTANT)

### 1. Use Structured Outputs with `output_pydantic`

**Why**: Agents return arbitrary formats without structure. Pydantic ensures consistent JSON output.

**Implementation** (in `crew.py`):

```python
from pydantic import BaseModel, Field
from typing import List

# Define output models
class DiscussionResult(BaseModel):
    title: str = Field(description="Post title")
    url: str = Field(description="Reddit post URL")
    subreddit: str = Field(description="Subreddit name")
    intent_score: int = Field(description="Intent score 0-100")

class Task1Output(BaseModel):
    discussions: List[DiscussionResult]

# Use in task definition
@task
def search_reddit_discussions(self) -> Task:
    return Task(
        config=self.tasks_config['search_reddit_discussions'],
        agent=self.reddit_intelligence_agent(),
        output_pydantic=Task1Output  # Forces structured output
    )
```

### 2. Pass Data Between Tasks with `context`

**Why**: Without `context`, Task 2 doesn't reliably receive Task 1's output.

**Implementation**:

```python
@task
def extract_reddit_leads(self) -> Task:
    return Task(
        config=self.tasks_config['extract_reddit_leads'],
        agent=self.lead_extraction_agent(),
        context=[self.search_reddit_discussions()],  # Explicit dependency
        output_pydantic=Task2Output
    )
```

### 3. Keep tasks.yaml Simple

**Why**: Verbose expected_output confuses the agent. Match Pydantic models exactly.

**Good**:
```yaml
expected_output: |
  Return a JSON object with a "discussions" array.
  Each discussion has: title, url, subreddit, intent_score, reasoning.
```

**Bad** (too verbose):
```yaml
expected_output: |
  A prioritized list of Reddit discussions showing buying intent:
  For each discussion include:
  1. INTENT SIGNAL: What problem they're discussing
     - Quote the most compelling part...
  [50 more lines of instructions]
```

### 4. Tools Must Return Strings

**Why**: CrewAI tools return strings that agents parse. Keep outputs parseable.

**Implementation** (in tool `_run` method):
```python
def _run(self, query: str, ...) -> str:
    # Do work...
    return json.dumps(results)  # Return JSON string
```

### 5. Add Debug Logging to Tools

**Why**: Silent failures cause "No results found" without explanation.

**Implementation**:
```python
def _fetch_data(self, ...):
    print(f"[DEBUG] Input: {json.dumps(input_data, indent=2)}")
    try:
        result = api_call()
        print(f"[DEBUG] Returned {len(result)} items")
        return result
    except Exception as e:
        print(f"[ERROR] Failed: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
```

---

## File Structure

```
backend/app/crews/reddit/
├── __init__.py          # Exports RedditProspectingCrew
├── crew.py              # Crew, agents, tasks, Pydantic models
├── agents.yaml          # Agent role, goal, backstory
├── tasks.yaml           # Task description, expected_output
└── README.md            # This file

backend/app/tools/
└── apify_reddit.py      # ApifyRedditSearchTool, RedditLeadExtractionTool
```

---

## Pydantic Output Models

### Task 1 Output: `Task1Output`

```python
class DiscussionResult(BaseModel):
    title: str           # Post title
    url: str             # Reddit URL
    subreddit: str       # e.g., "sales"
    upvotes: int         # Engagement
    num_comments: int    # Discussion depth
    intent_score: int    # 0-100
    reasoning: str       # Why relevant

class Task1Output(BaseModel):
    discussions: List[DiscussionResult]
```

### Task 2 Output: `Task2Output`

```python
class LeadResult(BaseModel):
    username: str        # e.g., "john_doe"
    profile_url: str     # https://reddit.com/u/john_doe
    buying_signal: str   # Quote showing intent
    intent_score: int    # 0-100
    fit_reasoning: str   # Why good lead
    source_url: str      # Discussion URL
    source_subreddit: str

class Task2Output(BaseModel):
    leads: List[LeadResult]
```

---

## Usage

### Basic Usage

```python
from app.crews.reddit.crew import RedditProspectingCrew

crew = RedditProspectingCrew()
result = crew.crew().kickoff(inputs={
    'search_query': 'CRM software',
    'desired_results': 10
})

# Get structured output
if result.pydantic:
    leads = result.pydantic.leads
    for lead in leads:
        print(f"{lead.username}: {lead.buying_signal}")
```

### Expected JSON Output

```json
{
  "leads": [
    {
      "username": "john_doe",
      "profile_url": "https://reddit.com/u/john_doe",
      "buying_signal": "Looking for Salesforce alternative - too expensive",
      "intent_score": 85,
      "fit_reasoning": "User actively seeking CRM alternatives due to pricing...",
      "source_url": "https://reddit.com/r/sales/comments/...",
      "source_subreddit": "sales"
    }
  ]
}
```

---

## Testing

```bash
cd backend
source .venv/Scripts/activate
python test_reddit.py
```

**Test Flow**:
1. Task 1: Searches "CRM software", returns 10 discussions
2. Task 2: Extracts leads from those 10 URLs
3. Output: JSON with leads array

---

## Performance

| Discussions | Task 1 | Task 2 | Total |
|-------------|--------|--------|-------|
| 10          | ~30s   | ~45s   | ~1.5min |
| 20          | ~45s   | ~1.5min | ~2.5min |
| 50          | ~1min  | ~3min  | ~4min |

**Optimizations**:
- 5x multiplier: Fetch 5x posts, filter to top N
- Parallel processing: URL batches of 10
- Batch scoring: 50 posts per LLM call
- Structured outputs: Guaranteed JSON response

---

## Cost

| Component | Cost |
|-----------|------|
| Apify (100 posts) | ~$0.001 |
| OpenAI (100 calls) | ~$0.005 |
| 10 discussions E2E | ~$0.002 |

---

## Troubleshooting

### Issue: "No posts found"
- **Check**: Debug logs for Apify errors
- **Fix**: Verify APIFY_API_TOKEN is set

### Issue: Only partial results (5 instead of 10)
- **Check**: Agent deciding arbitrarily
- **Fix**: Use `output_pydantic` to force exact structure

### Issue: Task 2 doesn't receive Task 1 URLs
- **Check**: Missing context attribute
- **Fix**: Add `context=[self.search_reddit_discussions()]`

### Issue: "I tried reusing the same input"
- **Check**: Tool returning empty/error result
- **Fix**: Add debug logging, check API responses

---

## Checklist for New Crews

Use this checklist when creating new crews:

- [ ] Define Pydantic output models for each task
- [ ] Add `output_pydantic` to all tasks
- [ ] Add `context` for task dependencies
- [ ] Keep tasks.yaml expected_output simple (match Pydantic)
- [ ] Add debug logging to all tool methods
- [ ] Tools return JSON strings
- [ ] Test end-to-end with structured output validation
- [ ] Document in README following this template

---

## References

- [CrewAI Tasks Documentation](https://docs.crewai.com/en/concepts/tasks)
- [CrewAI Custom Tools](https://docs.crewai.com/en/learn/create-custom-tools)
- [Pydantic Documentation](https://docs.pydantic.dev/)
