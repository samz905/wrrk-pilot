# WRRK Pilot - MVP v1 Documentation

## Product Overview

**WRRK Pilot** is an AI-powered lead prospecting platform that automatically discovers and enriches potential leads from multiple data sources. The system uses a supervisor-worker architecture where an LLM orchestrator coordinates three specialized workers running in parallel to find relevant prospects based on a natural language query.

### Core Value Proposition

- **Natural Language Prospecting**: Simply describe what you're selling (e.g., "CRM software for startups")
- **Multi-Source Intelligence**: Searches Reddit, TechCrunch funding articles, and LinkedIn competitor engagement
- **Real-Time Progress**: Watch agents work with live SSE streaming updates
- **Intent Scoring**: Leads ranked by buying intent signals (0-100 score)
- **Cost Tracking**: Monitors Apify API costs per prospecting run
- **Persistent History**: All jobs and leads stored in Supabase for later access and CSV export

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WRRK PILOT SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────┐         ┌─────────────────────────────────┐ │
│  │   FRONTEND (Vercel)    │   SSE   │      BACKEND (Render)           │ │
│  │                        │◄───────►│                                 │ │
│  │   Next.js 15           │   REST  │   FastAPI                       │ │
│  │   React 19             │         │   SupervisorOrchestrator        │ │
│  │   Supabase Auth        │         │   Parallel Workers              │ │
│  │   Tailwind CSS v4      │         │                                 │ │
│  └───────────┬────────────┘         └───────────────┬─────────────────┘ │
│              │                                      │                   │
│              ▼                                      ▼                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    SUPABASE (PostgreSQL)                         │   │
│  │   • User Authentication (auth.users)                             │   │
│  │   • Prospecting Jobs (jobs table)                                │   │
│  │   • Discovered Leads (leads table)                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  PARALLEL WORKERS                                 │   │
│  │                                                                   │   │
│  │   ┌─────────────┐  ┌──────────────┐  ┌────────────────┐          │   │
│  │   │   REDDIT    │  │  TECHCRUNCH  │  │  COMPETITOR    │          │   │
│  │   │   Worker    │  │   Worker     │  │    Worker      │          │   │
│  │   │             │  │              │  │                │          │   │
│  │   │ • Search    │  │ • Fetch      │  │ • Identify     │          │   │
│  │   │ • Score     │  │ • Select     │  │ • Scrape       │          │   │
│  │   │ • Extract   │  │ • Extract    │  │ • Filter       │          │   │
│  │   │ • Filter    │  │ • SERP DMs   │  │                │          │   │
│  │   └─────────────┘  └──────────────┘  └────────────────┘          │   │
│  │        │                  │                  │                   │   │
│  │        ▼                  ▼                  ▼                   │   │
│  │   ┌─────────────────────────────────────────────────────────┐    │   │
│  │   │              EXTERNAL DATA SOURCES                       │    │   │
│  │   │   • Reddit via Apify (TwqHBuZZPHJxiQrTU)                │    │   │
│  │   │   • TechCrunch RSS + SERP API                           │    │   │
│  │   │   • LinkedIn via Apify (company posts, profiles)        │    │   │
│  │   └─────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 15.x | React framework with App Router |
| React | 19.x | UI component library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Utility-first styling |
| Supabase Auth | Latest | Authentication (email + Google OAuth) |
| Radix UI | Latest | Accessible component primitives |
| Lucide React | Latest | Icons |

### Directory Structure

```
frontend/
├── app/                              # Next.js App Router pages
│   ├── page.tsx                      # Main prospecting page (/)
│   ├── login/page.tsx                # Auth page with login/signup
│   ├── runs/page.tsx                 # Job history list (/runs)
│   ├── runs/[id]/page.tsx            # Run details with leads (/runs/:id)
│   └── layout.tsx                    # Root layout with metadata
├── components/
│   ├── prospecting/                  # Prospecting-specific components
│   │   ├── AgentWorkspace.tsx        # Left panel - agent activity feed
│   │   ├── QueryInput.tsx            # Search bar with start/stop
│   │   ├── LeadsTable.tsx            # Right panel - results table
│   │   ├── LeadDetailModal.tsx       # Lead popup on click
│   │   ├── ToolCard.tsx              # Worker activity card
│   │   ├── ReasoningCard.tsx         # AI reasoning display
│   │   ├── ProgressHeader.tsx        # Lead count progress bar
│   │   └── ProgressBar.tsx           # Animated progress bar
│   ├── layout/
│   │   └── Header.tsx                # Global navigation header
│   └── ui/                           # Radix-based primitives
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       ├── table.tsx
│       ├── dialog.tsx
│       ├── dropdown-menu.tsx
│       └── ...
└── lib/
    ├── supabase/
    │   └── client.ts                 # Browser Supabase client
    ├── api.ts                        # Backend API client + SSE
    ├── types.ts                      # TypeScript interfaces
    └── utils.ts                      # Utility functions
```

### Pages and Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `page.tsx` | Main prospecting interface - enter query, see agents work, view leads |
| `/login` | `login/page.tsx` | Authentication - email/password or Google OAuth |
| `/runs` | `runs/page.tsx` | Job history - list of past prospecting runs |
| `/runs/[id]` | `runs/[id]/page.tsx` | Run details - leads table with CSV export |

### UI/UX Design

#### Main Prospecting Page (`/`)

The main page has a two-column layout:

```
┌──────────────────────────────────────────────────────────────────────┐
│  WRRK Logo                                      [User Menu ▼]        │
├──────────────────────────────────────────────────────────────────────┤
│  [ find me leads for my CRM software_________________ ] [Start]      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────┐     ┌──────────────────────────────────┐   │
│  │   AGENT WORKSPACE   │     │          LEADS TABLE             │   │
│  │                     │     │                                  │   │
│  │ ┌─────────────────┐ │     │  Name    Title    Company  Score │   │
│  │ │ 🔴 Reddit       │ │     │  ─────────────────────────────── │   │
│  │ │ Searching...    │ │     │  John D  CEO     Acme     85 HOT │   │
│  │ └─────────────────┘ │     │  Jane S  CTO     Beta     72 WARM│   │
│  │                     │     │  ...                             │   │
│  │ ┌─────────────────┐ │     │                                  │   │
│  │ │ 🟢 TechCrunch   │ │     │                                  │   │
│  │ │ Found 12 leads  │ │     │                                  │   │
│  │ └─────────────────┘ │     │                                  │   │
│  │                     │     │                                  │   │
│  │ Progress: 35/50     │     │                                  │   │
│  └─────────────────────┘     └──────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Key UI Components:**

1. **Header** (`Header.tsx`)
   - WRRK logo (target icon + text)
   - User dropdown menu (email, Past Runs, Sign Out)
   - Sticky navigation

2. **Query Input** (`QueryInput.tsx`)
   - Single input field with placeholder "find me leads for my CRM software"
   - Start button (blue) - disabled when empty
   - Stop button (red) - appears while running with spinner

3. **Agent Workspace** (`AgentWorkspace.tsx`)
   - Scrollable card showing chronological activity
   - **Tool Cards**: Show each worker's status (Reddit, TechCrunch/Google, LinkedIn)
   - **Reasoning Cards**: Display AI strategy decisions
   - **Progress Header**: Shows "35/50 leads" with progress bar
   - Auto-scrolls to latest activity
   - Cards expand/collapse on click

4. **Leads Table** (`LeadsTable.tsx`)
   - Sortable columns: Name, Title, Company, Platform, Score
   - Score badges: HOT (≥80, green), WARM (≥60, yellow), COLD (<60, gray)
   - Platform icons (Reddit, LinkedIn, Google)
   - Click row to open Lead Detail Modal
   - New leads highlight briefly when added

5. **Lead Detail Modal** (`LeadDetailModal.tsx`)
   - Full lead details in popup
   - Contact info, intent signals, source URL
   - Close button

#### Login Page (`/login`)

```
┌──────────────────────────────────────┐
│                                      │
│       🎯 WRRK                        │
│                                      │
│     Welcome back / Create account    │
│                                      │
│  Email: [___________________]        │
│  Password: [________________]        │
│                                      │
│  [        Sign In / Sign Up       ]  │
│                                      │
│  ─────── Or continue with ───────   │
│                                      │
│  [         🔵 Google              ]  │
│                                      │
│  Don't have an account? Sign up      │
│                                      │
└──────────────────────────────────────┘
```

- Toggle between Sign In / Sign Up modes
- Email + password authentication
- Google OAuth integration
- Redirects to main page on success

#### Runs History Page (`/runs`)

```
┌──────────────────────────────────────────────────────────────────────┐
│  WRRK                                         [+ New Search] [User]  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Your Prospecting Runs                                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ✓ CRM software for startups          Dec 2, 2025   2m 34s  47 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ✓ ML observability tool              Dec 1, 2025   3m 12s  52 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

- Lists all past runs with query, status, date, duration, lead count
- Click to view run details
- Status icons: ✓ completed, ✗ failed, ⟳ running

#### Run Details Page (`/runs/[id]`)

```
┌──────────────────────────────────────────────────────────────────────┐
│  WRRK    ← Back to Runs                                     [User]   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CRM software for startups                                           │
│  December 2, 2025 3:45 PM • 2m 34s • Completed                       │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │    47    │  │    15    │  │    12    │  │    20    │             │
│  │  Total   │  │ TechCrunch│  │ Competitor│  │  Reddit  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │
│                                                           [Export CSV]│
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Name         Title           Company        Platform   Score  │ │
│  │  ──────────────────────────────────────────────────────────── │ │
│  │  John Doe     CEO             Acme Corp      LinkedIn    85   │ │
│  │  ...                                                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

- Full run statistics with source breakdown
- Leads table with all discovered leads
- **Export CSV** button for download
- Click lead row for detail modal

### Authentication Flow

```
User visits any page
        │
        ▼
Check Supabase session (client-side)
        │
        ├──► No session + protected page ──► Redirect to /login
        │
        └──► Has session ──► Render page
                │
                ▼
        API calls include Bearer token
```

**Supported Auth Methods:**
1. Email + Password (sign up requires confirmation)
2. Google OAuth (immediate sign in)

---

## Backend Architecture

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | Latest | Web framework |
| Pydantic | 2.x | Data validation |
| OpenAI | Latest | GPT-4 for LLM agents |
| Apify Client | Latest | Web scraping APIs |
| Supabase-py | Latest | Database client |

### Directory Structure

```
backend/
├── app/
│   ├── main.py                       # FastAPI app entry point
│   ├── supervisor_orchestrator.py    # Main orchestration logic
│   ├── api/
│   │   └── v1/
│   │       └── prospect.py           # Prospecting endpoints
│   ├── core/
│   │   ├── config.py                 # Environment settings
│   │   ├── database.py               # Supabase operations
│   │   ├── auth.py                   # JWT verification
│   │   └── cost_tracker.py           # Apify cost tracking
│   ├── workers/                      # Parallel worker implementations
│   │   ├── reddit_worker.py          # Reddit prospecting
│   │   ├── techcrunch_worker.py      # TechCrunch prospecting
│   │   └── competitor_worker.py      # LinkedIn competitor scraping
│   └── tools/                        # Tool implementations
│       ├── stepped/                  # Step-by-step tools for workers
│       │   ├── reddit_tools.py
│       │   ├── techcrunch_tools.py
│       │   ├── competitor_tools.py
│       │   └── filter_sellers.py
│       ├── apify_reddit.py           # Apify Reddit scraper
│       ├── apify_twitter.py          # Apify Twitter scraper
│       ├── apify_linkedin_*.py       # Various LinkedIn scrapers
│       ├── apify_crunchbase.py       # Crunchbase scraper
│       └── serp_decision_makers.py   # Google SERP for founder lookup
├── scripts/
│   ├── check_apify_costs.py          # Cost monitoring utility
│   └── test_cost_tracking.py         # Cost tracking tests
└── requirements.txt
```

### API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/prospect/start` | Optional | Start prospecting job, returns job_id |
| GET | `/api/v1/prospect/{job_id}/stream` | No | SSE stream for real-time updates |
| POST | `/api/v1/prospect/{job_id}/cancel` | No | Cancel running job |
| GET | `/api/v1/prospect/{job_id}/status` | No | Get job status |
| GET | `/api/v1/prospect/{job_id}/results` | No | Get final results |
| GET | `/api/v1/prospect/runs` | Required | List user's job history |
| GET | `/api/v1/prospect/runs/{id}` | Required | Get run details with leads |
| GET | `/api/v1/prospect/runs/{id}/export` | Required | Download leads as CSV |

### SSE Event Types

The streaming endpoint sends these event types:

```typescript
type EventType =
  | 'status'          // Initial connection status
  | 'thought'         // AI reasoning/strategy decisions
  | 'worker_start'    // Worker begins (reddit/techcrunch/competitor)
  | 'worker_update'   // Worker progress update
  | 'worker_complete' // Worker finished
  | 'lead_batch'      // New leads discovered
  | 'completed'       // Job finished successfully
  | 'cancelled'       // Job cancelled by user
  | 'error'           // Error occurred
```

### SupervisorOrchestrator

The core orchestration logic (`supervisor_orchestrator.py`):

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SUPERVISOR ORCHESTRATOR v3.5                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: STRATEGY PLANNING (LLM Agent)                            │
│  ─────────────────────────────────────                             │
│  • Analyzes product description                                     │
│  • Generates Reddit search queries                                  │
│  • Identifies competitors to monitor                                │
│  • Sets TechCrunch industry focus                                   │
│                                                                     │
│  Phase 2: PARALLEL WORKER EXECUTION                                │
│  ─────────────────────────────────────                             │
│  • ThreadPoolExecutor launches 3 workers simultaneously             │
│  • Each worker runs its complete workflow                           │
│  • Results collected as workers complete                            │
│                                                                     │
│  Phase 2.5: COMPENSATION LOOP (if target not met)                  │
│  ─────────────────────────────────────────────────                 │
│  • LLM decides which strategies to retry                            │
│  • Runs additional passes with new queries/pages                    │
│  • Max 3 compensation rounds                                        │
│                                                                     │
│  Phase 3: AGGREGATION                                              │
│  ────────────────────                                              │
│  • Deduplicate leads across sources                                 │
│  • Sort by intent score (descending)                                │
│  • Return top N leads (target)                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Worker Workflows

**Reddit Worker:**
```
1. reddit_search(queries)     → Search Reddit for posts matching queries
2. reddit_score(posts)        → Score posts for buying intent (0-100)
3. reddit_extract(posts)      → Extract author info as leads
4. filter_sellers(leads)      → Remove sellers/promoters
```

**TechCrunch Worker:**
```
1. techcrunch_fetch(pages)    → Fetch funding articles from RSS
2. techcrunch_select(articles)→ Filter by target industry
3. techcrunch_extract(articles)→ Extract company details
4. serp_decision_makers(companies)→ Find founders via Google SERP
```

**Competitor Worker:**
```
1. competitor_identify(product) → Get competitor LinkedIn URLs
2. competitor_scrape(urls)      → Scrape post engagers (commenters, likers)
3. filter_sellers(leads)        → Remove sellers/competitor employees
```

---

## Database Schema

### Tables

#### `jobs`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key (auto-generated) |
| user_id | UUID | Foreign key to auth.users |
| query | TEXT | Natural language search query |
| max_leads | INTEGER | Target lead count (default 50) |
| status | TEXT | running, completed, failed, cancelled |
| total_leads | INTEGER | Final lead count |
| reddit_leads | INTEGER | Leads from Reddit |
| techcrunch_leads | INTEGER | Leads from TechCrunch |
| competitor_leads | INTEGER | Leads from competitor scraping |
| duration_seconds | INTEGER | Job execution time |
| cost_usd | DECIMAL(10,6) | Apify API cost |
| error | TEXT | Error message if failed |
| created_at | TIMESTAMP | Job creation time |
| completed_at | TIMESTAMP | Job completion time |

#### `leads`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key (auto-generated) |
| job_id | UUID | Foreign key to jobs |
| name | TEXT | Lead's name or username |
| title | TEXT | Job title |
| company | TEXT | Company name |
| linkedin_url | TEXT | LinkedIn profile URL |
| platform | TEXT | Source: reddit, techcrunch, linkedin |
| intent_score | INTEGER | Buying intent score (0-100) |
| intent_signals | TEXT[] | Array of intent indicators |
| bio | TEXT | Profile bio/summary |
| source_url | TEXT | Original source URL |
| created_at | TIMESTAMP | Discovery time |

### Row Level Security

```sql
-- Jobs: Users can only access their own jobs
CREATE POLICY "Users can view own jobs" ON jobs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own jobs" ON jobs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Leads: Access through job ownership
CREATE POLICY "Users can view leads for own jobs" ON leads
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM jobs
            WHERE jobs.id = leads.job_id
            AND jobs.user_id = auth.uid()
        )
    );
```

---

## Data Sources and Apify Tools

### Active Tools (Used by Workers)

| Tool | Actor ID | Worker | Purpose |
|------|----------|--------|---------|
| Reddit Scraper | `TwqHBuZZPHJxiQrTU` | Reddit | Search posts, extract authors |
| LinkedIn Profile Detail | `VhxlqQXRwhW8H5hNV` | Competitor | Deep profile scraping |
| LinkedIn Employees | `cIdqlEvw6afc1do1p` | Competitor | Company employee lookup |
| LinkedIn Company Search | `apimaestro/linkedin-companies-search-scraper` | Competitor | Find company pages |
| LinkedIn Company Posts | `harvestapi/linkedin-company-posts` | Competitor | Scrape post engagers |

### Reserved Tools (Available but not in current flow)

| Tool | Actor ID | Purpose |
|------|----------|---------|
| Twitter/X Scraper | `kaitoeasyapi/twitter-x-data-tweet-scraper` | Social mentions |
| LinkedIn Post Comments | `apimaestro/linkedin-post-comments-replies-engagements-scraper-no-cookies` | Engagement data |
| Crunchbase Scraper | `curious_coder/crunchbase-scraper` | Funding data |

### Non-Apify Data Sources

| Source | Method | Worker |
|--------|--------|--------|
| TechCrunch | RSS Feed parsing | TechCrunch |
| Google SERP | SerpAPI / direct | TechCrunch (founder lookup) |

---

## Cost Tracking System

### How It Works

```python
# 1. Job start - set tracking context
os.environ["CURRENT_JOB_ID"] = job_id

# 2. Each Apify call automatically tracks cost
run = client.actor(ACTOR_ID).call(run_input=input)
track_apify_cost(ACTOR_ID, run)  # Extracts cost from response

# 3. Job end - retrieve and save total
tracker = remove_tracker(job_id)
cost_usd = tracker.total_cost_usd
update_job_status(job_id, "completed", cost_usd=cost_usd)
```

### Cost Extraction

```python
def track_apify_cost(actor_id: str, run_result: Dict) -> float:
    # Method 1: Direct usageTotalUsd (pay-per-result actors)
    if run_result.get("usageTotalUsd", 0) > 0:
        cost = float(run_result["usageTotalUsd"])

    # Method 2: stats.computeUnits (compute billing)
    elif run_result.get("stats", {}).get("computeUnits", 0) > 0:
        cost = run_result["stats"]["computeUnits"] * 0.40

    # Method 3: usage.ACTOR_COMPUTE_UNITS
    elif run_result.get("usage", {}).get("ACTOR_COMPUTE_UNITS", 0) > 0:
        cost = run_result["usage"]["ACTOR_COMPUTE_UNITS"] * 0.40

    return cost
```

---

## Environment Variables

### Frontend (`.env.local`)

```bash
# Supabase (public keys)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Backend API URL
NEXT_PUBLIC_API_URL=https://api.yourapp.com
```

### Backend (`.env`)

```bash
# Supabase (service key for RLS bypass)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# OpenAI (for LLM agents)
OPENAI_API_KEY=sk-...

# Apify (for web scraping)
APIFY_API_TOKEN=apify_api_...

# Model configuration
AGENT_MODEL=gpt-4o-mini
AGENT_TEMPERATURE=0.3
TOOL_MODEL=gpt-4o-mini
```

---

## Deployment

### Frontend (Vercel)

- **Framework Preset**: Next.js
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Environment Variables**: Set via Vercel dashboard

### Backend (Render)

```yaml
# render.yaml
services:
  - type: web
    name: wrrk-pilot-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Required Environment Variables on Render:**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY`
- `APIFY_API_TOKEN`

---

## User Journey

```
1. User visits wrrk-pilot.vercel.app
            │
            ▼
2. (Optional) Signs in via /login
            │
            ▼
3. Enters query: "CRM software for startups"
            │
            ▼
4. Clicks "Start" → POST /api/v1/prospect/start
            │
            ▼
5. Opens SSE connection → GET /api/v1/prospect/{job_id}/stream
            │
            ▼
6. Watches Agent Workspace:
   • "Planning search strategy..."
   • "Deploying search agents..."
   • Reddit card: "Searching r/sales, r/startups..."
   • TechCrunch card: "Fetching funding articles..."
   • LinkedIn card: "Scraping competitor posts..."
            │
            ▼
7. Leads appear in table as they're found
   (sorted by intent score, HOT/WARM/COLD badges)
            │
            ▼
8. Job completes → "Complete: 47 qualified leads"
            │
            ▼
9. (If signed in) View history at /runs
   Click any run → see leads, export CSV
```

---

## Known Limitations (MVP v1)

1. **Fixed Target**: Always aims for 50 leads (hardcoded in frontend)
2. **No Real-Time Cost Display**: Cost only visible in database after completion
3. **No Lead Editing**: Cannot manually edit lead data
4. **Single User Sessions**: No team/workspace support
5. **No Email Integration**: Cannot send outreach from the app
6. **English Only**: No internationalization
7. **Limited Error Recovery**: Basic retry logic

---

## Future Roadmap

- [ ] Configurable lead targets
- [ ] Real-time cost display in UI
- [ ] Lead editing and notes
- [ ] Team workspaces
- [ ] Email outreach integration (SendGrid, Mailchimp)
- [ ] CRM export (Salesforce, HubSpot)
- [ ] Webhook notifications
- [ ] Usage analytics dashboard
- [ ] Custom ICP configuration
- [ ] Scheduled/recurring runs

---

## Development Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Supabase project
- Apify account
- OpenAI API key

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your keys
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Unix
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
uvicorn app.main:app --reload
```

---

*Last Updated: December 2025*
*Version: MVP v1.0*
