"""
Action Journal - 動作日誌與回滾機制

解決問題：錯誤操作無法撤回，沒有執行歷史

提供功能：
- 完整動作記錄
- 可撤回動作的回滾
- 錯誤標記與學習機制
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ActionStatus(Enum):
    """動作狀態"""
    PENDING = "pending"        # 待執行
    EXECUTING = "executing"    # 執行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失敗
    REVERTED = "reverted"      # 已撤回
    MARKED_MISTAKE = "marked_mistake"  # 標記為錯誤


class ActionType(Enum):
    """動作類型"""
    # 通訊類（不可撤回）
    EMAIL_SEND = "email_send"
    MESSAGE_SEND = "message_send"
    API_CALL_EXTERNAL = "api_call_external"

    # 資料類（可撤回）
    STAGE_CHANGE = "stage_change"
    DATA_UPDATE = "data_update"
    DATA_CREATE = "data_create"
    DATA_DELETE = "data_delete"

    # 檔案類（可撤回）
    FILE_CREATE = "file_create"
    FILE_UPDATE = "file_update"
    FILE_DELETE = "file_delete"

    # 系統類
    APPROVAL_REQUEST = "approval_request"
    AGENT_QUERY = "agent_query"

    # 其他
    CUSTOM = "custom"


@dataclass
class ActionRecord:
    """
    動作記錄

    記錄 Agent 執行的每一個動作
    """
    id: str
    agent_id: str
    task_id: Optional[str]
    action_type: ActionType
    action_name: str
    params: Dict[str, Any]

    # 執行資訊
    status: ActionStatus = ActionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # 可撤回性
    reversible: bool = False
    reverse_action: Optional[str] = None
    reverse_params: Optional[Dict[str, Any]] = None
    original_state: Optional[Dict[str, Any]] = None  # 執行前的狀態（用於回滾）

    # 學習機制
    marked_as_mistake: bool = False
    mistake_feedback: Optional[str] = None
    improvement_applied: bool = False

    # 時間戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reverted_at: Optional[datetime] = None

    # 關聯
    parent_action_id: Optional[str] = None  # 父動作（用於複合動作）
    checkpoint_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "action_type": self.action_type.value,
            "action_name": self.action_name,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "reversible": self.reversible,
            "marked_as_mistake": self.marked_as_mistake,
            "created_at": self.created_at.isoformat(),
        }


# 可撤回動作的定義
REVERSIBLE_ACTIONS = {
    ActionType.STAGE_CHANGE: True,
    ActionType.DATA_UPDATE: True,
    ActionType.DATA_CREATE: True,
    ActionType.DATA_DELETE: True,
    ActionType.FILE_CREATE: True,
    ActionType.FILE_UPDATE: True,
    ActionType.FILE_DELETE: True,
    ActionType.APPROVAL_REQUEST: True,
}


class ActionJournal:
    """
    動作日誌

    記錄所有 Agent 動作，支援回滾和錯誤學習
    """

    def __init__(self, db_session):
        self.db = db_session
        self._actions: Dict[str, ActionRecord] = {}
        self._reverse_handlers: Dict[ActionType, Callable] = {}

    def register_reverse_handler(
        self,
        action_type: ActionType,
        handler: Callable,
    ):
        """註冊撤回處理器"""
        self._reverse_handlers[action_type] = handler

    async def record(
        self,
        agent_id: str,
        action_type: ActionType,
        action_name: str,
        params: Dict[str, Any],
        task_id: Optional[str] = None,
        original_state: Optional[Dict[str, Any]] = None,
        checkpoint_id: Optional[str] = None,
    ) -> ActionRecord:
        """記錄動作（執行前）"""
        from uuid import uuid4

        action = ActionRecord(
            id=str(uuid4()),
            agent_id=agent_id,
            task_id=task_id,
            action_type=action_type,
            action_name=action_name,
            params=params,
            reversible=REVERSIBLE_ACTIONS.get(action_type, False),
            original_state=original_state,
            checkpoint_id=checkpoint_id,
        )

        self._actions[action.id] = action
        await self._persist_action(action)

        logger.info(
            f"[ActionJournal] Recorded: {action.action_name} "
            f"(reversible={action.reversible})"
        )

        return action

    async def start_execution(self, action_id: str):
        """標記開始執行"""
        action = self._actions.get(action_id)
        if action:
            action.status = ActionStatus.EXECUTING
            action.started_at = datetime.utcnow()
            await self._persist_action(action)

    async def complete(
        self,
        action_id: str,
        result: Dict[str, Any],
        success: bool = True,
    ):
        """完成動作"""
        action = self._actions.get(action_id)
        if not action:
            return

        action.result = result
        action.completed_at = datetime.utcnow()
        action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED

        if not success:
            action.error = result.get("error", "Unknown error")

        await self._persist_action(action)

        logger.info(
            f"[ActionJournal] Completed: {action.action_name} "
            f"(success={success})"
        )

    async def revert(self, action_id: str, reverted_by: str = "CEO") -> bool:
        """
        撤回動作

        Returns:
            True if successfully reverted, False otherwise
        """
        action = self._actions.get(action_id)

        if not action:
            logger.error(f"Action {action_id} not found")
            return False

        if not action.reversible:
            logger.error(f"Action {action_id} is not reversible")
            return False

        if action.status == ActionStatus.REVERTED:
            logger.warning(f"Action {action_id} already reverted")
            return True

        # 取得撤回處理器
        handler = self._reverse_handlers.get(action.action_type)

        if handler:
            try:
                await handler(action)
                action.status = ActionStatus.REVERTED
                action.reverted_at = datetime.utcnow()
                await self._persist_action(action)

                logger.info(
                    f"[ActionJournal] Reverted: {action.action_name} by {reverted_by}"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to revert action {action_id}: {e}")
                return False

        # 如果沒有處理器但有 original_state，嘗試還原
        if action.original_state:
            try:
                await self._restore_state(action)
                action.status = ActionStatus.REVERTED
                action.reverted_at = datetime.utcnow()
                await self._persist_action(action)
                return True
            except Exception as e:
                logger.error(f"Failed to restore state for {action_id}: {e}")
                return False

        logger.error(f"No reverse handler for action type {action.action_type}")
        return False

    async def mark_as_mistake(
        self,
        action_id: str,
        feedback: str,
        marked_by: str = "CEO",
    ):
        """
        標記動作為錯誤

        用於學習機制，記錄什麼情況下做了錯誤決策
        """
        action = self._actions.get(action_id)
        if not action:
            return

        action.marked_as_mistake = True
        action.mistake_feedback = feedback
        action.status = ActionStatus.MARKED_MISTAKE

        await self._persist_action(action)

        logger.info(
            f"[ActionJournal] Marked as mistake: {action.action_name} "
            f"by {marked_by}"
        )

        # 觸發學習機制
        await self._trigger_learning(action, feedback)

    async def get_actions(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        status: Optional[ActionStatus] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ActionRecord]:
        """查詢動作記錄"""
        actions = list(self._actions.values())

        if agent_id:
            actions = [a for a in actions if a.agent_id == agent_id]
        if task_id:
            actions = [a for a in actions if a.task_id == task_id]
        if status:
            actions = [a for a in actions if a.status == status]
        if since:
            actions = [a for a in actions if a.created_at >= since]

        # 按時間倒序
        actions.sort(key=lambda a: a.created_at, reverse=True)

        return actions[:limit]

    async def get_reversible_actions(
        self,
        agent_id: Optional[str] = None,
    ) -> List[ActionRecord]:
        """取得可撤回的動作"""
        return [
            a for a in self._actions.values()
            if a.reversible
            and a.status == ActionStatus.COMPLETED
            and (agent_id is None or a.agent_id == agent_id)
        ]

    async def get_mistakes(
        self,
        agent_id: Optional[str] = None,
    ) -> List[ActionRecord]:
        """取得標記為錯誤的動作"""
        return [
            a for a in self._actions.values()
            if a.marked_as_mistake
            and (agent_id is None or a.agent_id == agent_id)
        ]

    async def _restore_state(self, action: ActionRecord):
        """還原狀態"""
        # TODO: 根據 action_type 實作還原邏輯
        pass

    async def _trigger_learning(self, action: ActionRecord, feedback: str):
        """觸發學習機制"""
        # 記錄到學習日誌，供後續改進 prompt
        learning_record = {
            "action_id": action.id,
            "agent_id": action.agent_id,
            "action_type": action.action_type.value,
            "action_name": action.action_name,
            "params": action.params,
            "context": action.result,
            "mistake_feedback": feedback,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # TODO: 寫入學習資料庫
        logger.info(f"[Learning] Recorded mistake for future improvement")

    async def _persist_action(self, action: ActionRecord):
        """持久化動作到資料庫"""
        # TODO: 實作資料庫寫入
        pass


class ActionScope:
    """
    動作範圍上下文管理器

    自動記錄動作的開始和結束
    """

    def __init__(
        self,
        journal: ActionJournal,
        agent_id: str,
        action_type: ActionType,
        action_name: str,
        params: Dict[str, Any],
        task_id: Optional[str] = None,
        original_state: Optional[Dict[str, Any]] = None,
    ):
        self.journal = journal
        self.agent_id = agent_id
        self.action_type = action_type
        self.action_name = action_name
        self.params = params
        self.task_id = task_id
        self.original_state = original_state
        self.action: Optional[ActionRecord] = None

    async def __aenter__(self) -> ActionRecord:
        self.action = await self.journal.record(
            agent_id=self.agent_id,
            action_type=self.action_type,
            action_name=self.action_name,
            params=self.params,
            task_id=self.task_id,
            original_state=self.original_state,
        )
        await self.journal.start_execution(self.action.id)
        return self.action

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.action:
            if exc_type:
                await self.journal.complete(
                    self.action.id,
                    {"error": str(exc_val)},
                    success=False,
                )
            # 如果沒有例外，需要手動呼叫 complete
        return False  # 不抑制例外
