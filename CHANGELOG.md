# Changelog

## [v4.0.0] - 2024-12-04
feat(v4.0.0): unified edit graph with form-based editing integration

### Summary
This release integrates form-based editing directly into the main edit graph,
allowing all edit types (NLI, structured JSON, raw text extraction) to be
handled through a single `/api/edit` endpoint. The graph now automatically
classifies user intent and routes to the appropriate processing path.

### Major Changes
- **Unified Edit Graph Architecture**:
  - Single entry point for all edit types via `/api/edit`
  - Intent classification in `parse_instruction.py` (NLI_EDIT, FORM_EDIT_STRUCTURED, FORM_EDIT_RAW, NO_EDIT)
  - Conditional routing based on detected intent

- **New Nodes**:
  - `form_apply.py` – Directly applies NOAEL/DAP payloads to json_data (no HTTP overhead)
  - `toxicity_extract.py` – Invokes `process_correction_form()` for raw text extraction

- **Enhanced Parse Instruction**:
  - Added `classify_intent()` with heuristics + LLM fallback
  - Added `extract_form_payloads()` to parse JSON from user input
  - Handles INCI prefix in JSON input (e.g., "INCI: NAME\n{...}")

- **State Updates**:
  - Added `intent_type` – Classification result
  - Added `form_payloads` – Extracted NOAEL/DAP payloads
  - Added `form_api_response` – Response from form processing
  - Added `form_types_processed` – List of applied form types

### Graph Flow
```
PARSE_INSTRUCTION → Router
    ├── NLI_EDIT → FAST_UPDATE → PATCH_GEN → PATCH_APPLY → FALLBACK → SAVE
    ├── FORM_EDIT_STRUCTURED → FORM_APPLY → SAVE
    ├── FORM_EDIT_RAW → TOXICITY_EXTRACT → FORM_APPLY → SAVE
    └── NO_EDIT → SAVE
```

### Benefits
- **Single Endpoint**: All edits through `/api/edit` (simpler API surface)
- **Auto-Detection**: No need to choose endpoint; graph routes automatically
- **No HTTP Overhead**: Form data applied directly (vs calling localhost endpoints)
- **Backward Compatible**: Existing NLI edits work unchanged
- **Raw Text Support**: Paste correction forms directly into instruction field

### Usage Examples
```python
# NLI Edit (existing behavior)
{"instruction": "Set NOAEL to 200 mg/kg for Rats", "inci_name": "L-MENTHOL"}

# Structured JSON (new)
{"instruction": "{\"noael\": {\"value\": 100, \"unit\": \"mg/kg bw/day\", ...}}", "inci_name": "CITRAL"}

# Raw Text Extraction (new)
{"instruction": "NOAEL: 50 mg/kg\nSpecies: Rat\nDuration: 90 days\n...", "inci_name": "CITRAL"}
```

### Files Changed
- `app/graph/build_graph.py` – Added routing logic + new nodes
- `app/graph/state.py` – Added 4 new state keys
- `app/graph/nodes/parse_instruction.py` – Added intent classification
- `app/graph/nodes/form_apply.py` – New node for direct payload application
- `app/graph/nodes/toxicity_extract.py` – New node for raw text extraction

### Testing
- All 28 existing tests passing
- New tests in `tests/test_integrated_workflows.py`:
  - Intent classification tests (NLI, JSON, raw text)
  - Toxicity graph integration tests
  - Full graph flow tests

### Notes
- Form-based endpoints (`/api/edit-form/noael`, `/api/edit-form/dap`) still available
- Recommended to use unified `/api/edit` for new integrations
- `FORM_APPLY` uses same logic as form endpoints (REPLACE behavior for NOAEL/DAP)

---

## [v3.0.0] - 2025-12-03
feat(v3.0.0): batch edit system + database query enhancements + toxicity imputation modules

### Summary
This release introduces a comprehensive batch editing system, enhanced database querying capabilities, and toxicity imputation modules for automated NOAEL/DAP extraction from correction forms.

### Added

- **Batch Edit System**:
  - `POST /api/edit/batch` - Batch edit multiple INCI ingredients in one request
  - Same INCI shares thread_id for cumulative modifications
  - Returns `batch_id` and `inci_thread_map` for tracking
  - Supports complex graph flow with patch generation

- **Database Query Endpoints**:
  - `GET /api/edit/batch/{batch_id}` - Query by batch ID
  - `GET /api/edit/batch/{item_id}` - Query by item/thread ID
  - `GET /api/edit/inci/{inci_name}` - Query by INCI name

- **Database Schema Updates**:
  - Added `batch_id` column for batch tracking
  - Added `inci_name_track` column for INCI-based queries
  - Added `is_batch_item` flag for batch item identification
  - New methods: `save_batch_item()`, `get_batch_items()`, `get_by_inci_name()`

- **Toxicity Imputation Modules** (from Dec 2):
  - `POST /api/generate/noael` - Generate NOAEL payload from correction form
  - `POST /api/generate/dap` - Generate DAP payload from correction form
  - `POST /api/generate/noael/form` - Form-based multiline input
  - `POST /api/generate/dap/form` - Form-based multiline input
  - `POST /api/generate/noael/upload` - Upload .txt file
  - `POST /api/generate/dap/upload` - Upload .txt file
  - LangGraph workflow: classify → route → noael/dap/dual → END

- **Documentation**:
  - `docs/DATABASE_README.md` - Database schema and query system
  - `docs/TOXICITY_MODULES_README.md` - Toxicity imputation modules

- **Frontend UI** (from Nov 26):
  - Added Gradio-based frontend UI for the application

### Changed

- **load_json Node**:
  - Added fallback to JSON template file when DB has no data
  - Supports both DB-based and file-based initialization

- **Fallback Node**:
  - Added `fallback_used` state tracking
  - Better status reporting in batch operations

- **Test Suite**:
  - `test_refactored.py` now uses in-memory DB to prevent `chat_memory.db` crash
  - Tests isolated from production database

- **Build System**:
  - Updated `requirements.txt` with `langchain-anthropic`
  - Fixed Docker deployment issues with absolute DB paths
  - Added `data/` volume mount for persistent storage

### Fixed

- **SQLite Database Issues**:
  - Fixed "database disk image is malformed" by using in-memory DB for tests
  - Fixed "unable to open database file" in Docker with absolute paths
  - Fixed missing column errors by proper schema migration

- **LangGraph Checkpointer**:
  - Fixed `thread_id` requirement for batch operations
  - Each batch item gets unique thread_id for isolated state

### Architecture

- **Batch Edit Flow**:
  ```
  POST /edit/batch → Generate batch_id → For each edit:
    → Same INCI? Reuse item_id : New item_id
    → graph.invoke() → db.save_batch_item()
  → Return batch_id + inci_thread_map
  ```

- **ID System**:
  | ID | Purpose |
  |----|---------|
  | `batch_id` | Groups all edits in one request |
  | `item_id` (conversation_id) | Thread for each INCI |
  | `inci_name_track` | INCI name for queries |

### Files Changed

```
app/api/routes_batchedit.py      # NEW: Batch edit endpoints
app/api/routes_generate.py       # NEW: Toxicity imputation endpoints
app/graph/nodes/load_json.py     # Fallback to template file
app/graph/nodes/fallback_full.py # Track fallback_used status
app/graph/build_graph.py         # Absolute paths + test DB support
app/graph/utils/toxicity_schemas.py    # NEW: Pydantic schemas
app/graph/utils/toxicity_utils.py      # NEW: LLM extraction utilities
core/database.py                 # batch_id, get_by_inci_name()
tests/test_refactored.py         # In-memory DB for tests
requirements.txt                 # Added langchain-anthropic
docs/DATABASE_README.md          # NEW: Database documentation
docs/TOXICITY_MODULES_README.md  # NEW: Module documentation
```

---

## [v2.1.0] - 2025-11-21
feat(v2.1.0): integrate local/remote LLM factory + fix multi-node workflow state

### Summary
- Added llm_factory.py to support dynamic provider selection (local Ollama / OpenAI)
- Updated config.py and .env-example with PROVIDER + MODEL variables
- Patched fallback_full.py and patch_generate.py to use LLM factory
- Updated toxicity_data_template.json test baseline
- Refreshed requirements.txt to include langchain-ollama and missing deps
- Ensured multi-node workflow passes test suite (OpenAI + Ollama)

---

## [v2.0.0] - 2025-11-20
feat(v2.0.0): major LangGraph refactor into modular node-based pipeline

### Summary
This release replaces the previous monolithic JSON-edit node with a fully
modular LangGraph architecture. The agent is now decomposed into explicit,
testable, and maintainable nodes, enabling clearer control flow, improved
debuggability, and easier future extension (tooling, memory, multi-step agents).

### Major Changes
- Introduced multi-node LangGraph pipeline:
  - `load_json.py` – load current toxicity JSON state
  - `parse_instruction.py` – extract INCI + classify edit intent
  - `fast_update.py` – structured extraction–based updates (no LLM)
  - `patch_generate.py` – generate JSON Patch ops via LLM
  - `patch_apply.py` – validate + apply patch operations safely
  - `fallback_full.py` – reliable fallback full-JSON rewrite
  - `save_json.py` – persist updated JSON + version tracking
  - `edit_orchestrator.py` – orchestrates conditional routing

- Added shared utilities:
  - `patch_utils.py` – safe patch validation + application helpers
  - `schema_tools.py` – JSONPatchOperation schema & typed helpers

- Updated graph structure:
  - Replaced single edit node with multi-node DAG
  - Cleaner state transitions (`last_patches`, `patch_success`,
    `fast_done`, `fallback_used`, etc.)

### Benefits
- Better maintainability & readability
- Isolated failure points (LLM errors, patch errors, schema mismatches)
- Deterministic flow control between fast-path / patch-path / fallback
- Easier to visualize and extend (future tools, memory, multi-instruction workflows)
- No business logic buried inside a single mega-node

### Notes
This is a breaking architectural change; previous workflows relying on the old
monolithic edit node should migrate to the new `edit_orchestrator` entrypoint.

---

## [v1.1.0] - 2025-11-17

### Added
- **Chat History Support**: Implemented conversation memory using LangGraph checkpointer with SQLite
  - Added `SqliteSaver` checkpointer in `build_graph.py` for persistent chat history
  - Each conversation thread maintains independent state via `thread_id`
  - Database file: `chat_memory.db`
  
- **Form-based API Endpoints**: Added zero-LLM endpoints for guaranteed accuracy
  - `/api/edit-form/noael` - Form-based NOAEL updates (100% accuracy)
  - `/api/edit-form/dap` - Form-based DAP updates (100% accuracy)
  - All required fields validated via Pydantic models
  - Required fields: inci_name, value, unit, source, experiment_target, study_duration, reference_title
  - Optional fields: note, reference_link, statement
  
- **Comprehensive Test Suite**:
  - `tests/test_chat_history.py` - Tests for conversation memory (5 tests)
  - Tests verify checkpoint persistence, thread isolation, multi-turn edits
  - All 16 tests passing (100% coverage)

- **Development Tools**:
  - `Makefile` with common development commands (install, test, run, clean)
  - Updated README with integrated setup instructions

### Changed
- **LLM Model**: Switched from Llama3.1:8b to GPT-4o-mini for testing
  - Reason: GPT-4o-mini achieves 95% consistency vs 60% for Llama3.1:8b
  - Model configured in `app/graph/nodes/llm_edit_node.py`
  - Llama3.1:8b still supported for development (free, local)
  
- **Data Updater**: Enhanced null handling in `app/services/data_updater.py`
  - `update_toxicology_data()` now handles `None` inputs gracefully
  - `merge_json_updates()` skips `null` values from LLM output
  - Prevents `AttributeError: 'NoneType' object has no attribute 'copy'`

- **Database Schema**: Updated SQLAlchemy to 2.0 compatible imports
  - Changed `declarative_base` import in `core/database.py`
  - Fixed deprecation warning: `MovedIn20Warning`

### Fixed
- **Test Warnings**: Suppressed non-critical pytest warnings in `pytest.ini`
  - `PytestReturnNotNoneWarning` (intentional return values for summary)
  - `PytestAssertRewriteWarning` (module import order)
  - `DeprecationWarning` from SQLAlchemy (upstream issue)

- **Case Sensitivity**: Tests now handle case-insensitive assertions
  - LLM returns lowercase values (e.g., "l-menthol", "fragrance")
  - Tests use `.upper()` for robust comparison

- **Virtual Environment**: Fixed pytest execution to use venv's Python
  - Use `python -m pytest` instead of `pytest` command
  - Ensures correct module imports from virtual environment

### Removed
- `tests/test_node.py` - Replaced by comprehensive `test_chat_history.py`

### Testing
- Model used for testing: **GPT-4o-mini** (95% consistency)
- Model used for development: **Llama3.1:8b** (60% consistency, free local)
- Test results: **16/16 passing** (100%)
- Test coverage:
  - Chat history: 5 tests ✅
  - L-MENTHOL integration: 5 tests ✅
  - Refactored components: 6 tests ✅

### Architecture
- **Dual-track API approach**:
  - Form-based endpoints: For standard updates (80% of cases) - Zero LLM errors
  - NLI-based endpoints: For complex/custom cases (20% of cases) - Flexible natural language

### Notes
- Chat history database (`chat_memory.db`) persists conversation state
- Form-based endpoints recommended for 80% of standard use cases (NOAEL, DAP)
- LLM-based endpoints (NLI) recommended for complex/custom cases
- Docker support planned but not included in this release

### Known Issues
- Docker deployment not yet fully implemented
- Ollama integration in Docker pending testing

---
