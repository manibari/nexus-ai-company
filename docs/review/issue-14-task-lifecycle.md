# Code Review: Issue #14 — Task Lifecycle 狀態機 + DB Model + API 端點

**Reviewer:** Claude
**Date:** 2026-02-10
**Branch:** main
**Status:** Review → Fix → Commit

---

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `backend/app/db/models.py` | Modified | +38 (Task +4 cols, ActivityLog +2 cols, ExecutionPlan, TaskEvent) |
| `backend/app/core/task_state_machine.py` | New | 97 lines |
| `backend/app/task/__init__.py` | New | 0 (empty package) |
| `backend/app/task/models.py` | New | 58 lines |
| `backend/app/task/repository.py` | New | 348 lines |
| `backend/app/api/task_lifecycle.py` | New | 339 lines |
| `backend/app/api/intake.py` | Modified | +25 lines |
| `backend/app/main.py` | Modified | +2 lines |

---

## Architecture Conformance

| Pattern | Compliant | Notes |
|---------|-----------|-------|
| Lazy init singleton (`get_task_repo`) | Yes | Same as `get_product_repo()` |
| Session-per-operation | Yes | Each repo method `async with self._session()` |
| Pure state machine (no IO) | Yes | `TaskLifecycle` only validates transitions |
| Per-request reconstruct | Yes | API reads DB → builds Machine → triggers → writes back |
| WS broadcast guarded by `if mgr:` | Yes | `_broadcast_task_update` helper |
| Separate router `/api/v1/task` | Yes | Does not collide with `/api/v1/tasks` |

---

## Issues Found

### P1 — Must Fix

#### 1. `task_lifecycle.py:69` — f-string 中有多餘的 `f` prefix
```python
actor=f"user:ceo",  # f-string not needed, no interpolation
```
**Fix:** Remove `f` prefix → `actor="user:ceo"`

#### 2. `task_state_machine.py` — docstring 說 14 狀態但 STATES list 有 15 個
Spec 說 14 states / 22 transitions，但 `STATES` 實際有 15 個（含 `escalated`）。
`TRANSITIONS` 確實 22 條，正確。
**Fix:** Update docstring to say "15 狀態 / 22 轉換" to match actual implementation.

#### 3. `repository.py:92` — f-string in `logger.info` should use `%s` lazy formatting
```python
logger.info(f"Created lifecycle task: {task_id} (intent={intent})")
```
Existing codebase uses f-string in logging (see `product/repository.py:148`), so this is consistent.
**Verdict:** Keep as-is for consistency. Not blocking.

### P2 — Should Fix

#### 4. `intake.py:137-165` — lifecycle task creation 放在 dispatch 成功判斷之前
目前 lifecycle task 在 `extra_data` 設定後立刻建立，不管 dispatch 是否成功。如果 dispatch 結果是 `error`，仍然建立 lifecycle task。
**Analysis:** Plan says "dispatch 成功後建立"，but current code creates task unconditionally after dispatch call returns (regardless of success/error). Since all dispatches return a result dict (never throw), and the task tracks the full lifecycle including failures, this is acceptable. The task is created in `submitted` state which is correct — dispatch status doesn't gate task creation.
**Verdict:** Acceptable as-is. The lifecycle task tracks intent, not dispatch outcome.

### P3 — Minor / Informational

#### 5. `task/models.py` — `generate_task_id()` uses 4-hex-char suffix
4 hex chars = 65,536 combos per day. Low collision risk for this system's scale.
**Verdict:** Acceptable.

#### 6. `task_lifecycle.py:69` vs `intake.py:154` — actor format consistency
Both use `"user:ceo"` — consistent.

#### 7. DB Model `pipeline` field — value "lifecycle" is new
Existing values: `"sales"`, `"product"`. New value `"lifecycle"` added by repository. No migration conflict since `pipeline` is `String(20)` not an Enum column.
**Verdict:** Acceptable.

---

## Summary

| Severity | Count | Action |
|----------|-------|--------|
| P1 Must Fix | 2 | Fix items #1, #2 |
| P2 Should Fix | 0 | N/A |
| P3 Minor | 3 | Acceptable as-is |

**Overall:** Clean implementation. Matches plan spec closely. Follows existing patterns (session-per-operation, lazy singleton, WS guard). Only 2 minor fixes needed.
