"""
State definitions for the LangGraph workflow
"""
from typing import Dict, Any, TypedDict, List, Optional, Tuple, Annotated
from jsonpatch import PatchOperation
from operator import add
from langchain_core.messages import BaseMessage

class JSONEditState(TypedDict):
    """State for JSON editing workflow"""
    messages: Annotated[List[BaseMessage], add]
    conversation_id: str
    json_data: Dict[str, Any]
    user_input: str
    response: str
    current_inci: str
    edit_history: Optional[List[Tuple[str, str]]]  # (instruction, timestamp)
    error: Optional[str]
    last_patches: Optional[List[PatchOperation]]

class ToxicologyData(TypedDict):
    """Structure for toxicology data entries"""
    data: List[str]
    reference: Dict[str, Optional[str]]
    replaced: Dict[str, str]
    source: str
    statement: Optional[str]
