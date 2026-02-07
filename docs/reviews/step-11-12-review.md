# Step 11-12 Code Review: DEVELOPER Agent + QA Agent

**Date**: 2026-02-07
**Reviewer**: Claude Opus 4.6
**Issues**: #11 (DEVELOPER Agent), #12 (QA Agent)

---

## Summary

完成開發流水線的最後兩個 Agent，打通 CEO → GATEKEEPER → PM → CEO 批准 → **DEVELOPER → QA → UAT** 完整流程。

### 新增檔案
| 檔案 | 行數 | 說明 |
|------|------|------|
| `backend/app/agents/developer.py` | ~280 | DeveloperAgent — Gemini 生成實作計畫 |
| `backend/app/api/developer.py` | ~70 | Developer API (health/stats/tasks) |
| `backend/app/agents/qa.py` | ~370 | QAAgent — 測試計畫 + 驗收評估 + UAT Todo |
| `backend/app/api/qa.py` | ~110 | QA API (health/stats/results/retest) |

### 修改檔案
| 檔案 | 變更說明 |
|------|---------|
| `backend/app/agents/pm.py` | `_assign_to_developer()` — 改用 `registry.dispatch("DEVELOPER", ...)` 實際派發；移除 PM 端的重複 TASK_START 日誌 |
| `backend/app/api/intake.py` | `routable_agents` 加入 `"QA"`（支援 GATEKEEPER 路由 product_bug） |
| `backend/app/main.py` | import + registry.register(DEVELOPER, QA) + include_router |

---

## Architecture Review

### 1. AgentHandler Protocol Compliance
- `DeveloperAgent`: `agent_id="DEVELOPER"`, `agent_name="Developer Agent"`, `handle(payload)` ✅
- `QAAgent`: `agent_id="QA"`, `agent_name="QA Agent"`, `handle(payload)` ✅
- 兩者皆遵循 lazy singleton 模式（`get_developer_agent()` / `get_qa_agent()`）✅

### 2. Dispatch Chain
```
PM._assign_to_developer()
  → registry.dispatch("DEVELOPER", payload, from_agent="PM")
    → DeveloperAgent.handle()
      → develop_feature()
        → set_stage(in_progress) → Gemini 實作計畫 → set_stage(qa_testing)
        → registry.dispatch("QA", payload, from_agent="DEVELOPER")
          → QAAgent.handle()
            → test_feature()
              → Gemini 測試計畫 → evaluate criteria → add_qa_result()
              → 全部通過 → set_stage(uat) → create UAT Todo
```

### 3. ProductItem Stage Transitions
| 階段 | 觸發 Agent | 驗證 |
|------|-----------|------|
| `spec_ready` → `in_progress` | DEVELOPER | ✅ `set_stage()` checks `can_advance_to()` |
| `in_progress` → `qa_testing` | DEVELOPER | ✅ |
| `qa_testing` → `uat` | QA | ✅ 只在全部 QA 通過時 |
| `uat` → `done` | CEO (未來) | 透過 UAT Todo 觸發 |

### 4. Gemini Integration
- 兩個 Agent 都有 Gemini fallback template ✅
- 使用同一模式：`_get_gemini()` lazy init + JSON prompt + markdown cleanup + fallback ✅

### 5. GATEKEEPER → QA Bug 路由
- `intake.py` 的 `routable_agents` 已加入 `"QA"` ✅
- `QAAgent.handle()` 根據 `intent == "product_bug"` 分流到 `test_bug_fix()` ✅
- `test_bug_fix()` 建立 `ProductType.BUG_FIX` + `ProductStage.P4_QA_TESTING` ✅

---

## Issues Found & Fixed

### Issue 1: PM 重複 TASK_START 日誌
- **問題**: PM `handle_ceo_decision()` 在 `_assign_to_developer()` 後又手動記錄了 DEVELOPER 的 TASK_START。但 `_assign_to_developer()` 現在走 `registry.dispatch()` → `DeveloperAgent.handle()` → `develop_feature()` 內部已有 TASK_START 記錄。
- **修復**: 移除 PM 端的重複 TASK_START 日誌，改為註解說明 DEVELOPER 自行記錄。

### Issue 2: Entity Format 處理
- **問題**: GATEKEEPER entities 使用 `entity_type`，但其他來源可能使用 `type`。
- **處理**: QA `test_bug_fix()` 使用 `entity.get("entity_type") or entity.get("type")` 兼容兩種格式 ✅

---

## Testing Checklist

- [ ] `GET /api/v1/agents/` → 回傳 7 Agent（含 DEVELOPER + QA）
- [ ] CEO 輸入功能需求 → GATEKEEPER → PM → CEO 批准 → DEVELOPER 開始開發
- [ ] DEVELOPER 產生實作計畫 → ProductItem in_progress → qa_testing → dispatch 給 QA
- [ ] QA 產生測試計畫 → 評估 acceptance criteria → QAResult 寫入
- [ ] QA 全部通過 → ProductItem uat → CEO Todo 建立
- [ ] CEO 輸入 product_bug → GATEKEEPER → QA 建立 BUG_FIX ProductItem
- [ ] `GET /api/v1/developer/stats` + `GET /api/v1/qa/stats` 回傳統計
- [ ] Activity Log 完整記錄所有 Agent 活動

---

## Verdict

**APPROVED** — 架構一致、Protocol 遵循、Gemini fallback 完整、Stage transition 正確。
