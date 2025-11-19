# Complete Integration Guide: Your Toxicology Node + JSON Patch

## 🎯 Step-by-Step Integration

This guide shows exactly how to integrate the customized helper functions into your existing node.

---

## Phase 1: Preparation (5 minutes)

### Step 1: Backup Your Current Code

```bash
# Backup your current file
cp your_toxicology_module.py your_toxicology_module.py.backup
```

### Step 2: Install Dependencies (if needed)

```bash
pip install jsonpatch --break-system-packages
```

---

## Phase 2: Add Code Components (20 minutes)

### Step 3: Add Imports at Top of File

Add these imports at the top of your file:

```python
import jsonpatch
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any, List, Dict, Tuple
```

### Step 4: Add JSONPatchOperation Model

Add this after your imports and before your existing functions:

```python
# ============================================================================
# JSON PATCH MODEL
# ============================================================================

class JSONPatchOperation(BaseModel):
    """Structured output for LLM - enforces valid JSON Patch format"""
    op: Literal["add", "remove", "replace"] = Field(
        description="Operation type: add, remove, or replace"
    )
    path: str = Field(
        description="JSON Pointer path (e.g., '/acute_toxicity/-' or '/NOAEL/0')"
    )
    value: Optional[Any] = Field(
        default=None,
        description="Value for add/replace operations (not needed for remove)"
    )
```

### Step 5: Add Helper Function `_generate_patch_with_llm`

Add this function (find it in TOXICOLOGY_SCHEMA_HELPERS.md, lines 45-180):

```python
def _generate_patch_with_llm(
    llm,
    current_json: Dict,
    user_input: str,
    current_inci: str
) -> JSONPatchOperation:
    """
    Generate a JSON Patch operation using LLM
    CUSTOMIZED FOR YOUR TOXICOLOGY SCHEMA
    """
    
    system_prompt = f"""You are a JSON Patch operation generator for toxicology data.

Your task: Generate a SINGLE JSON Patch operation to update the JSON.

JSON STRUCTURE:
{{
  "inci": "Chemical INCI name",
  "cas": ["CAS numbers array"],
  "isSkip": boolean,
  "category": "CATEGORY_NAME",
  
  // Toxicology arrays (each contains objects with reference, data, source, statement, replaced)
  "acute_toxicity": [...],
  "skin_irritation": [...],
  "skin_sensitization": [...],
  "ocular_irritation": [...],
  "phototoxicity": [...],
  "repeated_dose_toxicity": [...],
  "percutaneous_absorption": [...],
  "ingredient_profile": [...],
  
  // Metric arrays (numerical values)
  "NOAEL": [...],
  "DAP": [...],
  
  "inci_ori": "original INCI name"
}}

COMMON MODIFICATION TYPES:

TYPE 1 - Toxicology Data Addition (毒理資料插補):
- Add complete entry to toxicology array
- Required fields: reference, data, source, statement, replaced
- Use path: "/<field_name>/-" to append to array
- Example: {{"op": "add", "path": "/acute_toxicity/-", "value": {{complete_entry}}}}

TYPE 2 - DAP Update:
- Update "DAP" array with new value
- Often paired with "percutaneous_absorption" update
- Use path: "/DAP/-" for append, "/DAP/0" for replace first

TYPE 3 - NOAEL Update:
- Update "NOAEL" array with new value
- Often paired with "repeated_dose_toxicity" update
- Use path: "/NOAEL/-" for append, "/NOAEL/0" for replace first

TYPE 4 - Basic Field Updates:
- INCI name: "/inci"
- CAS numbers: "/cas" or "/cas/-"
- Category: "/category"
- Skip flag: "/isSkip"

CRITICAL RULES:
1. Generate ONE operation per patch
2. For arrays: Use "/-" to APPEND, or "/index" to replace at index
3. For toxicology arrays, value must be complete object with required fields
4. For metric arrays (NOAEL, DAP), value is usually a number or object
5. Extract EXACT values from user's input

EXAMPLES:

User: "Add acute toxicity data: LD50 = 500 mg/kg, reference: Study 2023"
→ {{
    "op": "add",
    "path": "/acute_toxicity/-",
    "value": {{
        "reference": "Study 2023",
        "data": "LD50 = 500 mg/kg",
        "source": "",
        "statement": "",
        "replaced": false
    }}
}}

User: "Set NOAEL to 100 mg/kg"
→ {{
    "op": "add",
    "path": "/NOAEL/-",
    "value": 100
}}

User: "Update INCI name to Sodium Lauryl Sulfate"
→ {{
    "op": "replace",
    "path": "/inci",
    "value": "Sodium Lauryl Sulfate"
}}
"""
    
    # Build field list dynamically
    toxicology_fields_str = ", ".join(TOXICOLOGY_FIELDS)
    metric_fields_str = ", ".join(METRIC_FIELDS)
    
    user_prompt = f"""Current JSON:
{json.dumps(current_json, indent=2, ensure_ascii=False)}

Current INCI: {current_inci}

Available toxicology fields: {toxicology_fields_str}
Available metric fields: {metric_fields_str}

User instruction: "{user_input}"

Analyze the instruction and generate a JSON Patch operation:"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    return llm.invoke(messages)
```

### Step 6: Add Helper Function `_apply_patch_safely`

```python
def _apply_patch_safely(
    current_json: Dict,
    patch_op: JSONPatchOperation
) -> Tuple[Dict, bool]:
    """
    Apply patch with validation
    CUSTOMIZED FOR YOUR TOXICOLOGY SCHEMA
    
    Returns:
        (updated_json, success)
    """
    try:
        # Validate operation
        if patch_op.op in ["add", "replace"] and patch_op.value is None:
            print(f"⚠️ {patch_op.op} operation requires a value")
            return current_json, False
        
        if not patch_op.path.startswith('/'):
            print(f"⚠️ Path must start with '/', got: {patch_op.path}")
            return current_json, False
        
        # Extract field name from path
        path_parts = patch_op.path.split('/')
        field_name = path_parts[1] if len(path_parts) > 1 else None
        
        # Validate toxicology array entries
        if field_name in TOXICOLOGY_FIELDS and patch_op.op == "add":
            if isinstance(patch_op.value, dict):
                # Check for required fields
                required_fields = ["reference", "data", "source", "statement", "replaced"]
                missing_fields = [f for f in required_fields if f not in patch_op.value]
                
                if missing_fields:
                    print(f"⚠️ Toxicology entry missing required fields: {missing_fields}")
                    # Add default values for missing fields
                    for field in missing_fields:
                        if field == "replaced":
                            patch_op.value[field] = False
                        else:
                            patch_op.value[field] = ""
                    print(f"✓ Added default values for missing fields")
        
        # Validate metric fields (NOAEL, DAP)
        if field_name in METRIC_FIELDS and patch_op.op == "add":
            # Ensure value is numeric or valid format
            if not isinstance(patch_op.value, (int, float, str, dict)):
                print(f"⚠️ Metric value should be numeric or object, got: {type(patch_op.value)}")
                return current_json, False
        
        # Apply patch
        patch_list = [patch_op.model_dump(exclude_none=True)]
        updated_json = jsonpatch.apply_patch(
            current_json,
            patch_list,
            in_place=False
        )
        
        return updated_json, True
        
    except jsonpatch.JsonPatchException as e:
        print(f"⚠️ Invalid patch: {e}")
        return current_json, False
    except Exception as e:
        print(f"⚠️ Error applying patch: {e}")
        import traceback
        traceback.print_exc()
        return current_json, False
```

### Step 7: Add Helper Function `_fallback_to_full_json`

```python
def _fallback_to_full_json(
    state,
    llm,
    current_json: Dict,
    current_inci: str,
    conversation_id: str
):
    """
    Fallback to your original full JSON generation method
    """
    # Use your original LLM prompt
    prompt = _build_llm_prompt(current_json, state["user_input"], current_inci)
    
    try:
        result = llm.invoke(prompt)
        state["response"] = result.content
        
        # Parse and merge updates (your original logic)
        clean_content = clean_llm_json_output(result.content)
        print(f"DEBUG: Cleaned JSON (first 500 chars):\n{clean_content[:500]}")
        
        updates = json.loads(clean_content)
        merged_json = merge_json_updates(current_json, updates)
        
        response_msg = f"✅ Successfully updated {list(updates.keys())} for {current_inci}"
        
        # Save to DB (without patch since we generated full JSON)
        db.save_version(
            conversation_id=conversation_id,
            data=merged_json,
            modification_summary=f"Updated {', '.join(updates.keys())}"
        )
        
        ai_message = AIMessage(content=response_msg)
        
        state["json_data"] = merged_json
        state["response"] = response_msg
        state["messages"] = [ai_message]
        
    except json.JSONDecodeError as e:
        error_msg = f"⚠️ LLM output was not valid JSON: {str(e)}"
        ai_message = AIMessage(content=error_msg)
        state["response"] = error_msg
        state["error"] = error_msg
        state["json_data"] = current_json
        print(error_msg)
    
    return state
```

---

## Phase 3: Replace Your Node Function (15 minutes)

### Step 8: Create Enhanced Node Function

**Option A: Create New Function (Recommended for Testing)**

```python
def llm_edit_node_with_patch(state: JSONEditState) -> JSONEditState:
    """
    HYBRID: Process user input using JSON Patch for reliable updates
    CUSTOMIZED FOR YOUR TOXICOLOGY SCHEMA
    """
    # Setup LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(JSONPatchOperation)
    
    # Get conversation context from DB
    conversation_id = state.get("conversation_id")
    
    # Load current JSON from DB
    current_version_obj = db.get_current_version(conversation_id)
    if current_version_obj:
        current_json = json.loads(current_version_obj.data)
    else:
        current_json = state["json_data"]
    
    # Extract INCI name
    current_inci = extract_inci_name(state["user_input"])
    if not current_inci:
        current_inci = current_json.get("inci", "INCI_NAME")
    state["current_inci"] = current_inci
    
    # ========================================================================
    # PATH 1: Structured Data Extraction (FAST PATH - NO LLM)
    # ========================================================================
    toxicology_sections = extract_toxicology_sections(state["user_input"])
    
    if toxicology_sections:
        print("🚀 Using structured data extraction (fast path)")
        
        updated_json = current_json.copy()
        patches = []
        
        for section, data in toxicology_sections.items():
            if section in updated_json:
                # Apply your existing update logic
                updated_json[section] = update_toxicology_data(
                    updated_json[section], 
                    data
                )
                
                # ✨ NEW: Create patch for tracking
                if isinstance(data, list):
                    # Multiple entries
                    for item in data:
                        patch = JSONPatchOperation(
                            op="add",
                            path=f"/{section}/-",
                            value=item
                        )
                        patches.append(patch)
                else:
                    # Single entry
                    patch = JSONPatchOperation(
                        op="add",
                        path=f"/{section}/-",
                        value=data
                    )
                    patches.append(patch)
        
        response_msg = f"✅ Updated toxicology data for {current_inci}: {', '.join(toxicology_sections.keys())}"
        
        # Save to DB with patches
        db.save_version(
            conversation_id=conversation_id,
            data=updated_json,
            modification_summary=f"Updated {', '.join(toxicology_sections.keys())}",
            patch_operations=[p.model_dump() for p in patches]
        )
        
        ai_message = AIMessage(content=response_msg)
        
        state["json_data"] = updated_json
        state["response"] = response_msg
        state["messages"] = [ai_message]
        state["last_patches"] = patches  # ✨ NEW: Track patches
        
        return state
    
    # ========================================================================
    # PATH 2: JSON Patch Generation (NEW RELIABLE PATH)
    # ========================================================================
    print("🤖 Using LLM JSON Patch generation")
    
    try:
        # Generate JSON Patch operation using LLM
        patch_op = _generate_patch_with_llm(
            llm=structured_llm,
            current_json=current_json,
            user_input=state["user_input"],
            current_inci=current_inci
        )
        
        print(f"Generated patch: {patch_op.model_dump()}")
        
        # Validate and apply patch
        updated_json, patch_applied = _apply_patch_safely(
            current_json=current_json,
            patch_op=patch_op
        )
        
        if patch_applied:
            # Success!
            response_msg = f"✅ Applied {patch_op.op} operation at {patch_op.path} for {current_inci}"
            
            # Save to DB with patch
            db.save_version(
                conversation_id=conversation_id,
                data=updated_json,
                modification_summary=f"{patch_op.op} at {patch_op.path}",
                patch_operations=[patch_op.model_dump()]
            )
            
            ai_message = AIMessage(content=response_msg)
            
            state["json_data"] = updated_json
            state["response"] = response_msg
            state["messages"] = [ai_message]
            state["last_patches"] = [patch_op]  # ✨ NEW: Track patch
            
            return state
        else:
            # Patch failed - fallback
            print("⚠️ JSON Patch failed, falling back to full JSON generation")
            return _fallback_to_full_json(state, llm, current_json, current_inci, conversation_id)
    
    except Exception as e:
        # Error in patch generation - fallback
        print(f"⚠️ Error in patch generation: {e}, falling back to full JSON")
        import traceback
        traceback.print_exc()
        return _fallback_to_full_json(state, llm, current_json, current_inci, conversation_id)
```

**Option B: Replace Existing Function**

Simply rename your existing `llm_edit_node` to `llm_edit_node_old` and use the new function as `llm_edit_node`.

---

## Phase 4: Update Database (10 minutes)

### Step 9: Update Database Schema

Add the `patch_operations` column to your database:

```python
# If using SQLAlchemy with Alembic
"""
alembic revision -m "add_patch_operations"
"""

# In migration file:
def upgrade():
    op.add_column('json_versions', 
                  sa.Column('patch_operations', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('json_versions', 'patch_operations')
```

Or direct SQL:

```sql
ALTER TABLE json_versions ADD COLUMN patch_operations TEXT;
```

### Step 10: Update ToxicityDB.save_version()

Modify your `save_version` method:

```python
def save_version(
    self,
    conversation_id: str,
    data: Dict,
    modification_summary: str,
    patch_operations: Optional[List[Dict]] = None  # ✨ ADD THIS PARAMETER
):
    """
    Save version with optional patch operations
    """
    version = JSONVersion(
        conversation_id=conversation_id,
        data=json.dumps(data, ensure_ascii=False),  # Your existing logic
        modification_summary=modification_summary,
        timestamp=datetime.now()
    )
    
    # ✨ NEW: Store patches if provided
    if patch_operations:
        version.patch_operations = json.dumps(patch_operations, ensure_ascii=False)
    
    self.session.add(version)
    self.session.commit()
    
    return version
```

---

## Phase 5: Update Your Graph (2 minutes)

### Step 11: Update Graph Node Reference

If you created a new function (`llm_edit_node_with_patch`):

```python
# In your graph setup

# OLD
# graph.add_node("llm_edit", llm_edit_node)

# NEW
graph.add_node("llm_edit", llm_edit_node_with_patch)
```

If you replaced the existing function, no changes needed!

---

## Phase 6: Testing (10 minutes)

### Step 12: Test Structured Data Path

```python
# Test 1: Structured toxicology data
test_input = "Oral LD50: 500 mg/kg, reference: Study 2023"

result = graph.invoke({
    "user_input": test_input,
    "json_data": current_json,
    "conversation_id": "test-001"
})

# Verify:
assert "acute_toxicity" in result["json_data"]
assert result.get("last_patches") is not None
print("✅ Test 1 passed: Structured data with patches")
```

### Step 13: Test JSON Patch Path

```python
# Test 2: Natural language (should generate patch)
test_input = "Add NOAEL value of 100 mg/kg"

result = graph.invoke({
    "user_input": test_input,
    "json_data": current_json,
    "conversation_id": "test-002"
})

# Verify:
assert 100 in result["json_data"]["NOAEL"]
assert len(result.get("last_patches", [])) > 0
print("✅ Test 2 passed: JSON Patch generation")
```

### Step 14: Test Fallback Path

```python
# Test 3: Complex update (might use fallback)
test_input = "Update all toxicity values and regulatory status comprehensively"

result = graph.invoke({
    "user_input": test_input,
    "json_data": current_json,
    "conversation_id": "test-003"
})

# Verify:
assert result["response"]  # Should have response
print("✅ Test 3 passed: Fallback path")
```

### Step 15: Verify Database Storage

```python
# Check patches are stored in DB
from sqlalchemy import text

with db.engine.connect() as conn:
    result = conn.execute(text("""
        SELECT patch_operations 
        FROM json_versions 
        WHERE conversation_id = 'test-001'
        ORDER BY id DESC 
        LIMIT 1
    """))
    
    row = result.fetchone()
    if row and row[0]:
        patches = json.loads(row[0])
        print(f"✅ Database test passed: {len(patches)} patches stored")
        for patch in patches:
            print(f"  - {patch['op']} at {patch['path']}")
    else:
        print("⚠️ No patches in database")
```

---

## Complete File Structure

After integration, your file should look like:

```python
# ============================================================================
# IMPORTS
# ============================================================================
import json
import jsonpatch  # ✨ NEW
from pydantic import BaseModel, Field  # ✨ NEW
from typing import Literal, Optional, Any, List, Dict, Tuple  # ✨ UPDATED
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
# ... your other imports


# ============================================================================
# CONSTANTS (YOUR EXISTING)
# ============================================================================
TOXICOLOGY_FIELDS = [...]
METRIC_FIELDS = [...]
JSON_TEMPLATE = {...}


# ============================================================================
# JSON PATCH MODEL (✨ NEW)
# ============================================================================
class JSONPatchOperation(BaseModel):
    ...


# ============================================================================
# DATABASE SETUP (YOUR EXISTING)
# ============================================================================
db = ToxicityDB()


# ============================================================================
# YOUR EXISTING HELPER FUNCTIONS
# ============================================================================
def extract_inci_name(...):
    ...

def extract_toxicology_sections(...):
    ...

def update_toxicology_data(...):
    ...

def _build_llm_prompt(...):
    ...

def clean_llm_json_output(...):
    ...

def merge_json_updates(...):
    ...


# ============================================================================
# NEW JSON PATCH HELPER FUNCTIONS (✨ NEW)
# ============================================================================
def _generate_patch_with_llm(...):
    ...

def _apply_patch_safely(...):
    ...

def _fallback_to_full_json(...):
    ...


# ============================================================================
# YOUR OLD NODE (KEEP FOR REFERENCE)
# ============================================================================
def llm_edit_node_old(state: JSONEditState) -> JSONEditState:
    """Your original node - kept as backup"""
    ...


# ============================================================================
# NEW ENHANCED NODE (✨ NEW)
# ============================================================================
def llm_edit_node_with_patch(state: JSONEditState) -> JSONEditState:
    """Enhanced with JSON Patch"""
    ...


# ============================================================================
# GRAPH SETUP (YOUR EXISTING, UPDATE NODE REFERENCE)
# ============================================================================
graph = StateGraph(JSONEditState)
graph.add_node("llm_edit", llm_edit_node_with_patch)  # ✨ UPDATED
# ... rest of graph
```

---

## Troubleshooting

### Issue: "JSONPatchOperation not defined"

**Fix:**
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
```

### Issue: "structured_llm not found"

**Fix:** Add after creating llm:
```python
structured_llm = llm.with_structured_output(JSONPatchOperation)
```

### Issue: Database error "no such column"

**Fix:** Run migration:
```sql
ALTER TABLE json_versions ADD COLUMN patch_operations TEXT;
```

### Issue: Patches always failing, using fallback

**Check:**
1. Print the generated patch: `print(patch_op.model_dump())`
2. Check if paths are correct for your JSON structure
3. Verify LLM is generating valid field names

### Issue: Missing required fields in toxicology entries

**Good news:** The `_apply_patch_safely` function auto-fills missing fields!
It will add defaults:
- `reference`, `data`, `source`, `statement`: "" (empty string)
- `replaced`: False

---

## Summary

**What Changed:**
- ✅ Added 3 helper functions (~150 lines)
- ✅ Enhanced your node with JSON Patch path
- ✅ Added 1 database column
- ✅ All your existing logic preserved!

**What Stayed the Same:**
- ✅ Your structured data extraction (fastest path)
- ✅ Your database structure (just 1 column added)
- ✅ Your conversation tracking
- ✅ Your INCI extraction
- ✅ Your graph structure

**Time:** ~1 hour total

**Result:** More reliable, better tracking, lower cost, same workflow!

---

## Next Steps

1. ✅ Complete integration following steps above
2. ✅ Test with your data
3. ✅ Monitor patch vs fallback usage
4. ✅ Adjust system prompts if needed
5. ✅ Deploy to production

Good luck! 🚀
