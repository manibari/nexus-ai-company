# ADR-011: Sales Pipeline Dashboard (銷售管道儀表板)

## 狀態
已採納

## 背景

系統目前有兩種不同性質的「執行追蹤」需求：

### 1. 專案執行 (Goal Dashboard) - 已實作
- 適用於：技術開發、系統建置、內部任務
- 特點：有明確的階段（Phases）、時間以分鐘計算
- 範例：「開發股票爬蟲系統」

### 2. 銷售管理 (Sales Dashboard) - 本 ADR
- 適用於：商機追蹤、客戶關係、成交推進
- 特點：有銷售階段（Pipeline Stages）、MEDDIC 分析
- 範例：「ABC Corp 系統整合案」

兩者雖然都是「追蹤進度」，但本質不同：
- Goal：任務導向，自己可控，追求效率
- Deal：客戶導向，外部依賴，追求成交

## 決策

建立獨立的 **Sales Pipeline Dashboard**，與 Goal Dashboard 分開：

```
┌─────────────────────────────────────────────────────────────────┐
│  Nexus AI Company - CEO War Room                                 │
├─────────────────────────────────────────────────────────────────┤
│  [📊 Dashboard] [💰 Sales Pipeline] [🎯 Project Goals] [📥 CEO Inbox] │
└─────────────────────────────────────────────────────────────────┘
         ↓                 ↓                  ↓              ↓
    總覽儀表板        銷售管理          專案管理       輸入/審批
```

**Tab 順序說明**：
- **Dashboard**：總覽 Agent 狀態、2.5D 辦公室地圖、KPI
- **Sales Pipeline**：商機追蹤、MEDDIC 分析、Pipeline 進度
- **Project Goals**：專案執行、Phase 進度、時間追蹤
- **CEO Inbox**：新輸入、決策審批、Agent 請求

## 核心概念

### 1. Opportunity (商機)

```yaml
opportunity:
  id: "OPP-2024-001"

  # === 基本資訊 ===
  name: "ABC Corp 系統整合案"
  company: "ABC Corporation"
  industry: "製造業"

  # === 金額 ===
  amount: 500000  # 預估金額
  currency: "TWD"

  # === 銷售階段 ===
  stage: "qualification"  # 見下方 Pipeline Stages
  stage_entered_at: "2024-02-06T10:00:00"

  # === MEDDIC 分數 ===
  meddic:
    pain_score: 8
    champion_score: 6
    eb_score: 4
    total_score: 65
    health: "at_risk"

  # === 關鍵人物 ===
  contacts:
    - name: "王大明"
      title: "CTO"
      role: "champion"
      email: "wang@abc.com"
    - name: "李總"
      title: "CEO"
      role: "economic_buyer"
      email: null  # 尚未取得

  # === 時間 ===
  created_at: "2024-02-01"
  expected_close: "2024-03-31"
  last_activity: "2024-02-06"
  days_in_stage: 5

  # === 來源 ===
  source: "referral"  # referral, inbound, outbound, event
  source_detail: "老王介紹"

  # === 負責人 ===
  owner: "HUNTER"

  # === 狀態 ===
  status: "open"  # open, won, lost, dormant

  # === 關聯 ===
  related_goals: ["GOAL-2024-001"]  # 如果成交，轉為專案
  activities: [...]  # 互動紀錄
```

### 2. Pipeline Stages (銷售階段)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Sales Pipeline                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [Lead]  →  [Qualification]  →  [Discovery]  →  [Proposal]  →  [Won] │
│    ↓             ↓                   ↓              ↓           ↓     │
│  新線索      資格確認            需求探索        提案報價      成交   │
│  (10%)        (20%)              (40%)           (70%)       (100%)   │
│                                                                        │
│              ↓                    ↓               ↓                   │
│           [Lost]               [Lost]          [Lost]                 │
└──────────────────────────────────────────────────────────────────────┘
```

**各階段定義：**

| 階段 | 說明 | 勝率 | 關鍵動作 | 退出條件 |
|------|------|------|----------|----------|
| Lead | 新線索，尚未接觸 | 10% | 首次聯繫 | 完成首次對話 |
| Qualification | 確認是否為有效商機 | 20% | BANT 確認 | Pain 已確認 |
| Discovery | 深入了解需求 | 40% | Discovery Call | Champion 已確認 |
| Proposal | 提案與報價 | 70% | 發送提案 | EB 已見面 |
| Negotiation | 議價與條款 | 85% | 合約協商 | 雙方同意條款 |
| Won | 成交 | 100% | 簽約 | - |
| Lost | 失敗 | 0% | - | 記錄失敗原因 |

### 3. MEDDIC Integration (整合)

每個 Opportunity 都有 MEDDIC 分析，用於：
- 判斷 Deal 健康度
- 識別銷售缺口
- 建議下一步動作
- 預測成交機率

```python
@dataclass
class OpportunityMEDDIC:
    # 從 MEDDIC Engine 分析結果
    pain: PainAnalysis
    champion: ChampionAnalysis
    economic_buyer: EBAnalysis

    # 擴充（未來）
    metrics: Optional[MetricsAnalysis] = None
    decision_criteria: Optional[DCAnalysis] = None
    decision_process: Optional[DPAnalysis] = None

    @property
    def total_score(self) -> int:
        """0-100 分"""
        pass

    @property
    def health(self) -> str:
        """healthy, at_risk, needs_attention, weak"""
        pass

    @property
    def stage_readiness(self) -> Dict[str, bool]:
        """判斷是否可進入下一階段"""
        return {
            "qualification": self.pain.identified,
            "discovery": self.champion.identified,
            "proposal": self.economic_buyer.access_level >= "meeting",
            "negotiation": self.total_score >= 70,
        }
```

### 4. Activity Tracking (互動追蹤)

```yaml
activity:
  id: "ACT-001"
  opportunity_id: "OPP-2024-001"

  type: "meeting"  # call, email, meeting, note, task
  subject: "Discovery Call with CTO"

  # 時間
  occurred_at: "2024-02-06T14:00:00"
  duration_minutes: 45

  # 內容
  summary: |
    - 確認系統效能問題是主要痛點
    - 每月損失約 50 萬
    - CTO 願意安排與 CEO 見面

  # 參與者
  attendees:
    - name: "王大明"
      role: "champion"

  # MEDDIC 更新
  meddic_updates:
    pain_intensity: 8  # 確認痛點強度
    champion_strength: "medium"  # 提升

  # 下一步
  next_action: "安排與 CEO 會議"
  next_action_due: "2024-02-13"

  # 記錄者
  created_by: "HUNTER"
```

## 資料模型

```python
class OpportunityStage(Enum):
    LEAD = "lead"
    QUALIFICATION = "qualification"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"
    DORMANT = "dormant"


class OpportunityStatus(Enum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    DORMANT = "dormant"


class ActivityType(Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"


@dataclass
class Contact:
    id: str
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "contact"  # champion, economic_buyer, influencer, blocker


@dataclass
class Opportunity:
    id: str
    name: str
    company: str

    # 金額
    amount: Optional[float] = None
    currency: str = "TWD"

    # 階段
    stage: OpportunityStage = OpportunityStage.LEAD
    stage_entered_at: datetime = field(default_factory=datetime.utcnow)

    # MEDDIC
    meddic: Optional[MEDDICAnalysis] = None

    # 聯絡人
    contacts: List[Contact] = field(default_factory=list)

    # 時間
    created_at: datetime = field(default_factory=datetime.utcnow)
    expected_close: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    # 來源
    source: str = "unknown"
    source_detail: Optional[str] = None
    source_input_id: Optional[str] = None  # 從 CEO Intake 來

    # 負責
    owner: str = "HUNTER"

    # 狀態
    status: OpportunityStatus = OpportunityStatus.OPEN

    # 失敗原因（如果 lost）
    lost_reason: Optional[str] = None

    @property
    def days_in_stage(self) -> int:
        return (datetime.utcnow() - self.stage_entered_at).days

    @property
    def is_stale(self) -> bool:
        """超過 14 天沒有活動"""
        if self.last_activity_at:
            return (datetime.utcnow() - self.last_activity_at).days > 14
        return True

    @property
    def win_probability(self) -> float:
        """基於階段的成交機率"""
        probabilities = {
            OpportunityStage.LEAD: 0.10,
            OpportunityStage.QUALIFICATION: 0.20,
            OpportunityStage.DISCOVERY: 0.40,
            OpportunityStage.PROPOSAL: 0.70,
            OpportunityStage.NEGOTIATION: 0.85,
            OpportunityStage.WON: 1.0,
            OpportunityStage.LOST: 0.0,
        }
        return probabilities.get(self.stage, 0.0)

    @property
    def weighted_amount(self) -> float:
        """加權金額"""
        if self.amount:
            return self.amount * self.win_probability
        return 0.0


@dataclass
class Activity:
    id: str
    opportunity_id: str
    type: ActivityType
    subject: str

    occurred_at: datetime = field(default_factory=datetime.utcnow)
    duration_minutes: Optional[int] = None

    summary: Optional[str] = None
    attendees: List[str] = field(default_factory=list)

    next_action: Optional[str] = None
    next_action_due: Optional[datetime] = None

    created_by: str = "HUNTER"
```

## API 設計

```yaml
# Opportunity Management
POST   /api/v1/pipeline/opportunities           # 建立商機
GET    /api/v1/pipeline/opportunities           # 列出商機（支援 stage 篩選）
GET    /api/v1/pipeline/opportunities/{id}      # 取得商機詳情
PUT    /api/v1/pipeline/opportunities/{id}      # 更新商機
DELETE /api/v1/pipeline/opportunities/{id}      # 刪除商機

# Stage Progression
POST   /api/v1/pipeline/opportunities/{id}/advance   # 推進階段
POST   /api/v1/pipeline/opportunities/{id}/lose      # 標記失敗
POST   /api/v1/pipeline/opportunities/{id}/win       # 標記成交

# Activities
POST   /api/v1/pipeline/opportunities/{id}/activities    # 新增活動
GET    /api/v1/pipeline/opportunities/{id}/activities    # 列出活動

# Contacts
POST   /api/v1/pipeline/opportunities/{id}/contacts      # 新增聯絡人
PUT    /api/v1/pipeline/contacts/{id}                    # 更新聯絡人

# MEDDIC
GET    /api/v1/pipeline/opportunities/{id}/meddic        # 取得 MEDDIC 分析
POST   /api/v1/pipeline/opportunities/{id}/meddic/refresh  # 重新分析

# Dashboard
GET    /api/v1/pipeline/dashboard                   # Pipeline 儀表板
GET    /api/v1/pipeline/statistics                  # 統計資訊
GET    /api/v1/pipeline/forecast                    # 銷售預測
```

## Dashboard 設計

```
┌─────────────────────────────────────────────────────────────────────────┐
│  💰 Sales Pipeline                                      [+ 新增商機]     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─── Pipeline Overview ─────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  Lead (3)    Qual (5)    Discovery (2)   Proposal (1)   Won (8)  │  │
│  │  $150K       $500K       $300K           $200K          $2.5M    │  │
│  │  ████        ████████    ██████          ████           ████████ │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── Active Deals ──────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │ ABC Corp 系統整合案                        $500K | Discovery │ │  │
│  │  │ MEDDIC: ████████░░ 65/100  🟡 At Risk                       │ │  │
│  │  │ Champion: 王大明 (CTO) | EB: 李總 (未接觸)                   │ │  │
│  │  │ ⚠️ 缺口: EB 尚未接觸                                         │ │  │
│  │  │ 💡 下一步: 透過 Champion 安排與 CEO 會議                     │ │  │
│  │  │ 📅 Last: 2 天前 | Expected: 2024-03-31                       │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │ XYZ Ltd 雲端遷移                           $200K | Proposal  │ │  │
│  │  │ MEDDIC: ██████████ 82/100  🟢 Healthy                        │ │  │
│  │  │ Champion: 陳經理 | EB: 張總 (已會面)                         │ │  │
│  │  │ ✅ 準備提案                                                   │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── Alerts ────────────────────────────────────────────────────────┐  │
│  │ 🔴 2 deals stale (>14 days no activity)                           │  │
│  │ 🟡 3 deals at risk (MEDDIC < 50)                                  │  │
│  │ 📅 1 deal closing this week                                       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 與現有系統整合

### 1. CEO Inbox → Opportunity
```
CEO 輸入商機資訊
    ↓
GATEKEEPER 識別為 opportunity
    ↓
MEDDIC Engine 分析
    ↓
建立 Opportunity（stage: lead）
    ↓
HUNTER Agent 接手追蹤
```

### 2. Opportunity → Goal
```
Opportunity 成交 (Won)
    ↓
建立相關 Goal（專案執行）
    ↓
關聯 opportunity_id
    ↓
ORCHESTRATOR 分解階段
```

### 3. Agent 整合
```
HUNTER Agent:
  - 負責 Lead → Qualification → Discovery
  - 更新 MEDDIC 分析
  - 記錄 Activities

CLOSER Agent (未來):
  - 負責 Proposal → Negotiation → Won
  - 處理報價與談判

ORCHESTRATOR:
  - 成交後接手專案執行
  - 建立 Goal 並分解 Phases
```

## 實作優先順序

### Phase 1: 核心模型（待實作）
- [ ] Opportunity, Contact, Activity 資料模型
- [ ] OpportunityRepository (in-memory)
- [ ] 基礎 CRUD API

### Phase 2: Pipeline 視圖（待實作）
- [ ] Pipeline 看板視圖
- [ ] Opportunity 詳情頁
- [ ] Activity Timeline

### Phase 3: MEDDIC 整合（待實作）
- [ ] 自動 MEDDIC 分析
- [ ] 階段推進建議
- [ ] Health 預警

### Phase 4: 報表與預測（待實作）
- [ ] Pipeline 統計
- [ ] 銷售預測
- [ ] Win/Loss 分析

## 與 Goal Dashboard 的區別

| 面向 | Goal Dashboard | Sales Dashboard |
|------|----------------|-----------------|
| 目的 | 專案執行追蹤 | 銷售機會追蹤 |
| 主體 | Goal (目標) | Opportunity (商機) |
| 階段 | Phases (技術階段) | Pipeline Stages (銷售階段) |
| 時間 | 分鐘計算 | 天/週計算 |
| 進度 | 任務完成度 | MEDDIC 分數 |
| 負責人 | ORCHESTRATOR | HUNTER |
| 可控性 | 高（自己執行） | 低（客戶決定） |
| 成功定義 | 交付完成 | 成交 Won |

## 參考
- MEDDIC Sales Methodology
- Salesforce Pipeline Management
- ADR-006: CEO Intake
- ADR-007: Engine Layer (MEDDIC Engine)
- ADR-010: Goal-Driven Execution
