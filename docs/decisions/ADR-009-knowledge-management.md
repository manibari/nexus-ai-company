# ADR-009: 知識管理系統

## 狀態
已採納

## 背景
ADR-008 直接跳到 Embedding 和 RAG，但忽略了基礎：
- 知識要先能「存」和「管」，才能談「智能檢索」
- 沒有好的知識管理，Embedding 也是垃圾進垃圾出

本 ADR 專注於 **知識管理的基礎建設**，ADR-008 的 Embedding 作為未來的增強層。

## 決策
建立基於文本的知識管理系統，包含：
1. 知識儲存與結構化
2. 分類與標籤體系
3. 全文搜尋
4. 知識生命週期管理

## 知識分類

### 知識類型

```
Knowledge Base
├── 📁 Cases (案例)
│   ├── 成交案例 (won)
│   ├── 失敗案例 (lost)
│   └── 進行中 (ongoing)
│
├── 📁 Projects (專案)
│   ├── 完成專案
│   ├── 技術方案
│   └── 問題記錄
│
├── 📁 Documents (文件)
│   ├── 提案書
│   ├── 合約範本
│   ├── 技術文件
│   └── 會議記錄
│
├── 📁 Templates (範本)
│   ├── Sales Deck
│   ├── Email 範本
│   ├── 報價單
│   └── 合約範本
│
├── 📁 Procedures (流程)
│   ├── SOP
│   ├── Checklist
│   └── 工作指南
│
├── 📁 Insights (洞察)
│   ├── 產業分析
│   ├── 競爭者資訊
│   └── 市場趨勢
│
└── 📁 Lessons (經驗)
    ├── 成功經驗
    ├── 失敗教訓
    └── Best Practices
```

### 知識卡片結構

每一筆知識都是一張「卡片」：

```yaml
knowledge_card:
  # === 基本資訊 ===
  id: "KB-2024-0001"
  type: "case"                    # case | project | document | template | procedure | insight | lesson

  title: "ABC Corp 金融系統案例"
  summary: "金融業大型客戶，45天成交，關鍵在於POC展示"  # 一句話摘要

  content: |
    ## 背景
    ABC Corp 是一家中型銀行...

    ## 挑戰
    現有系統效能不足...

    ## 解決方案
    我們提供了...

    ## 成果
    效能提升 3 倍...

  # === 分類 ===
  category: "cases/won"           # 路徑式分類
  tags:
    - "金融業"
    - "大型客戶"
    - "POC"
    - "效能優化"

  # === 關聯 ===
  related_to:
    - id: "KB-2024-0002"
      relation: "similar_case"    # 類似案例
    - id: "KB-2024-0050"
      relation: "used_template"   # 使用的範本
    - id: "DEAL-001"
      relation: "source"          # 來源 Deal

  # === 結構化資料（依類型不同）===
  metadata:
    # Case 專用欄位
    company: "ABC Corp"
    industry: "金融"
    deal_size: 500000
    sales_cycle_days: 45
    outcome: "won"
    win_factors:
      - "強力 Champion"
      - "POC 成功"

  # === 附件 ===
  attachments:
    - name: "proposal.pdf"
      path: "/attachments/KB-2024-0001/proposal.pdf"
      type: "application/pdf"
    - name: "deck.pptx"
      path: "/attachments/KB-2024-0001/deck.pptx"
      type: "application/vnd.openxmlformats-officedocument.presentationml.presentation"

  # === 生命週期 ===
  status: "published"             # draft | published | archived | deprecated
  visibility: "internal"          # public | internal | confidential

  created_by: "CEO"
  created_at: "2024-02-06T10:00:00Z"
  updated_by: "HUNTER"
  updated_at: "2024-02-06T15:00:00Z"

  # === 品質指標 ===
  quality:
    completeness: 0.9             # 欄位完整度
    last_reviewed: "2024-02-06"
    review_cycle_days: 90         # 多久要複查一次
    usage_count: 15               # 被引用次數
```

## 資料模型

### 資料庫 Schema

```sql
-- 知識卡片主表
CREATE TABLE knowledge_cards (
    id VARCHAR(20) PRIMARY KEY,   -- KB-YYYY-NNNN
    type VARCHAR(50) NOT NULL,

    -- 內容
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT,

    -- 分類
    category VARCHAR(200),
    tags TEXT[] DEFAULT '{}',

    -- 結構化資料（彈性欄位）
    metadata JSONB DEFAULT '{}',

    -- 狀態
    status VARCHAR(20) DEFAULT 'draft',
    visibility VARCHAR(20) DEFAULT 'internal',

    -- 生命週期
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 品質
    completeness DECIMAL(3,2) DEFAULT 0,
    last_reviewed TIMESTAMPTZ,
    review_cycle_days INTEGER DEFAULT 90,
    usage_count INTEGER DEFAULT 0
);

-- 關聯表
CREATE TABLE knowledge_relations (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(20) REFERENCES knowledge_cards(id),
    target_id VARCHAR(20) REFERENCES knowledge_cards(id),
    relation_type VARCHAR(50),    -- similar, used_template, source, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 附件表
CREATE TABLE knowledge_attachments (
    id SERIAL PRIMARY KEY,
    card_id VARCHAR(20) REFERENCES knowledge_cards(id),
    name VARCHAR(500),
    path VARCHAR(1000),
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_cards_type ON knowledge_cards(type);
CREATE INDEX idx_cards_category ON knowledge_cards(category);
CREATE INDEX idx_cards_tags ON knowledge_cards USING GIN(tags);
CREATE INDEX idx_cards_metadata ON knowledge_cards USING GIN(metadata);
CREATE INDEX idx_cards_status ON knowledge_cards(status);
CREATE INDEX idx_cards_content_fts ON knowledge_cards
    USING GIN(to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,'')));

-- ID 自動生成
CREATE SEQUENCE knowledge_card_seq;

CREATE OR REPLACE FUNCTION generate_knowledge_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.id IS NULL THEN
        NEW.id := 'KB-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
                  LPAD(nextval('knowledge_card_seq')::TEXT, 4, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_knowledge_id
    BEFORE INSERT ON knowledge_cards
    FOR EACH ROW EXECUTE FUNCTION generate_knowledge_id();
```

## API 設計

### 知識 CRUD

```yaml
# 建立知識
POST /api/v1/knowledge
Body:
  type: "case"
  title: "ABC Corp 案例"
  content: "..."
  category: "cases/won"
  tags: ["金融", "大型客戶"]
  metadata:
    company: "ABC Corp"
    industry: "金融"
Response:
  id: "KB-2024-0001"
  status: "draft"

# 取得知識
GET /api/v1/knowledge/{id}
Response:
  id: "KB-2024-0001"
  type: "case"
  title: "ABC Corp 案例"
  ...

# 更新知識
PUT /api/v1/knowledge/{id}
Body:
  title: "ABC Corp 金融系統案例（更新）"
  status: "published"

# 刪除知識（軟刪除）
DELETE /api/v1/knowledge/{id}

# 列表
GET /api/v1/knowledge?type=case&category=cases/won&tags=金融&limit=20

# 搜尋
GET /api/v1/knowledge/search?q=金融+效能&type=case
```

### 分類與標籤

```yaml
# 取得分類樹
GET /api/v1/knowledge/categories
Response:
  - name: "cases"
    label: "案例"
    children:
      - name: "won"
        label: "成交案例"
        count: 15
      - name: "lost"
        label: "失敗案例"
        count: 8

# 取得熱門標籤
GET /api/v1/knowledge/tags?limit=20
Response:
  - tag: "金融"
    count: 23
  - tag: "POC"
    count: 18

# 批次打標籤
POST /api/v1/knowledge/batch/tags
Body:
  ids: ["KB-2024-0001", "KB-2024-0002"]
  add_tags: ["重要客戶"]
  remove_tags: ["待整理"]
```

### 關聯管理

```yaml
# 建立關聯
POST /api/v1/knowledge/{id}/relations
Body:
  target_id: "KB-2024-0002"
  relation_type: "similar_case"

# 取得關聯
GET /api/v1/knowledge/{id}/relations
Response:
  - target:
      id: "KB-2024-0002"
      title: "XYZ Bank 案例"
    relation_type: "similar_case"
```

### 附件管理

```yaml
# 上傳附件
POST /api/v1/knowledge/{id}/attachments
Content-Type: multipart/form-data
Body:
  file: (binary)

# 下載附件
GET /api/v1/knowledge/{id}/attachments/{attachment_id}
```

## 搜尋功能

### 全文搜尋（PostgreSQL FTS）

```python
class KnowledgeSearch:
    async def search(
        self,
        query: str,
        filters: SearchFilters = None
    ) -> List[KnowledgeCard]:
        """
        基本全文搜尋，不需要 embedding
        """
        sql = """
            SELECT
                *,
                ts_rank(
                    to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,'')),
                    plainto_tsquery('simple', $1)
                ) as rank
            FROM knowledge_cards
            WHERE
                to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,''))
                @@ plainto_tsquery('simple', $1)
                AND status = 'published'
                AND ($2::varchar IS NULL OR type = $2)
                AND ($3::varchar IS NULL OR category LIKE $3 || '%')
                AND ($4::text[] IS NULL OR tags && $4)
            ORDER BY rank DESC
            LIMIT $5
        """

        return await self.db.fetch(
            sql,
            query,
            filters.type if filters else None,
            filters.category if filters else None,
            filters.tags if filters else None,
            filters.limit or 20
        )

    async def search_by_metadata(
        self,
        filters: dict
    ) -> List[KnowledgeCard]:
        """
        結構化搜尋：用 metadata 欄位過濾
        例如：找所有金融業、金額 > 50萬的成交案例
        """
        sql = """
            SELECT *
            FROM knowledge_cards
            WHERE
                status = 'published'
                AND metadata @> $1::jsonb
            ORDER BY created_at DESC
            LIMIT 20
        """
        return await self.db.fetch(sql, json.dumps(filters))
```

### 搜尋範例

```python
# 全文搜尋
results = await knowledge.search("金融 效能 優化")

# 帶過濾的搜尋
results = await knowledge.search(
    query="系統效能",
    filters=SearchFilters(
        type="case",
        category="cases/won",
        tags=["金融"]
    )
)

# 純結構化搜尋
results = await knowledge.search_by_metadata({
    "industry": "金融",
    "outcome": "won",
    "deal_size": {"$gte": 500000}  # 需要自訂 operator 處理
})
```

## 知識生命週期

### 狀態流轉

```
draft → published → archived
          ↓
      deprecated
```

### 自動維護

```python
class KnowledgeMaintenanceJob:
    """定期執行的維護任務"""

    async def run_daily(self):
        # 1. 標記需要複查的知識
        await self.mark_needs_review()

        # 2. 計算完整度分數
        await self.calculate_completeness()

        # 3. 更新使用統計
        await self.update_usage_stats()

        # 4. 提醒過期知識
        await self.notify_stale_knowledge()

    async def mark_needs_review(self):
        """標記超過複查週期的知識"""
        await self.db.execute("""
            UPDATE knowledge_cards
            SET metadata = jsonb_set(metadata, '{needs_review}', 'true')
            WHERE
                last_reviewed < NOW() - (review_cycle_days || ' days')::INTERVAL
                AND status = 'published'
        """)

    async def calculate_completeness(self):
        """計算知識卡片的完整度"""
        # 依據類型檢查必填欄位
        required_fields = {
            "case": ["company", "industry", "outcome"],
            "project": ["tech_stack", "duration_days"],
            "template": ["variables"],
        }
        # ... 計算邏輯
```

## 目錄結構

```
backend/
├── app/
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── models.py           # KnowledgeCard, SearchFilters
│   │   ├── repository.py       # CRUD 操作
│   │   ├── search.py           # 搜尋邏輯
│   │   ├── maintenance.py      # 生命週期管理
│   │   └── api.py              # API endpoints
│   └── ...
│
├── knowledge/                   # 知識內容（可選：存檔案系統）
│   ├── cases/
│   ├── projects/
│   ├── templates/
│   └── attachments/
```

## 與 Agent 整合

### HUNTER 使用知識

```python
class HunterAgent:
    async def think(self, lead: Lead) -> ThinkResult:
        # 1. 搜尋類似案例
        similar_cases = await self.knowledge.search(
            query=f"{lead.industry} {lead.company}",
            filters=SearchFilters(
                type="case",
                category="cases/won"
            )
        )

        # 2. 搜尋適用範本
        templates = await self.knowledge.search(
            query=lead.industry,
            filters=SearchFilters(type="template")
        )

        # 3. 搜尋產業洞察
        insights = await self.knowledge.search(
            query=lead.industry,
            filters=SearchFilters(type="insight")
        )

        # 4. 基於知識做決策
        return ThinkResult(
            action="prepare_proposal",
            context={
                "reference_cases": [c.id for c in similar_cases[:3]],
                "suggested_template": templates[0].id if templates else None,
                "industry_insights": insights[0].summary if insights else None
            }
        )
```

### 知識貢獻

```python
# Deal 關閉時自動建立案例
@on_event("deal.closed")
async def create_case_from_deal(event: DealClosedEvent):
    deal = event.deal

    await knowledge.create(
        type="case",
        title=f"{deal.company} - {deal.industry}案例",
        summary=f"{'成交' if deal.outcome == 'won' else '失敗'}案例，週期{deal.cycle_days}天",
        content=generate_case_content(deal),
        category=f"cases/{deal.outcome}",
        tags=[deal.industry, deal.company_size],
        metadata={
            "company": deal.company,
            "industry": deal.industry,
            "outcome": deal.outcome,
            "deal_size": deal.value,
            "sales_cycle_days": deal.cycle_days,
            "source_deal_id": deal.id
        },
        status="draft"  # 先存草稿，CEO 確認後發布
    )
```

## 實作優先順序

### Phase 1: 基礎 CRUD（1 週）
- [ ] 資料庫 schema
- [ ] KnowledgeCard model
- [ ] 基本 CRUD API
- [ ] 檔案上傳

### Phase 2: 搜尋與分類（1 週）
- [ ] 全文搜尋
- [ ] 分類樹 API
- [ ] 標籤管理
- [ ] 關聯管理

### Phase 3: Agent 整合（1 週）
- [ ] HUNTER 整合
- [ ] 自動建立案例
- [ ] 知識引用追蹤

### Phase 4: 維護機制（持續）
- [ ] 完整度計算
- [ ] 複查提醒
- [ ] 使用統計

### Future: 智能增強（ADR-008）
- [ ] Embedding
- [ ] 語意搜尋
- [ ] 內容生成

## 與 ADR-008 的關係

```
ADR-009 (本文件)          ADR-008
知識管理基礎              智能檢索增強
─────────────────────────────────────
儲存結構          →      Embedding 欄位
全文搜尋          →      語意搜尋
分類/標籤         →      自動分類
手動關聯          →      自動發現關聯
範本管理          →      內容生成
```

ADR-008 建立在 ADR-009 之上，而非取代。

## 參考
- ADR-008: Knowledge Base (Embedding/RAG) - 未來增強
- ADR-007: Engine Layer
