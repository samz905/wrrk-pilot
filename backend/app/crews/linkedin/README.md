# LinkedIn Crew Documentation

> **Template Playbook**: This README follows the same pattern as Reddit crew. Use it as a reference for all CrewAI crews.

---

## Overview

The LinkedIn Crew discovers intent signals and extracts leads from LinkedIn posts using a two-task sequential workflow:

1. **Task 1**: Find top N LinkedIn posts with intent signals for a search query
2. **Task 2**: Extract users with buying intent from those posts

**Standalone Tool**:
- **Decision Makers Tool**: Find relevant employees at a specific company

**Key Features**:
- Structured outputs using Pydantic models
- Explicit context passing between tasks
- Flexible for any ICP (not just sales)
- Debug logging for troubleshooting

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LinkedInProspectingCrew                       │
├─────────────────────────────────────────────────────────────────┤
│  Inputs: search_query, desired_results                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Task 1: search_linkedin_posts                             │   │
│  │ Agent: linkedin_intelligence_agent                        │   │
│  │ Tool: ApifyLinkedInPostsSearchTool                        │   │
│  │ Output: Task1Output (Pydantic)                            │   │
│  │   └── posts: List[PostResult]                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼ context                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Task 2: extract_linkedin_leads                            │   │
│  │ Agent: lead_extraction_agent                              │   │
│  │ Tool: LinkedInLeadExtractionTool                          │   │
│  │ Output: Task2Output (Pydantic)                            │   │
│  │   └── leads: List[LeadResult]                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Final Output: Task2Output (JSON)                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Standalone Tools                              │
├─────────────────────────────────────────────────────────────────┤
│  LinkedInEmployeesSearchTool (Decision Makers)                   │
│    Input: company_url + query                                    │
│    Use case: Find decision makers at a specific company          │
│                                                                  │
│  ApifyLinkedInSearchTool (People Search)                         │
│    Input: keywords + location                                    │
│    Use case: Simple people search by title/keywords              │
│                                                                  │
│  ApifyLinkedInProfileDetailTool (Profile Enrichment)             │
│    Input: profile_url                                            │
│    Use case: Enrich profile with email/phone                     │
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
class PostResult(BaseModel):
    author_name: str = Field(description="Name of the poster")
    author_title: str = Field(description="Job title/headline")
    post_url: str = Field(description="URL to the post")
    intent_score: int = Field(description="Intent score 0-100")

class Task1Output(BaseModel):
    posts: List[PostResult]

# Use in task definition
@task
def search_linkedin_posts(self) -> Task:
    return Task(
        config=self.tasks_config['search_linkedin_posts'],
        agent=self.linkedin_intelligence_agent(),
        output_pydantic=Task1Output  # Forces structured output
    )
```

### 2. Pass Data Between Tasks with `context`

**Why**: Without `context`, Task 2 doesn't reliably receive Task 1's output.

**Implementation**:

```python
@task
def extract_linkedin_leads(self) -> Task:
    return Task(
        config=self.tasks_config['extract_linkedin_leads'],
        agent=self.lead_extraction_agent(),
        context=[self.search_linkedin_posts()],  # Explicit dependency
        output_pydantic=Task2Output
    )
```

### 3. Keep tasks.yaml Simple

**Why**: Verbose expected_output confuses the agent. Match Pydantic models exactly.

**Good**:
```yaml
expected_output: |
  Return a JSON object with a "posts" array.
  Each post has: author_name, author_title, post_url, intent_score, intent_signal.
```

**Bad** (too verbose):
```yaml
expected_output: |
  A prioritized list of LinkedIn posts showing buying intent:
  For each post include:
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
    return self._format_results(results)  # Return formatted string
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
backend/app/crews/linkedin/
├── __init__.py          # Exports LinkedInProspectingCrew
├── crew.py              # Crew, agents, tasks, Pydantic models
├── agents.yaml          # Agent role, goal, backstory
├── tasks.yaml           # Task description, expected_output
└── README.md            # This file

backend/app/tools/
├── apify_linkedin_posts.py       # LinkedIn Posts Search tool
├── apify_linkedin_leads.py       # LinkedIn Lead Extraction tool
├── apify_linkedin_employees.py   # Decision Makers tool
├── apify_linkedin.py             # People Search tool
└── apify_linkedin_profile_detail.py  # Profile Enrichment tool
```

---

## Pydantic Output Models

### Task 1 Output: `Task1Output`

```python
class PostResult(BaseModel):
    author_name: str      # Name of the poster
    author_title: str     # Job title/headline
    author_url: str       # LinkedIn profile URL
    post_content: str     # Post text (max 300 chars)
    post_url: str         # URL to the post
    likes: int            # Number of likes
    comments: int         # Number of comments
    intent_score: int     # 0-100
    intent_signal: str    # Why this shows buying intent

class Task1Output(BaseModel):
    posts: List[PostResult]
```

### Task 2 Output: `Task2Output`

```python
class LeadResult(BaseModel):
    name: str             # Full name
    title: str            # Job title
    company: str          # Company name
    linkedin_url: str     # Profile URL
    intent_signal: str    # Quote showing intent (max 100 chars)
    intent_score: int     # 0-100
    fit_reasoning: str    # Why good lead
    source_post_url: str  # Where they were found

class Task2Output(BaseModel):
    leads: List[LeadResult]
```

---

## Usage

### Basic Usage (Main Crew)

```python
from app.crews.linkedin.crew import LinkedInProspectingCrew

crew = LinkedInProspectingCrew()
result = crew.crew().kickoff(inputs={
    'search_query': 'CRM software',
    'desired_results': 10
})

# Get structured output
if result.pydantic:
    leads = result.pydantic.leads
    for lead in leads:
        print(f"{lead.name}: {lead.intent_signal}")
```

### Decision Makers Tool (Standalone)

```python
from app.tools.apify_linkedin_employees import LinkedInEmployeesSearchTool

tool = LinkedInEmployeesSearchTool()
result = tool._run(
    company_url="https://www.linkedin.com/company/google/",
    query="engineering managers",
    max_employees=30
)
print(result)
```

### Expected JSON Output

```json
{
  "leads": [
    {
      "name": "John Doe",
      "title": "VP of Sales",
      "company": "Acme Corp",
      "linkedin_url": "https://linkedin.com/in/johndoe",
      "intent_signal": "Looking for Salesforce alternative - too expensive",
      "intent_score": 85,
      "fit_reasoning": "User actively seeking CRM alternatives due to pricing...",
      "source_post_url": "https://linkedin.com/posts/..."
    }
  ]
}
```

---

## Testing

### Main Crew Test

```bash
cd backend
source .venv/Scripts/activate
python test_linkedin.py
```

**Test Flow**:
1. Task 1: Searches "CRM software", returns 10 posts with intent signals
2. Task 2: Extracts leads from those posts
3. Output: JSON with leads array

### Decision Makers Test

```bash
cd backend
source .venv/Scripts/activate
python test_linkedin.py --decision-makers "https://www.linkedin.com/company/google/" "engineering managers"
```

---

## Apify Actors Used

| Tool | Actor ID | Actor Name |
|------|----------|------------|
| Posts Search | `5QnEH5N71IK2mFLrP` | apimaestro/linkedin-posts-search-scraper-no-cookies |
| People Search | `M2FMdjRVeF1HPGFcc` | harvestapi/linkedin-profile-search |
| Profile Detail | `VhxlqQXRwhW8H5hNV` | apimaestro/linkedin-profile-detail |
| Company Employees | `cIdqlEvw6afc1do1p` | harvestapi/linkedin-company-employees |

---

## Troubleshooting

### Issue: "No posts found"
- **Check**: Debug logs for Apify errors
- **Fix**: Verify APIFY_API_TOKEN is set

### Issue: Only partial results (5 instead of 10)
- **Check**: Agent deciding arbitrarily
- **Fix**: Use `output_pydantic` to force exact structure

### Issue: Task 2 doesn't receive Task 1 data
- **Check**: Missing context attribute
- **Fix**: Add `context=[self.search_linkedin_posts()]`

### Issue: "Apify monthly limit exceeded"
- **Check**: Apify account usage
- **Fix**: Add new Apify API key or wait for reset

---

## Checklist for New Crews

Use this checklist when creating new crews:

- [ ] Define Pydantic output models for each task
- [ ] Add `output_pydantic` to all tasks
- [ ] Add `context` for task dependencies
- [ ] Keep tasks.yaml expected_output simple (match Pydantic)
- [ ] Add debug logging to all tool methods
- [ ] Tools return formatted strings
- [ ] Test end-to-end with structured output validation
- [ ] Document in README following this template

---

## References

- [CrewAI Tasks Documentation](https://docs.crewai.com/en/concepts/tasks)
- [CrewAI Custom Tools](https://docs.crewai.com/en/learn/create-custom-tools)
- [Pydantic Documentation](https://docs.pydantic.dev/)
