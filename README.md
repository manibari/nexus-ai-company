# Nexus AI Company

> 零員工、全智能的虛擬企業系統

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 概述

Project Nexus 是一個由 AI Agent 組成的自動化企業系統，包含：

- **Sales Agent (HUNTER)**：業務開發、客戶關係維護
- **PM Agent (ORCHESTRATOR)**：需求拆解、任務排程
- **Engineer Agent (BUILDER)**：程式碼撰寫、系統建置
- **QA Agent (INSPECTOR)**：自動化測試、品質把關
- **Finance Agent (LEDGER)**：成本審計、預算控管
- **Admin Agent (GATEKEEPER)**：行程管理、資訊摘要

## 特色

- **2.5D 戰情室 (War Room)**：辦公室地圖，每個 Agent 以精細的 2.5D 角色呈現（含身體、頭髮、衣服、狀態指示燈、工作動畫）
- **多 Board 管理系統**：
  - **Sales Board**：商機追蹤、MEDDIC 分析、Pipeline 階段管理
  - **Project Board**：專案執行、Goal → Phase → Checkpoint
  - **Product Board**：產品開發、P1-P6 階段、QA/UAT 追蹤
  - **Knowledge Base**：公司知識庫、搜尋篩選、Markdown 支援
- **Human-in-the-Loop**：關鍵決策由 CEO 審批
- **LLM Provider 可切換**：支援 Gemini / Claude / OpenAI
- **Tab 導覽順序**：Dashboard → Sales Board → Project Board → Product Board → Knowledge Base → Inbox

## 快速開始

### 前置需求

- Docker & Docker Compose
- Node.js 18+ (前端開發)
- Python 3.11+ (後端開發)

### 啟動服務

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯 .env，填入 API Keys
nano .env

# 一鍵啟動
docker-compose up -d

# 查看服務狀態
docker-compose ps
```

### 存取服務

- **前端戰情室**：http://localhost:3000
- **後端 API**：http://localhost:8000
- **API 文件**：http://localhost:8000/docs

## 專案結構

```
nexus-ai-company/
├── backend/                 # FastAPI 後端
│   ├── app/
│   │   ├── agents/         # Agent 類別 (GATEKEEPER, HUNTER, ORCHESTRATOR)
│   │   ├── pipeline/       # Sales Pipeline (Opportunity, Contact, Activity)
│   │   ├── goals/          # Project Goals (Goal, Phase, Checkpoint)
│   │   ├── product/        # Product Board (ProductItem, QA, UAT)
│   │   ├── knowledge/      # Knowledge Base (KnowledgeCard)
│   │   ├── engines/        # Engine Layer (MEDDIC, NLP)
│   │   ├── db/             # 資料庫 Models
│   │   └── api/            # API Routes
│   └── tests/
├── frontend/               # React 前端 (Vite + TypeScript)
│   └── src/
│       └── components/     # UI 元件 (SalesPipeline, GoalDashboard, ProductBoard, KnowledgeBase)
├── docs/                   # 設計文件
│   ├── architecture/       # 架構設計
│   ├── decisions/          # ADR 決策紀錄
│   └── pipelines/          # Pipeline 設計
└── docker-compose.yml
```

## 文件

- [專案白皮書](docs/PROJECT-WHITEPAPER.md)
- [系統架構](docs/architecture/001-system-overview.md)
- [LLM 抽象層設計](docs/architecture/002-llm-abstraction.md)
- [Agent 通訊機制](docs/architecture/003-agent-communication.md)
- [技術選型決策](docs/decisions/ADR-001-tech-stack.md)

## 開發

### 後端開發

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端開發

```bash
cd frontend
npm install
npm run dev
```

### 執行測試

```bash
# 後端測試
cd backend && pytest

# 前端測試
cd frontend && npm test
```

## Roadmap

- [x] Phase 1: 基礎架構 (Infrastructure)
- [ ] Phase 2: Sales Agent 實作
- [ ] Phase 3: PM + QA Agent
- [ ] Phase 4: 財務與優化

## License

MIT
