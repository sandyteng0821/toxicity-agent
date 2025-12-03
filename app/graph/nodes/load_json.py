# nodes/load_json.py
import json

from core.database import ToxicityDB
from app.services.json_io import read_json

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
    elif state.get("json_data"):
        current_json = state["json_data"]    
    else:
        current_json = read_json() # Fallback: load json from JSON_TEMPLATE_PATH (defined within config.py)

    # Update JSON data 
    state["json_data"] = current_json
    return state