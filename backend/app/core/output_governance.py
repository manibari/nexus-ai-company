"""
Output Governance — Draft 治理

Issue #16: 第二層治理 — Agent 產出驗證。

Schema Check: 驗證 Agent output 結構是否符合預期
Rule Check: 商業規則驗證，決定自動核准或 CEO 審核
"""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# Schema Definitions — 每個 Agent 的預期輸出欄位
# ============================================================

AGENT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "PM": {
        "required_fields": ["status", "feature", "message"],
        "feature_required": ["id", "title"],
        "valid_statuses": {
            "awaiting_approval", "approved", "needs_modification", "cancelled",
        },
    },
    "DEVELOPER": {
        "required_fields": ["status", "feature_id", "implementation_plan", "message"],
        "plan_required": ["architecture", "files_to_modify", "technical_breakdown"],
        "valid_statuses": {"completed"},
    },
    "QA": {
        "required_fields": ["status", "message"],
        "valid_statuses": {"passed", "failed", "bug_reported"},
    },
    "SALES": {
        "required_fields": ["status", "message"],
        "valid_statuses": {"created", "advanced", "ok"},
    },
}

# Output Governance 自動核准門檻
DRAFT_AUTO_APPROVE_RISK_THRESHOLD = 0.3


def validate_schema(agent_id: str, result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    驗證 Agent output 是否符合 schema。

    Returns:
        (passed, errors) — passed=True 表示通過，errors 為空 list
    """
    schema = AGENT_SCHEMAS.get(agent_id)
    if not schema:
        # 未定義 schema 的 Agent 直接通過
        return True, []

    errors: List[str] = []

    # Agent 回傳 error 直接 fail
    if result.get("status") == "error":
        errors.append(f"Agent returned error: {result.get('message', 'unknown')}")
        return False, errors

    # 必要欄位
    for field in schema.get("required_fields", []):
        if field not in result or result[field] is None:
            errors.append(f"Missing required field: {field}")

    # status 值
    valid_statuses = schema.get("valid_statuses", set())
    if valid_statuses and result.get("status") not in valid_statuses:
        errors.append(
            f"Invalid status '{result.get('status')}', "
            f"expected one of: {valid_statuses}"
        )

    # Agent-specific nested checks
    if agent_id == "PM":
        feature = result.get("feature", {})
        if isinstance(feature, dict):
            for field in schema.get("feature_required", []):
                if field not in feature or feature[field] is None:
                    errors.append(f"Missing feature.{field}")

    elif agent_id == "DEVELOPER":
        plan = result.get("implementation_plan", {})
        if isinstance(plan, dict):
            for field in schema.get("plan_required", []):
                if field not in plan or plan[field] is None:
                    errors.append(f"Missing implementation_plan.{field}")

    return len(errors) == 0, errors


def check_rules(
    agent_id: str,
    result: Dict[str, Any],
    plan_data: Dict[str, Any],
) -> Tuple[bool, float, List[str]]:
    """
    商業規則驗證。

    Returns:
        (auto_approve, risk_score, reasons)
        auto_approve=True 表示可自動核准
    """
    reasons: List[str] = []

    # 1. 基於原始 routing_risk
    routing_risk = plan_data.get("routing_risk_score", 0.5)
    risk_score = routing_risk

    # 2. Agent-specific 規則
    if agent_id == "PM":
        # PM 產出 feature + PRD，已在 PM 層建立 CEO Todo
        if result.get("status") == "awaiting_approval":
            risk_score = max(risk_score - 0.1, 0)
            reasons.append("PM 已建立 CEO 審核流程")

    elif agent_id == "DEVELOPER":
        plan = result.get("implementation_plan", {})
        if isinstance(plan, dict):
            complexity = plan.get("estimated_complexity", "medium")
            if complexity in ("high", "critical"):
                risk_score = min(risk_score + 0.2, 1.0)
                reasons.append(f"技術複雜度: {complexity}")

            files = plan.get("files_to_modify", [])
            if isinstance(files, list) and len(files) > 10:
                risk_score = min(risk_score + 0.1, 1.0)
                reasons.append(f"影響 {len(files)} 個檔案")

    elif agent_id == "SALES":
        deal = result.get("deal", {})
        if isinstance(deal, dict):
            amount = deal.get("amount", 0)
            try:
                if amount and float(amount) > 1_000_000:
                    risk_score = min(risk_score + 0.3, 1.0)
                    reasons.append(f"金額超過 100 萬: {amount}")
            except (TypeError, ValueError):
                pass

    elif agent_id == "QA":
        if result.get("status") == "failed":
            risk_score = min(risk_score + 0.1, 1.0)
            reasons.append("QA 測試未通過")

    # 3. 判斷
    auto_approve = risk_score < DRAFT_AUTO_APPROVE_RISK_THRESHOLD

    if auto_approve:
        reasons.append(
            f"風險 {risk_score:.2f} < {DRAFT_AUTO_APPROVE_RISK_THRESHOLD}，自動核准"
        )
    else:
        reasons.append(
            f"風險 {risk_score:.2f} >= {DRAFT_AUTO_APPROVE_RISK_THRESHOLD}，需 CEO 審核"
        )

    return auto_approve, risk_score, reasons
