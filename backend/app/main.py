"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings

app = FastAPI(
    title="Lead Prospecting API",
    description="Intent-based lead prospecting tool",
    version="0.1.0"
)

# Parse ALLOWED_ORIGINS from comma-separated string
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_v1_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Lead Prospecting API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "lead-prospecting-api"}


if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
