"""
Rules Engine - Agent 行為規則引擎

解決問題：Agent 行為規則 hardcode 在程式碼中，調整需要改程式

提供功能：
- YAML 配置 Agent 行為
- 動態載入和更新規則
- 規則驗證和套用
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ApprovalThreshold:
    """審批門檻"""
    discount_percentage: float = 10.0
    deal_value_usd: float = 100000.0
    custom_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommunicationRules:
    """通訊規則"""
    tone: str = "professional"  # formal, professional, casual, friendly
    max_follow_ups: int = 3
    follow_up_interval_days: int = 7
    max_email_length_chars: int = 2000
    require_greeting: bool = True
    require_signature: bool = True


@dataclass
class ScheduleRules:
    """時程規則"""
    blackout_days: List[str] = field(
        default_factory=lambda: ["saturday", "sunday"]
    )
    preferred_hours_start: str = "09:00"
    preferred_hours_end: str = "18:00"
    timezone: str = "Asia/Taipei"
    respect_holidays: bool = True
    holiday_country: str = "TW"


@dataclass
class EscalationRules:
    """升級規則"""
    always_notify_ceo: List[str] = field(
        default_factory=lambda: [
            "competitor_mentioned",
            "legal_concern",
            "negative_sentiment",
            "budget_exceeded",
        ]
    )
    auto_escalate_after_hours: int = 24
    escalation_chain: List[str] = field(
        default_factory=lambda: ["ORCHESTRATOR", "CEO"]
    )


@dataclass
class AgentRules:
    """
    Agent 行為規則

    完整的 Agent 行為配置
    """
    agent_id: str
    agent_name: str
    version: str = "1.0.0"

    # 各類規則
    approval_thresholds: ApprovalThreshold = field(
        default_factory=ApprovalThreshold
    )
    communication: CommunicationRules = field(
        default_factory=CommunicationRules
    )
    schedule: ScheduleRules = field(default_factory=ScheduleRules)
    escalation: EscalationRules = field(default_factory=EscalationRules)

    # 自定義規則
    custom_rules: Dict[str, Any] = field(default_factory=dict)

    # 元資料
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: str = "system"

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "version": self.version,
            "approval_thresholds": {
                "discount_percentage": self.approval_thresholds.discount_percentage,
                "deal_value_usd": self.approval_thresholds.deal_value_usd,
            },
            "communication": {
                "tone": self.communication.tone,
                "max_follow_ups": self.communication.max_follow_ups,
            },
            "schedule": {
                "blackout_days": self.schedule.blackout_days,
                "timezone": self.schedule.timezone,
            },
        }

    def requires_approval(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        """
        檢查動作是否需要審批

        Returns:
            (需要審批, 原因)
        """
        # 檢查折扣
        discount = params.get("discount_percentage", 0)
        if discount > self.approval_thresholds.discount_percentage:
            return True, f"Discount {discount}% exceeds threshold {self.approval_thresholds.discount_percentage}%"

        # 檢查金額
        deal_value = params.get("deal_value", 0)
        if deal_value > self.approval_thresholds.deal_value_usd:
            return True, f"Deal value ${deal_value} exceeds threshold ${self.approval_thresholds.deal_value_usd}"

        # 檢查自定義規則
        for rule_name, rule_config in self.approval_thresholds.custom_rules.items():
            field_name = rule_config.get("field")
            threshold = rule_config.get("threshold")
            operator = rule_config.get("operator", ">")

            if field_name and field_name in params:
                value = params[field_name]
                if self._compare(value, threshold, operator):
                    return True, f"{rule_name}: {field_name}={value} {operator} {threshold}"

        return False, ""

    def is_within_schedule(self, check_time: Optional[datetime] = None) -> bool:
        """檢查是否在允許的時間內"""
        if check_time is None:
            check_time = datetime.utcnow()

        # 檢查星期
        day_name = check_time.strftime("%A").lower()
        if day_name in [d.lower() for d in self.schedule.blackout_days]:
            return False

        # 檢查時間
        start = datetime.strptime(
            self.schedule.preferred_hours_start, "%H:%M"
        ).time()
        end = datetime.strptime(
            self.schedule.preferred_hours_end, "%H:%M"
        ).time()
        current_time = check_time.time()

        if not (start <= current_time <= end):
            return False

        return True

    def should_escalate(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """檢查是否應該升級給 CEO"""
        for trigger in self.escalation.always_notify_ceo:
            if context.get(trigger, False):
                return True, f"Trigger: {trigger}"

            # 檢查內容中是否包含觸發詞
            content = context.get("content", "")
            if trigger in content.lower():
                return True, f"Content contains: {trigger}"

        return False, ""

    @staticmethod
    def _compare(value: Any, threshold: Any, operator: str) -> bool:
        """比較值"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        return False


class RulesEngine:
    """
    規則引擎

    管理所有 Agent 的行為規則
    """

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or "config/agents"
        self._rules: Dict[str, AgentRules] = {}
        self._watchers: Dict[str, List[callable]] = {}

    def load_all(self):
        """載入所有規則配置"""
        config_path = Path(self.config_dir)

        if not config_path.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            return

        for yaml_file in config_path.glob("*.yaml"):
            agent_id = yaml_file.stem
            self.load_agent_rules(agent_id, yaml_file)

    def load_agent_rules(self, agent_id: str, file_path: Path):
        """載入單個 Agent 的規則"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            rules = self._parse_config(agent_id, config)
            self._rules[agent_id] = rules

            logger.info(f"Loaded rules for agent: {agent_id}")

            # 通知監聽者
            self._notify_watchers(agent_id, rules)

        except Exception as e:
            logger.error(f"Failed to load rules for {agent_id}: {e}")

    def get_rules(self, agent_id: str) -> Optional[AgentRules]:
        """取得 Agent 規則"""
        return self._rules.get(agent_id)

    def update_rules(
        self,
        agent_id: str,
        updates: Dict[str, Any],
        updated_by: str = "CEO",
    ) -> AgentRules:
        """
        更新 Agent 規則

        Args:
            agent_id: Agent ID
            updates: 要更新的規則（部分更新）
            updated_by: 更新者

        Returns:
            更新後的規則
        """
        rules = self._rules.get(agent_id)

        if not rules:
            # 建立新規則
            rules = AgentRules(agent_id=agent_id, agent_name=agent_id)

        # 套用更新
        self._apply_updates(rules, updates)
        rules.updated_at = datetime.utcnow()
        rules.updated_by = updated_by

        self._rules[agent_id] = rules

        # 持久化
        self._save_rules(agent_id, rules)

        # 通知監聽者
        self._notify_watchers(agent_id, rules)

        logger.info(f"Updated rules for {agent_id} by {updated_by}")

        return rules

    def watch(self, agent_id: str, callback: callable):
        """監聽規則變更"""
        if agent_id not in self._watchers:
            self._watchers[agent_id] = []
        self._watchers[agent_id].append(callback)

    def get_all_rules(self) -> Dict[str, AgentRules]:
        """取得所有規則"""
        return self._rules.copy()

    def validate_action(
        self,
        agent_id: str,
        action: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        驗證動作是否符合規則

        Returns:
            {
                "allowed": bool,
                "requires_approval": bool,
                "approval_reason": str,
                "warnings": List[str],
                "blocked_reason": str
            }
        """
        rules = self._rules.get(agent_id)

        if not rules:
            return {
                "allowed": True,
                "requires_approval": False,
                "warnings": ["No rules configured for this agent"],
            }

        result = {
            "allowed": True,
            "requires_approval": False,
            "approval_reason": "",
            "warnings": [],
            "blocked_reason": "",
        }

        # 檢查時間表
        if not rules.is_within_schedule():
            result["warnings"].append(
                f"Outside of preferred hours ({rules.schedule.preferred_hours_start} - {rules.schedule.preferred_hours_end})"
            )

        # 檢查是否需要審批
        needs_approval, reason = rules.requires_approval(action, params)
        if needs_approval:
            result["requires_approval"] = True
            result["approval_reason"] = reason

        # 檢查是否需要升級
        should_escalate, escalate_reason = rules.should_escalate(context)
        if should_escalate:
            result["requires_approval"] = True
            result["approval_reason"] = escalate_reason

        return result

    def _parse_config(self, agent_id: str, config: Dict[str, Any]) -> AgentRules:
        """解析 YAML 配置"""
        rules = AgentRules(
            agent_id=agent_id,
            agent_name=config.get("name", agent_id),
            version=config.get("version", "1.0.0"),
        )

        # 解析審批門檻
        if "approval_thresholds" in config:
            at = config["approval_thresholds"]
            rules.approval_thresholds = ApprovalThreshold(
                discount_percentage=at.get("discount_percentage", 10.0),
                deal_value_usd=at.get("deal_value_usd", 100000.0),
                custom_rules=at.get("custom_rules", {}),
            )

        # 解析通訊規則
        if "communication" in config:
            comm = config["communication"]
            rules.communication = CommunicationRules(
                tone=comm.get("tone", "professional"),
                max_follow_ups=comm.get("max_follow_ups", 3),
                follow_up_interval_days=comm.get("follow_up_interval_days", 7),
            )

        # 解析時程規則
        if "schedule" in config:
            sched = config["schedule"]
            rules.schedule = ScheduleRules(
                blackout_days=sched.get("blackout_days", ["saturday", "sunday"]),
                preferred_hours_start=sched.get("preferred_hours_start", "09:00"),
                preferred_hours_end=sched.get("preferred_hours_end", "18:00"),
                timezone=sched.get("timezone", "Asia/Taipei"),
            )

        # 解析升級規則
        if "escalation" in config:
            esc = config["escalation"]
            rules.escalation = EscalationRules(
                always_notify_ceo=esc.get("always_notify_ceo", []),
                auto_escalate_after_hours=esc.get("auto_escalate_after_hours", 24),
            )

        # 自定義規則
        rules.custom_rules = config.get("custom_rules", {})

        return rules

    def _apply_updates(self, rules: AgentRules, updates: Dict[str, Any]):
        """套用部分更新"""
        if "approval_thresholds" in updates:
            for key, value in updates["approval_thresholds"].items():
                if hasattr(rules.approval_thresholds, key):
                    setattr(rules.approval_thresholds, key, value)

        if "communication" in updates:
            for key, value in updates["communication"].items():
                if hasattr(rules.communication, key):
                    setattr(rules.communication, key, value)

        if "schedule" in updates:
            for key, value in updates["schedule"].items():
                if hasattr(rules.schedule, key):
                    setattr(rules.schedule, key, value)

        if "escalation" in updates:
            for key, value in updates["escalation"].items():
                if hasattr(rules.escalation, key):
                    setattr(rules.escalation, key, value)

    def _save_rules(self, agent_id: str, rules: AgentRules):
        """保存規則到文件"""
        config_path = Path(self.config_dir)
        config_path.mkdir(parents=True, exist_ok=True)

        file_path = config_path / f"{agent_id}.yaml"

        config = {
            "name": rules.agent_name,
            "version": rules.version,
            "approval_thresholds": {
                "discount_percentage": rules.approval_thresholds.discount_percentage,
                "deal_value_usd": rules.approval_thresholds.deal_value_usd,
                "custom_rules": rules.approval_thresholds.custom_rules,
            },
            "communication": {
                "tone": rules.communication.tone,
                "max_follow_ups": rules.communication.max_follow_ups,
                "follow_up_interval_days": rules.communication.follow_up_interval_days,
            },
            "schedule": {
                "blackout_days": rules.schedule.blackout_days,
                "preferred_hours_start": rules.schedule.preferred_hours_start,
                "preferred_hours_end": rules.schedule.preferred_hours_end,
                "timezone": rules.schedule.timezone,
            },
            "escalation": {
                "always_notify_ceo": rules.escalation.always_notify_ceo,
                "auto_escalate_after_hours": rules.escalation.auto_escalate_after_hours,
            },
            "custom_rules": rules.custom_rules,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def _notify_watchers(self, agent_id: str, rules: AgentRules):
        """通知監聽者"""
        for callback in self._watchers.get(agent_id, []):
            try:
                callback(rules)
            except Exception as e:
                logger.error(f"Watcher callback failed: {e}")
