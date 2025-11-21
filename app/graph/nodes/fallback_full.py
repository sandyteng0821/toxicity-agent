# nodes/fallback_full.py
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..utils.patch_utils import (
    _fallback_to_full_json
)
from ..utils.llm_factory import get_llm

# ============================================================================
# Fallback (Full JSON Rewrite Operation) (LANGGRAPH NODE)
# ============================================================================

def fallback_full_node(state):
    """"""
    msg = AIMessage(content="Patch failed → Using fallback full JSON rewrite.")
    state["messages"] = [msg]
    state["response"] = msg.content
    current_json = state["json_data"]
    current_inci = state.get("current_inci")
    conversation_id = state.get("conversation_id")
    state["last_patches"] = []

    # Setup LLM
    # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm = get_llm()

    # Full JSON regeneration logic
    # Patch failed - fallback (use v1 node)
    print("⚠️ JSON Patch failed, falling back to full JSON generation")

    return _fallback_to_full_json(state, llm, current_json, current_inci, conversation_id)