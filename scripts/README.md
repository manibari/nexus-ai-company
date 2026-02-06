# Agent Status Scripts

## 概述

這些腳本用於更新 Dashboard 上的 Agent 狀態，可與 Apple Intelligence 整合。

---

## 腳本說明

### 1. update_agent_status.sh

簡單的 Shell 腳本，直接呼叫 API 更新 Agent 狀態。

```bash
# 更新 BUILDER 為工作中
./update_agent_status.sh BUILDER working "Implementing feature X"

# 設為閒置
./update_agent_status.sh BUILDER idle
```

### 2. agent_status_bridge.py

智能橋接腳本，可解析任務描述並自動識別 Agent 和狀態。

```bash
# 自動解析並更新
python3 agent_status_bridge.py auto "SWE Agent 正在實作 StockPulse"

# 手動更新
python3 agent_status_bridge.py update BUILDER working "Bug fixing"

# 設為閒置
python3 agent_status_bridge.py idle BUILDER
```

---

## Agent ID 對照表

| Agent ID | 名稱 | 角色 |
|----------|------|------|
| HUNTER | Sales Agent | 業務 |
| ORCHESTRATOR | PM Agent | 專案經理 |
| BUILDER | Engineer Agent | 工程師 |
| INSPECTOR | QA Agent | 測試員 |
| LEDGER | Finance Agent | 財務 |
| GATEKEEPER | Admin Agent | 行政 |

---

## 狀態說明

| Status | 說明 | Dashboard 顯示 |
|--------|------|----------------|
| idle | 閒置 | ⚪ 灰色 |
| working | 工作中 | 🟢 綠色 |
| blocked_internal | 內部阻塞 | 🟡 黃色 |
| blocked_user | 等待用戶 | 🔴 紅色 |

---

## Apple Intelligence 整合

### 方法 1: Shortcuts App

1. 開啟 Shortcuts App
2. 建立新捷徑
3. 加入「Run Shell Script」動作
4. 輸入：
   ```bash
   /Users/manibari/Documents/Projects/nexus-ai-company/scripts/agent_status_bridge.py auto "$1"
   ```
5. 設定輸入為「Text」
6. 儲存為「Update Agent Status」

### 方法 2: 直接呼叫

透過 Siri 或 Apple Intelligence 說：
> "Run shortcut Update Agent Status with SWE Agent 正在實作功能"

---

## API 端點

```
PUT /api/v1/agents/{agent_id}/status

Body:
{
  "status": "working",
  "current_task": "Task description"
}
```

---

## 範例：模擬開發流程

```bash
# PM 開始規劃
python3 agent_status_bridge.py update ORCHESTRATOR working "規劃 StockPulse PRD"

# PM 完成，SWE 接手
python3 agent_status_bridge.py idle ORCHESTRATOR
python3 agent_status_bridge.py update BUILDER working "實作 StockPulse 後端"

# SWE 完成，QA 接手
python3 agent_status_bridge.py idle BUILDER
python3 agent_status_bridge.py update INSPECTOR working "測試 StockPulse API"

# QA 完成
python3 agent_status_bridge.py idle INSPECTOR
```
