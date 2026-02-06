# ADR-007: Engine Layer 架構

## 狀態
已採納

## 背景
隨著系統功能增加，我們發現多個 Agent 需要相似的分析能力（如 NLP、OCR、資料補全）。
如果將這些能力內建在各 Agent 中，會造成：
- 重複代碼
- 維護困難
- 測試複雜

## 決策
建立獨立的 **Engine Layer（能力層）**，提供可複用的分析服務。

## 架構

```
┌─────────────────────────────────────────────────────────────┐
│                       Agents (決策層)                        │
│         負責：流程編排、決策、與用戶/其他Agent互動             │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐         │
│  │ HUNTER  │ │ORCHESTRAT│ │ BUILDER │ │GATEKEEPER│  ...    │
│  └────┬────┘ └────┬─────┘ └────┬────┘ └────┬─────┘         │
└───────┼───────────┼────────────┼───────────┼────────────────┘
        │           │            │           │
        ▼           ▼            ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Engines (能力層)                        │
│              負責：專業分析、數據處理、模型推理                 │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ MEDDIC   │ │   OCR    │ │   NLP    │ │Enrichment│       │
│  │ Engine   │ │ Engine   │ │ Engine   │ │ Engine   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Code    │ │  Search  │ │ Pricing  │ │ Document │       │
│  │ Analysis │ │  Engine  │ │  Engine  │ │  Parser  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Engine 清單

### Phase 1 (MVP)
| Engine | 功能 | 使用者 |
|--------|------|--------|
| **MEDDIC Engine** | 銷售機會分析（Pain/Champion/EB評估） | HUNTER |
| **NLP Engine** | 意圖識別、實體抽取 | GATEKEEPER, HUNTER |
| **Enrichment Engine** | 公司/聯絡人資料補全 | GATEKEEPER, HUNTER |

### Phase 2
| Engine | 功能 | 使用者 |
|--------|------|--------|
| **OCR Engine** | 名片、文件、發票識別 | GATEKEEPER, LEDGER |
| **Document Parser** | 合約、報價單解析 | HUNTER, LEDGER |
| **Search Engine** | 內部知識庫搜尋 | ALL |

### Phase 3
| Engine | 功能 | 使用者 |
|--------|------|--------|
| **Code Analysis** | 代碼品質、複雜度分析 | BUILDER, INSPECTOR |
| **Pricing Engine** | 報價計算、折扣規則 | HUNTER, LEDGER |
| **Sentiment Engine** | 客戶情緒分析 | HUNTER |

## Engine 設計原則

### 1. 統一介面
```python
class BaseEngine:
    """所有 Engine 的基類"""

    async def analyze(self, input: Any) -> AnalysisResult:
        """主要分析方法"""
        raise NotImplementedError

    def get_confidence(self) -> float:
        """返回分析信心度"""
        raise NotImplementedError
```

### 2. 可配置
```yaml
# config/engines/meddic.yaml
meddic:
  pain:
    min_score_for_qualified: 6
    keywords:
      high_urgency: ["急", "立刻", "馬上"]
  champion:
    required_signals: 2
  economic_buyer:
    access_levels: ["unknown", "identified", "contacted", "meeting", "committed"]
```

### 3. 可 Mock
```python
class MockMEDDICEngine(BaseEngine):
    """用於測試的 Mock Engine"""

    async def analyze(self, lead: Lead) -> MEDDICAnalysis:
        return MEDDICAnalysis(
            pain=PainAnalysis(score=7, ...),
            champion=ChampionAnalysis(identified=True, ...),
            ...
        )
```

## Agent 與 Engine 的關係

### 依賴注入
```python
class HunterAgent:
    def __init__(
        self,
        meddic_engine: MEDDICEngine,
        enrichment_engine: EnrichmentEngine,
        nlp_engine: NLPEngine,
    ):
        self.meddic = meddic_engine
        self.enrichment = enrichment_engine
        self.nlp = nlp_engine
```

### 調用模式
```python
async def think(self, lead: Lead) -> ThinkResult:
    # 1. 使用 Engine 分析
    meddic_result = await self.meddic.analyze(lead)

    # 2. Agent 基於分析結果做決策
    if meddic_result.deal_score < 50:
        return ThinkResult(
            action="nurture",
            reasoning="MEDDIC 分數過低，建議放入培育池"
        )

    # 3. 決定下一步
    next_action = self._determine_next_action(meddic_result)
    return ThinkResult(action=next_action, ...)
```

## 目錄結構

```
backend/
├── app/
│   ├── agents/              # 決策層
│   │   ├── base.py
│   │   ├── hunter.py
│   │   └── ...
│   │
│   ├── engines/             # 能力層
│   │   ├── base.py          # BaseEngine
│   │   ├── meddic/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py    # MEDDICEngine
│   │   │   ├── models.py    # 資料模型
│   │   │   ├── analyzers/   # 各維度分析器
│   │   │   │   ├── pain.py
│   │   │   │   ├── champion.py
│   │   │   │   └── economic_buyer.py
│   │   │   └── scoring.py   # 評分邏輯
│   │   ├── nlp/
│   │   │   ├── engine.py
│   │   │   ├── intent.py
│   │   │   └── entity.py
│   │   ├── enrichment/
│   │   │   └── engine.py
│   │   └── ocr/
│   │       └── engine.py
│   │
│   └── ...
│
├── config/
│   └── engines/             # Engine 配置
│       ├── meddic.yaml
│       ├── nlp.yaml
│       └── enrichment.yaml
```

## 測試策略

### Unit Test
- 每個 Engine 獨立測試
- 使用固定輸入驗證輸出

### Integration Test
- Agent + Mock Engine
- 驗證決策邏輯

### E2E Test
- Agent + Real Engine
- 驗證完整流程

## 後續事項
- [ ] 實作 BaseEngine 介面
- [ ] 實作 MEDDIC Engine (Phase 1)
- [ ] 實作 NLP Engine (Phase 1)
- [ ] 建立 Engine 註冊機制
- [ ] 建立 Mock Engine 工具

## 參考
- ADR-005: Agent 可觀測性
- ADR-006: CEO Intake Layer
