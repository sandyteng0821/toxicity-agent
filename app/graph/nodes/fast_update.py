# nodes/fast_update.py
from langchain_core.messages import AIMessage

from core.database import ToxicityDB
from app.services.data_updater import update_toxicology_data
from ..utils.schema_tools import JSONPatchOperation

# ============================================================================
# Structured Data Extraction (FAST PATH - NO LLM) (LANGGRAPH NODE)
# ============================================================================
# Initialize DB at module level
db = ToxicityDB()

def fast_update_node(state):
    """"""
    # toxicology_sections = extract_toxicology_sections(state["user_input"])
    toxicology_sections = state["structured_sections"]
    current_json = state["json_data"]
    current_inci = state.get("current_inci")
    conversation_id = state.get("conversation_id")

    if not toxicology_sections:
        return state # no-op
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
        modification_summary=f"fastpath update: Updated {', '.join(toxicology_sections.keys())}",
        patch_operations=[p.model_dump() for p in patches]
    )
    
    ai_message = AIMessage(content=response_msg)
    
    state["json_data"] = updated_json
    state["response"] = response_msg
    state["messages"] = [ai_message]
    state["last_patches"] = patches # ✨ NEW: Track patches
    state["fast_patches"] = patches # ✨ NEW: Track patches
    state["fast_done"] = True
    
    return state