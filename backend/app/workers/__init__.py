"""
Python Worker Functions for Parallel Prospecting

Each worker is a deterministic Python function that:
1. Receives strategy/queries from the orchestrator
2. Calls tools in sequence (search → score → extract)
3. Returns raw results for orchestrator to review

Workers run in parallel via ThreadPoolExecutor.
Orchestrator reviews each worker's output and decides next steps.

v3.5: Part of Flow-based orchestrator architecture.
"""
from .reddit_worker import RedditWorker
from .techcrunch_worker import TechCrunchWorker
from .competitor_worker import CompetitorWorker

__all__ = ['RedditWorker', 'TechCrunchWorker', 'CompetitorWorker']
