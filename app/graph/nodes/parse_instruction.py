# nodes/parse_instruction.py
from app.services.text_processing import (
    extract_inci_name,
    extract_toxicology_sections
)

# ============================================================================
# Parse User Input (LANGGRAPH NODE)
# ============================================================================
def parse_instruction_node(state):
    user_input = state["user_input"]
    json_data = state["json_data"]

    # Extract INCI name
    current_inci = extract_inci_name(user_input)
    if not current_inci:
        current_inci = json_data.get("inci", "INCI_NAME")

    # Extract toxicology sections
    toxicology_sections = extract_toxicology_sections(user_input)

    # Update parsed data
    state["current_inci"] = current_inci
    state["structured_sections"] = toxicology_sections
    return state
