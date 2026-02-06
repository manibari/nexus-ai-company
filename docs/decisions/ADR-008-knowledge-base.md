# ADR-008: 公司知識庫架構

## 狀態
已採納

## 背景
目前系統的 Agent 每次執行都是「無狀態」的，缺乏：
- 歷史案例參考
- 過往經驗學習
- 公司知識累積
- 客製化內容生成能力

CEO 提出需求：
> "說不定有很多經驗可以根據不同的專案、以及數據做統整，
> 相關案例也可以調用成 sales deck 或是銷售的客製化產品"

## 決策
建立 **Company Knowledge Base** 作為核心基礎設施，
並透過 **Knowledge Engine** 提供 RAG (Retrieval Augmented Generation) 能力。

## 架構

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agents                                   │
│   HUNTER │ ORCHESTRATOR │ BUILDER │ INSPECTOR │ GATEKEEPER      │
└─────┬───────────┬───────────┬───────────┬───────────┬───────────┘
      │           │           │           │           │
      ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Knowledge Engine                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   Search    │ │  Retrieval  │ │  Generator  │               │
│  │  (語意搜尋)  │ │  (RAG 檢索)  │ │ (內容生成)   │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Knowledge Base                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Case Repository                        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │ 成交案例    │ │ 失敗案例   │ │ 進行中案例  │            │  │
│  │  │ Won Deals  │ │ Lost Deals │ │ Ongoing    │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Project Repository                      │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │ 完成專案    │ │ 技術方案   │ │ 問題解決    │            │  │
│  │  │ Completed  │ │ Solutions  │ │ Incidents  │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Template Repository                     │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │ Sales Deck │ │ Proposals  │ │ Contracts  │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │ Email 範本  │ │ 報價單     │ │ 技術文件    │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Analytics Repository                    │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │ 銷售數據    │ │ 專案數據   │ │ 產業洞察    │            │  │
│  │  │ Sales KPI  │ │ Project KPI│ │ Industry   │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Vector Database                             │
│                   (Embeddings Storage)                           │
│                    PostgreSQL + pgvector                         │
└─────────────────────────────────────────────────────────────────┘
```

## 知識類型

### 1. Case Repository (案例庫)

| 類型 | 內容 | 用途 |
|------|------|------|
| **Won Deals** | 成交案例完整記錄 | 成功模式分析、案例分享 |
| **Lost Deals** | 失敗案例 + 原因分析 | 避免重蹈覆轍 |
| **Ongoing** | 進行中案例 | 類似案例參考 |

**案例結構：**
```yaml
case:
  id: "CASE-2024-001"
  company: "ABC Corp"
  industry: "金融業"
  deal_size: 500000
  sales_cycle_days: 45
  outcome: "won"

  # MEDDIC 記錄
  meddic:
    pain: "現有系統效能不足，影響交易速度"
    pain_intensity: 8
    champion: "IT Director 王先生"
    champion_strength: "strong"
    economic_buyer: "CTO"
    decision_criteria: ["效能", "穩定性", "價格"]

  # 關鍵時刻
  key_moments:
    - date: "2024-01-15"
      event: "首次會議"
      insight: "客戶對價格敏感，但更在意效能"
    - date: "2024-02-01"
      event: "POC 展示"
      insight: "效能提升 3 倍，客戶驚艷"

  # 成功因素
  success_factors:
    - "找到強力 Champion"
    - "POC 數據說話"
    - "價格策略：分期付款"

  # 可複用資產
  assets:
    - type: "sales_deck"
      path: "/assets/cases/abc-corp/deck.pptx"
    - type: "proposal"
      path: "/assets/cases/abc-corp/proposal.pdf"
```

### 2. Project Repository (專案庫)

| 類型 | 內容 | 用途 |
|------|------|------|
| **Completed** | 完成的專案 | 估時參考、方案複用 |
| **Solutions** | 技術解決方案 | 架構參考、代碼複用 |
| **Incidents** | 問題與解決記錄 | 避免踩坑 |

**專案結構：**
```yaml
project:
  id: "PROJ-2024-001"
  name: "股票爬蟲分析系統"
  type: "internal_tool"

  # 基本資訊
  timeline:
    estimated_days: 5
    actual_days: 4
    accuracy: 0.8

  # 技術棧
  tech_stack:
    - Python
    - FastAPI
    - PostgreSQL
    - LINE Notify

  # 可複用元件
  reusable_components:
    - name: "TWSE Crawler"
      path: "/components/crawlers/twse/"
      description: "台股資料爬蟲，支援日K、法人買賣超"
    - name: "Stock Screener"
      path: "/components/analysis/screener/"
      description: "股票篩選引擎，支援自訂條件"

  # 經驗學習
  lessons_learned:
    - category: "estimation"
      lesson: "爬蟲專案要預留 20% 時間處理網站變更"
    - category: "technical"
      lesson: "TWSE 有 IP 限制，需要加入延遲和重試機制"
```

### 3. Template Repository (範本庫)

| 類型 | 內容 | 變數 |
|------|------|------|
| **Sales Deck** | 銷售簡報範本 | 產業、痛點、案例 |
| **Proposal** | 提案範本 | 客戶名、需求、報價 |
| **Email** | Email 範本 | 場景、客戶資訊 |

**範本結構：**
```yaml
template:
  id: "TPL-DECK-FINTECH"
  name: "金融業銷售簡報"
  type: "sales_deck"

  # 適用條件
  applicable_when:
    industry: ["金融", "銀行", "保險", "證券"]
    deal_size_min: 100000

  # 變數
  variables:
    - name: "company_name"
      type: "string"
    - name: "pain_points"
      type: "list"
    - name: "similar_cases"
      type: "case_reference"
      auto_fill: true  # 自動從 Case Repository 填入

  # 檔案
  file:
    path: "/templates/decks/fintech-v2.pptx"
    last_updated: "2024-02-01"
    win_rate: 0.65  # 使用此範本的成交率
```

### 4. Analytics Repository (數據庫)

| 類型 | 內容 | 用途 |
|------|------|------|
| **Sales KPI** | 銷售指標 | 預測、目標設定 |
| **Project KPI** | 專案指標 | 估時、資源規劃 |
| **Industry** | 產業洞察 | 客製化銷售策略 |

**數據結構：**
```yaml
analytics:
  sales:
    by_industry:
      金融:
        total_deals: 15
        won: 12
        win_rate: 0.8
        avg_deal_size: 450000
        avg_sales_cycle: 52
        common_objections:
          - "資安疑慮"
          - "需要總行核准"
        winning_strategies:
          - "提供 POC"
          - "資安認證文件"

  projects:
    by_type:
      爬蟲系統:
        count: 5
        avg_duration: 4.2
        avg_accuracy: 0.85  # 估時準確度
        common_issues:
          - "目標網站變更"
          - "IP 被封鎖"
```

## Knowledge Engine 功能

### 1. 語意搜尋 (Semantic Search)
```python
# HUNTER 問：「有沒有類似的金融業案例？」
results = knowledge_engine.search(
    query="金融業 系統效能 成功案例",
    filters={"outcome": "won", "industry": "金融"},
    limit=5
)
```

### 2. RAG 檢索 (Retrieval Augmented Generation)
```python
# HUNTER 需要準備 Sales Deck
context = knowledge_engine.retrieve_for_context(
    task="prepare_sales_deck",
    customer={
        "industry": "金融",
        "pain": "系統效能",
        "size": "enterprise"
    }
)
# 返回：相關案例 + 適用範本 + 產業洞察
```

### 3. 內容生成 (Content Generation)
```python
# 生成客製化 Sales Deck
deck = knowledge_engine.generate(
    template="TPL-DECK-FINTECH",
    variables={
        "company_name": "XYZ Bank",
        "pain_points": ["效能", "穩定性"],
    },
    include_cases=True,  # 自動插入相關案例
)
```

## Agent 整合

### HUNTER (Sales)
```python
class HunterAgent:
    async def think(self, lead: Lead) -> ThinkResult:
        # 1. 查詢類似案例
        similar_cases = await self.knowledge.search_cases(
            industry=lead.industry,
            deal_size=lead.estimated_value,
            outcome="won"
        )

        # 2. 取得產業洞察
        insights = await self.knowledge.get_industry_insights(
            industry=lead.industry
        )

        # 3. 基於歷史數據預測
        prediction = await self.knowledge.predict(
            lead=lead,
            based_on=similar_cases
        )

        # 4. 決策時參考這些資訊
        return ThinkResult(
            action="prepare_customized_deck",
            context={
                "similar_cases": similar_cases,
                "insights": insights,
                "win_probability": prediction.win_rate,
                "suggested_approach": insights.winning_strategies[0]
            }
        )
```

### ORCHESTRATOR (PM)
```python
class OrchestratorAgent:
    async def estimate_project(self, requirements: dict) -> Estimate:
        # 查詢類似專案
        similar_projects = await self.knowledge.search_projects(
            type=requirements["type"],
            tech_stack=requirements["tech_stack"]
        )

        # 基於歷史數據估時
        estimate = await self.knowledge.estimate_duration(
            requirements=requirements,
            based_on=similar_projects
        )

        # 取得常見問題
        risks = await self.knowledge.get_common_issues(
            project_type=requirements["type"]
        )

        return Estimate(
            days=estimate.suggested_days,
            confidence=estimate.confidence,
            based_on=f"{len(similar_projects)} similar projects",
            risks=risks
        )
```

## 知識累積機制

### 自動學習
```yaml
triggers:
  # Deal 關閉時
  on_deal_closed:
    - action: "create_case_record"
    - action: "update_industry_stats"
    - action: "analyze_success_factors"

  # 專案完成時
  on_project_completed:
    - action: "create_project_record"
    - action: "extract_reusable_components"
    - action: "update_estimation_model"

  # CEO 確認/修改時
  on_ceo_feedback:
    - action: "learn_from_correction"
    - action: "update_intent_model"
```

### 人工補充
```yaml
# CEO 可以主動補充知識
intake:
  supported_types:
    - case_study      # "這個案例很重要，記錄一下"
    - lesson_learned  # "下次記得..."
    - template        # "這份簡報效果很好"
```

## 技術實作

### 向量資料庫
```python
# 使用 pgvector 儲存 embeddings
class KnowledgeStore:
    def __init__(self):
        self.embedding_model = "text-embedding-3-small"

    async def store(self, content: str, metadata: dict):
        embedding = await self.embed(content)
        await self.db.execute("""
            INSERT INTO knowledge (content, embedding, metadata)
            VALUES ($1, $2, $3)
        """, content, embedding, metadata)

    async def search(self, query: str, limit: int = 5):
        query_embedding = await self.embed(query)
        return await self.db.fetch("""
            SELECT content, metadata,
                   1 - (embedding <=> $1) as similarity
            FROM knowledge
            ORDER BY embedding <=> $1
            LIMIT $2
        """, query_embedding, limit)
```

## 目錄結構

```
backend/
├── app/
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── engine.py         # Knowledge Engine
│   │   ├── store.py          # Vector DB 操作
│   │   ├── models.py         # 資料模型
│   │   ├── repositories/
│   │   │   ├── cases.py      # Case Repository
│   │   │   ├── projects.py   # Project Repository
│   │   │   ├── templates.py  # Template Repository
│   │   │   └── analytics.py  # Analytics Repository
│   │   └── generators/
│   │       ├── deck.py       # Sales Deck 生成
│   │       ├── proposal.py   # Proposal 生成
│   │       └── email.py      # Email 生成
│   └── ...
│
├── knowledge/                 # 知識庫內容
│   ├── cases/
│   ├── projects/
│   ├── templates/
│   └── analytics/
```

## 後續事項
- [ ] 實作 KnowledgeStore (pgvector)
- [ ] 實作 Knowledge Engine
- [ ] 定義 Case/Project 資料結構
- [ ] 建立範本系統
- [ ] 整合到 HUNTER Agent
- [ ] 整合到 ORCHESTRATOR Agent
- [ ] 建立知識累積 triggers

## 參考
- ADR-007: Engine Layer
- RAG (Retrieval Augmented Generation) 架構模式
