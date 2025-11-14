"""
State definitions for the LangGraph workflow
"""
from typing import Dict, Any, TypedDict, List, Optional, Tuple

class JSONEditState(TypedDict):
    """State for JSON editing workflow"""
    json_data: Dict[str, Any]
    user_input: str
    response: str
    current_inci: str
    edit_history: Optional[List[Tuple[str, str]]]  # (instruction, timestamp)
    error: Optional[str]

class ToxicologyData(TypedDict):
    """Structure for toxicology data entries"""
    data: List[str]
    reference: Dict[str, Optional[str]]
    replaced: Dict[str, str]
    source: str
    statement: Optional[str]
