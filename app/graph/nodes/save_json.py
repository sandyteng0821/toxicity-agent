# nodes/save_json.py
from langchain_core.messages import AIMessage

from core.database import ToxicityDB

# ============================================================================
# Save JSON Data (LANGGRAPH NODE)
# ============================================================================
# Initialize DB at module level
db = ToxicityDB()

def save_json_node(state):
    """Save JSON data for the specified conversation_id"""
    db.save_version(
        conversation_id=state.get("conversation_id"),
        inci_name=state.get("current_inci", "INCI_NAME"),
        data=state["json_data"],
        modification_summary="final-save",
        patch_operations=[]
    )

    msg = AIMessage(content="JSON saved successfully.")
    state["messages"] = [msg]
    state["response"] = msg.content

    return state