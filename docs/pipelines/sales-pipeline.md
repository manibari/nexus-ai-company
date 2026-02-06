# Sales Pipeline 設計

> **版本**: 1.0.0
> **日期**: 2026-02-06

---

## 狀態定義

```python
from enum import Enum

class SalesStage(Enum):
    """業務開發流水線階段"""

    S1_NEW_LEAD = "new_lead"
    S2_QUALIFIED = "qualified"
    S3_CONTACTED = "contacted"
    S4_ENGAGED = "engaged"
    S5_CLOSED_WON = "closed_won"
    S5_CLOSED_LOST = "closed_lost"
```

---

## 狀態機轉換規則

```
                    ┌─────────────┐
                    │  S1: New    │
                    │    Lead     │
                    └──────┬──────┘
                           │ qualify()
                           ▼
                    ┌─────────────┐
          ┌─────────│ S2:Qualified│─────────┐
          │ reject()└──────┬──────┘         │
          │                │ contact()       │
          ▼                ▼                 │
    ┌───────────┐   ┌─────────────┐         │
    │   LOST    │   │S3: Contacted│         │
    │(not ICP)  │   └──────┬──────┘         │
    └───────────┘          │                │
                           │ engage()       │
                           ▼                │
                    ┌─────────────┐         │
                    │ S4: Engaged │◀────────┘
                    │  ⚠️ CEO 關注 │  (fast track)
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │ close()                 │ lose()
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │S5: Closed   │          │S5: Closed   │
       │    Won 🎉   │          │    Lost     │
       └─────────────┘          └─────────────┘
```

---

## 狀態機實作

```python
from transitions import Machine

class SalesPipeline:
    """業務開發流水線狀態機"""

    states = [
        'new_lead',
        'qualified',
        'contacted',
        'engaged',
        'closed_won',
        'closed_lost'
    ]

    transitions = [
        # 正向流程
        {
            'trigger': 'qualify',
            'source': 'new_lead',
            'dest': 'qualified',
            'conditions': ['is_icp_match'],
            'after': 'on_qualified'
        },
        {
            'trigger': 'contact',
            'source': 'qualified',
            'dest': 'contacted',
            'after': 'on_contacted'
        },
        {
            'trigger': 'engage',
            'source': 'contacted',
            'dest': 'engaged',
            'after': 'on_engaged'
        },
        {
            'trigger': 'close',
            'source': 'engaged',
            'dest': 'closed_won',
            'after': 'on_closed_won'
        },

        # 失敗路徑
        {
            'trigger': 'reject',
            'source': 'qualified',
            'dest': 'closed_lost',
            'after': 'on_rejected'
        },
        {
            'trigger': 'lose',
            'source': ['contacted', 'engaged'],
            'dest': 'closed_lost',
            'after': 'on_lost'
        },

        # 快速通道（已有關係的客戶）
        {
            'trigger': 'fast_track',
            'source': 'qualified',
            'dest': 'engaged',
            'conditions': ['has_existing_relationship'],
            'after': 'on_engaged'
        }
    ]

    def __init__(self, lead_data: dict, db_session, message_bus):
        self.lead = lead_data
        self.db = db_session
        self.bus = message_bus

        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='new_lead'
        )

    # === 條件檢查 ===

    def is_icp_match(self) -> bool:
        """檢查是否符合目標客戶輪廓 (ICP)"""
        # TODO: 實作 ICP 匹配邏輯
        icp_criteria = {
            'industry': ['tech', 'finance', 'healthcare'],
            'company_size': (50, 5000),  # 員工數
            'region': ['TW', 'US', 'JP']
        }
        # ... 檢查邏輯
        return True

    def has_existing_relationship(self) -> bool:
        """檢查是否有既有關係"""
        return self.lead.get('existing_contact') is not None

    # === 狀態變更回呼 ===

    async def on_qualified(self):
        """進入 Qualified 階段"""
        await self._log_transition('new_lead', 'qualified')
        await self._update_db()

    async def on_contacted(self):
        """進入 Contacted 階段"""
        await self._log_transition('qualified', 'contacted')
        await self._update_db()

    async def on_engaged(self):
        """
        進入 Engaged 階段

        ⚠️ 關鍵階段：通知 CEO 關注
        """
        await self._log_transition(self.state, 'engaged')
        await self._update_db()

        # 升級通知 CEO（非阻擋）
        await self.bus.escalate_to_ceo(
            from_agent='HUNTER',
            subject=f'🔥 客戶感興趣: {self.lead["company"]}',
            payload={
                'lead_id': self.lead['id'],
                'company': self.lead['company'],
                'contact': self.lead['contact_name'],
                'notes': self.lead.get('engagement_notes', '')
            },
            blocking=False  # 不阻擋，只是通知
        )

    async def on_closed_won(self):
        """成交！"""
        await self._log_transition('engaged', 'closed_won')
        await self._update_db()

        # 通知全公司
        await self.bus.send(AgentMessage(
            id=generate_id(),
            type=MessageType.NOTIFY,
            from_agent='HUNTER',
            to_agent='ALL',
            subject=f'🎉 新訂單: {self.lead["company"]}',
            payload={'deal_value': self.lead.get('deal_value', 0)}
        ))

    async def on_lost(self):
        """失去客戶"""
        await self._log_transition(self.state, 'closed_lost')
        await self._update_db()

    async def on_rejected(self):
        """不符合 ICP"""
        await self._log_transition('qualified', 'closed_lost')
        await self._update_db()

    # === 輔助方法 ===

    async def _update_db(self):
        """更新資料庫"""
        await self.db.execute(
            tasks.update()
            .where(tasks.c.id == self.lead['id'])
            .values(
                stage=self.state,
                updated_at=datetime.utcnow()
            )
        )

    async def _log_transition(self, from_state: str, to_state: str):
        """記錄狀態轉換"""
        await self.db.execute(
            logs.insert().values(
                type='pipeline_transition',
                entity_type='lead',
                entity_id=self.lead['id'],
                from_state=from_state,
                to_state=to_state,
                timestamp=datetime.utcnow()
            )
        )
```

---

## 各階段詳細定義

### S1: New Lead (新名單)

| 項目 | 說明 |
|------|------|
| 來源 | 爬蟲自動抓取、手動輸入 |
| 資料需求 | 公司名稱、產業、聯絡資訊（至少 email） |
| 自動化 | 爬蟲每日執行，新名單自動進入此階段 |
| 停留時間 | < 24 小時（應快速篩選） |

### S2: Qualified (合格)

| 項目 | 說明 |
|------|------|
| 進入條件 | 通過 ICP 匹配（產業、規模、地區） |
| 自動化 | Sales Agent 自動評估並轉換 |
| 失敗路徑 | 不符合 ICP → 直接進入 Lost |

### S3: Contacted (已聯繫)

| 項目 | 說明 |
|------|------|
| 進入條件 | 開發信已寄出（需記錄寄送時間） |
| 資料需求 | email_sent_at, email_content_id |
| 追蹤 | 7 天無回覆 → 自動 follow-up（最多 3 次） |
| 失敗路徑 | 3 次 follow-up 無回覆 → Lost |

### S4: Engaged (已接洽) ⚠️

| 項目 | 說明 |
|------|------|
| 進入條件 | 客戶有回覆且表達興趣 |
| CEO 介入 | 此階段自動通知 CEO |
| 可能需審批 | 客戶要求折扣 > 10%、特殊付款條件 |
| 資料需求 | 對話記錄、需求摘要、預估金額 |

### S5: Closed Won / Lost (結案)

| 項目 | 說明 |
|------|------|
| Won | 簽約完成、收到訂金 |
| Lost | 客戶拒絕、超時無回應、不符合需求 |
| 資料需求 | lost_reason (如果是 Lost) |

---

## RPG 視覺化對應

| 階段 | 視覺元素 |
|------|----------|
| S1 | Sales 桌上出現新文件堆 |
| S2 | 文件從「收件匣」移到「處理中」 |
| S3 | Sales 角色做出「寄信」動畫 |
| S4 | Sales 頭上出現「❗」，辦公室亮燈 |
| S5 Won | 撒花動畫，金庫閃光 |
| S5 Lost | 文件移入「歸檔櫃」（灰色） |

---

## 參考文件

- [product-pipeline.md](./product-pipeline.md)
- [001-system-overview.md](../architecture/001-system-overview.md)
