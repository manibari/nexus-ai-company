"""
Nexus AI Company - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import activity, agents, catalog, ceo, ceo_todo, control, dashboard, developer, goals, health, intake, knowledge, pipeline, pm, product, qa, sales, tasks
from app.db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    import os

    # Startup
    await create_tables()

    # 初始化 Agent Registry
    from app.db.database import AsyncSessionLocal
    from app.agents.registry import AgentRegistry, set_registry
    from app.agents.gatekeeper import GatekeeperAgent
    from app.agents.pm import get_pm_agent
    from app.agents.sales import get_sales_agent
    from app.agents.orchestrator import OrchestratorAgent
    from app.agents.developer import get_developer_agent
    from app.agents.qa import get_qa_agent

    registry = AgentRegistry(session_factory=AsyncSessionLocal)
    registry.register(GatekeeperAgent())
    registry.register(get_pm_agent())
    registry.register(get_sales_agent())
    registry.register(OrchestratorAgent())
    registry.register(get_developer_agent())
    registry.register(get_qa_agent())
    set_registry(registry)

    # 初始化 Redis + Message Bus
    redis_client = None
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        import redis.asyncio as aioredis
        from app.agents.message_bus import MessageBus, set_bus

        redis_client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            retry_on_timeout=True,
        )

        # 檢查連線
        if await redis_client.ping():
            bus = MessageBus(
                redis_client=redis_client,
                registry=registry,
                session_factory=AsyncSessionLocal,
            )
            set_bus(bus)

            # Agent 狀態持久化：設定 Redis singleton + 恢復狀態
            from app.agents.agent_state import set_redis
            from app.api.agents import restore_agent_states
            set_redis(redis_client)
            await restore_agent_states()

            print(f"   Redis connected: {redis_url}")
        else:
            print(f"   Redis ping failed, MessageBus disabled")
    except Exception as e:
        print(f"   Redis unavailable ({e}), MessageBus disabled — running without it")
        redis_client = None

    print("🚀 Nexus AI Company is starting up...")
    print(f"   Registered agents: {[a['id'] for a in registry.list_agents()]}")
    yield
    # Shutdown
    if redis_client:
        await redis_client.aclose()
        print("   Redis connection closed")
    print("👋 Nexus AI Company is shutting down...")


app = FastAPI(
    title="Nexus AI Company",
    description="零員工、全智能的虛擬企業系統 API",
    version="0.8.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(ceo.router, prefix="/api/v1/ceo", tags=["CEO"])
app.include_router(ceo_todo.router, prefix="/api/v1/ceo", tags=["CEO To-Do"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(control.router, prefix="/api/v1/control", tags=["Control"])
app.include_router(intake.router, prefix="/api/v1/intake", tags=["CEO Intake"])
app.include_router(goals.router, prefix="/api/v1/goals", tags=["Goals"])
app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["Sales Pipeline"])
app.include_router(product.router, prefix="/api/v1/product", tags=["Product Board"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["Product Catalog"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"])
app.include_router(activity.router, prefix="/api/v1/activity", tags=["Agent Activity Log"])
app.include_router(pm.router, prefix="/api/v1/pm", tags=["PM Agent"])
app.include_router(developer.router, prefix="/api/v1/developer", tags=["Developer Agent"])
app.include_router(qa.router, prefix="/api/v1/qa", tags=["QA Agent"])
app.include_router(sales.router, prefix="/api/v1/sales", tags=["Sales Agent"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Nexus AI Company",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
    }
