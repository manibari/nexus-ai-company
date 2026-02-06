# ADR-005: Agent 可觀測性與可控制性架構

> **狀態**: 已採納
> **日期**: 2026-02-06
> **決策者**: CEO, Product Director

---

## 背景

產品總監審查後發現目前 Agent 架構存在以下問題：

1. **黑箱執行**：CEO 無法觀察 Agent 思考過程
2. **無回滾機制**：錯誤操作無法撤回
3. **Pipeline 缺乏人工介入**：無法暫停或手動調整
4. **規則 hardcode**：調整行為需要改程式碼
5. **無試運行模式**：新功能直接上線風險高

## 決策

引入六大機制來解決上述問題。

---

## 1. Step-by-Step 執行模式

### 執行模式

| 模式 | 說明 | 使用場景 |
|------|------|----------|
| `AUTO` | 全自動執行 | 信任的日常任務 |
| `SUPERVISED` | 每步需確認 | 新 Agent 或高風險任務 |
| `REVIEW` | Think 後暫停 | 需要審查決策的任務 |

### 檢查點 (Checkpoint)

每個 Agent 執行週期會產生檢查點：

```
Sense ──checkpoint──▶ Think ──checkpoint──▶ Act ──checkpoint──▶ Complete
         │                    │                    │
         ▼                    ▼                    ▼
    [可查看狀態]         [可審查決策]          [可確認執行]
```

---

## 2. Action Journal（動作日誌）

所有 Agent 動作記錄到 Journal，支援：

- 完整執行歷史
- 可撤回的動作標記
- 錯誤標記與學習

### 動作類型

| 類型 | 可撤回 | 範例 |
|------|--------|------|
| `email_send` | ❌ | 發送開發信（已送出無法撤回）|
| `stage_change` | ✅ | 更改 Pipeline 階段 |
| `data_update` | ✅ | 更新客戶資料 |
| `file_create` | ✅ | 建立檔案 |
| `approval_request` | ✅ | 發起審批請求 |

---

## 3. Pipeline Gate（關卡機制）

### 關卡類型

- **Approval Gate**：進入前需 CEO 審批
- **Condition Gate**：滿足條件才能進入
- **Time Gate**：等待一段時間後自動放行

### 人工覆寫

CEO 可以：
- `pause`：暫停處理
- `resume`：恢復處理
- `force_stage`：強制跳轉階段
- `skip`：跳過當前階段

---

## 4. Agent Behavior Rules（行為規則）

透過 YAML 配置 Agent 行為，無需改程式碼：

```yaml
# config/agents/hunter.yaml
approval_thresholds:
  discount_percentage: 5
  deal_value_usd: 50000

communication:
  tone: formal
  blackout_days: [saturday, sunday]
```

---

## 5. Dry Run Mode（試運行）

| 模式 | 說明 |
|------|------|
| `live` | 正式執行 |
| `dry_run` | 模擬執行，不真正操作 |
| `shadow` | 新舊版本同時跑，只採用舊版結果 |

---

## 6. Agent Metrics（績效追蹤）

追蹤指標：
- 任務完成率
- 平均響應時間
- CEO 覆寫率
- Token 成本

---

## 參考文件

- [003-agent-communication.md](../architecture/003-agent-communication.md)
- [sales-pipeline.md](../pipelines/sales-pipeline.md)
