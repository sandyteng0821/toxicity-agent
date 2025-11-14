# Toxicity Agent Review & Improvements

## Overview
Your toxicity agent uses LangGraph to manage cosmetic ingredient toxicology data editing. Here's a comprehensive review with actionable improvements.

---

## ✅ What's Working Well

1. **Clean Separation**: API (`app.py`) and logic (`agent_graph_toxicity.py`) are well separated
2. **Error Handling**: Good JSON parsing error handling with fallbacks
3. **Template Management**: Auto-creation of template files if missing
4. **Structured Data Extraction**: Smart regex patterns for toxicology sections
5. **FastAPI Integration**: Clean REST endpoints with OpenAPI docs

---

## 🔧 Critical Issues & Fixes

### Issue 1: **State Management Problem**
**Problem**: Your graph doesn't maintain conversation history or multi-turn edits.

**Current Flow**:
```
User Request → Graph Invoke → Update JSON → Return
     ↓
No memory of previous edits in the same session
```

**Fix**: Add conversation memory
```python
from typing import List, Tuple

class JSONEditState(TypedDict):
    json_data: Dict[str, Any]
    user_input: str
    response: str
    current_inci: str
    edit_history: List[Tuple[str, str]]  # NEW: (instruction, timestamp)
    
def llm_edit_node(state: JSONEditState):
    # Capture edit history
    import datetime
    if "edit_history" not in state:
        state["edit_history"] = []
    
    state["edit_history"].append((
        state["user_input"],
        datetime.datetime.now().isoformat()
    ))
    
    # Rest of your code...
```

---

### Issue 2: **LLM Prompt Issues**
**Problems**:
- Too verbose (reduces token efficiency)
- Examples are good but could be more systematic
- No validation of output format before parsing

**Improved Prompt**:
```python
def llm_edit_node(state: JSONEditState):
    llm = ChatOllama(model="llama3.1:8b")
    
    # Simplified, focused prompt
    prompt = f"""Update toxicology JSON for: {current_inci}

INSTRUCTION: {state['user_input']}

CURRENT DATA:
{json.dumps(state["json_data"], indent=2)[:1000]}...

OUTPUT RULES:
1. Return ONLY changed fields as valid JSON
2. Use exact field names: "inci", "NOAEL", "DAP", etc.
3. For arrays: provide complete entries (no "..." placeholders)
4. Match this structure:

{{
  "inci": "NAME",
  "NOAEL": [{{ "value": 800, "unit": "mg/kg bw/day", "source": "echa", ... }}],
  "repeated_dose_toxicity": [{{ "reference": {{}}, "data": [], ... }}]
}}

RESPOND WITH JSON ONLY:"""

    # Add validation before parsing
    result = llm.invoke(prompt)
    
    # Validate JSON structure
    if not validate_llm_output(result.content):
        state["response"] = "LLM output validation failed - please retry"
        return state
    
    # Rest of parsing logic...
```

---

### Issue 3: **No Validation Layer**
**Problem**: No schema validation before updating JSON

**Fix**: Add Pydantic models
```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict

class Reference(BaseModel):
    title: str
    link: Optional[str] = None

class ToxicologyEntry(BaseModel):
    reference: Reference
    data: List[str]
    source: str
    statement: Optional[str] = None
    replaced: Dict[str, str] = Field(default_factory=lambda: {"replaced_inci": "", "replaced_type": ""})
    
    @validator('data')
    def validate_data_not_empty(cls, v):
        if not v or v == ["..."]:
            raise ValueError("Data cannot be empty or placeholder")
        return v

class NOAELEntry(BaseModel):
    note: Optional[str] = None
    unit: str
    experiment_target: Optional[str] = None
    source: str
    type: str = "NOAEL"
    study_duration: Optional[str] = None
    value: float
    
    @validator('value')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

# Use in your code:
def validate_and_update(updates: dict, state: JSONEditState):
    """Validate updates before applying them"""
    validated_updates = {}
    
    if "NOAEL" in updates:
        try:
            validated_updates["NOAEL"] = [NOAELEntry(**entry) for entry in updates["NOAEL"]]
        except Exception as e:
            print(f"⚠️ NOAEL validation failed: {e}")
            return False
    
    if "repeated_dose_toxicity" in updates:
        try:
            validated_updates["repeated_dose_toxicity"] = [
                ToxicologyEntry(**entry) for entry in updates["repeated_dose_toxicity"]
            ]
        except Exception as e:
            print(f"⚠️ Toxicology validation failed: {e}")
            return False
    
    return validated_updates
```

---

### Issue 4: **File I/O Race Conditions**
**Problem**: Multiple API requests could cause concurrent file writes

**Fix**: Add file locking
```python
import fcntl
from contextlib import contextmanager

@contextmanager
def file_lock(filepath):
    """Context manager for file locking"""
    lock_file = f"{filepath}.lock"
    with open(lock_file, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def write_json(data, filepath="edited.json"):
    """Write JSON with file locking"""
    with file_lock(filepath):
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON successfully saved to {filepath}")
```

---

## 🚀 Architectural Improvements

### Improvement 1: **Add Multi-Step Workflow**
Your current graph is too simple (single node). Enhance it:

```python
def build_enhanced_graph():
    """Enhanced graph with validation and retry logic"""
    graph = StateGraph(JSONEditState)
    
    # Add nodes
    graph.add_node("parse_instruction", parse_instruction_node)
    graph.add_node("validate_input", validate_input_node)
    graph.add_node("edit", llm_edit_node)
    graph.add_node("validate_output", validate_output_node)
    graph.add_node("retry", retry_node)
    
    # Set entry point
    graph.set_entry_point("parse_instruction")
    
    # Add edges
    graph.add_edge("parse_instruction", "validate_input")
    
    graph.add_conditional_edges(
        "validate_input",
        lambda state: "edit" if state.get("validation_passed") else "end",
        {
            "edit": "edit",
            "end": END
        }
    )
    
    graph.add_edge("edit", "validate_output")
    
    graph.add_conditional_edges(
        "validate_output",
        lambda state: "end" if state.get("output_valid") else "retry",
        {
            "end": END,
            "retry": "retry"
        }
    )
    
    graph.add_conditional_edges(
        "retry",
        lambda state: "edit" if state.get("retry_count", 0) < 3 else "end",
        {
            "edit": "edit",
            "end": END
        }
    )
    
    return graph.compile()

# Implement new nodes:
def parse_instruction_node(state: JSONEditState):
    """Extract structured data from instruction"""
    state["parsed_sections"] = extract_toxicology_sections(state["user_input"])
    return state

def validate_input_node(state: JSONEditState):
    """Validate input before processing"""
    state["validation_passed"] = bool(state["user_input"].strip())
    return state

def validate_output_node(state: JSONEditState):
    """Validate LLM output"""
    try:
        updates = json.loads(state["response"])
        validated = validate_and_update(updates, state)
        state["output_valid"] = bool(validated)
    except:
        state["output_valid"] = False
    return state

def retry_node(state: JSONEditState):
    """Handle retry logic"""
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["user_input"] = f"RETRY #{state['retry_count']}: {state['user_input']}\nPrevious attempt had validation errors."
    return state
```

---

### Improvement 2: **Add Observability**
Track what your agent is doing:

```python
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('toxicity_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def llm_edit_node(state: JSONEditState):
    logger.info(f"Processing edit for INCI: {state.get('current_inci')}")
    logger.debug(f"User input: {state['user_input'][:200]}...")
    
    start_time = datetime.now()
    
    # Your existing code...
    result = llm.invoke(prompt)
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"LLM response received in {duration:.2f}s")
    logger.debug(f"LLM output: {result.content[:200]}...")
    
    # Rest of your code...
    
    return state
```

---

### Improvement 3: **API Enhancements**

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI(
    title="Cosmetic Ingredient Toxicology Editor API",
    description="API for managing toxicology data of cosmetic ingredients",
    version="2.0.0"
)

# Add CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request tracking
from collections import defaultdict
request_tracking = defaultdict(list)

@app.post("/edit")
async def edit_json(req: EditRequest, background_tasks: BackgroundTasks):
    """Enhanced edit endpoint with async processing"""
    request_id = f"{req.inci_name}_{datetime.now().timestamp()}"
    
    try:
        current_json = read_json()
        
        user_input = req.instruction
        if req.inci_name:
            user_input = f"INCI: {req.inci_name}\n{user_input}"
        
        # Run graph
        result = graph.invoke({
            "json_data": current_json,
            "user_input": user_input,
            "response": "",
            "current_inci": req.inci_name or current_json.get('inci', 'INCI_NAME')
        })
        
        # Save in background
        background_tasks.add_task(
            write_json, 
            result["json_data"], 
            "toxicity_data_template.json"
        )
        
        # Track request
        request_tracking[req.inci_name].append({
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "instruction": req.instruction
        })
        
        return {
            "request_id": request_id,
            "inci": result["current_inci"],
            "updated_json": result["json_data"],
            "raw_response": result["response"],
            "edit_history": result.get("edit_history", [])
        }
        
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{inci_name}")
async def get_edit_history(inci_name: str):
    """Get edit history for an ingredient"""
    return {
        "inci": inci_name,
        "history": request_tracking.get(inci_name, [])
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_model": "llama3.1:8b",
        "graph_nodes": len(graph.get_graph().nodes),
        "timestamp": datetime.now().isoformat()
    }
```

---

## 🎯 Testing Strategy

```python
# tests/test_agent.py
import pytest
from core.agent_graph_toxicity import build_graph, JSONEditState

@pytest.fixture
def test_state():
    return JSONEditState(
        json_data={
            "inci": "TEST_INGREDIENT",
            "NOAEL": [],
            "repeated_dose_toxicity": []
        },
        user_input="Set NOAEL to 500 mg/kg bw/day",
        response="",
        current_inci="TEST_INGREDIENT"
    )

def test_noael_update(test_state):
    """Test NOAEL update functionality"""
    graph = build_graph()
    result = graph.invoke(test_state)
    
    assert "NOAEL" in result["json_data"]
    assert len(result["json_data"]["NOAEL"]) > 0
    assert result["json_data"]["NOAEL"][0]["value"] == 500

def test_invalid_input(test_state):
    """Test handling of invalid input"""
    test_state["user_input"] = ""
    graph = build_graph()
    result = graph.invoke(test_state)
    
    assert "error" in result["response"].lower() or not result["response"]

# Run tests:
# pytest tests/test_agent.py -v
```

---

## 📊 Performance Optimization

### 1. **Cache LLM Responses**
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_llm_invoke(prompt_hash: str, model: str):
    """Cache LLM responses for identical prompts"""
    llm = ChatOllama(model=model)
    return llm.invoke(prompt_hash)

def llm_edit_node(state: JSONEditState):
    prompt = f"..." # your prompt
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
    
    result = cached_llm_invoke(prompt_hash, "llama3.1:8b")
    # Rest of your code...
```

### 2. **Async LLM Calls** (if supported by your LLM provider)
```python
async def async_llm_edit_node(state: JSONEditState):
    """Async version for better concurrency"""
    llm = ChatOllama(model="llama3.1:8b")
    result = await llm.ainvoke(prompt)  # Use async invoke
    # Rest of your code...
```

---

## 🔒 Security Improvements

```python
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Verify API key for protected endpoints"""
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/edit")
async def edit_json(
    req: EditRequest,
    api_key: str = Depends(verify_api_key)
):
    # Your existing code...
```

---

## 📝 Documentation Improvements

### Add Docstrings:
```python
def llm_edit_node(state: JSONEditState) -> JSONEditState:
    """
    Process user input and update toxicology JSON using LLM.
    
    Args:
        state: Current state containing:
            - json_data: Current JSON structure
            - user_input: User instruction
            - current_inci: Current ingredient name
    
    Returns:
        Updated state with:
            - json_data: Modified JSON
            - response: LLM response or error message
    
    Raises:
        json.JSONDecodeError: If LLM output is not valid JSON
    
    Example:
        >>> state = JSONEditState(
        ...     json_data={"inci": "PETROLATUM", "NOAEL": []},
        ...     user_input="Set NOAEL to 800",
        ...     response="",
        ...     current_inci="PETROLATUM"
        ... )
        >>> result = llm_edit_node(state)
        >>> assert len(result["json_data"]["NOAEL"]) > 0
    """
    # Your code...
```

---

## 🎁 Bonus: Monitoring Dashboard

```python
# Add Prometheus metrics
from prometheus_client import Counter, Histogram, make_asgi_app

REQUEST_COUNT = Counter('toxicity_requests_total', 'Total requests')
REQUEST_DURATION = Histogram('toxicity_request_duration_seconds', 'Request duration')

@app.post("/edit")
@REQUEST_DURATION.time()
async def edit_json(req: EditRequest):
    REQUEST_COUNT.inc()
    # Your existing code...

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

---

## 🚦 Migration Checklist

- [ ] Add Pydantic validation models
- [ ] Implement multi-step workflow graph
- [ ] Add file locking for concurrent writes
- [ ] Set up logging infrastructure
- [ ] Write unit tests for critical paths
- [ ] Add API authentication
- [ ] Implement request caching
- [ ] Add monitoring/metrics
- [ ] Document all public APIs
- [ ] Set up CI/CD pipeline

---

## 📚 Additional Resources

1. **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
2. **FastAPI Best Practices**: https://fastapi.tiangolo.com/tutorial/
3. **Pydantic Validation**: https://docs.pydantic.dev/
4. **Testing with pytest**: https://docs.pytest.org/

---

## 💡 Next Steps

1. **Immediate**: Implement validation layer (biggest risk currently)
2. **Short-term**: Add multi-step workflow and error handling
3. **Medium-term**: Set up monitoring and testing
4. **Long-term**: Consider database instead of file storage for production

Your foundation is solid! These improvements will make your agent more robust, maintainable, and production-ready.
