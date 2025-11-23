"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting LifeOS backend...")
    await db.connect_db()

    # Start background scheduler if enabled
    if settings.enable_scheduler:
        from app.workers.scheduler import scheduler

        scheduler.start()
        logger.info("Background scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down LifeOS backend...")
    await db.close_db()

    if settings.enable_scheduler:
        from app.workers.scheduler import scheduler

        scheduler.shutdown()
        logger.info("Background scheduler stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Personal Life Assistant - Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return JSONResponse(
        content={
            "message": "Welcome to LifeOS - AI Personal Life Assistant",
            "version": settings.app_version,
            "docs": "/docs",
        }
    )


# Import and include routers
from app.agent.router import router as agent_router
from app.auth.router import router as auth_router
from app.calendar.router import router as calendar_router
from app.confirmations.router import router as confirmations_router
from app.conversations.router import router as conversations_router
from app.emails.router import router as emails_router
from app.integrations.router import router as integrations_router
from app.memory.router import router as memory_router
from app.tasks.router import router as tasks_router

# API v1 routes
API_V1_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=f"{API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(
    integrations_router, prefix=f"{API_V1_PREFIX}/integrations", tags=["Integrations"]
)
app.include_router(emails_router, prefix=f"{API_V1_PREFIX}/emails", tags=["Emails"])
app.include_router(
    calendar_router, prefix=f"{API_V1_PREFIX}/calendar", tags=["Calendar"]
)
app.include_router(tasks_router, prefix=f"{API_V1_PREFIX}/tasks", tags=["Tasks"])
app.include_router(memory_router, prefix=f"{API_V1_PREFIX}/memory", tags=["Memory"])
app.include_router(agent_router, prefix=f"{API_V1_PREFIX}/agent", tags=["Agent"])
app.include_router(
    confirmations_router, prefix=f"{API_V1_PREFIX}/confirmations", tags=["Confirmations"]
)
app.include_router(
    conversations_router, prefix=f"{API_V1_PREFIX}/conversations", tags=["Conversations"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=settings.workers,
    )
