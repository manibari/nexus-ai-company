# 提案文件 PROPOSAL-001: 敏捷開發流程設計

## 基本資訊

| 欄位 | 內容 |
|------|------|
| 提案 ID | PROPOSAL-001 |
| 標題 | Nexus AI Company 敏捷開發流程 |
| 提案者 | PM Agent |
| 日期 | 2026-02-07 |
| 狀態 | ✅ CEO 已核准 (2026-02-07) |

---

## 1. 目標

建立標準化的敏捷開發流程，使 CEO 能夠：
- 快速提出產品需求
- 追蹤開發進度
- 確保交付品質

---

## 2. 角色定義

### 2.1 角色與職責

| 角色 | 職責 | 輸入 | 輸出 |
|------|------|------|------|
| **CEO** | 產品願景、需求提出、優先級決策、驗收 | 市場洞察、用戶反饋 | User Story、驗收標準 |
| **PM** | 需求分析、任務拆解、Sprint 規劃、進度追蹤 | User Story | PRD、Task List、Sprint Plan |
| **SWE** | 技術設計、開發實作、Code Review | Task、PRD | 程式碼、技術文件 |
| **QA** | 測試計劃、測試執行、缺陷追蹤 | 完成的功能 | 測試報告、Bug Report |

### 2.2 RACI 矩陣

| 活動 | CEO | PM | SWE | QA |
|------|-----|-----|-----|-----|
| 定義需求 | **R** | A | C | I |
| 拆解任務 | I | **R** | C | I |
| 技術設計 | I | A | **R** | I |
| 開發實作 | I | I | **R** | I |
| 測試驗證 | I | I | C | **R** |
| 驗收交付 | **R** | A | I | C |

> R=Responsible（負責執行）, A=Accountable（最終負責）, C=Consulted（諮詢）, I=Informed（知會）

---

## 3. Sprint 週期

### 3.1 建議 Sprint 長度

| 專案類型 | Sprint 長度 | 適用情境 |
|----------|-------------|----------|
| MVP 快速迭代 | 1 週 | 新產品探索、概念驗證 |
| 標準開發 | 2 週 | 功能開發、穩定迭代 |
| 大型功能 | 3 週 | 跨系統整合、重大重構 |

**預設建議：2 週 Sprint**

### 3.2 Sprint 時程表（2 週範例）

```
Week 1
├── Day 1 (Mon): Sprint Planning
│   ├── CEO 提出 User Stories
│   ├── PM 拆解 Tasks
│   └── Team 估算與承諾
├── Day 2-4: 開發 Sprint 1
└── Day 5 (Fri): 中期 Check-in

Week 2
├── Day 6-8: 開發 Sprint 2
├── Day 9 (Thu):
│   ├── Code Freeze
│   └── QA 測試
└── Day 10 (Fri):
    ├── Sprint Review (Demo)
    ├── CEO 驗收
    └── Retrospective
```

---

## 4. 工作流程

### 4.1 需求到交付流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           敏捷開發流程                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌────────┐│
│  │  CEO    │───▶│   PM    │───▶│   SWE   │───▶│   QA    │───▶│  CEO   ││
│  │ 需求提出 │    │ 任務拆解 │    │ 開發實作 │    │ 測試驗證 │    │  驗收  ││
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └────────┘│
│       │              │              │              │              │     │
│       ▼              ▼              ▼              ▼              ▼     │
│  User Story    Task List      Pull Request   Test Report    Sign-off   │
│  + 驗收標準    + 估算時間     + Code Review  + Bug Report   + Release  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 狀態流轉

```
┌──────────┐   PM 拆解   ┌──────────┐   SWE 開始   ┌──────────┐
│ Backlog  │ ──────────▶ │  To Do   │ ──────────▶ │ In Progress│
└──────────┘             └──────────┘             └──────────┘
                                                       │
                              ┌────────────────────────┘
                              ▼
┌──────────┐   CEO 驗收   ┌──────────┐   QA 測試   ┌──────────┐
│   Done   │ ◀────────── │ Accepted │ ◀────────── │ In Review │
└──────────┘             └──────────┘             └──────────┘
      │                        │
      │    ┌───────────────────┘
      │    │ 發現問題
      │    ▼
      │  ┌──────────┐
      └─▶│ Released │
         └──────────┘
```

---

## 5. 文件與範本

### 5.1 User Story 格式

```markdown
## US-[專案代號]-[編號]: [標題]

**作為** [用戶角色]
**我想要** [功能描述]
**以便於** [商業價值]

### 驗收標準 (Acceptance Criteria)
- [ ] AC1: [具體可驗證的條件]
- [ ] AC2: [具體可驗證的條件]
- [ ] AC3: [具體可驗證的條件]

### 優先級
- [ ] P0 - 緊急（阻擋發布）
- [ ] P1 - 高（本 Sprint 必須完成）
- [ ] P2 - 中（盡量完成）
- [ ] P3 - 低（可延後）

### 估算
- Story Points: [1/2/3/5/8/13]
- 預估工時: [X 小時/天]
```

### 5.2 Task 格式

```markdown
## TASK-[編號]: [標題]

**關聯 User Story:** US-XXX-XXX
**負責人:** [SWE/QA]
**狀態:** [To Do / In Progress / In Review / Done]

### 描述
[任務的具體描述]

### 完成定義 (Definition of Done)
- [ ] 程式碼完成
- [ ] 單元測試通過
- [ ] Code Review 通過
- [ ] 文件更新（如需要）

### 預估工時
- [ ] XS (< 2 小時)
- [ ] S (2-4 小時)
- [ ] M (4-8 小時)
- [ ] L (1-2 天)
- [ ] XL (> 2 天) ← 應拆分
```

### 5.3 Sprint 文件結構

```
projects/
└── [PROD-XXXX-專案名稱]/
    ├── 01_initiation/
    │   └── project_charter.md
    ├── 02_planning/
    │   ├── product_backlog.md      # 所有 User Stories
    │   └── sprints/
    │       ├── sprint_001/
    │       │   ├── sprint_plan.md   # Sprint 目標與承諾
    │       │   ├── tasks.md         # Task 清單
    │       │   └── retrospective.md # 回顧紀錄
    │       └── sprint_002/
    │           └── ...
    ├── 03_execution/
    │   └── source_code/
    ├── 04_monitoring/
    │   ├── qa_test_plan.md
    │   └── bug_tracker.md
    └── 05_closing/
        └── release_notes.md
```

---

## 6. 儀式 (Ceremonies)

### 6.1 Sprint Planning（Sprint 規劃會議）

| 項目 | 內容 |
|------|------|
| **時機** | Sprint 第一天 |
| **時長** | 1-2 小時 |
| **參與者** | CEO, PM, SWE, QA |
| **輸入** | Product Backlog（已排序） |
| **輸出** | Sprint Backlog、Sprint Goal |

**議程：**
1. CEO 說明本 Sprint 優先需求
2. PM 確認 User Stories 的驗收標準
3. SWE 進行任務拆解與估算
4. Team 承諾 Sprint 範圍

### 6.2 Daily Standup（每日站會）

| 項目 | 內容 |
|------|------|
| **時機** | 每日固定時間 |
| **時長** | 15 分鐘以內 |
| **參與者** | PM, SWE, QA |
| **格式** | 異步文字更新（適合 AI Agent） |

**每日更新格式：**
```markdown
## [日期] Daily Update - [Agent Name]

### 昨日完成
- [完成項目 1]
- [完成項目 2]

### 今日計劃
- [計劃項目 1]
- [計劃項目 2]

### 阻礙/風險
- [如有阻礙]
```

### 6.3 Sprint Review（Sprint 審查/Demo）

| 項目 | 內容 |
|------|------|
| **時機** | Sprint 最後一天 |
| **時長** | 30 分鐘 - 1 小時 |
| **參與者** | CEO, PM, SWE, QA |
| **輸出** | 驗收結果、下 Sprint 調整建議 |

**議程：**
1. PM 總結 Sprint 完成情況
2. SWE Demo 完成的功能
3. QA 報告測試結果
4. CEO 驗收並提供回饋

### 6.4 Retrospective（回顧會議）

| 項目 | 內容 |
|------|------|
| **時機** | Sprint Review 之後 |
| **時長** | 30 分鐘 |
| **參與者** | PM, SWE, QA |
| **輸出** | 改進行動項目 |

**回顧格式：**
```markdown
## Sprint [N] Retrospective

### 做得好的 (Keep)
- [繼續保持的事項]

### 需改進的 (Problem)
- [需要改進的事項]

### 嘗試的 (Try)
- [下個 Sprint 要嘗試的改進]
```

---

## 7. 工具與追蹤

### 7.1 建議追蹤方式

| 工具 | 用途 | 實作方式 |
|------|------|----------|
| **Backlog** | User Story 管理 | `product_backlog.md` |
| **Sprint Board** | 任務追蹤 | `tasks.md` + 狀態標記 |
| **Bug Tracker** | 缺陷追蹤 | `bug_tracker.md` |
| **Daily Log** | 進度更新 | `daily_updates/` 資料夾 |

### 7.2 狀態標記規範

```markdown
| 狀態標記 | 意義 |
|----------|------|
| ⬜ | Backlog（待排入 Sprint）|
| 📋 | To Do（已排入 Sprint）|
| 🔄 | In Progress（進行中）|
| 👀 | In Review（待審查）|
| 🧪 | Testing（QA 測試中）|
| ✅ | Done（完成）|
| ❌ | Blocked（受阻）|
| 🚀 | Released（已發布）|
```

---

## 8. 指令介面

### 8.1 CEO 指令格式

CEO 可以透過以下格式提出需求：

```
@PM 新需求

產品：[產品名稱]
需求：[需求描述]
優先級：P0/P1/P2/P3
期望完成：[日期或 Sprint]
```

**範例：**
```
@PM 新需求

產品：StockPulse
需求：新增股票觀察清單功能，用戶可以將感興趣的股票加入觀察清單，並在首頁快速查看
優先級：P1
期望完成：Sprint 2
```

### 8.2 PM 回應格式

PM 收到需求後回覆：

```markdown
## 需求確認

**User Story:** US-SP-001
**理解摘要：** [PM 對需求的理解]

### 拆解任務
| Task | 負責 | 估算 | 依賴 |
|------|------|------|------|
| TASK-001: ... | SWE | M | - |
| TASK-002: ... | SWE | S | TASK-001 |
| TASK-003: ... | QA | S | TASK-002 |

### 預計時程
- 開發：X 天
- 測試：X 天
- 總計：X 天

請 CEO 確認是否正確理解需求？
```

---

## 9. 實作計劃

### 9.1 需要建立的文件

| 文件 | 位置 | 用途 |
|------|------|------|
| `agile_workflow.md` | `docs/protocols/` | 流程規範（本文件精簡版）|
| `user_story_template.md` | `docs/templates/` | User Story 範本 |
| `sprint_plan_template.md` | `docs/templates/` | Sprint 計劃範本 |
| `task_template.md` | `docs/templates/` | Task 範本 |
| `retrospective_template.md` | `docs/templates/` | 回顧範本 |

### 9.2 需要修改的文件

| 文件 | 修改內容 |
|------|----------|
| `docs/agents/PM.md` | 加入敏捷流程職責 |
| `docs/agents/SWE.md` | 加入 Task 執行流程 |
| `docs/agents/QA.md` | 加入 Sprint 測試流程 |

---

## 10. CEO 決策結果

| 問題 | 決策 | 說明 |
|------|------|------|
| Q1: Sprint 長度 | **1 天 + 彈性** | 快速迭代為主，依專案調整 |
| Q2: 需求提交方式 | **C: 兩者皆可** | 對話或範本皆可 |
| Q3: 進度更新頻率 | **C: 里程碑更新** | Sprint 開始/完成/阻礙時更新 |
| Q4: 驗收方式 | **C: 結合模式** | 重要功能立即驗收，一般功能 Sprint 結束驗收 |

**決策日期：** 2026-02-07

---

## 11. 簽核

| 角色 | 姓名 | 日期 | 簽核 |
|------|------|------|------|
| CEO | CEO | 2026-02-07 | ✅ 已核准 |
| PM | PM Agent | 2026-02-07 | ✅ 提案 |

---

## 附錄：快速參考卡

```
┌────────────────────────────────────────────────────────────┐
│                    敏捷開發快速參考                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  CEO 提需求 ──▶ PM 拆任務 ──▶ SWE 開發 ──▶ QA 測試 ──▶ 驗收 │
│                                                            │
│  Sprint 週期：2 週                                          │
│  Day 1: Planning ──▶ Day 2-8: 開發 ──▶ Day 9: QA ──▶ Day 10: Demo│
│                                                            │
│  狀態：⬜Backlog 📋ToDo 🔄InProgress 👀Review 🧪Testing ✅Done │
│                                                            │
│  優先級：P0(緊急) > P1(高) > P2(中) > P3(低)                │
│                                                            │
│  估算：XS(<2h) S(2-4h) M(4-8h) L(1-2d) XL(>2d,需拆分)      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```
