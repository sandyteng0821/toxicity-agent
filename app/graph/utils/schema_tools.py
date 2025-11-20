# utils/schema_tools.py
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any, List, Dict, Tuple, Union

# ============================================================================
# JSON PATCH MODEL
# ============================================================================

class JSONPatchOperation(BaseModel):
    """Structured output for LLM - enforces valid JSON Patch format"""
    op: Literal["add", "remove", "replace"] = Field(
        description="Operation type: add, remove, or replace"
    )
    path: str = Field(
        description="JSON Pointer path (e.g., '/acute_toxicity/-' or '/NOAEL/0')"
    )
    value: Union[str, int, float, bool, dict, list, None] = Field(
        default=None,
        description="Value for add/replace operations (not needed for remove)"
    )