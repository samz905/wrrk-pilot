# Lead Prospecting Backend

Intent-based lead prospecting tool using CrewAI and Apify.

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Then edit `.env` and add your API keys:

```
APIFY_API_TOKEN=your_actual_apify_token
ANTHROPIC_API_KEY=your_actual_anthropic_key
```

### 3. Test Setup

```bash
python test_setup.py
```

This will verify:
- Environment variables are loaded
- All dependencies are installed
- LinkedIn tool can be instantiated

### 4. Run FastAPI Server

```bash
python -m app.main
```

Or with uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then visit:
- http://localhost:8000 - Root endpoint
- http://localhost:8000/health - Health check
- http://localhost:8000/docs - API documentation (Swagger)

## Phase 1 Complete ✓

- [x] Backend structure created
- [x] FastAPI app with health check
- [x] LinkedIn Apify tool implemented
- [x] Test script created

## Next Steps

**Phase 2**: Create LinkedIn Crew with agent personality and test end-to-end scraping.
