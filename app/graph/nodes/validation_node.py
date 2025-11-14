"""
Validation node for checking input/output quality
"""
from app.graph.state import JSONEditState

def validate_input_node(state: JSONEditState) -> JSONEditState:
    """
    Validate user input before processing
    
    Args:
        state: Current workflow state
        
    Returns:
        State with validation flag
    """
    if not state["user_input"].strip():
        state["error"] = "Empty input"
        return state
    
    # Add more validation as needed
    return state

def validate_output_node(state: JSONEditState) -> JSONEditState:
    """
    Validate LLM output and JSON structure
    
    Args:
        state: Current workflow state
        
    Returns:
        State with validation results
    """
    from app.services.json_io import validate_json_structure
    
    if not validate_json_structure(state["json_data"]):
        state["error"] = "Invalid JSON structure after update"
    
    return state