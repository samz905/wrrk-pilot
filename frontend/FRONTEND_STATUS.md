# Frontend Implementation Status

## ✅ Completed

### Phase 1: Project Setup
- ✅ Created Next.js 14 project with TypeScript
- ✅ Installed Tailwind CSS
- ✅ Set up shadcn/ui with 9 components (button, input, textarea, card, badge, table, dialog, progress, label)
- ✅ Installed additional dependencies:
  - @tanstack/react-table
  - zustand
  - lucide-react
  - clsx
  - date-fns
- ✅ Created folder structure (components/prospecting, hooks, stores, lib)

### Phase 2: Data Layer
- ✅ Created TypeScript interfaces (lib/types.ts)
  - Lead interface with all fields
  - ActivityEvent interface
  - ProspectingJob interface
  - CREWS constant array
- ✅ Created mock data (lib/mock-data.ts)
  - 10 realistic leads with scores 58-92
  - 3 HOT leads (80-92)
  - 6 WARM leads (61-78)
  - 1 COLD lead (58)
  - Mock event timeline simulating 6-crew pipeline

## 🚧 Remaining Work

### Phase 2: UI Components (Next Step)
Need to create 5 components in `components/prospecting/`:

1. **QueryInput.tsx** - Search form
   - Textarea for query
   - Number input for max leads
   - Submit button
   - Loading state

2. **AgentActivity.tsx** - Live event log
   - Scrollable container
   - Color-coded event types (thought=gray, crew_started=blue, crew_completed=green, error=red)
   - Icons for each event type
   - Auto-scroll to bottom
   - Timestamps

3. **ProgressBar.tsx** - Pipeline progress
   - Progress bar 0-100%
   - 6 crew badges (Reddit, LinkedIn, Twitter, Google, Aggregation, Qualification)
   - Current crew highlighted
   - Completed crews shown as green

4. **LeadsTable.tsx** - Results table
   - TanStack React Table
   - Columns: Priority, Score, Name, Title, Company, Email (checkmark), Recency
   - Click row to open detail modal
   - Hover state
   - Sort by score

5. **LeadDetailModal.tsx** - Full lead details
   - Dialog with lead information
   - Sections:
     - Contact info (name, title, company, email, LinkedIn, Twitter)
     - Fit score breakdown with progress bars
     - Match reason
     - Intent signals (platform badges + quotes)
     - Final score breakdown
     - Recommended action

### Phase 3: Hooks
Create in `hooks/`:

1. **useEventStream.ts** - SSE connection
   - EventSource to backend `/stream` endpoint
   - Parse events and add to array
   - Handle completed/error states
   - Auto-close on completion

2. **useProspecting.ts** - Main API hook
   - POST to `/start` endpoint
   - Poll `/status` endpoint
   - Fetch `/results` endpoint
   - Manage job state

### Phase 4: Store
Create in `stores/`:

1. **prospecting-store.ts** - Zustand store
   - Current job state
   - Leads array
   - Events array
   - Loading/error states
   - Actions (startJob, updateEvents, setLeads)

### Phase 5: Main Page
Update `app/page.tsx`:
- 2-column layout (4/8 split)
- Left: QueryInput, ProgressBar, AgentActivity
- Right: LeadsTable
- Wire up all components
- Handle demo mode vs real API

### Phase 6: Demo Mode Toggle
Add environment variable:
- `NEXT_PUBLIC_DEMO_MODE=true` → use mock data
- `NEXT_PUBLIC_DEMO_MODE=false` → use real API
- Simulate delays in demo mode (show events appearing over time)

## Quick Start to Continue

### To run the dev server:
```bash
cd frontend
npm run dev
```

### Next component to build:
Start with `components/prospecting/QueryInput.tsx` - simplest component

### File locations:
- Types: `lib/types.ts`
- Mock data: `lib/mock-data.ts`
- UI components: `components/ui/` (already created by shadcn)
- Custom components: `components/prospecting/` (create these)

## Demo Mode vs Real API

**Demo Mode** (for quick demos):
- Uses `MOCK_LEADS` from `lib/mock-data.ts`
- Uses `generateMockEvents()` for agent activity
- Simulates delays with `setTimeout`
- No backend connection required

**Real API Mode**:
- Connects to `http://localhost:8000`
- POST `/api/v1/prospect/start`
- EventSource `/api/v1/prospect/{job_id}/stream`
- GET `/api/v1/prospect/{job_id}/results`

## Key Implementation Notes

1. **TanStack Table**: Use `useReactTable` hook with `getCoreRowModel`
2. **Event colors**: thought=gray-50, crew_started=blue-50, crew_completed=green-50, error=red-50
3. **Priority badges**: HOT=destructive (red), WARM=warning (yellow), COLD=secondary (gray)
4. **Progress calculation**: Sum crew weights based on current crew index
5. **Auto-scroll**: Use `useEffect` with `scrollTo` on event changes
6. **Modal**: Use shadcn Dialog component
7. **Icons**: Import from lucide-react (Loader, CheckCircle, AlertCircle, Brain, etc.)

## Example Usage

Once completed, users will:
1. Enter query: "find me leads for my project management software"
2. Click "Start Prospecting"
3. Watch real-time agent activity (6 crews executing)
4. See progress bar move 0% → 100%
5. View table of 10 leads with scores
6. Click lead → see full scoring breakdown and signals

## Components to Build (Estimated Time)

- QueryInput: 30 min
- AgentActivity: 45 min
- ProgressBar: 30 min
- LeadsTable: 1 hour
- LeadDetailModal: 1.5 hours
- Hooks: 1 hour
- Main page: 1 hour
- Polish: 1 hour

**Total remaining: ~6-7 hours**
