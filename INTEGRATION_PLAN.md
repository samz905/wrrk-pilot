# Frontend-Backend Integration Plan

## Overview
Integrate the Next.js frontend with the FastAPI backend to enable real-time prospecting with parallel worker visualization and live lead population.

**Target:** 50 leads (hardcoded for now)
**Key Change:** Backend runs 3 workers in parallel - UI must show all 3 simultaneously

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  1. User clicks Start                                                   │
│  2. POST /api/v1/prospect/start → get job_id + stream_url               │
│  3. Connect to SSE stream → receive real-time events                    │
│  4. Transform events → update workspaceCards + leads state              │
│  5. Stop button → abort fetch + call cancel endpoint                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  POST /start → creates job, spawns background thread                    │
│  GET /stream → SSE endpoint, yields events from queue                   │
│  POST /cancel → abort running job                                       │
│                                                                         │
│  SupervisorOrchestrator runs:                                           │
│  ├─ Strategy Planning (LLM)                                             │
│  ├─ 3 Parallel Workers: Reddit, TechCrunch, Competitor                  │
│  ├─ Compensation Loop (up to 3 rounds)                                  │
│  └─ Aggregation + Deduplication                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Progress Tracking

- [x] **Phase 1: Backend API**
  - [x] Switch prospect.py to use SupervisorOrchestrator
  - [x] Add cancel endpoint
  - [x] Wire log_callback to event queue
- [x] **Phase 2: Frontend API**
  - [x] Create frontend/lib/api.ts
- [x] **Phase 3: Frontend UI**
  - [x] Update types.ts (simplified Lead)
  - [x] Update page.tsx (real API + stop button)
  - [x] Update QueryInput.tsx (stop button)
  - [x] Update LeadsTable.tsx (new columns)
  - [x] Update LeadDetailModal.tsx
- [ ] **Phase 4: Integration Test**
  - [ ] Start backend server
  - [ ] Start frontend dev server
  - [ ] Test query with 50 leads
  - [ ] Verify parallel cards work
  - [ ] Verify stop button works
- [x] **Phase 5: UI Polish & Real-time Leads**
  - [x] Fix table scrolling (add height constraints)
  - [x] Add strategic details to workspace cards (lead count, companies)
  - [x] Real-time lead streaming (emit per-worker instead of batch)
- [x] **Phase 6: UX Overhaul (Cursor-inspired)**
  - [x] Table auto-scroll to bottom on new leads
  - [x] Switch to Lucide icons (fixed broken SVG loading)
  - [x] Message transformation layer (hide technical jargon)
  - [x] Filter meaningful reasoning cards only
  - [x] Progress header with visual progress bar
  - [x] Visual refinements to ToolCard (status badges)

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/api/v1/prospect.py` | MODIFY | Switch to SupervisorOrchestrator, add cancel endpoint, message transformation |
| `frontend/lib/api.ts` | CREATE | API client with SSE support |
| `frontend/lib/types.ts` | MODIFY | Simplify Lead interface, add StrategicDetails |
| `frontend/app/page.tsx` | MODIFY | Real API integration, stop button, progress tracking, reasoning filter |
| `frontend/components/prospecting/QueryInput.tsx` | MODIFY | Add stop button |
| `frontend/components/prospecting/LeadsTable.tsx` | MODIFY | Update columns, add auto-scroll |
| `frontend/components/prospecting/LeadDetailModal.tsx` | MODIFY | Update for simplified Lead |
| `frontend/components/prospecting/ToolCard.tsx` | MODIFY | Lucide icons, status badges, strategic details |
| `frontend/components/prospecting/AgentWorkspace.tsx` | MODIFY | Add ProgressHeader integration |
| `frontend/components/prospecting/ProgressHeader.tsx` | CREATE | Progress bar component with lead count |

---

## Testing

```bash
# Terminal 1: Backend
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open http://localhost:3000, enter "AI-powered customer support platform", verify:
- 3 tool cards appear simultaneously
- Leads populate in real-time
- Stop button works
- Final count reaches ~50 leads
