# Unified Edit Graph Integration

## Overview

The edit graph supports three input types through a single `/api/edit` endpoint:

| Intent | Input Type | Example |
|--------|------------|---------|
| `NLI_EDIT` | Natural language | "Set NOAEL to 200 mg/kg for Rats" |
| `FORM_EDIT_STRUCTURED` | JSON payload | `{"noael": {"value": 100, ...}}` |
| `FORM_EDIT_RAW` | Raw pasted form | "NOAEL: 50\nSpecies: Rat\n..." |

## Architecture

```
PARSE_INSTRUCTION (+ intent classification)
         │
         ├── NLI_EDIT ──────────► FAST_UPDATE → PATCH_GEN → PATCH_APPLY → FALLBACK ─┐
         │                                                                          │
         ├── FORM_EDIT_STRUCTURED ──────────────────────► FORM_APPLY ───────────────┤
         │                                                     ▲                    │
         ├── FORM_EDIT_RAW ──► TOXICITY_EXTRACT ───────────────┘                    │
         │                                                                          │
         └── NO_EDIT ───────────────────────────────────────────────────────────────┤
                                                                                    ▼
                                                                                  SAVE
```

## Key Components

### 1. Intent Classification (`parse_instruction.py`)

```python
def classify_intent(user_input: str) -> str:
    # Priority order:
    # 1. JSON detection → FORM_EDIT_STRUCTURED
    # 2. NLI patterns (change/set/update/delete) → NLI_EDIT
    # 3. Raw toxicity patterns (NOAEL:, Species:) → FORM_EDIT_RAW
    # 4. Questions → NO_EDIT
    # 5. LLM fallback for ambiguous cases
```

### 2. Form Apply (`form_apply.py`)

Directly modifies `json_data` matching `/api/edit-form/*` behavior:
- NOAEL/DAP entries **replace** existing (not append)
- `repeated_dose_toxicity`/`percutaneous_absorption` entries **append**

### 3. Toxicity Extract (`toxicity_extract.py`)

Invokes existing `process_correction_form()` for raw text → structured payload conversion.

## State Keys

```python
# Added to JSONEditState
intent_type: Optional[str]           # NLI_EDIT, FORM_EDIT_STRUCTURED, FORM_EDIT_RAW, NO_EDIT
form_payloads: Optional[Dict]        # {"noael": {...}, "dap": {...}}
form_api_response: Optional[Dict]    # Processing result
form_types_processed: Optional[List] # ["noael", "dap"]
```

## Routing Logic

```python
def route_by_intent(state):
    intent = state.get("intent_type", "NLI_EDIT")
    
    if intent == "FORM_EDIT_STRUCTURED":
        return "form_apply"
    elif intent == "FORM_EDIT_RAW":
        return "toxicity_extract"
    elif intent == "NO_EDIT":
        return "save"
    return "nli_path"  # Default
```

## API Usage

All examples use `POST /api/edit`:

```json
// NLI Edit
{
  "instruction": "Set NOAEL to 200 mg/kg bw/day for Rats",
  "inci_name": "L-MENTHOL"
}

// Structured JSON
{
  "instruction": "{\"noael\": {\"value\": 100, \"unit\": \"mg/kg bw/day\", \"source\": \"ECHA\", \"experiment_target\": \"Rats\", \"study_duration\": \"2y\", \"reference_title\": \"ECHA Study\"}}",
  "inci_name": "CITRAL"
}

// Raw Text (auto-extracted)
{
  "instruction": "INCI: CITRAL\nNOAEL: 100 mg/kg bw/day\nSpecies: Rats\nDuration: 2y\nSource: ECHA",
  "inci_name": "CITRAL"
}
```

## File Structure

```
app/graph/
├── build_graph.py          # Routing logic
├── state.py                # +4 state keys
└── nodes/
    ├── parse_instruction.py  # Intent classification
    ├── form_apply.py         # Direct payload application
    └── toxicity_extract.py   # Raw text → payload
```
