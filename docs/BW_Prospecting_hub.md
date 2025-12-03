# BW_Prospecting_hub - Complete Documentation

## Product Overview

**BW_Prospecting_hub** is an ICP-based (Ideal Customer Profile) lead generation system that finds decision-makers matching specific criteria and enriches them with verified email addresses. Unlike the main WRRK Pilot which uses natural language queries and intent signals, this system focuses on structured ICP parameters and guaranteed email delivery.

### Core Value Proposition

- **ICP-Based Targeting**: Define exact criteria (job titles, industries, company size, region)
- **Multi-Source Search**: Combines SerpAPI (Google) + Bright Data MCP for comprehensive coverage
- **Email Discovery & Verification**: Multi-step email finding with Bouncer validation + Apollo fallback
- **Deep Company Research**: 7 different search queries per company for rich enrichment
- **AI-Powered Parsing**: GPT-4o-mini extracts structured data from search results

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BW_PROSPECTING_HUB SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────┐         ┌─────────────────────────────────┐ │
│  │  FRONTEND (Vite+React) │  REST   │      BACKEND (Flask)            │ │
│  │                        │◄───────►│                                 │ │
│  │  Landing Page          │         │   app.py (main)                 │ │
│  │  ICP Form Modal        │         │   app_mcp.py (MCP client)       │ │
│  │  Prospect Cards        │         │   email_finder/ module          │ │
│  │  Company Modal         │         │                                 │ │
│  └────────────────────────┘         └───────────────┬─────────────────┘ │
│                                                     │                   │
│                                                     ▼                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    DATA SOURCES (Parallel)                        │   │
│  │                                                                   │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐           │   │
│  │  │   SerpAPI   │  │ Bright Data  │  │  Email Finder  │           │   │
│  │  │   (Google)  │  │   MCP        │  │   Pipeline     │           │   │
│  │  │             │  │              │  │                │           │   │
│  │  │ • LinkedIn  │  │ • search_    │  │ • Google CSE   │           │   │
│  │  │   profiles  │  │   engine     │  │ • Bouncer      │           │   │
│  │  │ • Company   │  │ • scrape_as_ │  │ • Apollo       │           │   │
│  │  │   info      │  │   markdown   │  │                │           │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘           │   │
│  │        │                  │                  │                   │   │
│  │        └──────────────────┴──────────────────┘                   │   │
│  │                           │                                      │   │
│  │                           ▼                                      │   │
│  │               ┌─────────────────────┐                            │   │
│  │               │  OpenAI GPT-4o-mini │                            │   │
│  │               │  (Parsing + Scoring)│                            │   │
│  │               └─────────────────────┘                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI library |
| Vite | Latest | Build tool |
| Lucide React | Latest | Icons |
| CSS Variables | - | Dark theme styling |

### Directory Structure

```
lead_finder/BW_Prospecting_hub/frontend/
├── src/
│   ├── App.jsx                    # Main app with state management
│   ├── main.jsx                   # Entry point
│   └── components/
│       ├── LandingPage.jsx        # Hero page with "Get Started"
│       ├── ICPForm.jsx            # ICP criteria form modal
│       ├── Header.jsx             # Sticky header with New Search
│       ├── ProspectList.jsx       # Grid of prospect cards
│       ├── ProspectCard.jsx       # Individual lead card
│       └── CompanyModal.jsx       # Detailed company popup
└── dist/                          # Built static files
```

### UI/UX Flow

#### Landing Page
```
┌────────────────────────────────────────────────────┐
│                  LANDING PAGE                       │
│                                                    │
│        🎯 AI-Powered Lead Intelligence             │
│              Simplified                            │
│                                                    │
│      ⚡ Lightning Fast   🎯 Precision Targeting    │
│                🧠 Deep Intelligence                │
│                                                    │
│              [ Get Started ]                       │
└────────────────────────────────────────────────────┘
```

#### ICP Form Modal
```
┌────────────────────────────────────────────────────┐
│               CREATE ICP                     ✕     │
├────────────────────────────────────────────────────┤
│                                                    │
│  ICP Name: [Enterprise SaaS Buyers_______]         │
│  Company Size: [50-500 employees     ▼]            │
│                                                    │
│  Job Titles: [CTO, VP Engineering________]         │
│  Industries: [SaaS, Fintech______________]         │
│                                                    │
│  Region: [North America__________________]         │
│  Technologies: [AWS, Salesforce__________]         │
│                                                    │
│  Pain Points: [churn, security___________]         │
│  Budget: [$50,000] - [$500,000]                    │
│                                                    │
│         [ 🔍 Find Prospects ]                      │
└────────────────────────────────────────────────────┘
```

#### Results Page
```
┌────────────────────────────────────────────────────────────┐
│  Prospecting Hub                      [ + New Search ]     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌──────────────┐  ┌──────────────────────────────────────┐│
│ │ ICP DETAILS  │  │         PROSPECT CARDS               ││
│ │              │  │                                      ││
│ │ Name:        │  │ ┌───────────┐  ┌───────────┐         ││
│ │ Enterprise   │  │ │ John Doe  │  │ Jane S.   │         ││
│ │ SaaS Buyers  │  │ │ CTO       │  │ VP Eng    │         ││
│ │              │  │ │ Acme Corp │  │ Beta Inc  │         ││
│ │ Size: 50-500 │  │ │ SF, CA    │  │ NYC       │         ││
│ │              │  │ │  85% 🟢   │  │  72% 🟡   │         ││
│ │ Titles:      │  │ └───────────┘  └───────────┘         ││
│ │ CTO, VP...   │  │                                      ││
│ │              │  │ ┌───────────┐  ┌───────────┐         ││
│ │ Industries:  │  │ │ Alex B.   │  │ Mike T.   │         ││
│ │ SaaS, Fintech│  │ │ ...       │  │ ...       │         ││
│ └──────────────┘  └──────────────────────────────────────┘│
│                                                            │
│               [ Click card → Company Modal ]               │
└────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. LandingPage.jsx
- Animated gradient background grid
- Hero section with tagline: "AI-Powered Lead Intelligence, Simplified"
- Feature highlights:
  - ⚡ Lightning Fast - "Get qualified leads in seconds"
  - 🎯 Precision Targeting - "Define your ideal customer"
  - 🧠 Deep Intelligence - "AI-powered company research"
- "Get Started" CTA button

#### 2. ICPForm.jsx (9 fields)
- **ICP Name**: Label for this search profile
- **Company Size**: Dropdown (1-50, 50-500, 500-5000, 5000+)
- **Job Titles**: Comma-separated (CTO, VP Engineering, etc.)
- **Industries**: Comma-separated (SaaS, Fintech, etc.)
- **Region**: Geographic target (North America, Europe, etc.)
- **Technologies**: Tech stack filter (AWS, Salesforce, etc.)
- **Pain Points**: Problems they face (churn, security, etc.)
- **Min/Max Budget**: Dollar amounts for budget range

#### 3. ProspectCard.jsx
- Name, Title, Company, Location display
- Confidence badge with color coding:
  - 🟢 Green (80%+): High confidence match
  - 🟡 Yellow (50-79%): Medium confidence
  - 🔴 Red (<50%): Low confidence
- LinkedIn icon for direct profile access
- Click to open CompanyModal

#### 4. CompanyModal.jsx
- Header: Company name, website link, location
- Contact Info section: All emails, all phones
- Company About: AI-generated description
- Social Links: LinkedIn, Twitter, Facebook
- Domain and website information
- Close button (✕)

---

## Backend Architecture

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.x | Runtime |
| Flask | Latest | Web framework |
| Flask-CORS | Latest | Cross-origin support |
| OpenAI | 1.0+ | GPT-4o-mini for parsing |
| aiohttp | Latest | Async HTTP (MCP client) |
| BeautifulSoup4 | Latest | HTML parsing |
| requests | Latest | HTTP client |

### File Structure

```
lead_finder/BW_Prospecting_hub/
├── app.py                    # Main Flask app (1073 lines)
│                             # - /find-leads endpoint
│                             # - SerpAPI integration
│                             # - Deep company research
│                             # - OpenAI enrichment
├── app_mcp.py                # Bright Data MCP client (867 lines)
│                             # - BrightDataMCP class
│                             # - search_web(), scrape_url()
│                             # - ICP-based lead search
├── email_finder/             # Email discovery module
│   ├── __init__.py
│   ├── finder.py             # Main find_contact_details()
│   ├── validators.py         # Bouncer + Apollo APIs
│   └── utils.py              # Domain extraction, patterns
├── mcp_test.py               # MCP connectivity test
├── requirements.txt          # Python dependencies
└── .env.example              # Environment template
```

### API Endpoints

#### POST `/find-leads`
Main endpoint for ICP-based lead discovery.

**Request Body:**
```json
{
  "icpName": "Enterprise SaaS Buyers",
  "companySize": "50-500",
  "jobTitles": "CTO, VP Engineering",
  "industries": "SaaS, Fintech",
  "region": "North America",
  "technologies": "AWS, Salesforce",
  "painPoints": "churn, security",
  "minBudget": 50000,
  "maxBudget": 500000,
  "useGemini": true,
  "useCompanyResearch": true
}
```

**Response:**
```json
{
  "count": 15,
  "query": "\"CTO\" SaaS North America site:linkedin.com/in",
  "leads": [...],
  "mcp_leads": [...],
  "serpapi_leads_count": 10,
  "mcp_leads_count": 5,
  "api_stats": {
    "serpapi_success": 10,
    "serpapi_fail": 0
  }
}
```

#### GET `/api/health`
Health check endpoint.

#### GET `/api/mcp-status`
Returns MCP client status and configuration.

---

## Data Flow

### Main Processing Pipeline

```
1. ICP Form Submission
         │
         ▼
2. Build LinkedIn Search Query
   "\"CTO, VP Engineering\" SaaS North America site:linkedin.com/in"
         │
         ▼
3. SerpAPI Search (10 results)
         │
         ├──► Parse LinkedIn profiles from results
         │
         ▼
4. For each lead: process_lead_ultimate()
         │
         ├──► Extract name, title from LinkedIn title
         │    (formats: "Name - Title" or "Name | Title")
         │
         ├──► Extract company from snippet
         │    (patterns: "at Company", "@ Company", "Experience: Company")
         │
         ▼
5. Deep Company Research (7 queries per company)
         │
         ├──► Query 1: "{company} official website"
         ├──► Query 2: "{company} about headquarters address employees"
         ├──► Query 3: "{company} contact email phone customer support"
         ├──► Query 4: "{company} funding valuation revenue employees size"
         ├──► Query 5: "{company} news 2024 2025"
         ├──► Query 6: "{company} linkedin twitter facebook crunchbase"
         └──► Query 7: "site:{domain} about OR contact OR team OR company"
         │
         ▼
6. Website Scraping (scrape_website_contacts)
         │
         ├──► Scrape pages: /, /contact, /contact-us, /about, /about-us, /team
         ├──► Extract emails via regex
         ├──► Extract phones via regex
         └──► Extract social media links
         │
         ▼
7. OpenAI GPT-4o-mini Enrichment (extract_with_openai_ultimate)
         │
         ├──► Parse all research into structured JSON
         ├──► Extract: person details, company info
         ├──► Generate: pain points, buying signals, talking points
         └──► Calculate confidence scores (0-100)
         │
         ▼
8. Email Finder Fallback (if no email found)
         │
         ├──► Google Custom Search → find company domain
         ├──► Generate 15+ email patterns
         ├──► Validate with Bouncer API
         └──► Fallback to Apollo People Match
         │
         ▼
9. Parallel: MCP Agent Search (background thread, 60s timeout)
         │
         ├──► Build ICP-based queries
         ├──► Bright Data search_engine tool
         ├──► OpenAI parsing
         └──► Merge with SerpAPI leads
         │
         ▼
10. Deduplicate by (name, company) & Return
```

---

## Email Finding Pipeline

### Complete Flow (email_finder module)

```
find_contact_details(name, company)
         │
         ▼
1. Google Custom Search API
   Query: "{company} official website"
         │
         ├──► Check knowledge graph website first
         ├──► Get top search result link
         └──► Extract domain from URL
         │
         ▼
2. Domain Validation & Guessing
         │
         ├──► Check if valid format (has dot, letters)
         ├──► If invalid, try common TLDs:
         │    - {sanitized_company}.com
         │    - {sanitized_company}.io
         │    - {sanitized_company}.co
         │    - {sanitized_company}.net
         │    - {sanitized_company}.ai
         └──► HTTP HEAD check if domain responds
         │
         ▼
3. Email Pattern Generation (15+ patterns)
         │
         ├──► first.last@domain.com
         ├──► first_last@domain.com
         ├──► first-last@domain.com
         ├──► flast@domain.com
         ├──► f.last@domain.com
         ├──► firstl@domain.com
         ├──► first@domain.com
         ├──► last@domain.com
         ├──► first.l@domain.com
         └──► ... additional variations
         │
         ▼
4. Bouncer Real-Time Validation
   API: https://api.usebouncer.com/v1/email/verify
         │
         ├──► For each pattern (with 8s timeout):
         │    - GET with x-api-key header
         │    - Check response.status == "deliverable"
         │    - If valid → RETURN immediately
         └──► If none valid → continue to fallback
         │
         ▼
5. Apollo People Match Fallback
   API: https://api.apollo.io/v1/people/match
         │
         ├──► POST: { first_name, last_name, company }
         ├──► Check: response.person.email
         ├──► Check: response.people[0].email
         └──► Return if found
         │
         ▼
6. Return Result
   {
     "name": "John Doe",
     "company": "Acme Corp",
     "domain": "acme.com",
     "valid_email": "john.doe@acme.com",
     "source": "bouncer" | "apollo" | "none",
     "all_generated_patterns": [...]
   }
```

---

## MCP (Bright Data) Integration

### BrightDataMCP Class

```python
class BrightDataMCP:
    """Client for Bright Data MCP server with proper session management"""

    # Protocol: JSON-RPC 2.0
    # Endpoint: https://mcp.brightdata.com/mcp?token={token}
    # Handles: SSE (Server-Sent Events) responses

    async def initialize():
        """Start MCP session with protocol version 2024-11-05"""
        # Returns session ID for subsequent calls

    async def call_tool(tool_name, arguments):
        """Generic JSON-RPC tool invocation"""
        # Handles session expiration and re-initialization

    async def search_web(query, count=10):
        """Uses 'search_engine' tool for web search"""

    async def scrape_url(url):
        """Uses 'scrape_as_markdown' tool for content extraction"""
```

### MCP Search Flow (app_mcp.py)

```
1. Build ICP-based search queries (max 5):
   ├──► "{title}" {industry} companies {region} LinkedIn
   ├──► {title} at {industry} company {region} contact email
   ├──► {industry} companies using {technologies} decision makers
   └──► {company_size} {industry} companies {region} executives

2. Execute searches via Bright Data MCP search_engine tool

3. Parse results with OpenAI GPT-4o-mini:
   ├──► Extract: name, title, company, email, LinkedIn, source
   ├──► Score relevance to ICP (1-10)
   └──► Return only REAL data (no fabrication)

4. Calculate confidence scores:
   ├──► Industry match: +30 points
   ├──► Job title match: +25 points
   ├──► Location match: +15 points
   ├──► Email available: +10 points
   ├──► LinkedIn available: +10 points
   └──► Company size match: +10 points

5. Grade assignment:
   ├──► A: 80-100% (PRIORITY: High-value lead)
   ├──► B: 60-79% (QUALIFIED: Good fit)
   ├──► C: 40-59% (NURTURE: Potential fit)
   └──► D: <40% (RESEARCH: Needs qualification)
```

---

## OpenAI Integration

### AI Enrichment (extract_with_openai_ultimate)

```python
# Model: gpt-4o-mini
# Temperature: 0.3 (low for consistency)
# Max tokens: 4000

System Prompt:
"You are a world-class B2B sales intelligence analyst.
Extract maximum information from provided research data.
Return only valid JSON with no markdown formatting."

Output Schema:
{
  "person": {
    "full_name": "John Doe",
    "job_title": "Chief Technology Officer",
    "seniority_level": "C-level",
    "department": "Engineering",
    "email": "john@company.com",
    "phone": "+1-555-123-4567",
    "linkedin_url": "linkedin.com/in/johndoe",
    "location": "San Francisco, CA",
    "years_of_experience": "15+",
    "education": "Stanford CS",
    "previous_companies": ["Google", "Meta"]
  },
  "company": {
    "name": "Acme Corp",
    "website": "https://acme.com",
    "domain": "acme.com",
    "description": "2-4 sentence description...",
    "industry": "SaaS",
    "sub_industry": "Marketing Automation",
    "founded": "2018",
    "headquarters": {
      "address": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "country": "USA"
    },
    "size": {
      "employees": "100-500",
      "growth_rate": "Growing"
    },
    "contact": {
      "main_phone": "+1-800-555-0000",
      "support_email": "support@acme.com",
      "sales_email": "sales@acme.com"
    },
    "financials": {
      "revenue": "$10M ARR",
      "funding": "$25M Series B",
      "valuation": "$100M"
    },
    "leadership": {
      "ceo": "Jane Smith",
      "founders": ["Jane Smith", "Bob Johnson"]
    },
    "social": {
      "linkedin": "linkedin.com/company/acme",
      "twitter": "@acmecorp"
    }
  },
  "sales_intelligence": {
    "pain_points": [
      "Scaling customer success team",
      "Reducing churn rate",
      "Improving onboarding"
    ],
    "buying_signals": [
      "Recent Series B funding",
      "Hiring 5+ sales reps",
      "Expanding to Europe"
    ],
    "talking_points": [
      "Congrats on the Series B!",
      "Noticed you're scaling CS - we help with..."
    ]
  },
  "confidence_scores": {
    "person_info": 85,
    "company_info": 90,
    "contact_info": 75,
    "overall": 83
  }
}
```

---

## Environment Variables

### Required

```bash
# Search APIs (at least one required)
SERPAPI_KEY=               # SerpAPI - Google search API

# AI (required for enrichment)
OPENAI_API_KEY=            # GPT-4o-mini for parsing

# Email Finding (for verified emails)
GOOGLE_API_KEY=            # Google Custom Search
GOOGLE_CX=                 # Custom Search Engine ID
BOUNCER_API_KEY=           # Email validation (usebouncer.com)
APOLLO_API_KEY=            # People matching fallback
```

### Optional

```bash
# Parallel search (enhances results)
BRIGHT_DATA_API_TOKEN=     # Bright Data MCP

# Alternative validators (configured but unused)
CLEAROUT_API_KEY=          # Clearout email validation
ZEROBN_API_KEY=            # ZeroBounce (legacy)
```

---

## Key Differences: WRRK Pilot vs BW_Prospecting_hub

| Aspect | WRRK Pilot (Main) | BW_Prospecting_hub |
|--------|-------------------|-------------------|
| **Input** | Natural language query ("CRM software") | Structured ICP form (9 fields) |
| **Approach** | Intent-based (buying signals) | Criteria-based (ICP matching) |
| **Data Sources** | Reddit, TechCrunch, LinkedIn competitors | SerpAPI + Bright Data MCP |
| **Email Finding** | Optional (from LinkedIn profiles) | **Core feature** (multi-step pipeline) |
| **Real-time** | SSE streaming updates | Batch request/response |
| **Framework** | Next.js 15 + FastAPI | Vite + Flask |
| **LLM Use** | Strategy planning + intent scoring | Parsing + sales intelligence |
| **Output** | Leads with intent signals | Leads with verified emails |
| **History** | Saved to Supabase | No persistence |
| **Processing Time** | ~5-8 min (parallel workers) | ~30-45s per lead (serial) |
| **Confidence Scoring** | Intent score (0-100) | ICP match score (A/B/C/D grades) |

---

## Potential Merge Opportunities

### Complementary Capabilities

**WRRK Pilot provides:**
- Intent detection from Reddit discussions
- TechCrunch funding signals (buyers with budget)
- Competitor engagement monitoring
- Real-time streaming UX
- Persistent job history

**BW_Prospecting_hub provides:**
- ICP-based structured filtering
- Email discovery & verification pipeline
- Deep 7-query company research
- Sales intelligence generation
- Confidence scoring with grades

### Suggested Integration Points

1. **Add email_finder module to WRRK backend**
   - Import `find_contact_details()` function
   - Run after leads discovered by workers
   - Prioritize high-intent leads for email lookup

2. **Add ICP form as search mode option**
   - Toggle between "Natural Language" and "ICP Form"
   - Use ICP fields to enhance worker targeting

3. **Integrate Bouncer/Apollo for email verification**
   - Add BOUNCER_API_KEY and APOLLO_API_KEY to env
   - Validate emails found in LinkedIn profiles

4. **Add deep company research for high-value leads**
   - Run 7-query research for leads with score > 80
   - Display sales_intelligence in lead details

5. **Merge confidence scoring**
   - Combine intent_score with ICP match score
   - Create composite "lead quality" metric

---

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 18+ (for frontend)
- API keys (see Environment Variables)

### Backend Setup
```bash
cd lead_finder/BW_Prospecting_hub
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python app.py  # Starts on http://localhost:5000
```

### Frontend Setup
```bash
cd lead_finder/BW_Prospecting_hub/frontend
npm install
npm run dev   # Development
npm run build # Production (outputs to dist/)
```

---

*Last Updated: December 2025*
*Version: 1.0*
