# Step-by-Step Refactoring Guide for Toxicity Agent

## 🎯 Goal
Transform your monolithic `agent_graph_toxicity.py` into a clean, maintainable structure without breaking existing functionality.

---

## 📋 Refactoring Strategy

**Approach**: Incremental refactoring with testing at each step
- ✅ Each phase is independent and testable
- ✅ Your API keeps working throughout
- ✅ Easy to rollback if something breaks

---

## Phase 1: Setup New Structure (15 mins)

### Step 1.1: Create Directory Structure

```bash
# From your project root (/Users/sandyteng/code/workspace/toxicity-agent/)
mkdir -p app/graph/nodes
mkdir -p app/services
mkdir -p app/api
mkdir -p tests

# Create __init__.py files
touch app/__init__.py
touch app/graph/__init__.py
touch app/graph/nodes/__init__.py
touch app/services/__init__.py
touch app/api/__init__.py
```

### Step 1.2: Create Config File

**File**: `app/config.py`

```python
"""
Global configuration for the toxicity agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# File paths
JSON_TEMPLATE_PATH = DATA_DIR / "toxicity_data_template.json"
EDITOR_JSON_PATH = DATA_DIR / "editor.json"

# LLM configuration
DEFAULT_LLM_MODEL = "llama3.1:8b"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Toxicology field names
TOXICOLOGY_FIELDS = [
    "acute_toxicity",
    "skin_irritation",
    "skin_sensitization",
    "ocular_irritation",
    "phototoxicity",
    "repeated_dose_toxicity",
    "percutaneous_absorption",
    "ingredient_profile"
]

METRIC_FIELDS = ["NOAEL", "DAP"]

# Template structure
JSON_TEMPLATE = {
    "inci": "INCI_NAME",
    "cas": [],
    "isSkip": False,
    "category": "OTHERS",
    **{field: [] for field in TOXICOLOGY_FIELDS},
    **{field: [] for field in METRIC_FIELDS},
    "inci_ori": "inci_name"
}
```

**Why this helps**: 
- Centralized configuration
- Easy to change paths/models
- Environment-specific settings (dev/prod)

---

## Phase 2: Extract State Definition (10 mins)

### Step 2.1: Create State Module

**File**: `app/graph/state.py`

```python
"""
State definitions for the LangGraph workflow
"""
from typing import Dict, Any, TypedDict, List, Optional, Tuple

class JSONEditState(TypedDict):
    """State for JSON editing workflow"""
    json_data: Dict[str, Any]
    user_input: str
    response: str
    current_inci: str
    edit_history: Optional[List[Tuple[str, str]]]  # (instruction, timestamp)
    error: Optional[str]

class ToxicologyData(TypedDict):
    """Structure for toxicology data entries"""
    data: List[str]
    reference: Dict[str, Optional[str]]
    replaced: Dict[str, str]
    source: str
    statement: Optional[str]
```

**Migration tip**: This is a direct copy from your original code, just isolated.

---

## Phase 3: Extract Services (30 mins)

### Step 3.1: JSON I/O Service

**File**: `app/services/json_io.py`

```python
"""
JSON file I/O operations
"""
import json
import os
from typing import Dict, Any
from pathlib import Path

from app.config import JSON_TEMPLATE, JSON_TEMPLATE_PATH

def read_json(filepath: str = None) -> Dict[str, Any]:
    """
    Read JSON file with error handling
    
    Args:
        filepath: Path to JSON file (defaults to template path)
        
    Returns:
        Dict containing JSON data
    """
    if filepath is None:
        filepath = str(JSON_TEMPLATE_PATH)
    
    try:
        if not os.path.exists(filepath):
            # Create template if doesn't exist
            write_json(JSON_TEMPLATE, filepath)
            return JSON_TEMPLATE

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
            
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {filepath}: {e}")
        return {"error": f"Failed to read JSON: {str(e)}"}

def write_json(data: Dict[str, Any], filepath: str = None) -> bool:
    """
    Write JSON file with error handling
    
    Args:
        data: Data to write
        filepath: Path to write to (defaults to template path)
        
    Returns:
        True if successful, False otherwise
    """
    if filepath is None:
        filepath = str(JSON_TEMPLATE_PATH)
    
    try:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ JSON successfully saved to {filepath}")
        return True
        
    except IOError as e:
        print(f"❌ Error writing {filepath}: {e}")
        return False

def validate_json_structure(data: Dict[str, Any]) -> bool:
    """
    Validate that JSON has required fields
    
    Args:
        data: JSON data to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["inci", "cas", "category"]
    return all(field in data for field in required_fields)
```

**Test it immediately**:
```python
# In Python shell or temporary test file
from app.services.json_io import read_json, write_json

data = read_json()
print(data.get("inci"))  # Should print "INCI_NAME" or your current value
```

---

### Step 3.2: Text Processing Service

**File**: `app/services/text_processing.py`

```python
"""
Text processing utilities for toxicology data extraction
"""
import re
import json
from typing import Dict, List

def extract_inci_name(text: str) -> str:
    """
    Extract INCI name from instruction text
    
    Args:
        text: User instruction containing INCI name
        
    Returns:
        Extracted INCI name or empty string
    """
    inci_match = re.search(r'inci_name\s*=\s*["\']?([^"\'\n]+)["\']?', text)
    if inci_match:
        return inci_match.group(1)
    
    # Try alternative pattern
    inci_match = re.search(r'INCI:\s*([^\n]+)', text)
    if inci_match:
        return inci_match.group(1).strip()
    
    return ""

def extract_toxicology_sections(text: str) -> Dict[str, List[Dict]]:
    """
    Extract structured toxicology data from instruction text
    
    Args:
        text: Instruction text potentially containing JSON sections
        
    Returns:
        Dict mapping section names to data arrays
    """
    sections = {}

    patterns = {
        'acute_toxicity': r'"acute_toxicity":\s*\[(.*?)\]',
        'skin_irritation': r'"skin_irritation":\s*\[(.*?)\]',
        'skin_sensitization': r'"skin_sensitization":\s*\[(.*?)\]',
        'ocular_irritation': r'"ocular_irritation":\s*\[(.*?)\]',
        'phototoxicity': r'"phototoxicity":\s*\[(.*?)\]',
        'repeated_dose_toxicity': r'"repeated_dose_toxicity":\s*\[(.*?)\]',
        'percutaneous_absorption': r'"percutaneous_absorption":\s*\[(.*?)\]',
        'ingredient_profile': r'"ingredient_profile":\s*\[(.*?)\]',
        'NOAEL': r'"NOAEL":\s*\[(.*?)\]',
        'DAP': r'"DAP":\s*\[(.*?)\]'
    }

    for section, pattern in patterns.items():
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            try:
                json_str = f"[{matches[0]}]"
                data = json.loads(json_str)
                sections[section] = data
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse {section} as JSON")
                continue

    return sections

def clean_llm_json_output(content: str) -> str:
    """
    Clean LLM output to extract valid JSON
    
    Args:
        content: Raw LLM output
        
    Returns:
        Cleaned JSON string
    """
    clean_content = content.strip()

    # Remove leading text before JSON
    json_start = -1
    for i, char in enumerate(clean_content):
        if char in ['{', '[']:
            json_start = i
            break
    
    if json_start > 0:
        clean_content = clean_content[json_start:]

    # Remove markdown code blocks
    if clean_content.startswith("```json"):
        clean_content = clean_content[7:]
    elif clean_content.startswith("```"):
        clean_content = clean_content[3:]
        
    if clean_content.endswith("```"):
        clean_content = clean_content[:-3]
    
    clean_content = clean_content.strip()

    # Remove trailing text after JSON
    json_end = -1
    for i in range(len(clean_content) - 1, -1, -1):
        if clean_content[i] in ['}', ']']:
            json_end = i + 1
            break
    
    if json_end > 0:
        clean_content = clean_content[:json_end]

    return clean_content
```

---

### Step 3.3: Data Update Service

**File**: `app/services/data_updater.py`

```python
"""
Logic for updating toxicology data structures
"""
from typing import Dict, List, Any

def update_toxicology_data(
    current_data: List[Dict], 
    new_data: List[Dict]
) -> List[Dict]:
    """
    Update toxicology data by merging new entries with existing
    
    Args:
        current_data: Existing data array
        new_data: New entries to add/merge
        
    Returns:
        Updated data array
    """
    updated_data = current_data.copy()

    for new_entry in new_data:
        # Check if similar entry exists (same source and reference title)
        existing_index = -1
        for i, existing_entry in enumerate(updated_data):
            if (existing_entry.get('source') == new_entry.get('source') and
                existing_entry.get('reference', {}).get('title') == 
                new_entry.get('reference', {}).get('title')):
                existing_index = i
                break

        if existing_index >= 0:
            # Update existing entry
            updated_data[existing_index].update(new_entry)
        else:
            # Add new entry
            updated_data.append(new_entry)

    return updated_data

def fix_common_llm_errors(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix common mistakes LLMs make in JSON structure
    
    Args:
        updates: Raw updates from LLM
        
    Returns:
        Corrected updates
    """
    corrected = updates.copy()
    
    # Fix 1: INCI → inci
    if "INCI" in corrected and "inci" not in corrected:
        print("⚠️ Fixing: INCI → inci")
        corrected["inci"] = corrected.pop("INCI")
    
    # Fix 2: Unnest toxicology object
    if "toxicology" in corrected:
        print("⚠️ Fixing: unnesting toxicology")
        toxicology = corrected.pop("toxicology")
        corrected.update(toxicology)
    
    # Fix 3: Remove placeholder arrays
    for key, value in list(corrected.items()):
        if isinstance(value, list) and len(value) == 1 and value[0] == "...":
            print(f"⚠️ Removing placeholder for {key}")
            del corrected[key]
    
    return corrected

def merge_json_updates(
    base_json: Dict[str, Any], 
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge updates into base JSON with smart array handling
    
    Args:
        base_json: Current JSON structure
        updates: Updates to apply
        
    Returns:
        Merged JSON
    """
    from app.config import TOXICOLOGY_FIELDS
    
    merged = base_json.copy()
    updates = fix_common_llm_errors(updates)
    
    for key, value in updates.items():
        if key == "inci":
            merged["inci"] = value
            merged["inci_ori"] = value
            print(f"✅ Updated inci: {value}")
            
        elif key in merged:
            if isinstance(value, list) and value:
                # Toxicology fields: append
                if key in TOXICOLOGY_FIELDS:
                    merged[key] = update_toxicology_data(merged[key], value)
                    print(f"✅ Appended to {key}: {len(value)} entries")
                else:
                    # Metric fields (NOAEL, DAP): replace
                    merged[key] = value
                    print(f"✅ Replaced {key}: {len(value)} entries")
            else:
                merged[key] = value
                print(f"✅ Updated {key}")
        else:
            merged[key] = value
            print(f"✅ Added new field: {key}")
    
    return merged
```

---

## Phase 4: Extract Graph Nodes (45 mins)

### Step 4.1: LLM Edit Node

**File**: `app/graph/nodes/llm_edit_node.py`

```python
"""
LLM node for processing toxicology edit instructions
"""
import json
from langchain_ollama import ChatOllama

from app.config import DEFAULT_LLM_MODEL
from app.graph.state import JSONEditState
from app.services.text_processing import (
    extract_inci_name,
    extract_toxicology_sections,
    clean_llm_json_output
)
from app.services.data_updater import merge_json_updates

def llm_edit_node(state: JSONEditState) -> JSONEditState:
    """
    Process user input and update JSON using LLM
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with modified JSON data
    """
    llm = ChatOllama(model=DEFAULT_LLM_MODEL)
    
    # Extract INCI name
    current_inci = extract_inci_name(state["user_input"])
    if not current_inci:
        current_inci = state["json_data"].get("inci", "INCI_NAME")
    state["current_inci"] = current_inci
    
    # Try structured data extraction first
    toxicology_sections = extract_toxicology_sections(state["user_input"])
    
    if toxicology_sections:
        # Direct update without LLM
        updated_json = state["json_data"].copy()
        from app.services.data_updater import update_toxicology_data
        
        for section, data in toxicology_sections.items():
            if section in updated_json:
                updated_json[section] = update_toxicology_data(
                    updated_json[section], 
                    data
                )
        
        state["json_data"] = updated_json
        state["response"] = f"✅ Updated toxicology data for {current_inci}"
        return state
    
    # Use LLM for natural language processing
    prompt = _build_llm_prompt(state["json_data"], state["user_input"], current_inci)
    
    try:
        result = llm.invoke(prompt)
        state["response"] = result.content
        
        # Parse and merge updates
        clean_content = clean_llm_json_output(result.content)
        print(f"DEBUG: Cleaned JSON (first 500 chars):\n{clean_content[:500]}")
        
        updates = json.loads(clean_content)
        merged_json = merge_json_updates(state["json_data"], updates)
        
        state["json_data"] = merged_json
        state["response"] = f"✅ Successfully updated {list(updates.keys())} for {current_inci}"
        
    except json.JSONDecodeError as e:
        error_msg = f"⚠️ LLM output was not valid JSON: {str(e)}"
        state["response"] = error_msg
        state["error"] = error_msg
        print(error_msg)
    
    return state

def _build_llm_prompt(json_data: dict, user_input: str, current_inci: str) -> str:
    """
    Build the prompt for LLM processing
    
    Args:
        json_data: Current JSON structure
        user_input: User's instruction
        current_inci: Current ingredient name
        
    Returns:
        Formatted prompt string
    """
    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
    
    return f"""You are a toxicology data specialist for cosmetic ingredients. Update JSON for INCI: {current_inci}

Current JSON Structure:
{json_str}

User Instruction:
{user_input}

COMMON MODIFICATION TYPES:

TYPE 1 - Toxicology Data Addition:
- Add complete entry to toxicology array
- Required fields: reference, data, source, statement, replaced
- Action: Return ONLY the new entry to append

TYPE 2 - DAP Update:
- Update "DAP" array with new value
- Update "percutaneous_absorption" with supporting data
- Return: {{"DAP": [...], "percutaneous_absorption": [...]}}

TYPE 3 - NOAEL Update:
- Update "NOAEL" array with new value
- Update "repeated_dose_toxicity" with supporting data
- Return: {{"NOAEL": [...], "repeated_dose_toxicity": [...]}}

CRITICAL RULES:
1. Return ONLY the fields that need updating
2. Do NOT use [...] or "..." placeholders
3. Do NOT return entire JSON - only changed fields
4. Field names must be lowercase ("inci", not "INCI")
5. Return valid JSON only, no explanations

Now analyze and return ONLY the fields to update with COMPLETE data:
"""
```

---

### Step 4.2: Validation Node (Optional but Recommended)

**File**: `app/graph/nodes/validation_node.py`

```python
"""
Validation node for checking input/output quality
"""
from app.graph.state import JSONEditState

def validate_input_node(state: JSONEditState) -> JSONEditState:
    """
    Validate user input before processing
    
    Args:
        state: Current workflow state
        
    Returns:
        State with validation flag
    """
    if not state["user_input"].strip():
        state["error"] = "Empty input"
        return state
    
    # Add more validation as needed
    return state

def validate_output_node(state: JSONEditState) -> JSONEditState:
    """
    Validate LLM output and JSON structure
    
    Args:
        state: Current workflow state
        
    Returns:
        State with validation results
    """
    from app.services.json_io import validate_json_structure
    
    if not validate_json_structure(state["json_data"]):
        state["error"] = "Invalid JSON structure after update"
    
    return state
```

---

### Step 4.3: Build Graph

**File**: `app/graph/build_graph.py`

```python
"""
LangGraph workflow construction
"""
from langgraph.graph import StateGraph, END

from app.graph.state import JSONEditState
from app.graph.nodes.llm_edit_node import llm_edit_node

def build_graph():
    """
    Build and compile the toxicology editing workflow
    
    Returns:
        Compiled LangGraph application
    """
    graph = StateGraph(JSONEditState)
    
    # Add nodes
    graph.add_node("edit", llm_edit_node)
    
    # Set entry point
    graph.set_entry_point("edit")
    
    # Add edges
    graph.add_conditional_edges(
        "edit",
        _should_continue,
        {
            "end": END
        }
    )
    
    return graph.compile()

def _should_continue(state: JSONEditState) -> str:
    """
    Determine if workflow should continue
    
    Args:
        state: Current state
        
    Returns:
        "end" to finish workflow
    """
    return "end"

def view_graph(save_path: str = "graph_plot.png", display_image: bool = True):
    """
    Visualize the workflow graph
    
    Args:
        save_path: Path to save PNG
        display_image: Whether to display inline (Jupyter)
        
    Returns:
        PNG image data
    """
    app = build_graph()
    png_data = app.get_graph().draw_mermaid_png()
    
    with open(save_path, "wb") as f:
        f.write(png_data)
    print(f"✅ Graph saved to: {save_path}")
    
    if display_image:
        try:
            from IPython.display import Image, display
            display(Image(png_data))
        except ImportError:
            print(f"⚠️ IPython not available. Open {save_path} to view graph.")
    
    return png_data
```

---

## Phase 5: Refactor API (20 mins)

### Step 5.1: Create API Routes

**File**: `app/api/routes_edit.py`

```python
"""
API routes for toxicology editing
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.graph.build_graph import build_graph
from app.services.json_io import read_json, write_json
from app.config import JSON_TEMPLATE, JSON_TEMPLATE_PATH

router = APIRouter(prefix="/api", tags=["edit"])
graph = build_graph()

class EditRequest(BaseModel):
    """Request model for edit endpoint"""
    instruction: str
    inci_name: Optional[str] = None

class EditResponse(BaseModel):
    """Response model for edit endpoint"""
    inci: str
    updated_json: dict
    raw_response: str

@router.post("/edit", response_model=EditResponse)
async def edit_json(req: EditRequest):
    """
    Edit toxicology JSON based on natural language instruction
    
    Args:
        req: Edit request containing instruction and optional INCI name
        
    Returns:
        Updated JSON and processing details
    """
    try:
        current_json = read_json()
        
        # Prepare user input
        user_input = req.instruction
        if req.inci_name:
            user_input = f"INCI: {req.inci_name}\n{user_input}"
        
        # Run graph
        result = graph.invoke({
            "json_data": current_json,
            "user_input": user_input,
            "response": "",
            "current_inci": req.inci_name or current_json.get('inci', 'INCI_NAME'),
            "edit_history": None,
            "error": None
        })
        
        # Save result
        write_json(result["json_data"], str(JSON_TEMPLATE_PATH))
        
        return EditResponse(
            inci=result["current_inci"],
            updated_json=result["json_data"],
            raw_response=result["response"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current")
async def get_current_json():
    """Get the current JSON data"""
    return read_json()

@router.post("/reset")
async def reset_json():
    """Reset to template structure"""
    write_json(JSON_TEMPLATE, str(JSON_TEMPLATE_PATH))
    return {
        "message": "Reset to template successful",
        "data": JSON_TEMPLATE
    }
```

---

### Step 5.2: Create Main App

**File**: `app/main.py`

```python
"""
FastAPI application entrypoint
"""
import socket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.routes_edit import router as edit_router
from app.graph.build_graph import build_graph

app = FastAPI(
    title="Cosmetic Ingredient Toxicology Editor API",
    description="API for managing toxicology data of cosmetic ingredients",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(edit_router)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Cosmetic Ingredient Toxicology Editor API is running",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "toxicity-agent"
    }

@app.get("/graph")
async def get_graph_visualization():
    """Get workflow graph visualization"""
    app_graph = build_graph()
    png_data = app_graph.get_graph().draw_mermaid_png()
    return Response(content=png_data, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    from app.config import API_HOST, API_PORT
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    
    print(f"\n📍 API available at: http://{local_ip}:{API_PORT}/docs\n")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
```

---

## Phase 6: Migration Testing (30 mins)

### Step 6.1: Create Test File

**File**: `tests/test_refactored.py`

```python
"""
Tests to verify refactored code works correctly
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.json_io import read_json, write_json
from app.services.text_processing import extract_inci_name, clean_llm_json_output
from app.services.data_updater import fix_common_llm_errors, merge_json_updates
from app.graph.build_graph import build_graph

def test_json_io():
    """Test JSON read/write"""
    test_data = {"inci": "TEST", "cas": []}
    assert write_json(test_data, "test.json")
    loaded = read_json("test.json")
    assert loaded["inci"] == "TEST"

def test_extract_inci():
    """Test INCI extraction"""
    assert extract_inci_name("inci_name = PETROLATUM") == "PETROLATUM"
    assert extract_inci_name("INCI: WATER") == "WATER"

def test_clean_llm_output():
    """Test LLM output cleaning"""
    raw = '```json\n{"inci": "TEST"}\n```'
    cleaned = clean_llm_json_output(raw)
    assert cleaned == '{"inci": "TEST"}'

def test_fix_llm_errors():
    """Test error fixing"""
    errors = {"INCI": "TEST", "toxicology": {"NOAEL": []}}
    fixed = fix_common_llm_errors(errors)
    assert "inci" in fixed
    assert "INCI" not in fixed
    assert "NOAEL" in fixed

def test_graph_builds():
    """Test graph compilation"""
    graph = build_graph()
    assert graph is not None

def test_graph_invoke():
    """Test graph execution"""
    from app.graph.state import JSONEditState
    
    graph = build_graph()
    state = JSONEditState(
        json_data={"inci": "TEST", "NOAEL": []},
        user_input="Update INCI name to PETROLATUM",
        response="",
        current_inci="TEST",
        edit_history=None,
        error=None
    )
    
    result = graph.invoke(state)
    assert "json_data" in result
    assert "response" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Step 6.2: Run Tests

```bash
# Install pytest if needed
pip install pytest

# Run tests
pytest tests/test_refactored.py -v

# Expected output:
# test_json_io PASSED
# test_extract_inci PASSED
# test_clean_llm_output PASSED
# test_fix_llm_errors PASSED
# test_graph_builds PASSED
# test_graph_invoke PASSED
```

---

## Phase 7: Switch Over (15 mins)

### Step 7.1: Update Your Startup Script

**Create**: `run.py` (in project root)

```python
"""
Main entrypoint for running the application
"""
if __name__ == "__main__":
    from app.main import app
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 7.2: Update Your Existing Files

**Option A**: Keep old files as backup
```bash
# Rename old files
mv core/agent_graph_toxicity.py core/agent_graph_toxicity.py.backup
mv app/app.py app/app.py.backup

# Your new structure is now active!
```

**Option B**: Delete old files (after verifying everything works)
```bash
rm core/agent_graph_toxicity.py
rm app/app.py
```

### Step 7.3: Test the New API

```bash
# Start server
python run.py

# In another terminal, test:
curl -X POST "http://localhost:8000/api/edit" \
  -H "Content-Type: application/json" \
  -d '{"instruction": "Set INCI to PETROLATUM", "inci_name": "PETROLATUM"}'

# Should see successful response!
```

---

## Phase 8: Final Touches (15 mins)

### Step 8.1: Update Requirements

**File**: `requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
langgraph==0.0.26
langchain-ollama==0.0.1
langchain-openai==0.0.5
pytest==7.4.3
```

### Step 8.2: Create README

**File**: `README.md`

```markdown
# Toxicity Agent

Cosmetic ingredient toxicology data editor using LangGraph.

## Project Structure

```
toxicity-agent/
├── app/
│   ├── config.py          # Global configuration
│   ├── main.py            # FastAPI entrypoint
│   ├── graph/             # LangGraph workflow
│   │   ├── state.py       # State definitions
│   │   ├── build_graph.py # Graph construction
│   │   └── nodes/         # Individual workflow nodes
│   ├── services/          # Business logic
│   │   ├── json_io.py
│   │   ├── text_processing.py
│   │   └── data_updater.py
│   └── api/               # API routes
│       └── routes_edit.py
├── tests/                 # Test files
├── data/                  # JSON data files
└── requirements.txt
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python run.py

# Open API docs
open http://localhost:8000/docs
```

## API Usage

```python
import requests

# Edit toxicology data
response = requests.post(
    "http://localhost:8000/api/edit",
    json={
        "instruction": "Set NOAEL to 800 mg/kg bw/day",
        "inci_name": "PETROLATUM"
    }
)
print(response.json())
```

## Development

```bash
# Run tests
pytest tests/ -v

# View graph
curl http://localhost:8000/graph > graph.png
```
```

### Step 8.3: Create .gitignore

**File**: `.gitignore`

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/

# IDEs
.vscode/
.idea/
*.swp

# Data files
data/*.json
!data/toxicity_data_template.json

# Logs
logs/
*.log

# Environment
.env

# Tests
.pytest_cache/
```

---

## 🎯 Migration Checklist

Use this to track your progress:

- [ ] **Phase 1**: Created directory structure
- [ ] **Phase 2**: Created `app/config.py`
- [ ] **Phase 3**: Created `app/graph/state.py`
- [ ] **Phase 4**: Created services (`json_io.py`, `text_processing.py`, `data_updater.py`)
- [ ] **Phase 5**: Created graph nodes (`llm_edit_node.py`)
- [ ] **Phase 6**: Created `app/graph/build_graph.py`
- [ ] **Phase 7**: Created API routes (`routes_edit.py`)
- [ ] **Phase 8**: Created `app/main.py`
- [ ] **Phase 9**: Wrote tests and verified they pass
- [ ] **Phase 10**: Started new server and tested endpoints
- [ ] **Phase 11**: Backed up old files
- [ ] **Phase 12**: Updated documentation

---

## 🚨 Common Issues & Solutions

### Issue: Import errors after refactoring

**Solution**: Ensure you're running from project root and `app/__init__.py` exists

```bash
# From project root:
python -c "from app.config import DEFAULT_LLM_MODEL; print(DEFAULT_LLM_MODEL)"
```

### Issue: Old code still running

**Solution**: Restart your server and clear Python cache

```bash
find . -type d -name "__pycache__" -exec rm -r {} +
python run.py
```

### Issue: Tests failing

**Solution**: Make sure test paths are correct

```python
# In tests, use:
sys.path.insert(0, str(Path(__file__).parent.parent))
```

---

## 📊 Before/After Comparison

### Before: Monolithic (1 file, 500+ lines)
```
agent_graph_toxicity.py (500+ lines)
├── State definitions
├── File I/O
├── Text processing
├── LLM logic
├── Graph building
└── Testing code
```

### After: Modular (10+ files, organized)
```
app/
├── config.py (50 lines)
├── graph/
│   ├── state.py (20 lines)
│   ├── nodes/
│   │   └── llm_edit_node.py (100 lines)
│   └── build_graph.py (50 lines)
├── services/
│   ├── json_io.py (80 lines)
│   ├── text_processing.py (100 lines)
│   └── data_updater.py (80 lines)
└── api/
    └── routes_edit.py (80 lines)
```

**Benefits**:
- ✅ Each file has single responsibility
- ✅ Easy to test individual components
- ✅ Easy to locate and fix bugs
- ✅ Easy to add new features
- ✅ Multiple developers can work simultaneously

---

## 🎓 Next Steps After Refactoring

1. **Add type hints everywhere**: `mypy app/`
2. **Add docstrings**: Use Google or NumPy style
3. **Set up CI/CD**: GitHub Actions for testing
4. **Add logging**: Replace `print()` with `logger.info()`
5. **Add monitoring**: Prometheus metrics
6. **Database integration**: Replace file I/O with SQLite/PostgreSQL
7. **Authentication**: Add API keys or OAuth

---

## 💡 Tips for Smooth Migration

1. **Do one phase at a time** - Don't rush
2. **Test after each phase** - Catch issues early
3. **Keep backups** - Don't delete old code until new code works
4. **Use version control** - Commit after each successful phase
5. **Ask for help** - If stuck, review this guide or ask questions

---

## 📚 Additional Resources

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Python Project Structure](https://docs.python-guide.org/writing/structure/)
- [Clean Code Principles](https://github.com/ryanmcdermott/clean-code-python)

---

**Estimated Total Time**: 3-4 hours

**Difficulty**: Intermediate

**Prerequisites**: 
- Basic Python knowledge
- Understanding of your current code
- Patience and attention to detail

Good luck with your refactoring! 🚀
