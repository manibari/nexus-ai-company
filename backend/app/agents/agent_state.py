"""
Agent State Persistence — Redis-backed

Redis singleton + read/write functions for agent state.
Graceful fallback when Redis is unavailable.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# --- Global Redis singleton ---

_redis = None  # redis.asyncio.Redis | None


def get_redis():
    """Get the global Redis client (set by main.py lifespan)."""
    return _redis


def set_redis(client):
    """Set the global Redis client."""
    global _redis
    _redis = client


KEY_PREFIX = "agent:state:"
TTL_SECONDS = 86400  # 24 hours


async def save_agent_state(
    agent_id: str,
    status: str,
    current_task: Optional[str],
    name: str,
    role: str,
    blocking_info: Optional[str] = None,
) -> None:
    """Save agent state to Redis (HSET + EXPIRE 24h). No-op if Redis unavailable."""
    client = get_redis()
    if client is None:
        return
    try:
        key = f"{KEY_PREFIX}{agent_id}"
        mapping: Dict[str, Any] = {
            "agent_id": agent_id,
            "status": status,
            "current_task": current_task or "",
            "name": name,
            "role": role,
            "blocking_info": blocking_info or "",
        }
        await client.hset(key, mapping=mapping)
        await client.expire(key, TTL_SECONDS)
    except Exception as e:
        logger.warning(f"Failed to save agent state to Redis: {e}")


async def load_agent_state(agent_id: str) -> Optional[Dict[str, str]]:
    """Load a single agent state from Redis. Returns None if missing or Redis unavailable."""
    client = get_redis()
    if client is None:
        return None
    try:
        key = f"{KEY_PREFIX}{agent_id}"
        data = await client.hgetall(key)
        return data if data else None
    except Exception as e:
        logger.warning(f"Failed to load agent state from Redis: {e}")
        return None


async def load_all_agent_states() -> Dict[str, Dict[str, str]]:
    """Load all agent states from Redis via SCAN. Returns empty dict if Redis unavailable."""
    client = get_redis()
    if client is None:
        return {}
    try:
        result: Dict[str, Dict[str, str]] = {}
        async for key in client.scan_iter(match=f"{KEY_PREFIX}*"):
            data = await client.hgetall(key)
            if data and "agent_id" in data:
                result[data["agent_id"]] = data
        return result
    except Exception as e:
        logger.warning(f"Failed to load agent states from Redis: {e}")
        return {}
