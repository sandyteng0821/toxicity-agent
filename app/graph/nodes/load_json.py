# nodes/load_json.py
import json

from core.database import ToxicityDB

# ============================================================================
# Load JSON Data (LANGGRAPH NODE)
# ============================================================================
# Initialize DB at module level
db = ToxicityDB()

def load_json_node(state):
    """Load existing JSON data"""
    # Get conversation context from DB
    conversation_id = state.get("conversation_id")

    # Load current JSON from DB
    current_version_obj = db.get_current_version(conversation_id)
    if current_version_obj:
        current_json = json.loads(current_version_obj.data)
    else:
        current_json = state["json_data"]

    # Update JSON data 
    state["json_data"] = current_json
    return state