"""
LLM node for processing toxicology edit instructions 
(Refactored version from app/graph/nodes/llm_edit_node_with_patch.py)
"""
import json

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import DEFAULT_LLM_MODEL, TOXICOLOGY_FIELDS, METRIC_FIELDS
from app.graph.state import JSONEditState
from app.services.text_processing import (
    extract_inci_name,
    extract_toxicology_sections
)
from app.services.data_updater import (
    update_toxicology_data
)
from core.database import ToxicityDB
from ..utils.schema_tools import JSONPatchOperation
from ..utils.patch_utils import (
    _generate_patch_with_llm,
    _apply_patch_safely,
    _fallback_to_full_json
)

# ============================================================================
# EDIT ORCHESTRATOR (LANGGRAPH NODE)
# ============================================================================
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