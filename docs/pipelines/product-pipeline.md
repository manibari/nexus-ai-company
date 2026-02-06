# Product Pipeline 設計

> **版本**: 1.0.0
> **日期**: 2026-02-06

---

## 狀態定義

```python
from enum import Enum

class ProductStage(Enum):
    """產品開發流水線階段"""

    P1_BACKLOG = "backlog"
    P1_5_REQUIREMENTS = "requirements"  # 新增：需求蒐集
    P2_SPEC_READY = "spec_ready"
    P3_IN_PROGRESS = "in_progress"
    P4_QA_TESTING = "qa_testing"
    P5_UAT = "uat"
    P6_DONE = "done"
    BLOCKED = "blocked"
```

---

## 狀態機轉換規則

```
                    ┌─────────────┐
                    │ P1: Backlog │
                    │  (CEO 想法)  │
                    └──────┬──────┘
                           │ gather_requirements()
                           ▼
                    ┌─────────────────┐
                    │ P1.5: Requirements │  ← 新增階段
                    │   (需求蒐集)      │
                    │   PM ↔ CEO 對話   │
                    └──────┬──────────┘
                           │ approve_prd()
                           ▼
                    ┌─────────────┐
                    │ P2: Spec    │
                    │   Ready     │
                    └──────┬──────┘
                           │ start_dev()
                           ▼
                    ┌─────────────┐
              ┌────▶│ P3: In      │◀────┐
              │     │  Progress   │     │
              │     └──────┬──────┘     │
              │            │ submit()   │
              │            ▼            │
              │     ┌─────────────┐     │
              │     │ P4: QA      │     │
              │     │  Testing 🤖 │     │ reject()
              │     └──────┬──────┘     │
              │            │            │
              │     ┌──────┴──────┐     │
              │     │             │     │
              │  pass()        fail()───┘
              │     │
              │     ▼
              │ ┌─────────────┐
              │ │ P5: UAT 👤  │
              │ │(CEO 驗收)   │
              │ └──────┬──────┘
              │        │
              │ ┌──────┴──────┐
              │ │             │
           reject()      approve()
              │             │
              │             ▼
              │      ┌─────────────┐
              └──────│ P6: Done 🚀 │
                     │  (上線)     │
                     └─────────────┘
```

---

## 狀態機實作

```python
from transitions import Machine

class ProductPipeline:
    """產品開發流水線狀態機"""

    states = [
        'backlog',
        'spec_ready',
        'in_progress',
        'qa_testing',
        'uat',
        'done',
        'blocked'
    ]

    transitions = [
        # 正向流程
        {
            'trigger': 'spec',
            'source': 'backlog',
            'dest': 'spec_ready',
            'after': 'on_spec_ready'
        },
        {
            'trigger': 'start_dev',
            'source': 'spec_ready',
            'dest': 'in_progress',
            'after': 'on_dev_started'
        },
        {
            'trigger': 'submit',
            'source': 'in_progress',
            'dest': 'qa_testing',
            'after': 'on_submitted_to_qa'
        },
        {
            'trigger': 'pass_qa',
            'source': 'qa_testing',
            'dest': 'uat',
            'conditions': ['all_tests_passed'],
            'after': 'on_qa_passed'
        },
        {
            'trigger': 'approve',
            'source': 'uat',
            'dest': 'done',
            'after': 'on_approved'
        },

        # 退回流程
        {
            'trigger': 'fail_qa',
            'source': 'qa_testing',
            'dest': 'in_progress',
            'after': 'on_qa_failed'
        },
        {
            'trigger': 'reject_uat',
            'source': 'uat',
            'dest': 'in_progress',
            'after': 'on_uat_rejected'
        },

        # 阻擋
        {
            'trigger': 'block',
            'source': ['spec_ready', 'in_progress', 'qa_testing'],
            'dest': 'blocked',
            'after': 'on_blocked'
        },
        {
            'trigger': 'unblock',
            'source': 'blocked',
            'dest': 'in_progress',
            'after': 'on_unblocked'
        }
    ]

    def __init__(self, task_data: dict, db_session, message_bus):
        self.task = task_data
        self.db = db_session
        self.bus = message_bus
        self.qa_results = []
        self.uat_feedback = []

        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='backlog'
        )

    # === 條件檢查 ===

    def all_tests_passed(self) -> bool:
        """檢查所有測試是否通過"""
        if not self.qa_results:
            return False
        return all(r['passed'] for r in self.qa_results)

    # === 狀態變更回呼 ===

    async def on_spec_ready(self):
        """PM 完成規格"""
        await self._log_transition('backlog', 'spec_ready')

        # 通知 Engineer 可以開始
        await self.bus.send(AgentMessage(
            id=generate_id(),
            type=MessageType.NOTIFY,
            from_agent='ORCHESTRATOR',
            to_agent='BUILDER',
            subject=f'新任務可開始: {self.task["title"]}',
            payload={
                'task_id': self.task['id'],
                'spec': self.task.get('spec', {})
            }
        ))

    async def on_dev_started(self):
        """Engineer 開始開發"""
        await self._log_transition('spec_ready', 'in_progress')
        self.task['dev_started_at'] = datetime.utcnow()

    async def on_submitted_to_qa(self):
        """
        提交給 QA 測試

        🤖 自動化階段：QA Agent 執行測試
        """
        await self._log_transition('in_progress', 'qa_testing')

        # 觸發 QA Agent 執行測試
        await self.bus.send(AgentMessage(
            id=generate_id(),
            type=MessageType.NOTIFY,
            from_agent='BUILDER',
            to_agent='INSPECTOR',
            subject=f'請測試: {self.task["title"]}',
            payload={
                'task_id': self.task['id'],
                'artifact_url': self.task.get('artifact_url'),
                'test_suite': self.task.get('test_suite', 'default')
            }
        ))

    async def on_qa_passed(self):
        """
        QA 通過，進入 UAT

        👤 CEO 介入階段
        """
        await self._log_transition('qa_testing', 'uat')

        # 推送到 CEO Inbox 進行驗收
        await self.bus.escalate_to_ceo(
            from_agent='INSPECTOR',
            subject=f'🔍 待驗收: {self.task["title"]}',
            payload={
                'task_id': self.task['id'],
                'preview_url': self.task.get('staging_url'),
                'qa_report': self.qa_results,
                'spec_summary': self.task.get('spec', {}).get('summary', ''),
                'actions': [
                    {'id': 'approve', 'label': '✅ 通過'},
                    {'id': 'reject', 'label': '❌ 退回', 'requires_feedback': True}
                ]
            },
            blocking=True  # 阻擋等待 CEO 決策
        )

    async def on_qa_failed(self):
        """QA 發現問題，退回開發"""
        await self._log_transition('qa_testing', 'in_progress')

        # 通知 Engineer bug 資訊
        await self.bus.send(AgentMessage(
            id=generate_id(),
            type=MessageType.NOTIFY,
            from_agent='INSPECTOR',
            to_agent='BUILDER',
            subject=f'❌ 測試失敗: {self.task["title"]}',
            payload={
                'task_id': self.task['id'],
                'failures': [r for r in self.qa_results if not r['passed']],
                'logs': self.task.get('test_logs', '')
            },
            priority=MessagePriority.HIGH
        ))

    async def on_uat_rejected(self):
        """CEO 驗收不通過"""
        await self._log_transition('uat', 'in_progress')

        # 通知 PM 和 Engineer
        await self.bus.send(AgentMessage(
            id=generate_id(),
            type=MessageType.NOTIFY,
            from_agent='CEO',
            to_agent='ORCHESTRATOR',
            subject=f'⚠️ UAT 退回: {self.task["title"]}',
            payload={
                'task_id': self.task['id'],
                'feedback': self.uat_feedback
            },
            priority=MessagePriority.HIGH
        ))

    async def on_approved(self):
        """
        CEO 驗收通過，部署上線

        🚀 觸發部署流程
        """
        await self._log_transition('uat', 'done')
        self.task['completed_at'] = datetime.utcnow()

        # 通知全公司
        await self.bus.send(AgentMessage(
            id=generate_id(),
            type=MessageType.NOTIFY,
            from_agent='ORCHESTRATOR',
            to_agent='ALL',
            subject=f'🚀 已上線: {self.task["title"]}',
            payload={
                'task_id': self.task['id'],
                'production_url': self.task.get('production_url')
            }
        ))

    async def on_blocked(self):
        """任務被阻擋"""
        await self._log_transition(self.state, 'blocked')

    async def on_unblocked(self):
        """任務解除阻擋"""
        await self._log_transition('blocked', 'in_progress')

    # === QA 測試結果處理 ===

    async def record_qa_result(self, test_name: str, passed: bool, details: str = ''):
        """記錄單項測試結果"""
        self.qa_results.append({
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })

    # === UAT 回饋處理 ===

    async def record_uat_feedback(self, feedback: str, from_ceo: bool = True):
        """記錄 UAT 回饋"""
        self.uat_feedback.append({
            'feedback': feedback,
            'from_ceo': from_ceo,
            'timestamp': datetime.utcnow().isoformat()
        })

    # === 輔助方法 ===

    async def _log_transition(self, from_state: str, to_state: str):
        """記錄狀態轉換"""
        await self.db.execute(
            logs.insert().values(
                type='pipeline_transition',
                entity_type='task',
                entity_id=self.task['id'],
                from_state=from_state,
                to_state=to_state,
                timestamp=datetime.utcnow()
            )
        )
```

---

## 各階段詳細定義

### P1: Backlog (需求池)

| 項目 | 說明 |
|------|------|
| 來源 | CEO 手動輸入、Agent 建議 |
| 資料需求 | 標題、簡述（可模糊） |
| 負責人 | None（待認領） |

### P1.5: Requirements (需求蒐集) 🆕

| 項目 | 說明 |
|------|------|
| 來源 | PM 從 P1 認領後進入 |
| 資料需求 | 需求問卷回覆 |
| 負責人 | PM Agent (ORCHESTRATOR) |
| 產出文件 | PRD 草案 (`PRD-{id}.md`) |
| CEO 操作 | 回覆需求問卷、確認 PRD |
| 進入 P2 條件 | CEO 確認 PRD |

**需求問卷標準項目**：
1. 目標用戶 (Target Users)
2. 核心功能 (Core Features)
3. 數據來源 (Data Sources)
4. 技術平台 (Tech Platform)
5. 整合需求 (Integrations)
6. 預算時程 (Budget & Timeline)
7. 法規遵循 (Compliance)
8. 商業模式 (Business Model)
9. 成功指標 (Success Metrics)
10. 優先順序 (Priority)

**參考文件**：
- [PRD 模板](../templates/PRD-template.md)
- [ADR-014: Requirements Gathering](../decisions/ADR-014-requirements-gathering.md)

### P2: Spec Ready (規格確認)

| 項目 | 說明 |
|------|------|
| 進入條件 | PM 完成任務拆解 |
| 資料需求 | WBS、驗收標準、技術方案 |
| 負責人 | PM Agent (ORCHESTRATOR) |
| 產出文件 | `spec.md` |

### P3: In Progress (開發中)

| 項目 | 說明 |
|------|------|
| 進入條件 | Engineer 認領任務 |
| 資料需求 | 預估工時、開始時間 |
| 負責人 | Engineer Agent (BUILDER) |
| 產出 | Code、配置檔 |

### P4: QA Testing (內部測試) 🤖

| 項目 | 說明 |
|------|------|
| 進入條件 | Engineer 提交 PR/Artifact |
| 自動化 | QA Agent 自動執行測試腳本 |
| 測試類型 | 單元測試、整合測試、Lint |
| 退回條件 | 任一測試失敗 |
| 負責人 | QA Agent (INSPECTOR) |

### P5: UAT (使用者驗收) 👤

| 項目 | 說明 |
|------|------|
| 進入條件 | 所有 QA 測試通過 |
| CEO 操作 | 在 Staging 環境實際試用 |
| 可用動作 | Approve / Reject (with feedback) |
| 阻擋等級 | BLOCKED_USER |

### P6: Done (上線) 🚀

| 項目 | 說明 |
|------|------|
| 進入條件 | CEO 按下 Approve |
| 自動化 | 觸發部署腳本 |
| 後續 | 更新 changelog、通知相關人 |

---

## RPG 視覺化對應

| 階段 | 視覺元素 |
|------|----------|
| P1 | 看板上出現新便利貼（灰色） |
| P2 | 便利貼變成藍色，PM 桌上有文件 |
| P3 | 便利貼變成黃色，Engineer 在打字 |
| P4 | 便利貼閃爍，QA 角色執行動畫 |
| P5 | 展示間電腦亮起，CEO Inbox 有通知 |
| P6 | 便利貼變綠色並移到「完成區」 |

---

## 與其他 Pipeline 的互動

- **Sales Pipeline S4 → Product Pipeline P1**：客戶需求可轉為 Backlog 項目
- **Product P6 → Sales S4**：新功能上線可作為銷售素材

---

## 參考文件

- [sales-pipeline.md](./sales-pipeline.md)
- [001-system-overview.md](../architecture/001-system-overview.md)
