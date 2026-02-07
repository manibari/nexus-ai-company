# CEO Intake 意圖分類設計文件

## 問題描述

當前 CEO Intake 系統存在以下問題：
1. **GATEKEEPER 回傳 Mock 資料**：所有輸入都被硬編碼為「商機」
2. **意圖分類不準確**：無法區分產品需求、商機、任務等不同意圖
3. **Agent 分派錯誤**：產品功能需求應交給 PM，而非 HUNTER

### 錯誤案例
```
輸入: "股票軟體的首要要可以看到今天的大盤資料"
錯誤分類: 商機 → HUNTER
正確分類: 產品功能需求 → PM → DEVELOPER
```

---

## 意圖分類設計

### 意圖類型 (IntentType)

| Intent | 說明 | 下一步 Agent | 範例 |
|--------|------|-------------|------|
| `product_feature` | 產品功能需求 | PM | "StockPulse 要加入大盤資料" |
| `product_bug` | 產品 Bug 回報 | QA → DEVELOPER | "登入頁面壞了" |
| `opportunity` | 商機/銷售線索 | HUNTER | "ABC 公司想買我們的系統" |
| `project_status` | 專案狀態查詢 | ORCHESTRATOR | "StockPulse 進度如何？" |
| `task` | 直接任務指派 | 對應 Agent | "幫我寫一份報告" |
| `question` | 一般問題 | 直接回覆 | "今天幾號？" |
| `info` | 資訊分享 | 記錄 | "老王今天跟我說..." |

### 實體解析 (Entity Extraction)

GATEKEEPER 應從輸入中解析以下實體：

```json
{
  "project_name": "StockPulse",      // 相關專案
  "product_name": "StockPulse",      // 相關產品
  "company_name": null,              // 相關公司（商機用）
  "contact_name": null,              // 聯絡人
  "feature_description": "大盤資料", // 功能描述
  "urgency": "normal",               // 緊急程度
  "keywords": ["大盤", "資料"]       // 關鍵詞
}
```

---

## Agent 工作流程

### Flow 1: 產品功能需求 (product_feature)

```
CEO Input
    ↓
GATEKEEPER (Gemini 2.5 Flash)
    ↓ intent = product_feature
PM Agent
    ↓ 建立 Feature Request
    ↓ 設計 PRD
    ↓ 提交 CEO 確認
CEO 確認
    ↓
DEVELOPER Agent (Claude Code CLI)
    ↓ 實作功能
QA Agent (Claude Code CLI)
    ↓ 測試驗證
完成
```

### Flow 2: 商機線索 (opportunity)

```
CEO Input
    ↓
GATEKEEPER (Gemini 2.5 Flash)
    ↓ intent = opportunity
HUNTER Agent (Gemini)
    ↓ 建立 Lead
    ↓ MEDDIC 分析
    ↓ 提交 CEO 確認
進入 Sales Pipeline
```

### Flow 3: 產品 Bug (product_bug)

```
CEO Input
    ↓
GATEKEEPER (Gemini 2.5 Flash)
    ↓ intent = product_bug
QA Agent
    ↓ 建立 Bug Report
DEVELOPER Agent (Claude Code CLI)
    ↓ 修復 Bug
QA Agent
    ↓ 驗證修復
完成
```

---

## GATEKEEPER 實作規格

### 輸入
```python
class GatekeeperInput:
    content: str              # CEO 原始輸入
    source: str               # 來源 (web, api, slack)
    context: Dict[str, Any]   # 附加上下文
```

### 輸出
```python
class GatekeeperOutput:
    intent: IntentType        # 意圖類型
    confidence: float         # 信心度 (0.0-1.0)
    entities: Dict[str, Any]  # 解析的實體
    reasoning: str            # 推理過程
    next_agent: str           # 下一步 Agent
    suggested_actions: List[str]  # 建議動作
    requires_confirmation: bool   # 是否需要 CEO 確認
```

### Gemini Prompt 範例

```
你是 Nexus AI Company 的 GATEKEEPER Agent。

分析以下 CEO 指令，判斷意圖並提取實體。

## 意圖類型
- product_feature: 產品功能需求（新增/修改功能）
- product_bug: 產品 Bug 回報
- opportunity: 商機/銷售線索
- project_status: 專案狀態查詢
- task: 直接任務指派
- question: 一般問題
- info: 資訊分享

## 現有專案/產品
- StockPulse: 美股分析軟體
- Nexus AI Company: 本公司系統

## CEO 指令
{content}

## 回應格式 (JSON)
{
  "intent": "product_feature",
  "confidence": 0.95,
  "entities": {
    "project_name": "StockPulse",
    "feature_description": "大盤資料顯示",
    "urgency": "normal"
  },
  "reasoning": "CEO 提到「股票軟體」對應 StockPulse，「大盤資料」是新功能需求",
  "next_agent": "PM",
  "suggested_actions": [
    "由 PM 設計功能規格",
    "建立 Feature Request",
    "排入開發排程"
  ],
  "requires_confirmation": true
}
```

---

## 缺失的 Agent

### PM Agent (待實作)

**職責：**
- 接收產品功能需求
- 撰寫 PRD (Product Requirements Document)
- 設計 Wireframe/UI 規格
- 排定優先級
- 提交 CEO 確認

**使用的 LLM：** Gemini 2.5 Flash（輕量級任務）

**輸出：**
- Feature Request 文件
- PRD 草稿
- CEO 確認 Todo

### QA Agent (待實作)

**職責：**
- 接收 Bug 報告
- 撰寫測試計劃
- 執行測試（使用 Claude Code CLI）
- 驗證修復

**使用的 LLM：** Claude Code CLI（需要執行程式碼）

---

## 實作優先順序

| 優先級 | 項目 | 說明 |
|--------|------|------|
| P0 | 修復 GATEKEEPER | 使用 Gemini 實際分析意圖 |
| P0 | 更新 Intake API | 回傳真實分類結果 |
| P1 | 實作 PM Agent | 處理產品功能需求 |
| P1 | 更新前端 | 顯示正確的 Agent 和動作 |
| P2 | 實作 QA Agent | 處理 Bug 報告和測試 |

---

## 驗收標準

1. 輸入「股票軟體要看大盤資料」→ 識別為 `product_feature`，分派給 PM
2. 輸入「ABC 公司想買系統」→ 識別為 `opportunity`，分派給 HUNTER
3. 輸入「登入頁面壞了」→ 識別為 `product_bug`，分派給 QA
4. 輸入「StockPulse 進度如何」→ 識別為 `project_status`，分派給 ORCHESTRATOR
