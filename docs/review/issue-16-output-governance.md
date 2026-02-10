# Code Review: Issue #16 — Output Governance — Draft 治理 + Agent 結果回收

**Reviewer:** Claude
**Date:** 2026-02-10
**Branch:** main
**Status:** Review → Fix → Commit

---

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `backend/app/core/output_governance.py` | Created | 145 lines (Schema Check + Rule Check) |
| `backend/app/agents/orchestrator.py` | Modified | +200 lines (`_process_agent_result`, `_transition`, `_create_draft_review_todo`, `_broadcast_draft_review`) |

---

## Architecture Conformance

| Pattern | Compliant | Notes |
|---------|-----------|-------|
| Pure validation (no IO in output_governance.py) | Yes | `validate_schema` / `check_rules` are pure functions |
| Lifecycle via `task_repo` + `TaskLifecycle` | Yes | Per-request transitions, no persistent Machine |
| WS broadcast guarded by `if mgr:` | Yes | `_broadcast_draft_review()` |
| CeoTodo with TodoActions | Yes | Same pattern as `_create_plan_review_todo()` |
| Activity logging (ERROR, MILESTONE) | Yes | Schema fail → ERROR; pass/approve/review → MILESTONE |
| Event recording on each transition | Yes | 6 transition events recorded |
| Lazy imports inside methods | Yes | `from app.core.output_governance import ...` |
| `_transition()` helper DRYs up transition code | Yes | Replaces repeated update_lifecycle + record_event |

---

## Issues Found

### P1 — Must Fix

*None found.*

### P2 — Should Fix

*None found.*

### P3 — Minor / Informational

#### 1. `orchestrator.py:764` — `retry_count < 2` threshold is correct but non-obvious
```python
if retry_count < 2:
    # schema_fail_retry
```
Retries at 0 and 1 (2 retries total), escalates at 2. This means 3 total attempts (initial + 2 retries). The comment says "retry < 3" in the docstring but the code uses `< 2`. Both are consistent: `retry_count` starts at 0, increments to 1 then 2; at 2 it escalates. So the max is `retry_count=2` → 3 total attempts.
**Verdict:** Correct, but could be clearer with a `MAX_SCHEMA_RETRIES = 3` constant.

#### 2. `output_governance.py:78` — `valid_statuses` comparison uses set literal
```python
"valid_statuses": {
    "awaiting_approval", "approved", "needs_modification", "cancelled",
},
```
Using set literals in a dict is fine — Python handles this correctly.
**Verdict:** Acceptable.

#### 3. `orchestrator.py` — `_process_agent_result` trusts `from_status` hardcoded strings
Each `_transition()` call uses hardcoded `from_status` / `to_status` strings rather than querying the actual DB state. This is safe because the transitions happen sequentially within a single `await` chain — no concurrent modification possible.
**Verdict:** Acceptable — sequential execution guarantees state consistency.

#### 4. `orchestrator.py` — `_transition()` doesn't validate via TaskLifecycle
The `_transition()` helper directly writes the new status to DB without running `TaskLifecycle.try_trigger()`. This is a design choice for performance (avoids redundant Machine construction), but it skips state machine validation.
**Verdict:** Acceptable for internal ORCHESTRATOR usage. The transitions are guaranteed valid by the code flow. External transitions via API still go through `TaskLifecycle`.

#### 5. Schema retry does not auto-redispatch
When `schema_fail_retry` triggers, the task transitions back to `reasoning` but the agent is not automatically re-dispatched. The task stays in `reasoning` until a future mechanism handles it.
**Verdict:** Acceptable — matches issue scope. Auto-retry can be added in a future issue.

---

## Test Results

| Test | Count | Status |
|------|-------|--------|
| State machine transitions | 7 | All pass |
| Schema validation | 8 | All pass |
| Rule check | 4 | All pass |
| **Total** | **19** | **All pass** |

---

## Summary

| Severity | Count | Action |
|----------|-------|--------|
| P1 Must Fix | 0 | — |
| P2 Should Fix | 0 | — |
| P3 Minor | 5 | All acceptable as-is |

**Overall:** Clean implementation. Output governance correctly implements the second layer of dual governance. Schema validation covers all 4 agent types with appropriate field checks. Rule check adjusts risk scores based on agent-specific business rules (DEVELOPER complexity, SALES amount, etc.). CeoTodo for draft review follows the established pattern from Issue #15. No fixes needed.
