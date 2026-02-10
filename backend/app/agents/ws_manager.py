"""
WebSocket Connection Manager

管理所有 WebSocket 連線，提供 broadcast 推播功能。
"""

import json
import logging
from typing import List, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 連線管理器"""

    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受並記錄新的 WebSocket 連線"""
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(f"WebSocket connected, total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket):
        """移除已斷開的 WebSocket 連線"""
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info(f"WebSocket disconnected, total: {len(self._connections)}")

    async def broadcast(self, message: dict):
        """向所有連線推播 JSON 訊息，自動移除失效連線"""
        if not self._connections:
            return

        data = json.dumps(message, ensure_ascii=False)
        dead: List[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


# --- Global singleton ---

_ws_manager: Optional[ConnectionManager] = None


def get_ws_manager() -> Optional[ConnectionManager]:
    """Get the global ConnectionManager (set by main.py lifespan)."""
    return _ws_manager


def set_ws_manager(manager: ConnectionManager):
    """Set the global ConnectionManager."""
    global _ws_manager
    _ws_manager = manager
