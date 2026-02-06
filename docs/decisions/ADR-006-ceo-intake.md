# ADR-006: CEO 輸入端設計（Intake Layer）

> **狀態**: 已採納
> **日期**: 2026-02-06
> **決策者**: CEO, Product Director

---

## 背景

CEO 經常從多種渠道獲得潛在商機和資訊：
- 社交場合的名片
- 會議中的線索
- 朋友介紹的人脈
- 新聞/產業情報
- 轉發的 Email

這些輸入是**非結構化**的，需要解讀、研究、結構化後才能進入 Sales Pipeline。

## 問題

原本考慮讓 Sales Agent 直接處理，但這違反單一職責原則：
- Sales Agent 專注於「銷售執行」
- CEO 輸入需要「解讀與結構化」
- 混在一起會造成 Prompt 臃腫、任務混淆

## 決策

**擴展 GATEKEEPER (Admin Agent) 職責，作為 CEO 輸入的統一入口**

### 新的資訊流

```
CEO 輸入（非結構化）
        │
        ▼
┌───────────────────────────────────────┐
│         GATEKEEPER (Intake)           │
│  1. 意圖識別                          │
│  2. 資訊解析與補全                    │
│  3. 結構化                            │
│  4. CEO 確認                          │
│  5. 路由到對應 Agent                  │
└───────────────────────────────────────┘
        │
        ├──→ HUNTER (商機) → Sales Pipeline
        ├──→ ORCHESTRATOR (專案) → Product Pipeline
        └──→ 直接回覆 CEO (問題/資訊)
```

### GATEKEEPER 新增職責

| 原有職責 | 新增職責 |
|---------|---------|
| 行程管理 | CEO 輸入解析 |
| 資訊摘要 | 意圖識別 |
| | 資訊結構化 |
| | 智能路由 |
| | 資訊補全（爬蟲/搜尋）|

### 意圖分類

| 意圖 | 說明 | 路由目標 |
|------|------|----------|
| `opportunity` | 潛在商機 | HUNTER |
| `project` | 專案需求 | ORCHESTRATOR |
| `question` | 問題詢問 | 直接回覆 |
| `task` | 待辦事項 | 建立任務 |
| `info` | 資訊分享 | 記錄存檔 |

---

## 資料模型

### CEO Input 表

```python
class CEOInput(Base):
    __tablename__ = "ceo_inputs"

    id: str                   # 唯一識別碼
    raw_content: str          # 原始輸入內容
    input_type: str           # text, email, url, voice, image
    source: str               # web, slack, email, api

    # 解析結果
    intent: str               # opportunity, project, question, task, info
    confidence: float         # 意圖識別信心度
    parsed_entities: dict     # 解析出的實體（公司、人名、金額等）
    enriched_data: dict       # 補全的資訊

    # 路由結果
    routed_to: str            # HUNTER, ORCHESTRATOR, None
    created_entity_type: str  # lead, task, None
    created_entity_id: str    # 建立的實體 ID

    # CEO 確認
    requires_confirmation: bool
    ceo_confirmed: bool
    ceo_feedback: str

    # 狀態
    status: str               # pending, processing, awaiting_confirmation,
                              # confirmed, rejected, completed

    # 時間戳
    created_at: datetime
    processed_at: datetime
    confirmed_at: datetime
```

### Lead 表擴展

```python
# 新增欄位
source_type: str          # cold_outreach, ceo_referral, inbound, event
source_input_id: str      # 關聯的 CEO Input ID
priority_reason: str      # 高優先級原因
ceo_notes: str            # CEO 的備註
```

---

## API 設計

### CEO 輸入端點

```
POST /api/v1/ceo/input
  - 接收 CEO 輸入
  - 自動進入 GATEKEEPER 處理流程

GET /api/v1/ceo/inputs
  - 查看所有輸入記錄

GET /api/v1/ceo/inputs/pending
  - 查看待確認的輸入

POST /api/v1/ceo/inputs/{id}/confirm
  - CEO 確認解析結果

POST /api/v1/ceo/inputs/{id}/reject
  - CEO 拒絕/修正解析結果
```

---

## 處理流程

### 1. 輸入接收

```python
@router.post("/input")
async def receive_ceo_input(content: str, input_type: str = "text"):
    # 建立輸入記錄
    input_record = CEOInput(
        raw_content=content,
        input_type=input_type,
        status="pending"
    )

    # 觸發 GATEKEEPER 處理
    await gatekeeper.process_input(input_record)
```

### 2. GATEKEEPER 處理

```python
async def process_input(self, input_record: CEOInput):
    # 1. 意圖識別
    intent = await self.identify_intent(input_record.raw_content)

    # 2. 實體解析
    entities = await self.parse_entities(input_record.raw_content)

    # 3. 資訊補全（如果是商機）
    if intent == "opportunity":
        enriched = await self.enrich_opportunity(entities)

    # 4. 結構化
    structured = await self.structure_data(intent, entities, enriched)

    # 5. 決定是否需要 CEO 確認
    if self.requires_confirmation(intent, structured):
        await self.request_ceo_confirmation(input_record, structured)
    else:
        await self.route_to_agent(input_record, structured)
```

### 3. CEO 確認

```python
async def confirm_input(self, input_id: str, feedback: str = None):
    input_record = await self.get_input(input_id)

    # 建立對應實體
    if input_record.intent == "opportunity":
        lead = await self.create_lead_from_input(input_record)
        await self.notify_hunter(lead)

    input_record.status = "completed"
```

---

## 實作優先級

### Phase 1（本次實作）
- [x] CEO Input 資料模型
- [x] 基本 API 端點
- [x] GATEKEEPER 配置擴展
- [x] 意圖識別基礎邏輯

### Phase 2
- [ ] 資訊補全（公司爬蟲）
- [ ] Email 轉發解析
- [ ] URL 內容提取

### Phase 3
- [ ] 語音輸入支援
- [ ] 圖片/名片 OCR
- [ ] 學習 CEO 偏好

---

## 參考文件

- [ADR-005-agent-observability.md](./ADR-005-agent-observability.md)
- [sales-pipeline.md](../pipelines/sales-pipeline.md)
