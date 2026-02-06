# 設計修正報告 CR-003

## 基本資訊

| 欄位 | 內容 |
|------|------|
| CR ID | CR-003 |
| 標題 | 產品部署架構分離規範 (Product Deployment Separation) |
| 請求者 | CEO |
| 日期 | 2026-02-07 |
| 類型 | 架構改進 / 流程改進 |
| 嚴重度 | 高 |
| 狀態 | ⬜ 待 CEO 審核 |

---

## 1. 問題描述

### 1.1 CEO 指出的問題

> 「交付部署是不是應該變成另一個獨立的專案與網域給我使用？不要跟這個核心軟體摻再一起才是正常的吧」

### 1.2 目前的錯誤架構

```
目前狀態（錯誤）：
┌─────────────────────────────────────────────────────────┐
│                    localhost                             │
├─────────────────────────────────────────────────────────┤
│  :3000  Nexus Dashboard (核心管理系統)                   │
│  :5173  StockPulse Frontend  ← 混在一起                  │
│  :8000  Nexus Backend                                    │
│  :8001  StockPulse Backend   ← 混在一起                  │
└─────────────────────────────────────────────────────────┘

問題：
1. 產品與管理系統共用開發環境
2. 無法獨立交付給用戶
3. 無法獨立擴展或維護
4. 安全風險：管理系統暴露給產品用戶
```

### 1.3 正確的架構

```
正確狀態：
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│     Nexus AI Company            │  │     StockPulse (產品)            │
│     (內部管理系統)               │  │     (獨立部署)                   │
├─────────────────────────────────┤  ├─────────────────────────────────┤
│  URL: nexus.internal            │  │  URL: stockpulse.app            │
│       或 localhost:3000         │  │       或 localhost:4000         │
│                                 │  │                                 │
│  用途：                         │  │  用途：                          │
│  - Agent 管理                   │  │  - 股票分析                      │
│  - 專案管理                     │  │  - AI 選股                       │
│  - CEO Dashboard                │  │  - 策略回測                      │
│                                 │  │                                 │
│  存取者：CEO、內部 Agent        │  │  存取者：終端用戶                 │
└─────────────────────────────────┘  └─────────────────────────────────┘
         ↑                                      ↑
         │                                      │
    內部使用                               對外產品
```

---

## 2. PM 流程修正

### 2.1 原有流程缺失

| 階段 | 原流程 | 問題 |
|------|--------|------|
| 規劃 | PRD → 技術設計 | **缺少部署規劃** |
| 實作 | 開發 → 測試 | 在開發環境完成 |
| 交付 | UAT → 結案 | **直接交付開發環境** |

### 2.2 修正後流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        專案生命週期（修正版）                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 規劃階段                                                         │
│     ├── PRD                                                         │
│     ├── 技術設計                                                     │
│     └── 【新增】部署規劃 ◀─────────────────────────────────────────┐ │
│              │                                                     │ │
│              ├── 部署環境（Dev/Staging/Prod）                       │ │
│              ├── 網域規劃（獨立 domain 或 subdomain）               │ │
│              ├── 基礎設施（VM/Container/Serverless）                │ │
│              └── CI/CD Pipeline                                    │ │
│                                                                     │
│  2. 實作階段                                                         │
│     ├── 開發（Dev 環境）                                             │
│     ├── 單元測試                                                     │
│     └── 整合測試                                                     │
│                                                                     │
│  3. 測試階段                                                         │
│     ├── QA 測試（Staging 環境）                                      │
│     └── UAT（Staging 環境）                                          │
│                                                                     │
│  4. 【新增】部署階段                                                  │
│     ├── 建立 Production 環境                                         │
│     ├── 部署應用程式                                                 │
│     ├── 設定網域                                                     │
│     ├── SSL 憑證                                                     │
│     └── 驗證部署                                                     │
│                                                                     │
│  5. 交付階段                                                         │
│     ├── DELIVERY.md（含 Production URL）                             │
│     ├── CEO Demo（在 Production 環境）                               │
│     └── 結案                                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 新增必要文件

| 文件 | 位置 | 時機 | 內容 |
|------|------|------|------|
| 部署規劃書 | `02_planning/deployment_plan.md` | 規劃階段 | 環境、網域、基礎設施 |
| 部署檢查清單 | `03_execution/deployment_checklist.md` | 部署階段 | 部署步驟與驗證 |
| 維運手冊 | `05_closing/operations_manual.md` | 結案時 | 監控、備份、故障排除 |

---

## 3. StockPulse 部署方案

### 3.1 建議方案比較

| 方案 | 成本 | 複雜度 | 適用情境 |
|------|------|--------|----------|
| A. 本地獨立埠 | $0 | 低 | MVP/Demo |
| B. Docker Compose | $0 | 中 | 開發/測試 |
| C. Cloud VM | ~$20/月 | 中 | 小規模生產 |
| D. Kubernetes | ~$100/月 | 高 | 大規模生產 |

### 3.2 MVP 建議方案：A + B 混合

**開發/Demo 環境：**
- StockPulse 獨立運行於 `localhost:4000` (前端) + `localhost:4001` (後端)
- 與 Nexus 系統完全分離

**未來生產環境：**
- 使用 Docker Compose 打包
- 部署至 Cloud VM 或 Container 服務
- 獨立網域：`stockpulse.yourcompany.com`

### 3.3 StockPulse 獨立部署架構

```
StockPulse 獨立部署
├── 程式碼位置
│   └── /Users/manibari/Documents/Projects/stockpulse/  ← 獨立專案目錄
│       ├── backend/
│       ├── frontend/
│       ├── docker-compose.yml
│       └── README.md
│
├── 開發環境
│   ├── Frontend: http://localhost:4000
│   └── Backend:  http://localhost:4001
│
├── Staging 環境
│   └── https://staging.stockpulse.app
│
└── Production 環境
    └── https://stockpulse.app
```

---

## 4. 實作步驟

### Phase 1: 程式碼分離（立即執行）

```bash
# 1. 建立獨立專案目錄
mkdir -p /Users/manibari/Documents/Projects/stockpulse

# 2. 複製 StockPulse 程式碼
cp -r nexux_company/backend/app/stockpulse stockpulse/backend/
cp -r nexux_company/frontend/src/components/stockpulse stockpulse/frontend/

# 3. 建立獨立的 main.py 和 package.json
# 4. 設定獨立埠號
```

### Phase 2: Docker 化（短期）

```yaml
# docker-compose.yml
version: '3.8'
services:
  stockpulse-backend:
    build: ./backend
    ports:
      - "4001:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

  stockpulse-frontend:
    build: ./frontend
    ports:
      - "4000:80"
    depends_on:
      - stockpulse-backend
```

### Phase 3: 雲端部署（中期）

- 選擇雲端平台（AWS/GCP/Azure/DigitalOcean）
- 設定 CI/CD Pipeline
- 設定網域和 SSL

---

## 5. 影響範圍

### 5.1 需要修改的文件

| 文件 | 變更 |
|------|------|
| `docs/protocols/project_delivery_checklist.md` | 加入部署檢查項目 |
| `docs/templates/PRD-template.md` | 加入部署需求章節 |
| `docs/templates/technical_design_template.md` | 加入部署架構章節 |

### 5.2 新增文件

| 文件 | 用途 |
|------|------|
| `docs/protocols/deployment_standards.md` | 部署標準規範 |
| `docs/templates/deployment_plan_template.md` | 部署規劃範本 |

---

## 6. CEO 決策項目

請 CEO 確認以下事項：

### Q1: StockPulse 部署方式

| 選項 | 說明 | 成本 |
|------|------|------|
| A | 本地獨立埠（localhost:4000）| $0 |
| B | Docker Compose 本地 | $0 |
| C | 雲端 VM 部署 | ~$20/月 |
| D | 暫時維持現狀，未來再調整 | $0 |

### Q2: 是否需要正式網域？

| 選項 | 說明 |
|------|------|
| A | 是，需要購買 stockpulse.com 或類似網域 |
| B | 否，使用子網域或 IP 存取即可 |
| C | 暫時不需要，MVP 階段用 localhost |

### Q3: 此規範是否適用於未來所有產品專案？

| 選項 | 說明 |
|------|------|
| A | 是，所有產品都必須獨立部署 |
| B | 視專案規模決定 |
| C | 僅限外部交付的產品 |

---

## 7. 簽核

| 角色 | 姓名 | 日期 | 簽核 |
|------|------|------|------|
| CEO | - | - | ⬜ 待審核 |
| PM | PM Agent | 2026-02-07 | ✅ 提交 |
| SWE | SWE Agent | 2026-02-07 | ✅ 技術可行 |

---

## 附錄 A: 部署規劃範本

```markdown
# [專案名稱] 部署規劃書

## 1. 部署環境

| 環境 | 用途 | URL |
|------|------|-----|
| Development | 開發測試 | localhost:XXXX |
| Staging | QA/UAT | staging.xxx.com |
| Production | 正式環境 | xxx.com |

## 2. 基礎設施

| 資源 | 規格 | 成本 |
|------|------|------|
| Compute | ... | ... |
| Database | ... | ... |
| Storage | ... | ... |

## 3. 網域規劃

| 網域 | 用途 |
|------|------|
| xxx.com | 主要網域 |
| api.xxx.com | API 端點 |

## 4. CI/CD Pipeline

...

## 5. 監控與告警

...
```
