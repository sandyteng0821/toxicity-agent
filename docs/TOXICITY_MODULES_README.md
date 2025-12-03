# Toxicity Imputation Modules

從毒理修正單 (Correction Form) 自動生成 NOAEL / DAP JSON payload。

---

## 📁 檔案結構

```
app/
├── api/
│   └── routes_generate.py          # API endpoints
├── graph/
│   ├── nodes/
│   │   └── toxicity_imputation_nodes.py  # LangGraph nodes
│   ├── utils/
│   │   ├── toxicity_schemas.py     # Pydantic schemas
│   │   └── toxicity_utils.py       # LLM extraction utilities
│   └── toxicity_graph.py           # LangGraph workflow
└── main.py                         # Router registration
```

---

## 🔌 API Endpoints

| Method | Endpoint | Input | Description |
|--------|----------|-------|-------------|
| POST | `/api/generate/noael` | JSON body | 從 JSON 輸入生成 NOAEL payload |
| POST | `/api/generate/dap` | JSON body | 從 JSON 輸入生成 DAP payload |
| POST | `/api/generate/noael/form` | Form data | 支援多行文字貼上 (NOAEL) |
| POST | `/api/generate/dap/form` | Form data | 支援多行文字貼上 (DAP) |
| POST | `/api/generate/noael/upload` | File (.txt) | 上傳文字檔生成 NOAEL payload |
| POST | `/api/generate/dap/upload` | File (.txt) | 上傳文字檔生成 DAP payload |

---

## 📋 使用方式

### 方式 1：JSON Body

```bash
curl -X POST "http://localhost:8000/api/generate/noael" \
  -H "Content-Type: application/json" \
  -d '{
    "correction_form_text": "INCI: COUMARIN\nNOAEL: 138.3 mg/kg bw/day\nSource: ECHA..."
  }'
```

### 方式 2：Form Data (多行文字)

```bash
curl -X POST "http://localhost:8000/api/generate/noael/form" \
  -F "correction_form_text=INCI: COUMARIN
NOAEL: 138.3 mg/kg bw/day
Source: ECHA
..."
```

### 方式 3：上傳文字檔

```bash
curl -X POST "http://localhost:8000/api/generate/noael/upload" \
  -F "file=@correction_form.txt"
```

---

## 📤 Response 格式

```json
{
  "task_type": "noael",
  "inci_name": "COUMARIN",
  "payload": {
    "conversation_id": "uuid",
    "inci_name": "COUMARIN",
    "value": 138.3,
    "unit": "mg/kg bw/day",
    "experiment_target": "Mice",
    "source": "ECHA",
    "study_duration": "90-day",
    "note": "...",
    "reference_title": "...",
    "reference_link": "...",
    "statement": "..."
  },
  "json_string": "{ ... }",
  "api_endpoint": "/api/edit-form/noael"
}
```

---

## 🔧 模組說明

### `toxicity_schemas.py`

Pydantic schemas for structured LLM output.

| Schema | Description |
|--------|-------------|
| `NOAELUpdateSchema` | NOAEL 資料結構 (value, unit, source, note...) |
| `DAPUpdateSchema` | DAP 資料結構 (value, unit, source, note...) |
| `ToxicityTaskClassification` | 任務分類 (noael / dap / both / unknown) |

### `toxicity_utils.py`

LLM extraction utilities.

| Function | Description |
|----------|-------------|
| `_generate_noael_with_llm()` | 使用 LLM 從文字提取 NOAEL 資料 |
| `_generate_dap_with_llm()` | 使用 LLM 從文字提取 DAP 資料 |
| `_classify_task_with_llm()` | 分類任務類型 |
| `build_noael_payload()` | 建立 NOAEL API payload |
| `build_dap_payload()` | 建立 DAP API payload |

### `toxicity_imputation_nodes.py`

LangGraph nodes for workflow integration.

| Node | Description |
|------|-------------|
| `toxicity_classify_node` | 分類修正單任務類型 |
| `noael_generate_node` | 生成 NOAEL payload |
| `dap_generate_node` | 生成 DAP payload |
| `toxicity_dual_generate_node` | 同時生成 NOAEL + DAP |
| `toxicity_error_node` | 錯誤處理 |

### `toxicity_graph.py`

LangGraph workflow definition.

```
修正單 → classify → route → noael/dap/dual → END
```

---

## 🔄 Workflow 流程

```
┌─────────────────┐
│  修正單文字輸入  │
└────────┬────────┘
         ▼
┌─────────────────┐
│   classify_node │  判斷 NOAEL / DAP / both
└────────┬────────┘
         ▼
    ┌────┴────┐
    │  route  │
    └────┬────┘
         │
   ┌─────┼─────┬─────┐
   ▼     ▼     ▼     ▼
noael   dap   dual  error
   │     │     │     │
   └─────┴─────┴─────┘
         │
        END
```

---

## 🛠️ 整合到 main.py

```python
# app/main.py
from app.api.routes_generate import router as toxicity_form_router

app.include_router(toxicity_form_router)
```

---

## 📝 相關 Endpoints (已存在)

生成的 payload 可直接用於以下 endpoints：

| Endpoint | Description |
|----------|-------------|
| `POST /api/edit-form/noael` | 更新 NOAEL 資料到資料庫 |
| `POST /api/edit-form/dap` | 更新 DAP 資料到資料庫 |

### 完整流程

```
修正單 → /api/generate/noael/upload → 取得 payload → /api/edit-form/noael → 資料庫更新
```
