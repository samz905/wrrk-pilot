# Lead Prospecting API - Demo Guide

## Quick Start for Team Demo

This API takes a query like "find me leads for my CRM software" and returns 10 high-quality leads with fit scores, intent signals, and match reasons.

### Starting the API

```bash
cd backend
source .venv/Scripts/activate  # On Windows: .venv\Scripts\activate
python app/main.py
```

The API will run on `http://localhost:8000`

### API Endpoints

#### 1. Start Prospecting Job
```bash
POST http://localhost:8000/api/v1/prospect/start
Content-Type: application/json

{
  "query": "find me leads for my CRM software",
  "max_leads": 10
}
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Prospecting job started",
  "stream_url": "/api/v1/prospect/550e8400-e29b-41d4-a716-446655440000/stream"
}
```

#### 2. Check Job Status
```bash
GET http://localhost:8000/api/v1/prospect/{job_id}/status
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",  // or "completed", "failed"
  "query": "find me leads for my CRM software",
  "max_leads": 10,
  "created_at": "2025-11-23T01:00:00",
  "error": null
}
```

#### 3. Get Final Results (THE MONEY SHOT FOR DEMO)
```bash
GET http://localhost:8000/api/v1/prospect/{job_id}/results
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "find me leads for my CRM software",
  "status": "completed",
  "pipeline": "Reddit → LinkedIn → Twitter → Google → Aggregation → Qualification",
  "lead_count": "Top 10",
  "qualified_leads_text": "... Top 10 leads with fit scores, signals, match reasons ...",
  "message": "Top 10 highest-quality leads identified and scored"
}
```

### Full Pipeline

The API runs 6 specialized AI crews in sequence:

1. **Reddit Crew** - Finds intent signals in discussions (r/sales, r/startups, etc.)
2. **LinkedIn Crew** - Identifies decision-makers and enriches profiles
3. **Twitter Crew** - Discovers conversations and pain points
4. **Google Crew** - Finds company triggers (funding, leadership changes)
5. **Aggregation Crew** - Deduplicates and merges leads across all platforms
6. **Qualification Crew** - Scores each lead (0-100) and returns top 10

### Example Lead Output Format

Each of the top 10 leads includes:

```
LEAD 1 (Score: 92) - PRIORITY: HOT
Name: Sarah Chen
Title: VP of Sales
Company: DataTech Corp
Contact:
  - Email: sarah.chen@datatech.com
  - LinkedIn: linkedin.com/in/sarachen
  - Twitter: @sarachen

Fit Score: 85
ICP Match:
  - Title Score: 45 - VP level in revenue organization
  - Industry Score: 25 - Perfect fit (B2B SaaS)
  - Signals Score: 25 - Strong buying intent detected

Final Score Breakdown:
  - ICP contribution: 34 (from 85 ICP score)
  - Platform diversity (Tier 2): 15
  - Contact quality: 20 (email + LinkedIn)
  - Intent strength: 15 (high intent)
  - Data completeness: 8

Match Reason: VP of Sales at B2B SaaS company actively evaluating CRM
alternatives with strong buying signals across multiple platforms. High
authority decision-maker with immediate need.

Intent Signals:
  - LinkedIn: Posted about evaluating CRM alternatives 5 days ago
  - Twitter: "Salesforce is way too expensive for what we need" 3 days ago

Platforms Found: LinkedIn, Twitter
Recency: 3 days ago
Domain: datatech.com

Recommended Action: Immediate outreach
```

### For the Frontend Table

When clicking on a lead in the table, show these details:
- **Fit Score**: 0-100 (higher = better fit)
- **Priority**: HOT (80-100), WARM (60-79), COLD (40-59)
- **Intent Signals**: What they said/did on each platform
- **Match Reason**: Why they're a good fit (1-2 sentences)
- **ICP Breakdown**: Title score, industry score, signals score
- **Contact Info**: Email, LinkedIn, Twitter
- **Tier**: 1 (3+ platforms), 2 (2 platforms), 3 (1 platform)
- **Recency**: How recent the signals are
- **Recommended Action**: Immediate outreach / Prioritize / Nurture

### Testing with cURL

```bash
# 1. Start job
curl -X POST http://localhost:8000/api/v1/prospect/start \
  -H "Content-Type: application/json" \
  -d '{"query": "find me leads for my CRM software", "max_leads": 10}'

# Save the job_id from response

# 2. Check status (repeat until "completed")
curl http://localhost:8000/api/v1/prospect/{job_id}/status

# 3. Get results
curl http://localhost:8000/api/v1/prospect/{job_id}/results
```

### Notes for Demo

- **Query Examples**:
  - "find me leads for my CRM software"
  - "companies looking for sales automation tools"
  - "VPs of Sales frustrated with Salesforce"

- **Response Time**: Full pipeline takes 3-5 minutes (runs 6 AI crews)

- **Quality Over Quantity**: Returns only top 10 highest-scoring leads, not all matches

- **Real Data**: This is NOT dummy data - it actually searches LinkedIn, Reddit, Twitter, and Google

- **Fit Scores**:
  - 80-100 = HOT (C-level + strong intent)
  - 60-79 = WARM (Directors/managers + pain points)
  - 40-59 = COLD (Questionable fit)
  - <40 = Disqualified (filtered out)

### Health Check

```bash
GET http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "lead-prospecting-api"
}
```
