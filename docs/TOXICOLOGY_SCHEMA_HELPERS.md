# Helper Functions for Your Toxicology Schema

## Updated Helper Functions for Your JSON Structure

```python
import json
import jsonpatch
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# ============================================================================
# YOUR SCHEMA CONSTANTS
# ============================================================================

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


# ============================================================================
# ENHANCED HELPER FUNCTIONS FOR YOUR SCHEMA
# ============================================================================

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

COMMON PATHS:
- Append to acute toxicity: "/acute_toxicity/-"
- Append to skin irritation: "/skin_irritation/-"
- Append to NOAEL: "/NOAEL/-"
- Replace first NOAEL: "/NOAEL/0"
- Append to DAP: "/DAP/-"
- Update INCI: "/inci"
- Add CAS number: "/cas/-"

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

User: "Add CAS number 68585-34-2"
→ {{
    "op": "add",
    "path": "/cas/-",
    "value": "68585-34-2"
}}

User: "Mark as skip"
→ {{
    "op": "replace",
    "path": "/isSkip",
    "value": true
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


def _apply_patch_safely(
    current_json: Dict,
    patch_op: JSONPatchOperation
) -> tuple[Dict, bool]:
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


def _create_patch_from_structured_update(
    section: str,
    data: Any,
    operation: str = "add"
) -> JSONPatchOperation:
    """
    Create a patch operation from your structured data extraction
    
    This converts your existing structured updates to patches for tracking.
    
    Args:
        section: Field name (e.g., "acute_toxicity", "NOAEL")
        data: The data to add/update
        operation: "add" or "replace"
    
    Returns:
        JSONPatchOperation for tracking
    """
    # Determine path based on operation
    if operation == "add":
        path = f"/{section}/-"  # Append to array
    else:
        path = f"/{section}"  # Replace entire field
    
    return JSONPatchOperation(
        op=operation,
        path=path,
        value=data
    )


def _apply_multi_field_update(
    current_json: Dict,
    updates: Dict[str, Any]
) -> tuple[Dict, List[JSONPatchOperation]]:
    """
    Apply multiple field updates and return patches for tracking
    
    This is useful for TYPE 2 (DAP Update) and TYPE 3 (NOAEL Update)
    where you update multiple fields together.
    
    Args:
        current_json: Current JSON data
        updates: Dictionary of field updates {field_name: new_data}
    
    Returns:
        (updated_json, list_of_patches)
    """
    updated_json = current_json.copy()
    patches = []
    
    for field, data in updates.items():
        if field in updated_json:
            # For arrays, append
            if isinstance(updated_json[field], list):
                if isinstance(data, list):
                    # If data is array, extend
                    for item in data:
                        patch = JSONPatchOperation(
                            op="add",
                            path=f"/{field}/-",
                            value=item
                        )
                        patches.append(patch)
                        updated_json[field].append(item)
                else:
                    # Single item, append
                    patch = JSONPatchOperation(
                        op="add",
                        path=f"/{field}/-",
                        value=data
                    )
                    patches.append(patch)
                    updated_json[field].append(data)
            else:
                # Replace entire field
                patch = JSONPatchOperation(
                    op="replace",
                    path=f"/{field}",
                    value=data
                )
                patches.append(patch)
                updated_json[field] = data
    
    return updated_json, patches


# ============================================================================
# FALLBACK FUNCTION (YOUR ORIGINAL METHOD)
# ============================================================================

def _fallback_to_full_json(
    state,
    llm,
    current_json: Dict,
    current_inci: str,
    conversation_id: str
) -> Any:
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
        
        from langchain_core.messages import AIMessage
        ai_message = AIMessage(content=response_msg)
        
        state["json_data"] = merged_json
        state["response"] = response_msg
        state["messages"] = [ai_message]
        
    except json.JSONDecodeError as e:
        error_msg = f"⚠️ LLM output was not valid JSON: {str(e)}"
        from langchain_core.messages import AIMessage
        ai_message = AIMessage(content=error_msg)
        state["response"] = error_msg
        state["error"] = error_msg
        state["json_data"] = current_json
        print(error_msg)
    
    return state


# ============================================================================
# ENHANCED NODE FOR YOUR TOXICOLOGY SCHEMA
# ============================================================================

def llm_edit_node_with_patch(state) -> Any:
    """
    HYBRID: Process user input using JSON Patch for reliable updates
    CUSTOMIZED FOR YOUR TOXICOLOGY SCHEMA
    
    Features:
    - ✅ Your DB, conversation, INCI extraction (unchanged)
    - ✅ Your structured data extraction (enhanced with patch tracking)
    - ✅ JSON Patch for LLM edits (new reliable path)
    - ✅ Graceful fallback to your original method
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import AIMessage
    
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
        state["last_patches"] = patches
        
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
            state["last_patches"] = [patch_op]
            
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


# ============================================================================
# EXAMPLE: Handling Multi-Field Updates (TYPE 2 & TYPE 3)
# ============================================================================

def handle_dap_update(current_json: Dict, dap_value: float, supporting_data: Dict):
    """
    Example: Handle TYPE 2 - DAP Update with percutaneous_absorption
    
    This shows how to handle your complex update types.
    """
    updates = {
        "DAP": dap_value,
        "percutaneous_absorption": supporting_data
    }
    
    updated_json, patches = _apply_multi_field_update(current_json, updates)
    
    return updated_json, patches


def handle_noael_update(current_json: Dict, noael_value: float, supporting_data: Dict):
    """
    Example: Handle TYPE 3 - NOAEL Update with repeated_dose_toxicity
    """
    updates = {
        "NOAEL": noael_value,
        "repeated_dose_toxicity": supporting_data
    }
    
    updated_json, patches = _apply_multi_field_update(current_json, updates)
    
    return updated_json, patches


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
EXAMPLE 1: Structured Data (Fast Path)
---------------------------------------
Input: "Oral LD50: 500 mg/kg, reference: Study 2023"

Flow:
1. extract_toxicology_sections() detects structured data ✓
2. Direct update to acute_toxicity array
3. Generate patches for tracking:
   [{
     "op": "add",
     "path": "/acute_toxicity/-",
     "value": {
       "reference": "Study 2023",
       "data": "Oral LD50: 500 mg/kg",
       "source": "",
       "statement": "",
       "replaced": false
     }
   }]
4. Save with patches ✓


EXAMPLE 2: Natural Language (Patch Path)
-----------------------------------------
Input: "Add NOAEL value of 100 mg/kg"

Flow:
1. No structured data detected
2. LLM generates patch:
   {
     "op": "add",
     "path": "/NOAEL/-",
     "value": 100
   }
3. Validate patch ✓
4. Apply patch ✓
5. Save with patch ✓


EXAMPLE 3: Complex Multi-Field Update
--------------------------------------
Input: "Set DAP to 0.5 based on percutaneous study XYZ"

Flow:
1. No structured data detected
2. LLM generates first patch for DAP
3. You might need second patch for percutaneous_absorption
4. Either:
   a) Generate two patches sequentially, OR
   b) Use fallback for complex multi-field updates


EXAMPLE 4: INCI Update
-----------------------
Input: "Change INCI name to Sodium Lauryl Sulfate"

Flow:
1. LLM generates patch:
   {
     "op": "replace",
     "path": "/inci",
     "value": "Sodium Lauryl Sulfate"
   }
2. Apply ✓
3. Save ✓
"""
```

---

## Key Customizations for Your Schema

### 1. **System Prompt Customized**
- Includes your exact field names (TOXICOLOGY_FIELDS, METRIC_FIELDS)
- Documents your 3 modification types
- Provides examples with correct structure

### 2. **Validation Enhanced**
- Checks for required fields in toxicology entries
- Auto-fills missing fields with defaults
- Validates metric field types

### 3. **Multi-Field Support**
- Helper functions for DAP/NOAEL updates
- Can track multiple patches for related updates

### 4. **Array Operations**
- Proper "/-" for appending to arrays
- Index-based updates for replacements

---

## Integration Notes

1. **Structured Data Path** remains fastest (unchanged logic + patch tracking)
2. **JSON Patch Path** handles single-field updates reliably
3. **Fallback Path** handles complex multi-field updates

For your TYPE 2 and TYPE 3 (DAP/NOAEL with supporting data), you might want to:
- Option A: Generate multiple patches sequentially
- Option B: Use fallback for these complex cases
- Option C: Enhance structured extraction to detect these patterns

The code above supports all three approaches!
