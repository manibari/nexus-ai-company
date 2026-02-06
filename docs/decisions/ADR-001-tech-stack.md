# ADR-001: 技術棧選型

> **狀態**: 已採納
> **日期**: 2026-02-06
> **決策者**: CEO, Claude (Technical Advisor)

---

## 背景

Project Nexus 需要選定核心技術棧，以支撐多 Agent 協作系統的開發。

## 決策

### 後端框架

**選擇：FastAPI (Python)**

理由：
- 原生支援 async，適合處理多 Agent 並發
- 自動生成 OpenAPI 文件，方便前端對接
- Python 生態豐富，LLM SDK 支援完整

### 資料庫

**選擇：SQLite (MVP) → PostgreSQL (Production)**

理由：
- SQLite 零配置，開發快速
- 已知限制：單寫鎖，高並發時需遷移
- Schema 設計時使用 SQLAlchemy ORM，確保可移植性

### LLM Provider

**選擇：Gemini API (Primary) + 抽象層支援 Claude/OpenAI**

理由：
- CEO 指定先使用 Gemini
- 透過 Provider Interface 抽象，可在前端切換
- 預留成本優化空間（不同任務用不同模型）

### 前端框架

**選擇：React + HTML5 Canvas**

理由：
- React 狀態管理成熟
- Canvas 適合 RPG 風格的自定義渲染
- 可考慮 Pixi.js 加速 2D 渲染

### 部署方式

**選擇：Docker Compose (Local)**

理由：
- MVP 階段不需複雜雲端架構
- 一鍵啟動所有服務
- 日後可無痛遷移至 Kubernetes

### 版本控制

**選擇：Monorepo on GitHub**

理由：
- 單一 repo 管理前後端，簡化 CI/CD
- 適合小團隊或單人開發
- Repo: `github.com/manibari/nexus-ai-company`

---

## 影響

1. 團隊需熟悉 Python async 開發模式
2. 前端需學習 Canvas 或 Pixi.js
3. 需設計 LLM Provider 抽象介面

---

## 替代方案（已排除）

| 方案 | 排除原因 |
|------|----------|
| Node.js + Express | Python LLM 生態更成熟 |
| MongoDB | 關聯式資料更適合 Pipeline 狀態追蹤 |
| Multi-repo | 增加維護複雜度 |
| 雲端 Serverless | MVP 階段過度工程 |

---

## 參考文件

- [PROJECT-WHITEPAPER.md](../PROJECT-WHITEPAPER.md)
- [002-llm-abstraction.md](../architecture/002-llm-abstraction.md)
