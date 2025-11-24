# Lead Prospecting Frontend

AI-powered multi-platform lead discovery with real-time agent visualization.

## Quick Start

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Demo Mode

Currently in **DEMO MODE** - no backend required!

1. Enter: "find me leads for my project management software"
2. Click "Start Prospecting"
3. Watch 6 AI crews execute in real-time
4. View 10 scored leads
5. Click any lead for full details

## Features

- Real-time agent activity visualization
- 6-crew pipeline: Reddit → LinkedIn → Twitter → Google → Aggregation → Qualification
- Interactive lead table (sortable, clickable)
- Detailed lead modals with fit scores, intent signals, match reasons
- Demo mode with realistic dummy data
- Production SSE streaming support

## Components Built

- QueryInput - Search form
- AgentActivity - Live event log
- ProgressBar - Pipeline visualization
- LeadsTable - Sortable results table
- LeadDetailModal - Complete lead details

## Tech Stack

- Next.js 14 + TypeScript
- Tailwind CSS + shadcn/ui
- TanStack React Table
- Lucide Icons

## Switch to Production

Set `DEMO_MODE = false` in `app/page.tsx` to connect to real backend at `http://localhost:8000`

See `FRONTEND_STATUS.md` for implementation details.
