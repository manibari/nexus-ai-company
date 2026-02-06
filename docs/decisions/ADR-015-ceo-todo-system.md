# ADR-015: CEO To-Do System (CEO 待辦系統)

## 狀態
提議中

## 背景

### 問題發現
目前 CEO Inbox (`CEOInbox.tsx`) 只有 **輸入功能**：
- CEO 輸入新想法/商機
- 系統分析並建議動作
- CEO 確認/取消

**缺少的功能**：
- **待辦清單 (To-Do List)**：顯示等待 CEO 處理的事項
- **統一格式**：專案名稱、待辦事項、DDL
- **來源追蹤**：哪個 Agent 發起的請求
- **行動按鈕**：直接在 Inbox 回覆/處理

### 使用場景

| 場景 | 發起者 | 類型 | CEO 動作 |
|------|--------|------|----------|
| PM 需求問卷 | ORCHESTRATOR | 需求確認 | 回覆問卷 |
| 商機折扣審批 | HUNTER | 審批 | 同意/拒絕 |
| UAT 驗收 | INSPECTOR | 驗收 | 通過/退回 |
| 預算超支警告 | LEDGER | 通知 | 確認已讀 |
| 專案阻擋升級 | ORCHESTRATOR | 決策 | 選擇方案 |

## 決策

### 重新設計 CEO Inbox

將 CEO Inbox 分為兩個 Tab：
1. **To-Do（待辦）**：等待 CEO 處理的事項
2. **Input（輸入）**：CEO 主動輸入新想法（現有功能）

### UI 設計

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📥 CEO Inbox                                                             │
├─────────────────────────────────────────────────────────────────────────┤
│ [📋 To-Do (3)] [✏️ Input]                                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ === 待辦清單 ===                                                         │
│                                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🔴 緊急                                                              │ │
│ ├─────────────────────────────────────────────────────────────────────┤ │
│ │ 專案：美股分析買賣軟體                                               │ │
│ │ 待辦：回覆需求問卷 (17題)                                            │ │
│ │ 來源：PM Agent (ORCHESTRATOR)                                        │ │
│ │ DDL：2026-02-07 18:00                                                │ │
│ │                                                                      │ │
│ │ [展開詳情 ▼]                           [處理]                        │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🟡 一般                                                              │ │
│ ├─────────────────────────────────────────────────────────────────────┤ │
│ │ 專案：ABC Corp 系統整合案                                            │ │
│ │ 待辦：審批 15% 折扣                                                  │ │
│ │ 來源：Sales Agent (HUNTER)                                           │ │
│ │ DDL：2026-02-08 12:00                                                │ │
│ │                                                                      │ │
│ │ [展開詳情 ▼]                    [拒絕] [同意]                        │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🟢 低優先                                                            │ │
│ ├─────────────────────────────────────────────────────────────────────┤ │
│ │ 專案：內部報表系統                                                   │ │
│ │ 待辦：UAT 驗收                                                       │ │
│ │ 來源：QA Agent (INSPECTOR)                                           │ │
│ │ DDL：2026-02-10 18:00                                                │ │
│ │                                                                      │ │
│ │ [展開詳情 ▼]              [退回] [通過]                              │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 資料模型

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


class TodoPriority(Enum):
    URGENT = "urgent"       # 🔴 緊急
    HIGH = "high"           # 🟠 高
    NORMAL = "normal"       # 🟡 一般
    LOW = "low"             # 🟢 低


class TodoType(Enum):
    APPROVAL = "approval"             # 審批（同意/拒絕）
    QUESTIONNAIRE = "questionnaire"   # 問卷（填寫回覆）
    REVIEW = "review"                 # 審查（通過/退回）
    DECISION = "decision"             # 決策（選擇方案）
    NOTIFICATION = "notification"     # 通知（確認已讀）


class TodoStatus(Enum):
    PENDING = "pending"       # 待處理
    IN_PROGRESS = "in_progress"  # 處理中
    COMPLETED = "completed"   # 已完成
    EXPIRED = "expired"       # 已過期


@dataclass
class TodoAction:
    """可執行的動作"""
    id: str
    label: str               # 按鈕文字，如 "同意", "拒絕"
    style: str = "default"   # default, primary, danger
    requires_input: bool = False  # 是否需要輸入（如退回原因）
    input_placeholder: Optional[str] = None


@dataclass
class TodoItem:
    """CEO 待辦事項"""
    id: str                          # TODO-{timestamp}-{xxxx}

    # 基本資訊
    project_name: str                # 專案名稱
    subject: str                     # 待辦事項
    description: Optional[str]       # 詳細說明

    # 來源
    from_agent: str                  # 發起的 Agent ID
    from_agent_name: str             # Agent 名稱

    # 分類
    type: TodoType
    priority: TodoPriority = TodoPriority.NORMAL

    # 時間
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None  # DDL
    completed_at: Optional[datetime] = None

    # 狀態
    status: TodoStatus = TodoStatus.PENDING

    # 動作
    actions: List[TodoAction] = field(default_factory=list)

    # 回覆（CEO 的回應）
    response: Optional[Dict[str, Any]] = None

    # 關聯
    related_entity_type: Optional[str] = None  # opportunity, product, goal
    related_entity_id: Optional[str] = None

    # 額外資料（問卷題目、審批詳情等）
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "subject": self.subject,
            "description": self.description,
            "from_agent": self.from_agent,
            "from_agent_name": self.from_agent_name,
            "type": self.type.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "actions": [{"id": a.id, "label": a.label, "style": a.style,
                        "requires_input": a.requires_input} for a in self.actions],
            "response": self.response,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "payload": self.payload,
            "is_overdue": self.is_overdue,
        }

    @property
    def is_overdue(self) -> bool:
        if self.deadline and self.status == TodoStatus.PENDING:
            return datetime.utcnow() > self.deadline
        return False
```

### API 設計

```yaml
# CEO To-Do API
GET    /api/v1/ceo/todos                    # 取得待辦清單
GET    /api/v1/ceo/todos/{id}               # 取得待辦詳情
POST   /api/v1/ceo/todos/{id}/respond       # CEO 回覆
POST   /api/v1/ceo/todos/{id}/snooze        # 延後處理
DELETE /api/v1/ceo/todos/{id}               # 刪除（標記完成）

# Agent 發起待辦
POST   /api/v1/ceo/todos                    # Agent 建立待辦

# 統計
GET    /api/v1/ceo/todos/stats              # 待辦統計（數量、過期）
```

### 前端實作

#### 1. 更新 CEOInbox.tsx

```tsx
// 新增 Tab 切換
const [activeView, setActiveView] = useState<'todo' | 'input'>('todo')

// 新增待辦狀態
const [todos, setTodos] = useState<TodoItem[]>([])
const [todoStats, setTodoStats] = useState<TodoStats | null>(null)

// 渲染
return (
  <div className="bg-slate-800 rounded-lg p-6">
    {/* Tab 切換 */}
    <div className="flex gap-2 mb-6">
      <button onClick={() => setActiveView('todo')}>
        📋 To-Do ({todoStats?.pending || 0})
      </button>
      <button onClick={() => setActiveView('input')}>
        ✏️ Input
      </button>
    </div>

    {/* 內容 */}
    {activeView === 'todo' ? (
      <TodoList todos={todos} onRespond={handleRespond} />
    ) : (
      <InputForm ... />  // 現有功能
    )}
  </div>
)
```

#### 2. 新增 TodoList 元件

```tsx
interface TodoListProps {
  todos: TodoItem[]
  onRespond: (todoId: string, actionId: string, input?: string) => void
}

function TodoList({ todos, onRespond }: TodoListProps) {
  // 按優先級分組
  const grouped = groupByPriority(todos)

  return (
    <div className="space-y-4">
      {/* 緊急 */}
      {grouped.urgent.length > 0 && (
        <TodoGroup title="🔴 緊急" items={grouped.urgent} onRespond={onRespond} />
      )}
      {/* 一般 */}
      {grouped.normal.length > 0 && (
        <TodoGroup title="🟡 待處理" items={grouped.normal} onRespond={onRespond} />
      )}
      {/* 低優先 */}
      {grouped.low.length > 0 && (
        <TodoGroup title="🟢 低優先" items={grouped.low} onRespond={onRespond} />
      )}
    </div>
  )
}
```

#### 3. 新增 TodoCard 元件

```tsx
function TodoCard({ item, onRespond }: { item: TodoItem, onRespond: Function }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-slate-600 rounded-lg p-4">
      {/* Header */}
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-medium text-white">{item.project_name}</div>
          <div className="text-cyan-400">{item.subject}</div>
        </div>
        <div className="text-right text-sm">
          <div className="text-gray-400">來源: {item.from_agent_name}</div>
          <div className={item.is_overdue ? 'text-red-400' : 'text-gray-400'}>
            DDL: {formatDeadline(item.deadline)}
          </div>
        </div>
      </div>

      {/* Expand/Collapse */}
      <button onClick={() => setExpanded(!expanded)}>
        {expanded ? '收起 ▲' : '展開詳情 ▼'}
      </button>

      {/* Payload (expanded) */}
      {expanded && (
        <div className="mt-4 p-4 bg-slate-700 rounded-lg">
          {renderPayload(item.type, item.payload)}
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 mt-4">
        {item.actions.map(action => (
          <button
            key={action.id}
            onClick={() => onRespond(item.id, action.id)}
            className={getActionStyle(action.style)}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  )
}
```

## 實作計劃

### Phase 1: 後端 API (優先)

| 步驟 | 檔案 | 內容 |
|------|------|------|
| 1 | `backend/app/ceo/__init__.py` | 模組初始化 |
| 2 | `backend/app/ceo/models.py` | TodoItem, TodoAction 等模型 |
| 3 | `backend/app/ceo/repository.py` | In-memory CRUD |
| 4 | `backend/app/api/ceo.py` | REST API endpoints |
| 5 | `backend/app/main.py` | 註冊 router |

### Phase 2: 前端 UI

| 步驟 | 檔案 | 內容 |
|------|------|------|
| 1 | `frontend/src/components/CEOInbox.tsx` | 重構，加入 Tab 切換 |
| 2 | `frontend/src/components/TodoList.tsx` | 待辦清單元件 |
| 3 | `frontend/src/components/TodoCard.tsx` | 待辦卡片元件 |
| 4 | `frontend/src/components/QuestionnaireForm.tsx` | 問卷回覆表單 |

### Phase 3: Agent 整合

| 步驟 | 內容 |
|------|------|
| 1 | PM Agent 發需求問卷時，建立 TodoItem |
| 2 | Sales Agent 需審批時，建立 TodoItem |
| 3 | QA Agent 送 UAT 時，建立 TodoItem |

## 時程估算

| 階段 | 內容 | 預估時間 |
|------|------|----------|
| Phase 1 | 後端 API | 30 分鐘 |
| Phase 2 | 前端 UI | 45 分鐘 |
| Phase 3 | Agent 整合 | 30 分鐘 |
| **總計** | | **~2 小時** |

## 後果

### 優點
- CEO 有統一的待辦管理介面
- 待辦格式標準化（專案、事項、DDL）
- 可追蹤處理進度
- 過期提醒

### 缺點
- 增加系統複雜度
- 需維護待辦狀態

## 參考

- ADR-006: CEO Intake
- ADR-014: Requirements Gathering
- 現有 `frontend/src/components/CEOInbox.tsx`
