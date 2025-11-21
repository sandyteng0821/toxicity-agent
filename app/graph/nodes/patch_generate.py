# nodes/patch_generate.py
from langchain_openai import ChatOpenAI

from ..utils.llm_factory import get_structured_llm
from ..utils.schema_tools import JSONPatchOperation
from ..utils.patch_utils import (
    _generate_patch_with_llm
)

# ============================================================================
# Generate JSON Patch Operation (LANGGRAPH NODE)
# ============================================================================

def patch_generate_node(state):
    """Generate json patch operation"""
    current_json = state["json_data"]
    current_inci = state.get("current_inci")

    # Setup LLM
    # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # structured_llm = llm.with_structured_output(JSONPatchOperation, method="function_calling")
    structured_llm = get_structured_llm(JSONPatchOperation)

    # Generate JSON Patch operation using LLM
    patch_op = _generate_patch_with_llm(
        llm=structured_llm,
        current_json=current_json,
        user_input=state["user_input"],
        current_inci=current_inci
    )
    
    print(f"Generated patch: {patch_op.model_dump()}")

    state["patch_op"] = patch_op
    return state