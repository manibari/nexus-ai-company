# Code Review: Issue #15 — ORCHESTRATOR 升級 — Execution Plan 生成 + Routing Governance

**Reviewer:** Claude
**Date:** 2026-02-10
**Branch:** main
**Status:** Review → Fix → Commit

---

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `backend/app/agents/orchestrator.py` | Rewritten | 542 → 590 lines (+Gemini plan gen, routing governance, lifecycle integration) |
| `backend/app/api/intake.py` | Modified | Lifecycle task creation moved before dispatch; task_id/trace_id passed in payload |

---

## Architecture Conformance

| Pattern | Compliant | Notes |
|---------|-----------|-------|
| Lazy Gemini init (`_get_gemini()`) | Yes | Same pattern as PM/Sales agents |
| Lifecycle via `task_repo` + `TaskLifecycle` | Yes | Per-request reconstruct, no persistent Machine |
| WS broadcast guarded by `if mgr:` | Yes | `_broadcast_plan_review()` |
| CeoTodo with TodoActions | Yes | Same pattern as PM `_create_ceo_todo()` |
| Activity logging (TASK_START, MILESTONE) | Yes | Uses `get_activity_repo()` |
| Backward compat (handle routing) | Yes | No `task_id` → falls through to old `process_project_request` |
| Event recording on each transition | Yes | TRANSITION_START_PLANNING, PLAN_GENERATED, PLAN_AUTO_APPROVED, PLAN_PENDING_REVIEW |
| Dispatch via `registry.dispatch()` | Yes | `_dispatch_plan_steps()` uses standard dispatch |
| Intake creates lifecycle task before dispatch | Yes | Moved from after-dispatch to before-dispatch |

---

## Issues Found

### P1 — Must Fix

*None found.*

### P2 — Should Fix

#### 1. `orchestrator.py:181` — `self.name = "司禮監"` but module-level `_orchestrator` uses old `GoalRepository()`
`_orchestrator = OrchestratorAgent()` at module level creates an instance with default `GoalRepository()`. This is fine — same as before. No issue.
**Verdict:** Acceptable.

### P3 — Minor / Informational

#### 2. `orchestrator.py` — agent_name changed from `"PM Agent"` to `"司禮監"`
Was `"PM Agent"`, now `"司禮監"`. This affects activity log display. Consistent with the architecture doc's 明朝官制 naming. Frontend may need to handle the new name.
**Verdict:** Acceptable — intentional rename per architecture spec.

#### 3. `orchestrator.py:249` — `content[:60]` truncation + `...` suffix always added
```python
message=f"開始編排任務: {content[:60]}...",
```
Always appends `...` even if content < 60 chars.
**Verdict:** Cosmetic only, consistent with existing pattern in `intake.py:86`.

#### 4. `intake.py` — lifecycle task created for ALL routable agents, not just ORCHESTRATOR
Both PM/SALES/QA and ORCHESTRATOR get lifecycle tasks. Only ORCHESTRATOR drives the state machine. For PM/SALES/QA the task stays in `submitted` forever.
**Verdict:** Acceptable for now. Future issues can add lifecycle integration to PM/SALES/QA handlers.

#### 5. `orchestrator.py:417` — `_dispatch_plan_steps` only dispatches the first step
For multi-step plans (e.g., PM → DEVELOPER → QA), only the first step is dispatched. Sequential execution will be implemented in a future issue.
**Verdict:** Acceptable — plan says "目前只 dispatch 第一步", matches current scope.

---

## Summary

| Severity | Count | Action |
|----------|-------|--------|
| P1 Must Fix | 0 | — |
| P2 Should Fix | 0 | — |
| P3 Minor | 4 | All acceptable as-is |

**Overall:** Clean implementation. ORCHESTRATOR correctly integrates with Issue #14's state machine and task repo. Routing governance logic is sound (risk threshold + auto_approve_eligible + single-step check). Gemini plan generation follows established pattern with proper fallback. Backward compatibility preserved via `task_id` presence check in `handle()`. No fixes needed.
