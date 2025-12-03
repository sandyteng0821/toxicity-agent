# Database Schema & Query System

毒理資料版本控制與批次編輯追蹤系統。

---

## 📁 檔案結構

```
core/
└── database.py                 # SQLAlchemy models & methods

app/api/
├── routes_edit.py              # Single edit endpoints
└── routes_batchedit.py         # Batch edit endpoints
```

---

## 🗄️ Database Schema

### `ToxicityVersion` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `conversation_id` | String(100) | Item/Thread ID (索引) |
| `batch_id` | String(100) | Batch ID (索引, nullable) |
| `inci_name_track` | String(255) | INCI 名稱 (nullable) |
| `version` | Integer | 版本號 |
| `data` | Text | JSON 資料 (字串) |
| `modification_summary` | Text | 修改摘要 |
| `created_at` | DateTime | 建立時間 |
| `patch_operations` | Text | Patch 操作記錄 (nullable) |
| `is_batch_item` | Boolean | 是否為批次項目 |

---

## 🔑 ID 系統說明

| ID | 說明 | 用途 |
|----|------|------|
| `batch_id` | 整個批次請求的 ID | 查詢同一批次的所有修改 |
| `conversation_id` (item_id) | 每個 INCI 的 thread ID | 查詢特定 INCI 的修改歷史 |
| `inci_name_track` | INCI 名稱 | 按成分名稱篩選 |

### ID 關係圖

```
batch_id: "batch-001"
├── conversation_id: "thread-aaa" (INCI: COUMARIN)
│   ├── version 1: set inci_ori
│   └── version 2: update reference
├── conversation_id: "thread-bbb" (INCI: MENTHOL)
│   └── version 1: update NOAEL
└── conversation_id: "thread-ccc" (INCI: GLYCERIN)
    └── version 1: update DAP
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/edit/batch` | 批次編輯多個 INCI |
| GET | `/api/edit/batch/{batch_id}` | 用 batch_id 查詢 |
| GET | `/api/edit/batch/{item_id}` | 用 item_id 查詢 |
| GET | `/api/edit/inci/{inci_name}` | 用 INCI 名稱查詢 |

---

## 📋 使用方式

### 批次編輯請求

```bash
curl -X POST "http://localhost:8000/api/edit/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "edits": [
      {
        "inci_name": "COUMARIN",
        "instruction": "set inci_ori to Coumarin"
      },
      {
        "inci_name": "COUMARIN",
        "instruction": "Update reference title to PubChem - Coumarin"
      }
    ]
  }'
```

### 查詢 - 用 Batch ID

```bash
curl "http://localhost:8000/api/edit/batch/d381e0f0-8e22-4b23-ae74-9b9e6913f799"
```

### 查詢 - 用 INCI 名稱

```bash
curl "http://localhost:8000/api/edit/inci/COUMARIN"
```

---

## 📤 Response 格式

### Batch Edit Response

```json
{
  "batch_id": "d381e0f0-8e22-4b23-ae74-9b9e6913f799",
  "patch_success_data": [true, true],
  "fallback_used_data": [false, false],
  "updated_data": [
    { /* 第一次修改後的 JSON */ },
    { /* 第二次修改後的 JSON */ }
  ],
  "data_count": 2,
  "inci_thread_map": {
    "COUMARIN": "603e0ccf-9f15-4d80-bdc5-b6804d110641"
  }
}
```

### Query Response

```json
[
  {
    "id": 1,
    "item_id": "603e0ccf-9f15-4d80-bdc5-b6804d110641",
    "batch_id": "d381e0f0-8e22-4b23-ae74-9b9e6913f799",
    "inci_name": "COUMARIN",
    "version": 1,
    "summary": "[BATCH] INCI: COUMARIN | Success: True | ...",
    "timestamp": "2025-12-03T07:37:17.823091",
    "data": { /* JSON 資料 */ }
  }
]
```

---

## 🔧 Database Methods

### `ToxicityDB` Class

| Method | Description |
|--------|-------------|
| `save_version()` | 儲存一般版本 |
| `save_batch_item()` | 儲存批次編輯項目 |
| `get_current_version()` | 取得最新版本 |
| `get_modification_history()` | 取得修改歷史 |
| `get_modification_history_with_patches()` | 取得含 patch 的歷史 |
| `get_batch_items()` | 用 batch_id 查詢 |
| `get_by_inci_name()` | 用 INCI 名稱查詢 |

---

## 🔄 Batch Edit 流程

```
┌─────────────────────┐
│  POST /edit/batch   │
│  { edits: [...] }   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Generate batch_id  │
└──────────┬──────────┘
           ▼
    ┌──────┴──────┐
    │  For each   │
    │    edit     │◄────────────────┐
    └──────┬──────┘                 │
           ▼                        │
┌─────────────────────┐             │
│ Same INCI?          │             │
│ Yes → reuse item_id │             │
│ No  → new item_id   │             │
└──────────┬──────────┘             │
           ▼                        │
┌─────────────────────┐             │
│  graph.invoke()     │             │
│  (LangGraph)        │             │
└──────────┬──────────┘             │
           ▼                        │
┌─────────────────────┐             │
│  db.save_batch_item │             │
│  (store to DB)      │             │
└──────────┬──────────┘             │
           │                        │
           └────── next edit ───────┘
           ▼
┌─────────────────────┐
│  Return Response    │
│  (batch_id, map)    │
└─────────────────────┘
```

---

## 💡 注意事項

### 相同 INCI 累積修改

當同一個 batch 中有多個相同 INCI 的編輯：
- 共用同一個 `item_id` (thread_id)
- 後續修改會基於前一次的結果
- 修改會累積生效

### 資料庫重建

新增欄位後需要重建 DB：

```bash
rm -f data/*.db
make run
```

---

## 📝 相關文件

| 文件 | 說明 |
|------|------|
| `TOXICITY_MODULES_README.md` | NOAEL/DAP 生成模組 |
| `routes_edit.py` | 單一編輯 API |
| `routes_batchedit.py` | 批次編輯 API |
