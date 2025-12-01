"""Supabase database client and operations."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from .config import settings


# Initialize Supabase client
_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client."""
    global _supabase
    if _supabase is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_ANON_KEY
        )
    return _supabase


# =============================================================================
# Job Operations
# =============================================================================

def create_job(user_id: str, query: str, max_leads: int = 50) -> Dict[str, Any]:
    """Create a new prospecting job."""
    supabase = get_supabase()
    result = supabase.table("jobs").insert({
        "user_id": user_id,
        "query": query,
        "max_leads": max_leads,
        "status": "running"
    }).execute()
    return result.data[0] if result.data else None


def update_job_status(
    job_id: str,
    status: str,
    error: Optional[str] = None,
    total_leads: Optional[int] = None,
    reddit_leads: Optional[int] = None,
    techcrunch_leads: Optional[int] = None,
    competitor_leads: Optional[int] = None,
    duration_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """Update job status and stats."""
    supabase = get_supabase()

    update_data = {"status": status}

    if error is not None:
        update_data["error"] = error
    if total_leads is not None:
        update_data["total_leads"] = total_leads
    if reddit_leads is not None:
        update_data["reddit_leads"] = reddit_leads
    if techcrunch_leads is not None:
        update_data["techcrunch_leads"] = techcrunch_leads
    if competitor_leads is not None:
        update_data["competitor_leads"] = competitor_leads
    if duration_seconds is not None:
        update_data["duration_seconds"] = duration_seconds
    if status in ["completed", "failed", "cancelled"]:
        update_data["completed_at"] = datetime.utcnow().isoformat()

    result = supabase.table("jobs").update(update_data).eq("id", job_id).execute()
    return result.data[0] if result.data else None


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get a job by ID."""
    supabase = get_supabase()
    result = supabase.table("jobs").select("*").eq("id", job_id).execute()
    return result.data[0] if result.data else None


def get_user_jobs(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all jobs for a user, ordered by created_at desc."""
    supabase = get_supabase()
    result = supabase.table("jobs").select("*").eq(
        "user_id", user_id
    ).order("created_at", desc=True).limit(limit).execute()
    return result.data or []


# =============================================================================
# Lead Operations
# =============================================================================

def save_leads(job_id: str, leads: List[Dict[str, Any]]) -> int:
    """Save multiple leads to the database. Returns count saved."""
    if not leads:
        return 0

    supabase = get_supabase()

    # Prepare leads for insertion
    lead_records = []
    for lead in leads:
        lead_records.append({
            "job_id": job_id,
            "name": lead.get("name", ""),
            "title": lead.get("title", ""),
            "company": lead.get("company", ""),
            "linkedin_url": lead.get("linkedin_url", ""),
            "platform": lead.get("platform") or lead.get("source_platform", ""),
            "intent_score": lead.get("intent_score", 0),
            "intent_signals": lead.get("intent_signals") or lead.get("intent_signal", []),
            "bio": lead.get("bio", ""),
            "source_url": lead.get("source_url", "")
        })

    # Batch insert
    result = supabase.table("leads").insert(lead_records).execute()
    return len(result.data) if result.data else 0


def get_job_leads(job_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get leads for a job, ordered by intent_score desc."""
    supabase = get_supabase()
    result = supabase.table("leads").select("*").eq(
        "job_id", job_id
    ).order("intent_score", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []


def get_job_lead_count(job_id: str) -> int:
    """Get total lead count for a job."""
    supabase = get_supabase()
    result = supabase.table("leads").select("id", count="exact").eq("job_id", job_id).execute()
    return result.count or 0


# =============================================================================
# Test Connection
# =============================================================================

def test_connection() -> bool:
    """Test Supabase connection."""
    try:
        supabase = get_supabase()
        # Try a simple query
        supabase.table("jobs").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"[DB] Connection test failed: {e}")
        return False
