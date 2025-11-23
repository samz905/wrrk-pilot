"""API v1 routes."""
from fastapi import APIRouter
from .prospect import router as prospect_router

router = APIRouter()
router.include_router(prospect_router)

__all__ = ['router']
