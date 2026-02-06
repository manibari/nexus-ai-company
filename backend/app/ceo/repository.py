"""
CEO To-Do Repository

In-memory 儲存（Tracer Bullet 版本）
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.ceo.models import (
    TodoItem,
    TodoAction,
    TodoType,
    TodoPriority,
    TodoStatus,
)


class TodoRepository:
    """CEO 待辦儲存庫"""

    def __init__(self):
        self._todos: Dict[str, TodoItem] = {}
        # 移除自動初始化樣本資料，避免每次重啟覆蓋用戶回覆
        # self._init_sample_data()

    def _init_sample_data(self):
        """初始化範例資料"""
        # 範例：需求問卷
        sample_questionnaire = TodoItem(
            id="TODO-202602061200-0001",
            project_name="美股分析買賣軟體",
            subject="回覆需求問卷 (17題)",
            description="PM 需要您回覆以下問題以開始規劃開發",
            from_agent="ORCHESTRATOR",
            from_agent_name="PM Agent",
            type=TodoType.QUESTIONNAIRE,
            priority=TodoPriority.HIGH,
            deadline=datetime.utcnow() + timedelta(days=1),
            actions=[
                TodoAction(id="respond", label="填寫問卷", style="primary"),
                TodoAction(id="skip", label="稍後處理", style="default"),
            ],
            related_entity_type="product",
            related_entity_id="PRD-2026-0001",
            payload={
                "questions": [
                    {"id": "q1", "question": "目標用戶是誰？", "options": ["散戶", "專業交易員", "機構", "全部"]},
                    {"id": "q2", "question": "用戶地區？", "options": ["台灣", "美國", "全球"]},
                    {"id": "q3", "question": "即時報價？", "options": ["即時 (付費)", "延遲15分鐘 (免費)"]},
                    {"id": "q4", "question": "分析功能？", "options": ["技術指標", "K線圖", "基本面", "財報"], "multi": True},
                    {"id": "q5", "question": "AI 功能？", "options": ["AI選股", "風險評估", "新聞情緒", "對話助理", "不需要"], "multi": True},
                    {"id": "q6", "question": "交易功能？", "options": ["僅分析", "模擬交易", "串接券商下單"]},
                    {"id": "q7", "question": "策略回測？", "options": ["需要", "不需要"]},
                    {"id": "q8", "question": "數據來源偏好？", "options": ["Yahoo Finance", "Alpha Vantage", "Polygon.io", "IEX Cloud", "無偏好"]},
                    {"id": "q9", "question": "目標平台？", "options": ["Web", "Desktop", "Mobile", "全平台"]},
                    {"id": "q10", "question": "開發預算？", "type": "text", "placeholder": "請輸入金額"},
                    {"id": "q11", "question": "月費預算？", "type": "text", "placeholder": "API+伺服器"},
                    {"id": "q12", "question": "MVP 時程？", "options": ["2週", "1個月", "3個月"]},
                    {"id": "q13", "question": "SEC 法規？", "options": ["需要", "不需要", "不確定"]},
                    {"id": "q14", "question": "商業模式？", "options": ["訂閱制", "買斷", "免費+廣告", "自用"]},
                    {"id": "q15", "question": "預期售價？", "type": "text", "placeholder": "若訂閱制，月費多少？"},
                    {"id": "q16", "question": "競品參考？", "type": "text", "placeholder": "TradingView/其他"},
                    {"id": "q17", "question": "最重要3功能？", "type": "text", "placeholder": "請排序"},
                ],
            },
        )
        self._todos[sample_questionnaire.id] = sample_questionnaire

    # === CRUD ===

    async def create(self, todo: TodoItem) -> TodoItem:
        """建立待辦"""
        self._todos[todo.id] = todo
        return todo

    async def get(self, todo_id: str) -> Optional[TodoItem]:
        """取得待辦"""
        return self._todos.get(todo_id)

    async def update(self, todo: TodoItem) -> TodoItem:
        """更新待辦"""
        self._todos[todo.id] = todo
        return todo

    async def delete(self, todo_id: str) -> bool:
        """刪除待辦"""
        if todo_id in self._todos:
            del self._todos[todo_id]
            return True
        return False

    async def list(
        self,
        status: Optional[TodoStatus] = None,
        priority: Optional[TodoPriority] = None,
        limit: int = 50,
    ) -> List[TodoItem]:
        """列出待辦"""
        results = list(self._todos.values())

        # 篩選
        if status:
            results = [t for t in results if t.status == status]
        if priority:
            results = [t for t in results if t.priority == priority]

        # 排序：優先級 > 過期 > 建立時間
        results.sort(key=lambda t: (
            t.priority_order,
            0 if t.is_overdue else 1,
            t.created_at,
        ))

        return results[:limit]

    async def list_pending(self) -> List[TodoItem]:
        """列出待處理的待辦"""
        return await self.list(status=TodoStatus.PENDING)

    # === 操作 ===

    async def respond(
        self,
        todo_id: str,
        action_id: str,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[TodoItem]:
        """CEO 回覆待辦"""
        todo = await self.get(todo_id)
        if not todo:
            return None

        todo.status = TodoStatus.COMPLETED
        todo.completed_at = datetime.utcnow()
        todo.response = {
            "action_id": action_id,
            "data": response_data,
            "responded_at": datetime.utcnow().isoformat(),
        }

        await self.update(todo)
        return todo

    async def snooze(
        self,
        todo_id: str,
        hours: int = 24,
    ) -> Optional[TodoItem]:
        """延後處理"""
        todo = await self.get(todo_id)
        if not todo:
            return None

        if todo.deadline:
            todo.deadline = todo.deadline + timedelta(hours=hours)
        else:
            todo.deadline = datetime.utcnow() + timedelta(hours=hours)

        await self.update(todo)
        return todo

    # === 統計 ===

    def get_stats(self) -> Dict[str, Any]:
        """取得統計"""
        all_todos = list(self._todos.values())
        pending = [t for t in all_todos if t.status == TodoStatus.PENDING]
        overdue = [t for t in pending if t.is_overdue]

        by_priority = {}
        for p in TodoPriority:
            by_priority[p.value] = len([t for t in pending if t.priority == p])

        by_type = {}
        for tt in TodoType:
            by_type[tt.value] = len([t for t in pending if t.type == tt])

        return {
            "total": len(all_todos),
            "pending": len(pending),
            "overdue": len(overdue),
            "completed": len([t for t in all_todos if t.status == TodoStatus.COMPLETED]),
            "by_priority": by_priority,
            "by_type": by_type,
        }
