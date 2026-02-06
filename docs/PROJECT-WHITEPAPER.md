# Project Nexus 白皮書

> **版本**: 1.0.0
> **日期**: 2026-02-06
> **專案代號**: NEXUS
> **專案負責人**: CEO / Project Director

---

## 1. 執行摘要 (Executive Summary)

Project Nexus 旨在構建一個**「零員工、全智能」**的虛擬企業。系統由一組具備專門職能的 AI Agent 組成，透過 Python 自動化腳本執行業務開發、專案管理與軟體交付。

不同於傳統黑箱式的自動化腳本，Nexus 引入三大核心機制：

1. **RPG 上帝視角戰情室**：將枯燥的 Log 轉化為 2.5D 像素風格的辦公室動態，提供直觀的監控體驗。
2. **標準化流水線 (Pipeline)**：定義明確的狀態機 (State Machine)，確保 Agent 依循 SOP 執行。
3. **雙重驗收機制 (QA + UAT)**：引入 AI QA 進行初步測試，並由人類 CEO 進行最終驗收 (UAT)，確保產出品質。

---

## 2. 系統架構 (System Architecture)

採用 **三層式架構 (3-Tier Architecture)**，確保邏輯運算與視覺呈現分離，並透過資料庫作為唯一訊號源。

### 2.1 前端 (The View - 戰情室)

- **介面**：Web-based RPG 地圖 (HTML5 Canvas / React)
- **功能**：
  - **辦公室地圖**：顯示 Sales、PM、Eng 等角色的即時位置與狀態動畫
  - **KPI 抬頭顯示器 (HUD)**：常駐顯示燒錢速率 (Burn Rate)、營收預估 (Pipeline Value)
  - **Inbox (決策中心)**：彈出視窗，處理 Agent 的請示（如：核准折扣、驗收產品）

### 2.2 後端 (The Brain - Python 核心)

- **核心**：FastAPI Server
- **邏輯**：運行 Agent 的思考迴圈 (Thought Loop)、調用外部工具 (Tools)、執行計費 (Token Audit)
- **通訊**：實作 Message Bus，允許 Agent 之間互相 Query（如 PM 問 Sales）

### 2.3 資料庫 (The Memory - 狀態庫)

- **儲存**：SQLite (MVP 階段)
- **關鍵表單**：
  - `Agents`：狀態
  - `Tasks`：任務與 Pipeline 階段
  - `Logs`：對話紀錄
  - `Ledger`：財務帳本

---

## 3. 組織編制 (The AI Workforce)

本公司設有六大關鍵職位，每個 Agent 都是一個獨立的 Python Class。

| 職位代號 | 角色名稱 | 核心職責 | 關鍵依賴與互動 |
|----------|----------|----------|----------------|
| HUNTER | Sales Agent (業務) | 陌生開發、客戶初篩、維繫關係 | 當權限不足（如折扣 >10%）時，狀態轉紅，呼叫 CEO |
| ORCHESTRATOR | PM Agent (專案經理) | 需求拆解 (WBS)、任務排程、進度監控 | 當資訊不足時，呼叫 Sales 查詢客戶背景 |
| BUILDER | Engineer Agent (工程師) | 撰寫程式碼、建置環境 | 產出需先經過 QA Agent 測試，不得直接交付 CEO |
| INSPECTOR | QA Agent (測試員) | 執行自動化測試、找 Bug、退件 | 作為 Engineer 與 CEO 間的防火牆，確保 Code 能跑 |
| LEDGER | Finance Agent (財務) | 成本審計、計算 ROI、預算風控 | 當預算超支時，強制暫停所有 Agent 運作 |
| GATEKEEPER | Admin Agent (行政) | 行程管理、資訊摘要 | 協助 CEO 整理會議與決策資訊 |

---

## 4. 營運流水線 (Operational Pipelines)

為了讓 CEO 能一目了然進度，我們定義了兩條不可逆的狀態流水線。

### 4.1 業務開發流水線 (Sales Pipeline)

**CEO 監控點**：RPG 地圖上的「業務區」文件堆疊量與顏色變化。

```
S1: New Lead (新名單)
    └─ 爬蟲抓回的原始資料
         │
         ▼
S2: Qualified (合格)
    └─ 確認符合 ICP (目標客群)
         │
         ▼
S3: Contacted (已聯繫)
    └─ 開發信已寄出
         │
         ▼
S4: Engaged (已接洽) ⚠️ [關鍵點]
    └─ 客戶回覆且有興趣，觸發通知，需 CEO 關注
         │
         ▼
S5: Closed / Lost (結案)
    └─ 訂單成立或失敗
```

### 4.2 產品開發流水線 (Product Pipeline)

**CEO 監控點**：RPG 地圖上的「看板 (Kanban)」以及最終的「展示間 (Showroom)」。

```
P1: Backlog (需求池)
    └─ CEO 提出的模糊想法
         │
         ▼
P2: Spec Ready (規格確認)
    └─ PM 完成任務拆解
         │
         ▼
P3: In Progress (開發中)
    └─ Engineer 撰寫程式碼
         │
         ▼
P4: QA Testing (內部測試) 🤖 [自動化]
    └─ QA Agent 執行測試腳本，若失敗則退回 P3
         │
         ▼
P5: UAT (使用者驗收) 👤 [CEO 介入]
    └─ 測試通過的產品進入 Staging 環境，CEO 親自試用並按下 Approve
         │
         ▼
P6: Done (上線)
    └─ 部署至生產環境
```

---

## 5. 協作與阻擋機制 (Human-in-the-Loop)

系統並非總是全自動，遇到以下狀況會觸發「阻擋 (Blocking)」機制：

### 🟡 BLOCKED_INTERNAL (內部阻擋)

- **情境**：PM 不知道台積電的窗口是誰
- **行為**：暫停排程，自動發訊問 Sales
- **RPG 畫面**：顯示兩人間有虛線傳輸

### 🔴 BLOCKED_USER (決策阻擋)

- **情境**：Sales 遇到客戶殺價、QA 通過但需要 CEO 驗收 (UAT)
- **行為**：Agent 停止動作並亮紅燈
- **RPG 畫面**：CEO 的 Inbox 彈出「待辦事項卡片」

---

## 6. CEO 儀表板與可視化 (Dashboard & Visibility)

作為 CEO，你不需要看 Code，你透過以下方式管理公司：

### 戰略地圖 (The Map)

- 看 **Sales 區**：知道現在名單夠不夠、業務忙不忙
- 看 **PM 白板**：知道現在有多少功能在排隊
- 看 **財務金庫**：知道今天燒了多少錢

### 成果展示間 (The Showroom)

當產品通過 QA 進入 UAT 階段，點擊 RPG 畫面中的「展示電腦」，直接開啟網頁/App 預覽畫面，進行驗收。

### 財務儀表 (The Ledger)

即時顯示：**Cost (USD) vs Revenue (USD)**

---

## 7. 實施路徑 (Roadmap)

採用 **MVP (最小可行性產品)** 策略。

### Phase 1: 創世紀 (Infrastructure)

- 建立 Python FastAPI 後端
- 建立 SQLite 資料庫與基礎 Schema（包含 Pipeline 欄位）
- 建立簡易 RPG 前端（能顯示 Agent 狀態顏色變化）
- **產出**：一個能跑的「空殼公司」，可下指令改變畫面狀態

### Phase 2: 第一位員工 (Sales)

- 實作 Sales Agent + 爬蟲工具
- 跑通 S1 -> S3 流程

### Phase 3: 團隊擴張 (PM + QA)

- 加入任務拆解邏輯
- 實作 QA 自動測試迴圈

### Phase 4: 財務與優化

- 加入 Token 計費與各種 Dashboard

---

## 附錄：修訂歷史

| 版本 | 日期 | 修訂內容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-02-06 | 初版白皮書 | CEO |
