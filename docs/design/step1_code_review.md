# Step 1: Docker Compose 基礎設施 — Code Review

**日期**: 2026-02-07
**審查範圍**: docker-compose.yml, .env.example, database.py, requirements.txt, Dockerfile
**結論**: 需要額外修正 1 項才能 commit

---

## 變更摘要

| 檔案 | 變更 |
|------|------|
| `docker-compose.yml` | 新增 postgres + redis services, backend depends_on 改為 health check, pgdata volume |
| `.env.example` | DATABASE_URL 改為 PostgreSQL, 新增 REDIS_URL |
| `backend/app/db/database.py` | 預設改 PostgreSQL, 保留 SQLite fallback, 新增 pool 設定 |
| `backend/requirements.txt` | 新增 asyncpg, redis[hiredis] |

---

## 審查結果

### PASS — 無問題項目

| 項目 | 說明 |
|------|------|
| Port 衝突 | 5432 / 6379 / 8000 / 3000 各自獨立，無衝突 |
| SQLAlchemy Models 相容性 | `models.py` 使用標準 ORM 型別 (JSON, DateTime, String, Integer)，全部 PostgreSQL 相容 |
| .env 覆蓋風險 | 目前不存在 `.env` 檔案，不會誤用舊 SQLite URL |
| database.py 邏輯 | URL 自動轉換正確 (`sqlite://` → `sqlite+aiosqlite://`, `postgresql://` → `postgresql+asyncpg://`)；pool 設定只套用非 SQLite |
| database.py 影響範圍 | 僅 `main.py` import `create_tables`，blast radius 很小 |
| Docker 服務依賴 | backend depends_on postgres/redis 使用 `condition: service_healthy`，確保啟動順序 |
| Redis 設定 | docker-compose 與 .env.example 的 REDIS_URL 一致 |

### NEEDS FIX — 必須修正

#### 1. Dockerfile 缺少 PostgreSQL 編譯依賴

**檔案**: `backend/Dockerfile`
**問題**: `asyncpg` 需要 `libpq-dev` 才能編譯 C extension，目前 Dockerfile 只裝了 `curl`。
**影響**: `docker-compose build` 時 `pip install asyncpg` 會失敗。
**修正**:

```dockerfile
# 修改前 (Line 9-11)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 修改後
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
```

---

### 已知但不在 Step 1 範圍（後續 Step 處理）

| 項目 | 歸屬 | 說明 |
|------|------|------|
| `activity_log.py` 直接使用 `sqlite3` | **Step 2** | 整個檔案繞過 SQLAlchemy 直接用 `sqlite3.connect()`，需遷移到 ORM |
| 現有 SQLite 資料遺失 | **Step 2** | `backend/data/activity.db` (28KB) 和 `nexus.db` (40KB) 不會自動遷移 |
| Alembic 尚未設定 | **不在範圍** | 初期用 `create_all()` 即可，後續再加 |

**說明**: `activity_log.py` 的 SQLite 問題不會影響 Step 1 的 commit，因為 Step 1 只改基礎設施層。activity_log.py 本身有獨立的 SQLite 連線 (`backend/data/activity.db`)，和 `database.py` 的 engine 無關。它會在 Step 2 統一遷移。

---

## 修正計畫

1. 修正 `backend/Dockerfile` — 加入 `libpq-dev` + `gcc`
2. Commit + Push

---

## 最終判定

修正 Dockerfile 後即可 commit。
