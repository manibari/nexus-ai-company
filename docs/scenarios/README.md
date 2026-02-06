# Validation Scenarios

用於驗證 Nexus AI Company 系統流程的測試場景。

## 場景類型

| Pipeline | 場景 | 驗證重點 |
|----------|------|---------|
| **Sales** | 001-sales-opportunity | GATEKEEPER → HUNTER → MEDDIC Engine |
| **Product** | 002-product-stock-crawler | GATEKEEPER → ORCHESTRATOR → BUILDER → INSPECTOR |

## 如何使用

### 1. 選擇場景
```bash
# 驗證 Sales Pipeline
docs/scenarios/001-sales-opportunity.yaml

# 驗證 Product Pipeline
docs/scenarios/002-product-stock-crawler.yaml
```

### 2. 填入真實案例
將 `input.raw_text` 改成你的真實案例：
```yaml
input:
  raw_text: |
    [貼上你收到的實際訊息/Email]
```

### 3. 執行驗證
```bash
# TODO: 建立驗證腳本
python scripts/run_scenario.py docs/scenarios/001-sales-opportunity.yaml
```

### 4. 比對結果
系統輸出 vs `expected_*` 欄位，計算準確率。

### 5. 記錄結果
更新 `execution_log` 和 `actual_outcome`。

## 場景結構

```yaml
scenario:
  id: "SCENARIO-XXX"
  name: "場景名稱"
  pipeline: "sales | product"
  agents_involved: [...]
  engines_involved: [...]

cases:  # (Sales Pipeline)
  - id: "CASE-XXX"
    input: {...}
    expected_parsing: {...}
    expected_meddic: {...}
    expected_actions: {...}
    actual_outcome: {...}

stages:  # (Product Pipeline)
  P1_requirements: {...}
  P2_analysis: {...}
  P3_P4_development: {...}
  P5_testing: {...}
  P6_deployment: {...}

validation:
  # 成功指標

execution_log:
  # 執行記錄
```

## 新增場景

1. 複製現有模板
2. 修改 `scenario.id` 和 `scenario.name`
3. 填入測試案例
4. 定義 `expected_*` 預期結果
5. 設定 `validation` 成功指標

## 場景清單

- [x] 001 - Sales Opportunity (MEDDIC 驗證)
- [x] 002 - Stock Crawler (Product Pipeline 驗證)
- [ ] 003 - 客戶支援流程
- [ ] 004 - 財務報表分析
- [ ] ...
