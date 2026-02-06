"""
Nexus AI Company - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, ceo, control, dashboard, health, tasks
from app.db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await create_tables()
    print("🚀 Nexus AI Company is starting up...")
    yield
    # Shutdown
    print("👋 Nexus AI Company is shutting down...")


app = FastAPI(
    title="Nexus AI Company",
    description="零員工、全智能的虛擬企業系統 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(ceo.router, prefix="/api/v1/ceo", tags=["CEO"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(control.router, prefix="/api/v1/control", tags=["Control"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Nexus AI Company",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
    }
