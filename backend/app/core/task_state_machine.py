"""
Task Lifecycle State Machine

15 狀態 / 22 轉換的狀態機，使用 transitions library。
純狀態轉換驗證，不含 DB/IO。

Issue #14
"""

from transitions import Machine

STATES = [
    "submitted",
    "planning",
    "plan_review",
    "plan_approved",
    "reasoning",
    "draft_generated",
    "schema_check",
    "rule_check",
    "draft_review",
    "draft_approved",
    "executing",
    "uat_review",
    "completed",
    "rejected",
    "escalated",
]

TRANSITIONS = [
    {"trigger": "start_planning",       "source": "submitted",       "dest": "planning"},
    {"trigger": "auto_approve_plan",    "source": "planning",        "dest": "plan_approved"},
    {"trigger": "request_plan_review",  "source": "planning",        "dest": "plan_review"},
    {"trigger": "approve_plan",         "source": "plan_review",     "dest": "plan_approved"},
    {"trigger": "revise_plan",          "source": "plan_review",     "dest": "planning"},
    {"trigger": "reject_plan",          "source": "plan_review",     "dest": "rejected"},
    {"trigger": "start_reasoning",      "source": "plan_approved",   "dest": "reasoning"},
    {"trigger": "draft_ready",          "source": "reasoning",       "dest": "draft_generated"},
    {"trigger": "check_schema",         "source": "draft_generated", "dest": "schema_check"},
    {"trigger": "schema_pass",          "source": "schema_check",    "dest": "rule_check"},
    {"trigger": "schema_fail_retry",    "source": "schema_check",    "dest": "reasoning"},
    {"trigger": "schema_fail_final",    "source": "schema_check",    "dest": "escalated"},
    {"trigger": "auto_approve_draft",   "source": "rule_check",      "dest": "draft_approved"},
    {"trigger": "request_draft_review", "source": "rule_check",      "dest": "draft_review"},
    {"trigger": "approve_draft",        "source": "draft_review",    "dest": "draft_approved"},
    {"trigger": "revise_draft",         "source": "draft_review",    "dest": "reasoning"},
    {"trigger": "reject_draft",         "source": "draft_review",    "dest": "rejected"},
    {"trigger": "start_execution",      "source": "draft_approved",  "dest": "executing"},
    {"trigger": "execution_done",       "source": "executing",       "dest": "uat_review"},
    {"trigger": "exec_fail",            "source": "executing",       "dest": "draft_review"},
    {"trigger": "confirm_uat",          "source": "uat_review",      "dest": "completed"},
    {"trigger": "request_fix",          "source": "uat_review",      "dest": "reasoning"},
]

TERMINAL_STATES = {"completed", "rejected", "escalated"}


class TaskLifecycle:
    """Task 生命週期狀態機（純驗證，不含 IO）"""

    def __init__(self, initial_state: str = "submitted"):
        self.machine = Machine(
            model=self,
            states=STATES,
            transitions=TRANSITIONS,
            initial=initial_state,
            auto_transitions=False,
            send_event=False,
        )

    def try_trigger(self, trigger_name: str) -> tuple:
        """
        嘗試觸發轉換。

        Returns:
            (True, new_state) on success
            (False, error_message) on failure
        """
        trigger_fn = getattr(self, trigger_name, None)
        if trigger_fn is None:
            return False, f"Unknown trigger: {trigger_name}"

        available = self.machine.get_triggers(self.state)
        if trigger_name not in available:
            return False, f"Cannot '{trigger_name}' from state '{self.state}'"

        trigger_fn()
        return True, self.state

    def get_available_triggers(self) -> list:
        """取得目前狀態可用的 trigger 列表"""
        return self.machine.get_triggers(self.state)

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
