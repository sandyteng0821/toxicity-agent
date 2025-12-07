# nodes/save_json.py
from langchain_core.messages import AIMessage

from core.database import ToxicityDB

# ============================================================================
# Save JSON Data (LANGGRAPH NODE)
# ============================================================================
# Initialize DB at module level
db = ToxicityDB()

# def save_json_node(state):
#     """Save JSON data for the specified conversation_id"""
#     db.save_version(
#         conversation_id=state.get("conversation_id"),
#         inci_name=state.get("current_inci", "INCI_NAME"),
#         data=state["json_data"],
#         modification_summary="final-save",
#         patch_operations=[]
#     )

#     msg = AIMessage(content="JSON saved successfully.")
#     state["messages"] = [msg]
#     state["response"] = msg.content

#     return state

def save_json_node(state):
    """Save JSON data for the specified conversation_id using the unified save_modification."""
    
    # 1. Prepare the modification summary base
    # Use user_input for the 'instruction' parameter, which builds the audit summary.
    # Provide a safe fallback if user_input is missing (e.g., in a system-only save).
    instruction_base = state.get("user_input", "System initiated final save post-edit.")
    
    # # 2. Extract patches (The unified method expects this if available)
    # # Check for patches from the successful path (last_patches) or fast update path (fast_patches)
    # applied_patches = state.get("last_patches", state.get("fast_patches", []))
    # 執行一次檢查性轉換，確保安全。
    raw_patches = state.get("last_patches", [])
    
    # 如果 raw_patches 不為空且第一個元素不是字典，就嘗試轉換它。
    if raw_patches and not isinstance(raw_patches[0], dict):
        patches_to_save = [p.model_dump() for p in raw_patches if hasattr(p, 'model_dump')]
    else:
        patches_to_save = raw_patches
    
    db.save_modification(
        # --- Mandatory Fields ---
        item_id=state.get("conversation_id"),               # Mapped from 'conversation_id'
        inci_name=state.get("current_inci", "INCI_NAME"),   # Mapped from 'inci_name'
        data=state["json_data"],                            # The final JSON data
        instruction=instruction_base,                       # Mapped from 'modification_summary' base
        
        # --- Optional/Audit Fields ---
        patch_operations=patches_to_save,                   # Pass the actual patches applied
        batch_id=None,                                      # Explicitly None for a single transaction
        is_batch_item=False,                                # Explicitly False for a single transaction
        patch_success=True,                                 # Assumed True if reaching the final save node
        fallback_used=state.get("fallback_used", False),    # Pass the audit flag if available
    )
    
    msg = AIMessage(content="JSON saved successfully.")
    state["messages"] = [msg]
    state["response"] = msg.content

    # Note: The old db.save_version call has been entirely removed.
    return {"result": "JSON data version saved successfully."}