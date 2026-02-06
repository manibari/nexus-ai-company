# ADR-013: Sales Board CRM 增強 (草案)

## 狀態
**Phase 1 已實作** - Closed Deals 視圖已完成

## 背景

目前 Sales Board 的結構：
- `Opportunity` 直接儲存 `company` (字串) 和 `contacts` (列表)
- Pipeline 階段包含 `LOST` 和 `DORMANT`，但前端沒有專門的檢視區域
- 沒有獨立的 CRM（客戶關係管理）儲存位置

**使用者需求：**
1. 需要一個 **CRM 儲存位置** - 獨立管理公司/客戶資料
2. 需要一個地方管理 **Pending（休眠）和 Lost（失敗）** 的商機

## 提議方案

### 方案 A：新增 Company 模型 + Closed Deals 視圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│  💰 Sales Board                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  [Active Pipeline] [Closed Deals] [CRM]                                  │
│                                                                          │
│  === Active Pipeline (現有) ===                                          │
│  Lead → Qualification → Discovery → Proposal → Negotiation              │
│                                                                          │
│  === Closed Deals (新增) ===                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ 🏆 Won      │  │ ❌ Lost     │  │ 💤 Dormant  │                      │
│  │    (8)      │  │    (3)      │  │    (2)      │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                          │
│  === CRM (新增) ===                                                      │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │ 公司名稱      │ 產業    │ 規模   │ 聯絡人數 │ 商機數 │ 總營收     │     │
│  │ ABC Corp    │ 製造業  │ 500人  │ 3        │ 2      │ $1,000,000 │     │
│  │ XYZ Ltd     │ 金融業  │ 1000人 │ 5        │ 1      │ $500,000   │     │
│  └────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 新增資料模型

#### 1. Company（公司/客戶）

```python
@dataclass
class Company:
    id: str                      # COM-{uuid}
    name: str                    # 公司名稱

    # 基本資訊
    industry: Optional[str]      # 產業別
    size: Optional[str]          # 規模 (員工數)
    website: Optional[str]       # 網站
    address: Optional[str]       # 地址

    # 分類
    tier: str = "prospect"       # prospect, customer, partner, churned
    tags: List[str] = []

    # 關聯
    contacts: List[Contact] = [] # 聯絡人列表

    # 統計（計算屬性）
    # - opportunity_count: 商機數量
    # - total_revenue: 總營收（Won 的商機）
    # - last_activity: 最後活動時間

    # 時間
    created_at: datetime
    updated_at: datetime
```

#### 2. Opportunity 關聯調整

```python
@dataclass
class Opportunity:
    # ... 現有欄位 ...

    # 改用 company_id 關聯
    company_id: Optional[str] = None  # 關聯到 Company
    company: str = ""                  # 保留原本字串（向後相容）
```

### 新增 API

```yaml
# Company (CRM)
POST   /api/v1/crm/companies           # 建立公司
GET    /api/v1/crm/companies           # 列表（支援篩選）
GET    /api/v1/crm/companies/{id}      # 取得詳情
PUT    /api/v1/crm/companies/{id}      # 更新
DELETE /api/v1/crm/companies/{id}      # 刪除
GET    /api/v1/crm/companies/{id}/opportunities  # 該公司的商機
GET    /api/v1/crm/companies/{id}/contacts       # 該公司的聯絡人

# Closed Deals
GET    /api/v1/pipeline/closed         # 取得 Won/Lost/Dormant 商機
GET    /api/v1/pipeline/closed/won     # 只取 Won
GET    /api/v1/pipeline/closed/lost    # 只取 Lost
GET    /api/v1/pipeline/closed/dormant # 只取 Dormant
POST   /api/v1/pipeline/{id}/reactivate  # 重新啟動 Dormant 商機
```

### 前端調整

#### SalesPipeline.tsx 新增 Tab

```typescript
// 新增內部 tab 狀態
const [view, setView] = useState<'pipeline' | 'closed' | 'crm'>('pipeline')

// Tab 切換
<div className="flex gap-2 mb-4">
  <button onClick={() => setView('pipeline')}>📊 Active Pipeline</button>
  <button onClick={() => setView('closed')}>📁 Closed Deals</button>
  <button onClick={() => setView('crm')}>🏢 CRM</button>
</div>

// 內容渲染
{view === 'pipeline' && <PipelineKanban />}
{view === 'closed' && <ClosedDealsView />}
{view === 'crm' && <CRMView />}
```

---

## 實作範圍

### Phase 1: Closed Deals 視圖（優先）✅ 已完成
- [x] 前端新增 Closed Deals tab
- [x] 顯示 Won / Lost / Dormant 三區
- [x] 支援 Reactivate 功能（Dormant → Lead）
- [x] 支援 Mark as Dormant 功能

### Phase 2: CRM 基礎
- [ ] 後端 Company 模型
- [ ] 後端 CRM API
- [ ] 前端 CRM 列表視圖
- [ ] Opportunity 關聯 Company

### Phase 3: CRM 進階（未來）
- [ ] 公司詳情頁（商機歷史、聯絡人管理）
- [ ] 客戶分級（Tier）
- [ ] 統計報表

---

## 問題確認

請確認以下問題：

1. **Closed Deals 視圖**是否為優先需求？
2. **CRM 公司資料**需要儲存哪些欄位？（目前提議：name, industry, size, website, address, tier, tags）
3. 是否需要**匯入/匯出**功能？
4. 是否需要與外部 CRM（如 Salesforce、HubSpot）整合的考量？

---

## 檔案清單（預計）

| 操作 | 路徑 |
|------|------|
| 新增 | `backend/app/crm/__init__.py` |
| 新增 | `backend/app/crm/models.py` |
| 新增 | `backend/app/crm/repository.py` |
| 新增 | `backend/app/api/crm.py` |
| 修改 | `backend/app/api/pipeline.py` (新增 closed endpoints) |
| 修改 | `backend/app/main.py` |
| 修改 | `frontend/src/components/SalesPipeline.tsx` |

---

## 參考

- ADR-011: Sales Pipeline
- 現有 `backend/app/pipeline/models.py`
