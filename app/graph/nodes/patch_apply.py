# nodes/patch_apply.py
from ..utils.patch_utils import (
    _apply_patch_safely
)

# ============================================================================
# Apply JSON Patch Operation (LANGGRAPH NODE)
# ============================================================================

def patch_apply_node(state):
    patch_op = state["patch_op"]
    updated_json, success = _apply_patch_safely(state["json_data"], patch_op)

    if success:
        state["last_patches"] = [patch_op]

    state["json_data"] = updated_json
    state["patch_success"] = success

    return state
