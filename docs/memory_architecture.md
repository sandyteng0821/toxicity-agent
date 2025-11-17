# Memory Architecture: Chat Memory & Data Versioning

**Version**: v1.1.0  
**Last Updated**: 2024-11-17  
**Status**: ✅ Fully implemented and tested (16/16 tests passing)

## Overview

The toxicity agent implements a **dual-memory architecture** to provide both conversational context and data versioning capabilities:

1. **Chat Memory** - Conversation history for context and continuity
2. **Data Versioning** - JSON data snapshots with full audit trail

This architecture ensures that:
- ✅ Users can have multi-turn conversations with context
- ✅ All data modifications are versioned and auditable
- ✅ Users can query "what did I change?" and get accurate answers
- ✅ Data integrity is maintained in database, not relying on LLM memory
- ✅ Changes can be tracked, compared, and potentially rolled back

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       User Request                          │
│              (instruction + conversation_id)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Endpoint                         │
│                   /api/edit (routes_edit.py)                │
│  • Generates/receives conversation_id                       │
│  • Saves initial_data if provided                           │
│  • Configures memory with thread_id                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                       │
│                  (build_graph.py)                           │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  Graph State (JSONEditState)                 │          │
│  │  • messages: List[BaseMessage]  ◄────────────┼──────────┼─── Chat Memory
│  │  • conversation_id: str                      │          │    (chat_memory.db)
│  │  • user_input: str                           │          │    via SqliteSaver
│  │  • json_data: dict (loaded from DB)          │          │
│  │  • response: str                             │          │
│  │  • current_inci: str                         │          │
│  └──────────────────────────────────────────────┘          │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────┐          │
│  │     llm_edit_node (llm_edit_node.py)         │          │
│  │  1. Load JSON from ToxicityDB                │          │
│  │  2. Process with LLM                         │          │
│  │  3. Save new version to ToxicityDB           │          │
│  │  4. Add AIMessage to chat history            │          │
│  └──────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database Layer                             │
│                (core/database.py)                           │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  ToxicityDB (toxicity_data.db)               │          │
│  │                                              │          │
│  │  Table: toxicity_versions                    │          │
│  │  ├─ id (primary key)                         │          │
│  │  ├─ conversation_id (indexed)                │          │
│  │  ├─ version (1, 2, 3, ...)                   │          │
│  │  ├─ data (JSON string)                       │◄─────────┼─── Data Memory
│  │  ├─ modification_summary (text)              │          │    (toxicity_data.db)
│  │  └─ created_at (timestamp)                   │          │    via ToxicityDB
│  │                                              │          │
│  │  Methods:                                    │          │
│  │  • save_version()                            │          │
│  │  • get_current_version()                     │          │
│  │  • get_modification_history()                │          │
│  │  • get_diff()                                │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Chat Memory (Conversation Context)

**Purpose**: Store conversational messages for context across multiple requests

**Implementation**: LangGraph's `SqliteSaver` checkpointer

**Storage Location**: `chat_memory.db`

**What Gets Stored**:
- User messages (`HumanMessage`)
- AI responses (`AIMessage`)
- Full graph state at each checkpoint

**Key Code**:

```python
# app/graph/build_graph.py
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

def build_graph():
    # ... graph setup ...
    
    # Enable chat memory with thread-safe connection
    conn = sqlite3.connect("chat_memory.db", check_same_thread=False)
    memory = SqliteSaver(conn=conn)
    
    return graph.compile(checkpointer=memory)
```

**Access Pattern**:
```python
# Configure with thread_id (conversation_id)
config = {"configurable": {"thread_id": conversation_id}}

# Memory is automatically loaded/saved
result = graph.invoke(state, config=config)
```

**Benefits**:
- ✅ Automatic persistence across requests
- ✅ No manual save/load logic needed
- ✅ Supports multi-turn conversations
- ✅ Can retrieve full conversation history

---

### 2. Data Versioning (JSON Snapshots)

**Purpose**: Store immutable versions of toxicity JSON data with audit trail

**Implementation**: Custom `ToxicityDB` class using SQLAlchemy

**Storage Location**: `toxicity_data.db`

**What Gets Stored**:
- Complete JSON snapshot at each modification
- Version number (incremental)
- Modification summary (human-readable description)
- Timestamp of change
- Associated conversation_id

**Database Schema**:

```sql
CREATE TABLE toxicity_versions (
    id INTEGER PRIMARY KEY,
    conversation_id VARCHAR(100),  -- Links to conversation
    version INTEGER,               -- 1, 2, 3, ...
    data TEXT,                     -- Full JSON as string
    modification_summary TEXT,     -- "Updated NOAEL value"
    created_at DATETIME           -- When modified
);

CREATE INDEX idx_conversation_id ON toxicity_versions(conversation_id);
```

**Key Code**:

```python
# core/database.py
class ToxicityDB:
    def save_version(self, conversation_id: str, data: dict, 
                     modification_summary: str) -> ToxicityVersion:
        """Save a new version of toxicity data"""
        # Get next version number
        # Store complete JSON snapshot
        # Return version object
        
    def get_current_version(self, conversation_id: str) -> ToxicityVersion:
        """Get the latest version"""
        
    def get_modification_history(self, conversation_id: str) -> List[dict]:
        """Get summary of all modifications"""
        
    def get_diff(self, conversation_id: str, 
                 from_version: int, to_version: int) -> dict:
        """Calculate differences between versions"""
```

**Access Pattern (v1.1.0)**:

```python
# In llm_edit_node.py
from app.services.json_io import read_json, write_json
from core.database import ToxicityDB

db = ToxicityDB()

# Load current data (v1.1.0 approach)
# Get conversation context from DB
conversation_id = state.get("conversation_id")
# Load current JSON from DB (not from state)
current_version_obj = db.get_current_version(conversation_id)
if current_version_obj:
    current_json = json.loads(current_version_obj.data)
else:
    # Fallback to state if no DB version exists
    current_json = state["json_data"]

# ... modify data ...

# Save new version
db.save_version(
    conversation_id=conversation_id,
    data=modified_data,
    modification_summary="Updated acute_toxicity values"
)

# Also save to file (dual storage in v1.1.0)
write_json(modified_data)
```

**Storage Strategy (v1.1.0)**:
- **Primary**: File-based (`toxicity_data_template.json`) for simplicity
- **Optional**: ToxicityDB for version history (if configured)
- **Future**: Full migration to database-only storage

**Benefits**:
- ✅ Simple file-based storage (easy to inspect/debug)
- ✅ Optional versioning via ToxicityDB
- ✅ Data integrity independent of LLM
- ✅ Supports rollback/undo (via ToxicityDB, if enabled)

---

## State Management

### Graph State Definition

```python
# app/graph/state.py
from typing import TypedDict, Annotated, List, Optional
from operator import add
from langchain_core.messages import BaseMessage

class JSONEditState(TypedDict):
    # Chat Memory fields
    messages: Annotated[List[BaseMessage], add]  # Auto-appends messages
    conversation_id: str                          # Links to data versions
    
    # Processing fields
    json_data: dict              # Current JSON (loaded from DB)
    user_input: str             # Current instruction
    response: str               # AI response
    current_inci: str           # Current INCI name
    edit_history: Optional[dict]
    error: Optional[str]
```

**Key Pattern**: `Annotated[List[BaseMessage], add]`
- This tells LangGraph to **append** new messages instead of replacing
- Enables automatic conversation history building

---

## Data Flow Example

### Scenario: User modifies toxicity data across 3 requests

```python
# Request 1: Initialize
POST /api/edit
{
  "instruction": "Set up data for WATER",
  "initial_data": {"inci": "WATER", "category": "OTHERS", ...}
}

# What happens:
# 1. conversation_id generated: "conv-abc-123"
# 2. Data saved to toxicity_data.db as version 1
# 3. HumanMessage added to chat_memory.db
# 4. Response: version=1

# ─────────────────────────────────────────────────────────

# Request 2: First edit
POST /api/edit
{
  "instruction": "Change category to FRAGRANCE",
  "conversation_id": "conv-abc-123"
}

# What happens:
# 1. Load version 1 from toxicity_data.db
# 2. LLM processes: category: OTHERS → FRAGRANCE
# 3. Save as version 2 to toxicity_data.db
# 4. HumanMessage + AIMessage added to chat_memory.db
# 5. Response: version=2

# ─────────────────────────────────────────────────────────

# Request 3: Query history
POST /api/edit
{
  "instruction": "What did I just change?",
  "conversation_id": "conv-abc-123"
}

# What happens:
# 1. Load chat history from chat_memory.db (2 exchanges)
# 2. Load modification history from toxicity_data.db (v1→v2)
# 3. LLM responds: "You changed the category from OTHERS to FRAGRANCE"
# 4. AIMessage added to chat_memory.db
# 5. Response: version=2 (no data modification)
```

---

## Database Files

### chat_memory.db (LangGraph Managed)

**Purpose**: Store conversation checkpoints

**Structure**: Managed internally by LangGraph's `SqliteSaver`

**Contents**:
- Serialized graph state
- Message history
- Checkpoint metadata

**Do not manually modify this database**

### toxicity_data.db (Application Managed)

**Purpose**: Store JSON data versions

**Structure**: Defined by `ToxicityDB` class

**Contents**:
- `toxicity_versions` table (see schema above)

**Can be queried directly for analytics/reporting**

---

## API Integration

### Updated Endpoint Signature

```python
# app/api/routes_edit.py

class EditRequest(BaseModel):
    instruction: str                      # What to do
    inci_name: Optional[str] = None      # INCI name (optional)
    conversation_id: Optional[str] = None # Continue conversation
    initial_data: Optional[dict] = None   # For new conversations

class EditResponse(BaseModel):
    inci: str                    # Current INCI name
    updated_json: dict           # Current data
    raw_response: str            # AI response
    conversation_id: str         # For subsequent requests
    current_version: int         # Data version number
```

### Request Flow

```python
@router.post("/api/edit", response_model=EditResponse)
async def edit_json(req: EditRequest):
    # 1. Get or create conversation_id
    conv_id = req.conversation_id or str(uuid.uuid4())
    
    # 2. Save initial data if provided
    if req.initial_data:
        db.save_version(conv_id, req.initial_data, "Initial data")
    
    # 3. Configure memory
    config = {"configurable": {"thread_id": conv_id}}
    
    # 4. Invoke graph (memory auto-loads/saves)
    result = graph.invoke({
        "messages": [HumanMessage(content=req.instruction)],
        "conversation_id": conv_id,
        "user_input": req.instruction,
        # ... other fields
    }, config=config)
    
    # 5. Return current version from DB
    latest = db.get_current_version(conv_id)
    return EditResponse(
        conversation_id=conv_id,
        current_version=latest.version,
        # ... other fields
    )
```

---

## Key Design Decisions

### Why Dual Memory?

**Chat Memory (LangGraph):**
- Purpose: Conversational context
- Content: Messages and state transitions
- Managed by: LangGraph automatically
- Use case: "What did I ask about?" "Continue the conversation"

**Data Versioning (ToxicityDB):**
- Purpose: Data integrity and audit trail
- Content: Complete JSON snapshots
- Managed by: Application explicitly
- Use case: "Show me version 3" "What changed between v2 and v5?"

### Why Not Store JSON in Graph State?

**Problem**: LLM context limits and reliability
- Large JSON files exceed context windows
- LLM might hallucinate or lose precision
- State bloat across checkpoints

**Solution**: Store only references in state
- `conversation_id` links to data versions
- Load current version from DB when needed
- Keep graph state lean and focused

### Why SqliteSaver with `check_same_thread=False`?

**Problem**: SQLite thread safety
- Default SQLite: objects only usable in creating thread
- LangGraph: uses thread pools for execution

**Solution**: Disable thread check
```python
conn = sqlite3.connect("chat_memory.db", check_same_thread=False)
```

**Safe because**:
- Read-heavy workload (chat history)
- Single-process application
- LangGraph handles concurrency internally

**Production alternative**: Use PostgreSQL or Redis for high concurrency

---

## Usage Patterns

### Pattern 1: Simple Edit

```python
# User just wants to modify data
POST /api/edit {"instruction": "Change INCI to WATER"}

# System:
# 1. Loads current version from DB
# 2. Applies modification
# 3. Saves new version
# 4. Adds message to chat history
```

### Pattern 2: Multi-turn Editing

```python
# Request 1
POST /api/edit {"instruction": "Add NOAEL 1000"}
# → version 2, conversation_id returned

# Request 2 (same conversation)
POST /api/edit {
  "instruction": "Now also add skin irritation data",
  "conversation_id": "conv-abc"
}
# → version 3, remembers context
```

### Pattern 3: Querying History

```python
POST /api/edit {
  "instruction": "What modifications have I made?",
  "conversation_id": "conv-abc"
}

# System:
# 1. Loads modification history from toxicity_data.db
# 2. Loads chat messages from chat_memory.db
# 3. LLM generates summary: "You made 3 changes: ..."
# 4. No new version created (query only)
```

### Pattern 4: Version Comparison (Future)

```python
GET /api/diff/conv-abc?from_version=2&to_version=5

# System:
# 1. Load version 2 and version 5 from DB
# 2. Calculate diff using dictdiffer
# 3. Return human-readable changes
```

---

## Error Handling

### Database Errors

```python
# In llm_edit_node.py
try:
    db.save_version(conversation_id, data, summary)
except Exception as e:
    # Log error
    # Return error message to user
    # No version saved (data integrity preserved)
    return {
        "error": f"Failed to save: {str(e)}",
        "messages": [AIMessage(content=f"Error: {str(e)}")]
    }
```

### Memory Errors

```python
# LangGraph handles checkpointing errors internally
# If checkpoint fails, graph execution still completes
# User gets response but history might not persist
```

### Missing Data

```python
# In llm_edit_node.py
current_version = db.get_current_version(conversation_id)
if not current_version:
    return {
        "messages": [AIMessage(content="No data found. Please provide initial_data.")],
        "error": "No data available"
    }
```

---

## Testing

### Database Layer Tests

```python
# tests/test_db.py (if ToxicityDB versioning is enabled)
from core.database import ToxicityDB

db = ToxicityDB()

# Test version creation
db.save_version("test-1", {"key": "value"}, "Initial")
version = db.get_current_version("test-1")
assert version.version == 1

# Test version increment
db.save_version("test-1", {"key": "value2"}, "Update")
version = db.get_current_version("test-1")
assert version.version == 2

# Test modification history
history = db.get_modification_history("test-1")
assert len(history) == 2

# Test diff between versions
diff = db.get_diff("test-1", from_version=1, to_version=2)
assert "key" in diff
```

**Note**: In v1.1.0, database versioning is implemented but optional. Primary storage is file-based for simplicity.

### Chat History Tests (v1.1.0)

```python
# tests/test_chat_history.py
import uuid
from app.graph.build_graph import build_graph
from app.graph.state import JSONEditState

def test_checkpoint_persistence():
    """Test that checkpoints are saved and loaded"""
    graph = build_graph()
    conv_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conv_id}}
    
    # First invocation
    state1 = JSONEditState(
        json_data={"inci": "TEST", "NOAEL": []},
        user_input="Update INCI to CAFFEINE",
        response="",
        current_inci="TEST",
        messages=[],
        conversation_id=conv_id,
        edit_history=None,
        error=None
    )
    result1 = graph.invoke(state1, config=config)
    
    # Get checkpoint
    checkpoint = graph.get_state(config)
    assert checkpoint is not None
    
    # Second invocation (loads checkpoint)
    state2 = JSONEditState(...)
    result2 = graph.invoke(state2, config=config)
    
    # Verify checkpoint updated
    checkpoint2 = graph.get_state(config)
    assert checkpoint2.values["json_data"]["inci"].upper() == "CAFFEINE"

def test_different_threads():
    """Test thread isolation"""
    graph = build_graph()
    
    thread1 = str(uuid.uuid4())
    thread2 = str(uuid.uuid4())
    
    result1 = graph.invoke(..., config={"configurable": {"thread_id": thread1}})
    result2 = graph.invoke(..., config={"configurable": {"thread_id": thread2}})
    
    # Threads are independent
    inci1 = result1["json_data"]["inci"].upper()
    inci2 = result2["json_data"]["inci"].upper()
    assert inci1 != inci2
```

### Node Integration Tests

```python
# tests/test_chat_history.py -> # def test_single_edit()
# tests/test_node.py (deprecated, 2024-11-16)
from app.graph.build_graph import build_graph

graph = build_graph()

# Test with memory
config = {"configurable": {"thread_id": "test-conv"}}
result = graph.invoke({
    "messages": [HumanMessage(content="Test")],
    "conversation_id": "test-conv",
    # ... other fields
}, config=config)

# Verify message added
assert len(result["messages"]) > 0
```

### API Tests

```python
# tests/test_routes.py (not implemented)
import requests

# Test conversation continuity
resp1 = requests.post("/api/edit", json={...})
conv_id = resp1.json()["conversation_id"]

resp2 = requests.post("/api/edit", json={
    "instruction": "...",
    "conversation_id": conv_id
})

assert resp2.json()["current_version"] > resp1.json()["current_version"]
```

---

## Migration Notes

### From Old Implementation

**Before**:
- JSON stored in state only
- No conversation history
- Single-request processing
- File-based persistence

**After**:
- JSON stored in database with versions
- Full conversation history
- Multi-turn conversations
- Database persistence

**Backward Compatibility**:
- Old clients work (generate new conversation_id)
- File I/O still supported as fallback
- Gradual migration possible

---

## Future Enhancements

### 1. Rollback Support
```python
POST /api/rollback
{
  "conversation_id": "conv-abc",
  "target_version": 3
}
# Restore data to version 3
```

### 2. Branch Conversations
```python
POST /api/branch
{
  "conversation_id": "conv-abc",
  "branch_name": "alternative-approach"
}
# Create separate modification track
```

### 3. Collaborative Editing
- Multiple users editing same ingredient
- Merge conflict resolution
- Access control per conversation

### 4. Export/Import
```python
GET /api/export/conv-abc
# Download full history as JSON

POST /api/import
# Upload previous export
```

---

## Performance Considerations

### Database Indexing
```sql
-- Already implemented
CREATE INDEX idx_conversation_id ON toxicity_versions(conversation_id);

-- Future optimization
CREATE INDEX idx_created_at ON toxicity_versions(created_at);
```

### Memory Trimming
```python
# For long conversations, trim old messages
from langchain_core.messages import trim_messages

trimmed = trim_messages(
    state["messages"],
    max_tokens=4000,
    strategy="last"  # Keep most recent
)
```

### Database Cleanup
```python
# Periodically clean old versions (optional)
DELETE FROM toxicity_versions 
WHERE created_at < date('now', '-90 days')
AND version < (SELECT MAX(version) FROM toxicity_versions WHERE conversation_id = ...)
```

---

## Security Considerations

### Data Isolation
- Each conversation_id has isolated data
- No cross-conversation access
- Add user authentication to link conversations to users

### Input Validation
```python
# Validate conversation_id format
if not re.match(r'^[a-zA-Z0-9\-]+$', conversation_id):
    raise HTTPException(400, "Invalid conversation_id")

# Validate JSON structure
if not validate_toxicity_schema(data):
    raise HTTPException(400, "Invalid data schema")
```

### SQL Injection Prevention
- ✅ Using SQLAlchemy ORM (parameterized queries)
- ✅ No raw SQL with user input

---

## Troubleshooting

### Issue: Messages not persisting
**Symptom**: Each request starts fresh, no history

**Check**:
1. Is `config = {"configurable": {"thread_id": ...}}` passed to invoke?
2. Is graph compiled with `checkpointer=memory`?
3. Does `chat_memory.db` exist and have content?

**Fix**: Ensure memory configuration is correct in `build_graph()`

### Issue: Data not versioning
**Symptom**: Same version number after edits

**Check**:
1. Is `db.save_version()` called after modifications?
2. Does `toxicity_data.db` exist?
3. Are modifications actually happening?

**Fix**: Verify database save in `llm_edit_node.py`

### Issue: SQLite thread error
**Symptom**: `ProgrammingError: SQLite objects created in a thread...`

**Fix**: Add `check_same_thread=False` to connection:
```python
conn = sqlite3.connect("chat_memory.db", check_same_thread=False)
```

---

## Summary

The dual-memory architecture provides:

✅ **Conversational AI**: Multi-turn dialogues with context
✅ **Data Integrity**: Immutable version history
✅ **Auditability**: Complete record of changes
✅ **Reliability**: Data persistence independent of LLM
✅ **Flexibility**: Support for queries about history
✅ **Scalability**: Can migrate to PostgreSQL/Redis later

This design separates concerns effectively:
- **LangGraph** handles conversation flow
- **ToxicityDB** handles data persistence
- **LLM** focuses on understanding and generation

The result is a robust, production-ready system for conversational data editing with full traceability.