# Production MVP Progress Tracker

> **Goal**: Ship a production-ready MVP with auth, persistence, and deployment
> **Stack**: Supabase + Vercel + Render

---

## Progress Overview

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Supabase Setup | ✅ Done | Project created, schema deployed |
| 2. Backend Database | ✅ Done | database.py with CRUD operations |
| 3. Backend Auth | ✅ Done | auth.py with JWT validation |
| 4. Backend API Updates | ✅ Done | /runs, /runs/{id}, /runs/{id}/export |
| 5. Frontend Supabase | ✅ Done | Client + SSR + middleware |
| 6. Frontend Auth (Login) | ✅ Done | Login page with email + Google |
| 7. Frontend Runs Pages | ✅ Done | /runs and /runs/[id] with export |
| 8. Deployment Configs | ✅ Done | render.yaml + vercel.json |
| 9. Install & Test | ✅ Done | Local testing complete, bugs fixed |
| 10. Deploy Backend | 🔄 Next | Render deployment |
| 11. Deploy Frontend | ⏳ Pending | Vercel deployment |

---

## Deploy Backend to Render

### Step 1: Push to GitHub
Make sure all changes are committed and pushed to your GitHub repo.

### Step 2: Create New Web Service on Render
1. Go to https://dashboard.render.com
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `wrrk-api`
   - **Root Directory**: `backend`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Set Environment Variables
In Render dashboard, add these environment variables:

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.11.0` |
| `DEBUG` | `false` |
| `APIFY_API_TOKEN` | (copy from backend/.env) |
| `OPENAI_API_KEY` | (copy from backend/.env) |
| `SERPER_API_KEY` | (copy from backend/.env) |
| `SUPABASE_URL` | `https://zmfoenrsurrplyskhhcn.supabase.co` |
| `SUPABASE_ANON_KEY` | (copy from backend/.env) |
| `SUPABASE_SERVICE_KEY` | (copy from backend/.env - the JWT token) |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app,http://localhost:3000` |

### Step 4: Deploy
Click **Create Web Service**. Render will build and deploy.

### Step 5: Verify
Once deployed, test the health endpoint:
```
https://wrrk-api.onrender.com/health
```

---

## Deploy Frontend to Vercel (After Backend)

### Environment Variables for Vercel
| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://wrrk-api.onrender.com/api/v1` |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://zmfoenrsurrplyskhhcn.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | (copy from frontend/.env.local) |

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/core/database.py` | Supabase DB operations |
| `backend/app/core/auth.py` | JWT validation middleware |
| `backend/render.yaml` | Render deployment config |
| `frontend/.env.local` | Frontend environment vars |
| `frontend/lib/supabase/client.ts` | Browser Supabase client |
| `frontend/lib/supabase/server.ts` | Server Supabase client |
| `frontend/middleware.ts` | Route protection |
| `frontend/app/login/page.tsx` | Login/signup page |
| `frontend/app/auth/callback/route.ts` | OAuth callback |
| `frontend/app/runs/page.tsx` | Runs list page |
| `frontend/app/runs/[id]/page.tsx` | Run details page |
| `frontend/components/layout/Header.tsx` | Shared navigation header |
| `frontend/components/ui/dropdown-menu.tsx` | Dropdown component |
| `frontend/vercel.json` | Vercel deployment config |

## Files Modified

| File | Changes |
|------|---------|
| `backend/.env` | Added Supabase keys |
| `backend/requirements.txt` | Added supabase, PyJWT, pydantic-settings |
| `backend/app/core/config.py` | Added Supabase settings |
| `backend/app/api/v1/prospect.py` | Added auth, DB saves, /runs endpoints |
| `frontend/package.json` | Added @supabase/ssr, dropdown-menu |
| `frontend/lib/api.ts` | Added auth headers, env-based URL |

---

## Environment Variables (Reference)

See deployment sections above for actual values to use.

---

## Notes

- Backend uses service key to bypass RLS for saving leads
- Frontend uses anon key (client-safe)
- Auth is optional for /start endpoint (works without login, but no persistence)
- /runs endpoints require authentication
