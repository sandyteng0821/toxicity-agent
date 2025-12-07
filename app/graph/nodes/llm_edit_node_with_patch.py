"""
LLM node for processing toxicology edit instructions
"""
import json
import jsonpatch
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any, List, Dict, Tuple, Union
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import DEFAULT_LLM_MODEL, TOXICOLOGY_FIELDS, METRIC_FIELDS
from app.graph.state import JSONEditState
from app.services.text_processing import (
    extract_inci_name,
    extract_toxicology_sections,
    clean_llm_json_output
)
from app.services.data_updater import (
    merge_json_updates, 
    update_toxicology_data
)
from core.database import ToxicityDB

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
    value: Union[str, int, float, bool, dict, list, None] = Field(
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
            inci_name=state.get("current_inci", "INCI_NAME"),
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

# Initialize DB at module level
db = ToxicityDB()

def llm_edit_node_with_patch(state: JSONEditState) -> JSONEditState:
    """
    HYBRID: Process user input using JSON Patch for reliable updates
    CUSTOMIZED FOR YOUR TOXICOLOGY SCHEMA
    """
    # Setup LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(JSONPatchOperation, method="function_calling")
    
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
        # db.save_version(
        #     conversation_id=conversation_id,
        #     inci_name=state.get("current_inci", "INCI_NAME"),
        #     data=updated_json,
        #     modification_summary=f"Updated {', '.join(toxicology_sections.keys())}",
        #     patch_operations=[p.model_dump() for p in patches]
        # )
        db.save_modification( # 1. MIGRATION: Replaced save_version
            item_id=conversation_id,
            inci_name=state.get("current_inci", "INCI_NAME"),
            data=updated_json,
            instruction=state["user_input"], # 2. NEW PARAMETER: Replaced modification_summary
            patch_operations=[p.model_dump() for p in patches],
            is_batch_item=False, # 3. NEW AUDIT FLAG
            patch_success=True 
        )
        
        ai_message = AIMessage(content=response_msg)
        
        state["json_data"] = updated_json
        state["response"] = response_msg
        state["messages"] = [ai_message]
        state["last_patches"] = [patch_op.model_dump()]  # ✨ NEW: Track patches
        
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
            # db.save_version(
            #     conversation_id=conversation_id,
            #     inci_name=state.get("current_inci", "INCI_NAME"),
            #     data=updated_json,
            #     modification_summary=f"{patch_op.op} at {patch_op.path}",
            #     patch_operations=[patch_op.model_dump()]
            # )
            db.save_modification( # 1. MIGRATION: Replaced save_version
                item_id=conversation_id,
                inci_name=state.get("current_inci", "INCI_NAME"),
                data=updated_json,
                instruction=state["user_input"], # 2. NEW PARAMETER: Replaced modification_summary
                patch_operations=[patch_op.model_dump()],
                is_batch_item=False, # 3. NEW AUDIT FLAG
                patch_success=True
            )
            
            ai_message = AIMessage(content=response_msg)
            
            state["json_data"] = updated_json
            state["response"] = response_msg
            state["messages"] = [ai_message]
            state["last_patches"] = [patch_op.model_dump()] # ✨ NEW: Track patch
            
            return state
        else:
            # Patch failed - fallback
            print("⚠️ JSON Patch failed, falling back to full JSON generation")
            state["last_patches"] = []
            return _fallback_to_full_json(state, llm, current_json, current_inci, conversation_id)
    
    except Exception as e:
        # Error in patch generation - fallback
        print(f"⚠️ Error in patch generation: {e}, falling back to full JSON")
        import traceback
        traceback.print_exc()
        return _fallback_to_full_json(state, llm, current_json, current_inci, conversation_id)

# version v1.1.0 -> relatively stable prompt for minimal toxicity data adjustment (model: gpt-4o-mini correctness ~ 95% (reset data first))
def llm_edit_node(state: JSONEditState) -> JSONEditState:
    """
    Process user input and update JSON using LLM
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with modified JSON data
    """
    # llm = ChatOllama(model=DEFAULT_LLM_MODEL)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # It works. # need to have API key in .env
    
    # Get conversation context from DB
    conversation_id = state.get("conversation_id")
    # Load current JSON from DB (not from state)
    current_version_obj = db.get_current_version(conversation_id)
    if current_version_obj:
        current_json = json.loads(current_version_obj.data)
    else:
        # Fallback to state if no DB version exists
        current_json = state["json_data"]

    # Extract INCI name
    current_inci = extract_inci_name(state["user_input"])
    if not current_inci:
        current_inci = state["json_data"].get("inci", "INCI_NAME")
    state["current_inci"] = current_inci
    
    # Try structured data extraction first
    toxicology_sections = extract_toxicology_sections(state["user_input"])
    
    if toxicology_sections:
        # Direct update without LLM
        # updated_json = state["json_data"].copy()
        updated_json = update_toxicology_data(
                    updated_json[section], 
                    data
                )
        response_msg = f"✅ Updated toxicology data for {current_inci}"
        
        for section, data in toxicology_sections.items():
            if section in updated_json:
                updated_json[section] = update_toxicology_data(
                    updated_json[section], 
                    data
                )
        
        # Save to DB
        db.save_version(
            conversation_id=conversation_id,
            inci_name=state.get("current_inci", "INCI_NAME"),
            data=updated_json,
            modification_summary=f"Updated {', '.join(toxicology_sections.keys())}"
        )
        # Add to chat history
        ai_message = AIMessage(content=response_msg)

        state["json_data"] = updated_json
        state["response"] = response_msg
        state["messages"] = [ai_message]
        return state
    
    # Use LLM for natural language processing
    # prompt = _build_llm_prompt(state["json_data"], state["user_input"], current_inci)
    prompt = _build_llm_prompt(current_json, state["user_input"], current_inci)

    try:
        result = llm.invoke(prompt)
        state["response"] = result.content
        
        # Parse and merge updates
        clean_content = clean_llm_json_output(result.content)
        print(f"DEBUG: Cleaned JSON (first 500 chars):\n{clean_content[:500]}")
        
        updates = json.loads(clean_content)
        # merged_json = merge_json_updates(state["json_data"], updates)
        merged_json = merge_json_updates(current_json, updates)

        response_msg = f"✅ Successfully updated {list(updates.keys())} for {current_inci}"

        # NEW: Save to DB
        db.save_version(
            conversation_id=conversation_id,
            inci_name=state.get("current_inci", "INCI_NAME"),
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


# # baseline => gpt-4o-mini correctness ~ 73.9% (=> cheating issue)
# def _build_llm_prompt(json_data: dict, user_input: str, current_inci: str) -> str:
#     """
#     Build the prompt for LLM processing
    
#     Args:
#         json_data: Current JSON structure
#         user_input: User's instruction
#         current_inci: Current ingredient name
        
#     Returns:
#         Formatted prompt string
#     """
#     json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
    
#     return f"""You are a toxicology data specialist for cosmetic ingredients. Update JSON for INCI: {current_inci}

# Current JSON Structure:
# {json_str}

# User Instruction:
# {user_input}

# COMMON MODIFICATION TYPES:

# TYPE 1 - Toxicology Data Addition (毒理資料插補):
# - Add complete entry to toxicology array (acute_toxicity, skin_irritation, etc.)
# - Required fields: reference, data, source, statement, replaced
# - Action: Return ONLY the new entry to append

# TYPE 2 - DAP Update:
# - Update "DAP" array with new value
# - Update "percutaneous_absorption" array with supporting data
# - Return: {{"DAP": [...], "percutaneous_absorption": [...]}}

# TYPE 3 - NOAEL Update:
# - Update "NOAEL" array with new value
# - Update "repeated_dose_toxicity" array with supporting data
# - Return: {{"NOAEL": [...], "repeated_dose_toxicity": [...]}}

# CRITICAL RULES:
# 1. Return ONLY the fields that need to be updated
# 2. Do NOT use [...] or "..." placeholders - provide actual complete data
# 3. Do NOT return the entire JSON - only changed fields
# 4. Field names must be lowercase ("inci", not "INCI")
# 5. Return valid JSON only, no explanations

# EXAMPLES:

# Example 1 (TYPE 3 - NOAEL Update):
# Input: "Set NOAEL to 800 mg/kg bw/day from ECHA, add repeated dose toxicity study"
# Output:
# {{
#   "inci": "PETROLATUM",
#   "NOAEL": [
#     {{
#       "note": null,
#       "unit": "mg/kg bw/day",
#       "experiment_target": "Rats",
#       "source": "echa",
#       "type": "NOAEL",
#       "study_duration": "90-day",
#       "value": 800
#     }}
#   ],
#   "repeated_dose_toxicity": [
#     {{
#       "reference": {{
#         "title": "ECHA Registration Dossier",
#         "link": "https://echa.europa.eu"
#       }},
#       "data": ["90-day oral toxicity study in rats showed NOAEL of 800 mg/kg bw/day"],
#       "source": "echa",
#       "statement": "Based on repeated dose toxicity studies",
#       "replaced": {{
#         "replaced_inci": "",
#         "replaced_type": ""
#       }}
#     }}
#   ]
# }}

# Example 2 (TYPE 2 - DAP Update):
# Input: "Set DAP to 10% based on expert judgment"
# Output:
# {{
#   "inci": "INGREDIENT_NAME",
#   "DAP": [
#     {{
#       "note": "Expert assessment",
#       "unit": "%",
#       "experiment_target": null,
#       "source": "expert",
#       "type": "DAP",
#       "study_duration": null,
#       "value": 10
#     }}
#   ],
#   "percutaneous_absorption": [
#     {{
#       "reference": {{
#         "title": "Expert Assessment",
#         "link": null
#       }},
#       "data": ["Dermal absorption estimated at 10% based on molecular properties"],
#       "source": "expert",
#       "statement": "Conservative estimate for safety assessment",
#       "replaced": {{
#         "replaced_inci": "",
#         "replaced_type": ""
#       }}
#     }}
#   ]
# }}

# Now analyze the instruction and return ONLY the fields to update with COMPLETE data (no [...] placeholders):
# """

# prompt v1 
def _build_llm_prompt(json_data: dict, user_input: str, current_inci: str) -> str:
    """
    Build the prompt for LLM processing with anti-cheating measures
    
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

═══════════════════════════════════════════════════════════════════
USER INSTRUCTION FOR {current_inci} (READ THIS CAREFULLY):
═══════════════════════════════════════════════════════════════════
{user_input}
═══════════════════════════════════════════════════════════════════

COMMON MODIFICATION TYPES:

TYPE 1 - Toxicology Data Addition (毒理資料插補):
- Add complete entry to toxicology array (acute_toxicity, skin_irritation, etc.)
- Required fields: reference, data, source, statement, replaced
- Action: Return ONLY the new entry to append

TYPE 2 - DAP Update:
- Update "DAP" array with new value
- Update "percutaneous_absorption" array with supporting data
- Return: {{"DAP": [...], "percutaneous_absorption": [...]}}

TYPE 3 - NOAEL Update:
- Update "NOAEL" array with new value
- Update "repeated_dose_toxicity" array with supporting data
- Return: {{"NOAEL": [...], "repeated_dose_toxicity": [...]}}

CRITICAL RULES:
1. Return ONLY the fields that need to be updated
2. Do NOT use [...] or "..." placeholders - provide actual complete data
3. Do NOT return the entire JSON - only changed fields
4. Field names must be lowercase ("inci", not "INCI")
5. Return valid JSON only, no explanations
6. Extract ALL values from the user instruction above
7. If a field is NOT mentioned in the instruction, set it to null
8. DO NOT copy values from examples below - they use placeholder data only

CRITICAL FIELD-FILLING RULES:
→ If instruction specifies a value → Extract and use that exact value
→ If instruction does NOT specify a value → Use null (not example values)
→ Examples below use {{PLACEHOLDER}} notation - replace with instruction data
→ Never copy literal values from examples (they are templates, not real data)

STRUCTURE EXAMPLES (Templates with placeholders - extract real values from instruction):

Example 1 (TYPE 3 - NOAEL Update Pattern):
Input Pattern: "Set NOAEL to {{VALUE}} {{UNIT}} from {{SOURCE}}, add repeated dose toxicity study"
Output Structure:
{{
  "inci": "{current_inci}",
  "NOAEL": [
    {{
      "note": {{EXTRACT_NOTE_FROM_INSTRUCTION_OR_NULL}},
      "unit": "{{EXTRACT_UNIT_FROM_INSTRUCTION}}",
      "experiment_target": {{EXTRACT_TARGET_FROM_INSTRUCTION_OR_NULL}},
      "source": "{{EXTRACT_SOURCE_FROM_INSTRUCTION_LOWERCASE}}",
      "type": "NOAEL",
      "study_duration": {{EXTRACT_DURATION_FROM_INSTRUCTION_OR_NULL}},
      "value": {{EXTRACT_NUMERIC_VALUE_FROM_INSTRUCTION}}
    }}
  ],
  "repeated_dose_toxicity": [
    {{
      "reference": {{
        "title": "{{CREATE_APPROPRIATE_TITLE_FROM_SOURCE}}",
        "link": "{{EXTRACT_URL_FROM_INSTRUCTION_OR_NULL}}"
      }},
      "data": ["{{SUMMARIZE_KEY_FINDINGS_FROM_INSTRUCTION}}"],
      "source": "{{SAME_AS_NOAEL_SOURCE}}",
      "statement": "{{CREATE_SUMMARY_STATEMENT}}",
      "replaced": {{
        "replaced_inci": "",
        "replaced_type": ""
      }}
    }}
  ]
}}

Concrete example showing extraction:
Input: "Set NOAEL to 150 mg/kg bw/day from FDA GRAS notice"
Extraction Process:
  - VALUE: 150 (from "150 mg/kg")
  - UNIT: "mg/kg bw/day" (from instruction)
  - SOURCE: "fda" (from "FDA", lowercase)
  - TARGET: null (NOT mentioned in instruction)
  - DURATION: null (NOT mentioned in instruction)
  - REFERENCE_TITLE: "FDA GRAS Notice" (created from source)
  - LINK: null (not provided in instruction)
Output:
{{
  "inci": "{{INGREDIENT_FROM_INSTRUCTION}}",
  "NOAEL": [
    {{
      "note": null,
      "unit": "mg/kg bw/day",
      "experiment_target": null,
      "source": "fda",
      "type": "NOAEL",
      "study_duration": null,
      "value": 150
    }}
  ],
  "repeated_dose_toxicity": [
    {{
      "reference": {{
        "title": "FDA GRAS Notice",
        "link": null
      }},
      "data": ["NOAEL of 150 mg/kg bw/day established based on FDA assessment"],
      "source": "fda",
      "statement": "Based on FDA GRAS assessment",
      "replaced": {{
        "replaced_inci": "",
        "replaced_type": ""
      }}
    }}
  ]
}}

Example 2 (TYPE 2 - DAP Update Pattern):
Input Pattern: "Set DAP to {{VALUE}}% based on {{REASONING}}"
Output Structure:
{{
  "inci": "{current_inci}",
  "DAP": [
    {{
      "note": "{{EXTRACT_REASONING_AS_NOTE}}",
      "unit": "%",
      "experiment_target": null,
      "source": "{{DETERMINE_SOURCE_TYPE}}",
      "type": "DAP",
      "study_duration": null,
      "value": {{EXTRACT_NUMERIC_VALUE_FROM_INSTRUCTION}}
    }}
  ],
  "percutaneous_absorption": [
    {{
      "reference": {{
        "title": "{{CREATE_APPROPRIATE_TITLE}}",
        "link": {{EXTRACT_URL_OR_NULL}}
      }},
      "data": ["{{EXTRACT_REASONING_FROM_INSTRUCTION}}"],
      "source": "{{SAME_AS_DAP_SOURCE}}",
      "statement": "{{SUMMARIZE_REASONING}}",
      "replaced": {{
        "replaced_inci": "",
        "replaced_type": ""
      }}
    }}
  ]
}}

Concrete example showing extraction:
Input: "Set DAP to 7% based on molecular weight and lipophilicity considerations"
Extraction Process:
  - VALUE: 7 (from "7%")
  - REASONING: "molecular weight and lipophilicity considerations"
  - SOURCE: "expert" (inferred from "based on" phrasing)
  - TITLE: "Expert Assessment of Dermal Absorption"
Output:
{{
  "inci": "{{INGREDIENT_FROM_INSTRUCTION}}",
  "DAP": [
    {{
      "note": "Based on molecular weight and lipophilicity considerations",
      "unit": "%",
      "experiment_target": null,
      "source": "expert",
      "type": "DAP",
      "study_duration": null,
      "value": 7
    }}
  ],
  "percutaneous_absorption": [
    {{
      "reference": {{
        "title": "Expert Assessment of Dermal Absorption",
        "link": null
      }},
      "data": ["Dermal absorption estimated at 7% considering molecular weight and lipophilicity"],
      "source": "expert",
      "statement": "Based on physicochemical properties",
      "replaced": {{
        "replaced_inci": "",
        "replaced_type": ""
      }}
    }}
  ]
}}

Example 3 (Sparse Data - Showing Proper Null Handling):
Input: "Set NOAEL to 250 mg/kg bw/day from WHO report"
Note: Only value, unit, and source are mentioned
Output:
{{
  "inci": "{{INGREDIENT_FROM_INSTRUCTION}}",
  "NOAEL": [
    {{
      "note": null,                    // ← NOT mentioned, so null
      "unit": "mg/kg bw/day",
      "experiment_target": null,       // ← NOT mentioned, so null (not "Rats"!)
      "source": "who",
      "type": "NOAEL",
      "study_duration": null,          // ← NOT mentioned, so null (not "90-day"!)
      "value": 250
    }}
  ],
  "repeated_dose_toxicity": [
    {{
      "reference": {{
        "title": "WHO Report",
        "link": null
      }},
      "data": ["NOAEL of 250 mg/kg bw/day reported by WHO"],
      "source": "who",
      "statement": "Based on WHO assessment",
      "replaced": {{
        "replaced_inci": "",
        "replaced_type": ""
      }}
    }}
  ]
}}

⚠️ COMMON MISTAKES TO AVOID:

❌ WRONG - Copying placeholder values:
Instruction: "Set NOAEL to 200 mg/kg bw/day from OECD"
Wrong Output: {{"value": 150, "source": "fda"}}  ← Used values from example!
Correct Output: {{"value": 200, "source": "oecd"}}  ← Extracted from instruction!

❌ WRONG - Filling unspecified fields with example data:
Instruction: "Set NOAEL to 300 mg/kg bw/day from CIR"
Wrong Output: {{"experiment_target": "Rats", "study_duration": "90-day"}}  ← Not in instruction!
Correct Output: {{"experiment_target": null, "study_duration": null}}  ← Correctly null!

❌ WRONG - Using example ingredient names:
Instruction for {current_inci}: "Set NOAEL to 400"
Wrong Output: {{"inci": "INGREDIENT_NAME"}}  ← Generic placeholder!
Correct Output: {{"inci": "{current_inci}"}}  ← Actual ingredient name!

✅ CORRECT PATTERN:
1. Read the user instruction for {current_inci} carefully
2. Extract each specified value (numbers, units, sources, URLs)
3. For fields NOT mentioned in instruction → use null
4. Create appropriate reference titles based on the source
5. Summarize findings in your own words based on instruction content

FINAL VERIFICATION CHECKLIST:
□ Did I use {current_inci} as the INCI name?
□ Did I extract the numeric value from the instruction (not from examples)?
□ Did I extract the source from the instruction (not from examples)?
□ Did I set unmentioned fields to null (not filled with example values)?
□ Is my output valid JSON with complete data (no placeholders like {{...}})?
□ Did I create appropriate descriptions based on instruction content?

Now analyze the user instruction above and return ONLY the fields to update with COMPLETE data extracted from the instruction:
"""