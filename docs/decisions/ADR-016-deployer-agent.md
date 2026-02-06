# ADR-016: Deployer Agent 設計決策

## 狀態

**暫緩實作** (2026-02-07)

## 背景

CEO 詢問是否應將開發 (BUILDER) 與部署 (DEPLOYER) 職責分離。

## 分析結論

### 利弊權衡

| 優點 | 缺點 |
|------|------|
| 職責分離、專業化 | 小專案負擔增加 |
| 安全性提升 | 交接成本 |
| 流程清晰 | 協調複雜度 |
| 可擴展性 | 閒置風險 |

### 建議方案

**混合模式**：
- MVP/內部工具：BUILDER 負責
- 正式產品 Staging/Production：DEPLOYER 負責

## 決策

CEO 決定：**暫時不實作 DEPLOYER Agent**

理由：
1. 目前專案仍在 MVP 階段
2. 尚無生產環境部署需求
3. 避免過度設計

## 觸發條件

當以下情況發生時，應重新評估並實作 DEPLOYER：
1. 需要部署到雲端生產環境
2. 需要設定 CI/CD Pipeline
3. 多專案同時需要部署維運
4. 需要專人管理生產環境憑證/Secrets

## 預定設計

當需要實作時，DEPLOYER Agent 定義：

```
ID: DEPLOYER
名稱: DevOps Agent
角色: 部署工程師
職責:
- 環境建置（Staging/Production）
- Docker/Kubernetes 管理
- CI/CD Pipeline
- 雲端資源管理
- 監控與告警設定
- 安全強化
```

## 參考

- CR-003: 部署架構規範
- `docs/protocols/deployment_standards.md`
