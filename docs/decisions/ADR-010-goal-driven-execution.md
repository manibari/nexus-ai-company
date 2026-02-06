# ADR-010: Goal-Driven Execution (目標導向執行)

## 狀態
已採納

## 背景
CEO 提出關鍵需求：
> "所有 agent 的行動都要有明確的目標與邊界、交付時間與期限，
> 如果是大目標要分階段，並針對每個階段的成果進行確認。"

目前系統的問題：
1. Agent 執行任務沒有明確的「完成定義」
2. 沒有時間邊界，任務可能無限延長
3. 大任務一次性交付，無法早期發現問題
4. 沒有階段性確認機制

## 決策
導入 **Goal-Driven Execution** 框架：
- 每個任務必須有明確的 Goal（目標）
- 每個 Goal 必須有 Boundary（邊界）和 Deadline（期限）
- 大 Goal 必須拆分為 Phases（階段）
- 每個 Phase 完成後必須經過 Checkpoint（確認點）

## 核心概念

### 1. Goal（目標）

```yaml
goal:
  id: "GOAL-2024-001"
  title: "開發股票爬蟲分析系統"

  # === 目標定義 ===
  objective: "建立每日自動爬取台股資料並分析的系統"

  # === 成功標準（可測量）===
  success_criteria:
    - "能爬取全部上市股票收盤價"
    - "能識別符合 3 個篩選條件的股票"
    - "每日 8:30 前發送 LINE 通知"
    - "系統穩定運行 3 天無錯誤"

  # === 邊界 ===
  boundary:
    in_scope:
      - "台股上市股票"
      - "日K資料"
      - "三大法人買賣超"
      - "LINE 通知"
    out_of_scope:
      - "上櫃股票"
      - "即時報價"
      - "自動交易"
      - "手機 App"

  # === 時間 ===
  timeline:
    created_at: "2024-02-06"
    deadline: "2024-02-13"  # 7 天後
    buffer_days: 2          # 緩衝時間

  # === 優先級 ===
  priority: "high"  # critical, high, medium, low

  # === 負責人 ===
  owner: "ORCHESTRATOR"
  assignees: ["BUILDER", "INSPECTOR"]
```

### 2. Phase（階段）

大目標必須拆分為可交付的階段：

```yaml
phases:
  - id: "PHASE-001"
    name: "Phase 1: 資料爬取"
    goal_id: "GOAL-2024-001"

    # 階段目標
    objective: "完成股票資料爬取功能"

    # 交付物
    deliverables:
      - "爬蟲程式碼"
      - "資料儲存機制"
      - "錯誤處理"

    # 驗收標準
    acceptance_criteria:
      - "能爬取 TWSE 全部股票"
      - "資料正確存入資料庫"
      - "有重試機制"

    # 時間
    timeline:
      start: "2024-02-06"
      end: "2024-02-08"    # 2 天
      estimated_hours: 6

    # 狀態
    status: "pending"  # pending, in_progress, review, completed, blocked

    # 前置階段
    depends_on: []

  - id: "PHASE-002"
    name: "Phase 2: 分析邏輯"
    goal_id: "GOAL-2024-001"

    objective: "實作股票篩選條件"

    deliverables:
      - "篩選引擎"
      - "三個篩選條件實作"

    acceptance_criteria:
      - "法人連買 3 天"
      - "突破月線"
      - "量增 2 倍"

    timeline:
      start: "2024-02-08"
      end: "2024-02-10"    # 2 天
      estimated_hours: 4

    status: "pending"
    depends_on: ["PHASE-001"]

  - id: "PHASE-003"
    name: "Phase 3: 通知整合"
    objective: "LINE 通知功能"
    # ...

  - id: "PHASE-004"
    name: "Phase 4: 測試與部署"
    objective: "完整測試並上線"
    # ...
```

### 3. Checkpoint（確認點）

每個 Phase 完成後必須經過確認：

```yaml
checkpoint:
  phase_id: "PHASE-001"

  # === 確認類型 ===
  type: "phase_completion"  # phase_completion, milestone, gate, review

  # === 確認者 ===
  reviewers:
    - role: "INSPECTOR"
      type: "automated"     # 自動測試
    - role: "CEO"
      type: "manual"        # CEO 確認（可選）
      required: false

  # === 檢查項目 ===
  checklist:
    - item: "所有驗收標準通過"
      status: "pending"
    - item: "程式碼已審查"
      status: "pending"
    - item: "文件已更新"
      status: "pending"

  # === 確認結果 ===
  result:
    status: null  # approved, rejected, needs_revision
    comments: null
    approved_at: null
    approved_by: null
```

### 4. 時間管理

```yaml
time_management:
  # === 預警機制 ===
  alerts:
    - type: "approaching_deadline"
      trigger: "2 days before deadline"
      action: "notify_owner"

    - type: "overdue"
      trigger: "deadline passed"
      action: "escalate_to_ceo"

    - type: "phase_delayed"
      trigger: "phase end date passed"
      action: "notify_and_replan"

  # === 時間追蹤 ===
  tracking:
    estimated_hours: 12
    actual_hours: 0
    remaining_hours: 12

    # 每日更新
    daily_log:
      - date: "2024-02-06"
        hours_spent: 3
        progress: "完成爬蟲框架"
        blockers: []
```

## 架構整合

### Agent 執行流程更新

```
之前：
Task → Agent.think() → Agent.act() → 完成

之後：
Goal → Phases → 每個 Phase:
  ┌─────────────────────────────────────────────────────────────┐
  │  Phase Start                                                 │
  │    ↓                                                        │
  │  Agent.plan_phase() → 確認邊界和時間                         │
  │    ↓                                                        │
  │  Agent.execute_phase() → 執行（有時間限制）                   │
  │    ↓                                                        │
  │  Agent.report_progress() → 每日/每步驟回報                   │
  │    ↓                                                        │
  │  Checkpoint → 驗收確認                                       │
  │    ↓                                                        │
  │  Phase Complete → 進入下一階段                               │
  └─────────────────────────────────────────────────────────────┘
```

### ORCHESTRATOR 的角色

ORCHESTRATOR 負責：
1. **Goal Decomposition** - 將大目標拆解為 Phases
2. **Timeline Planning** - 安排時間和依賴關係
3. **Progress Tracking** - 追蹤進度
4. **Checkpoint Coordination** - 協調確認點
5. **Escalation** - 超時或問題升級

```python
class OrchestratorAgent:
    async def decompose_goal(self, goal: Goal) -> List[Phase]:
        """
        將目標拆解為階段

        規則：
        - 每個 Phase 不超過 3 天
        - 每個 Phase 有明確交付物
        - Phase 之間有清楚的依賴關係
        """
        pass

    async def validate_phase_plan(self, phases: List[Phase]) -> ValidationResult:
        """
        驗證階段計劃

        檢查：
        - 時間是否合理
        - 邊界是否清楚
        - 驗收標準是否可測量
        """
        pass

    async def track_progress(self, goal_id: str) -> ProgressReport:
        """
        追蹤目標進度

        包含：
        - 各階段狀態
        - 時間使用情況
        - 風險和阻礙
        """
        pass
```

### CEO Dashboard 整合

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Active Goals                                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ GOAL-001: 股票爬蟲系統                                   │   │
│  │ Deadline: 2024-02-13 (剩餘 5 天)                         │   │
│  │                                                         │   │
│  │ Progress: ████████░░░░░░░░ 50%                          │   │
│  │                                                         │   │
│  │ Phases:                                                 │   │
│  │ ✅ Phase 1: 資料爬取 (completed)                        │   │
│  │ 🔄 Phase 2: 分析邏輯 (in_progress) ← 目前               │   │
│  │ ⏳ Phase 3: 通知整合 (pending)                          │   │
│  │ ⏳ Phase 4: 測試部署 (pending)                          │   │
│  │                                                         │   │
│  │ 時間：預估 12h / 已用 5h / 剩餘 7h                       │   │
│  │ 狀態：🟢 On Track                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ GOAL-002: ABC Corp 提案                                  │   │
│  │ Deadline: 2024-02-10 (剩餘 2 天) ⚠️                      │   │
│  │                                                         │   │
│  │ Progress: ██████░░░░░░░░░░ 40%                          │   │
│  │ 狀態：🟡 At Risk - Phase 2 延遲 1 天                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 資料模型

```python
@dataclass
class Goal:
    id: str
    title: str
    objective: str

    # 成功標準
    success_criteria: List[str]

    # 邊界
    in_scope: List[str]
    out_of_scope: List[str]

    # 時間
    deadline: datetime
    buffer_days: int

    # 狀態
    status: GoalStatus  # draft, active, completed, cancelled
    progress: float  # 0.0 - 1.0

    # 關聯
    phases: List[Phase]
    owner: str
    assignees: List[str]


@dataclass
class Phase:
    id: str
    goal_id: str
    name: str
    objective: str

    # 交付物
    deliverables: List[str]
    acceptance_criteria: List[str]

    # 時間
    start_date: datetime
    end_date: datetime
    estimated_hours: float
    actual_hours: float

    # 狀態
    status: PhaseStatus  # pending, in_progress, review, completed, blocked

    # 依賴
    depends_on: List[str]  # phase IDs

    # 確認點
    checkpoint: Optional[Checkpoint]


@dataclass
class Checkpoint:
    phase_id: str
    type: CheckpointType

    # 檢查項
    checklist: List[ChecklistItem]

    # 結果
    status: CheckpointStatus  # pending, approved, rejected
    comments: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]


class GoalStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
```

## API 設計

```yaml
# Goal Management
POST   /api/v1/goals                    # 建立目標
GET    /api/v1/goals                    # 列出目標
GET    /api/v1/goals/{id}               # 取得目標詳情
PUT    /api/v1/goals/{id}               # 更新目標
DELETE /api/v1/goals/{id}               # 取消目標

# Phase Management
GET    /api/v1/goals/{id}/phases        # 取得階段列表
POST   /api/v1/goals/{id}/phases        # 新增階段
PUT    /api/v1/phases/{id}              # 更新階段
POST   /api/v1/phases/{id}/start        # 開始階段
POST   /api/v1/phases/{id}/complete     # 完成階段

# Checkpoint
POST   /api/v1/phases/{id}/checkpoint   # 提交確認
POST   /api/v1/checkpoints/{id}/approve # 核准
POST   /api/v1/checkpoints/{id}/reject  # 退回

# Progress
GET    /api/v1/goals/{id}/progress      # 取得進度報告
POST   /api/v1/phases/{id}/log          # 記錄工作日誌
```

## 實作優先順序

### Phase 1: 核心模型（3 天）
- [ ] Goal, Phase, Checkpoint 資料模型
- [ ] 資料庫 Schema
- [ ] 基礎 CRUD API

### Phase 2: ORCHESTRATOR 整合（3 天）
- [ ] Goal decomposition 邏輯
- [ ] Phase planning 邏輯
- [ ] Progress tracking

### Phase 3: 時間管理（2 天）
- [ ] Deadline 預警
- [ ] 超時處理
- [ ] 進度報告

### Phase 4: CEO Dashboard（2 天）
- [ ] Goal 列表視圖
- [ ] Phase 進度視圖
- [ ] Checkpoint 審批介面

## 與現有架構的關係

```
ADR-005 (Observability)     → 提供執行透明度
ADR-006 (CEO Intake)        → Goal 可從 CEO 輸入建立
ADR-007 (Engine Layer)      → 分析能力支援 Goal planning
ADR-009 (Knowledge)         → 歷史數據支援時間估算
ADR-010 (Goal-Driven) ←     → 本文件
```

## 範例：完整流程

```
1. CEO 輸入: "幫我做一個股票爬蟲系統，下週要用"

2. GATEKEEPER 解析:
   - Intent: project
   - Deadline: 7 days
   - Route to: ORCHESTRATOR

3. ORCHESTRATOR 建立 Goal:
   - 定義目標和邊界
   - 拆解為 4 個 Phases
   - 估算時間
   - 推送給 CEO 確認

4. CEO 確認後，執行開始:
   - Phase 1: BUILDER 執行，INSPECTOR 驗收
   - Checkpoint: 自動測試 + CEO 選擇性確認
   - Phase 2: ...

5. 每日進度更新:
   - Dashboard 顯示進度
   - 延遲預警
   - 問題升級

6. 完成:
   - 所有 Phase 完成
   - 最終 Checkpoint 確認
   - Goal 標記為 Completed
```

## 參考
- Agile/Scrum Sprint 概念
- OKR (Objectives and Key Results)
- SMART Goals
- ADR-005: Agent Observability
