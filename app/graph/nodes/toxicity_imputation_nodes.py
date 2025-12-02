# app/graph/nodes/toxicity_imputation.py
# =============================================================================
# Toxicity Imputation Nodes (NOAEL / DAP)
# =============================================================================

import json
from langchain_core.messages import AIMessage

from ..utils.llm_factory import get_structured_llm
from ..utils.toxicity_schemas import (
    NOAELUpdateSchema,
    DAPUpdateSchema,
    ToxicityTaskClassification,
)
from ..utils.toxicity_utils import (
    _generate_noael_with_llm,
    _generate_dap_with_llm,
    _classify_task_with_llm,
    build_noael_payload,
    build_dap_payload,
)


# =============================================================================
# Task Classification Node
# =============================================================================

def toxicity_classify_node(state):
    """
    Classify the toxicity correction form task type.
    
    Determines if the input contains NOAEL data, DAP data, or both.
    
    State Input:
        - correction_form_text: str (raw text from 毒理修正單)
        
    State Output:
        - task_type: str ("noael", "dap", "both", "unknown")
        - has_noael_data: bool
        - has_dap_data: bool
        - current_inci: str (extracted INCI name)
    """
    correction_form_text = state.get("correction_form_text", "")
    
    if not correction_form_text:
        state["task_type"] = "unknown"
        state["error"] = "No correction form text provided"
        return state
    
    # Get structured LLM for classification
    structured_llm = get_structured_llm(ToxicityTaskClassification)
    
    # Classify task
    classification = _classify_task_with_llm(
        llm=structured_llm,
        correction_form_text=correction_form_text,
    )
    
    print(f"📋 Task Classification: {classification.task_type}")
    print(f"   - Has NOAEL: {classification.has_noael_data}")
    print(f"   - Has DAP: {classification.has_dap_data}")
    print(f"   - INCI: {classification.inci_name}")
    
    state["task_type"] = classification.task_type
    state["has_noael_data"] = classification.has_noael_data
    state["has_dap_data"] = classification.has_dap_data
    
    if classification.inci_name:
        state["current_inci"] = classification.inci_name
    
    msg = AIMessage(content=f"Task classified as: {classification.task_type}")
    state["messages"] = [msg]
    
    return state


# =============================================================================
# NOAEL Imputation Node
# =============================================================================

def noael_generate_node(state):
    """
    Generate NOAEL payload from correction form text.
    
    Similar structure to patch_generate_node.
    
    State Input:
        - correction_form_text: str (raw text from 毒理修正單)
        - conversation_id: str (optional)
        
    State Output:
        - noael_data: NOAELUpdateSchema
        - noael_payload: dict (ready for API POST)
        - noael_json: str (JSON string)
        - api_endpoint: str
    """
    correction_form_text = state.get("correction_form_text", "")
    conversation_id = state.get("conversation_id", "optional-existing-id")
    
    # Get structured LLM for NOAEL extraction
    structured_llm = get_structured_llm(NOAELUpdateSchema)
    
    # Generate NOAEL data using LLM
    noael_data = _generate_noael_with_llm(
        llm=structured_llm,
        correction_form_text=correction_form_text,
    )
    
    print(f"✅ Generated NOAEL data: {noael_data.model_dump()}")
    
    # Build API payload
    noael_payload = build_noael_payload(noael_data, conversation_id)
    
    # Update state
    state["noael_data"] = noael_data
    state["noael_payload"] = noael_payload
    state["noael_json"] = json.dumps(noael_payload, ensure_ascii=False, indent=2)
    state["api_endpoint"] = "/api/edit-form/noael"
    state["current_inci"] = noael_data.inci_name
    
    msg = AIMessage(content=f"NOAEL data extracted for {noael_data.inci_name}: {noael_data.value} {noael_data.unit}")
    state["messages"] = state.get("messages", []) + [msg]
    state["response"] = msg.content
    
    return state


# =============================================================================
# DAP Imputation Node
# =============================================================================

def dap_generate_node(state):
    """
    Generate DAP payload from correction form text.
    
    Similar structure to patch_generate_node.
    
    State Input:
        - correction_form_text: str (raw text from 毒理修正單)
        - conversation_id: str (optional)
        
    State Output:
        - dap_data: DAPUpdateSchema
        - dap_payload: dict (ready for API POST)
        - dap_json: str (JSON string)
        - api_endpoint: str
    """
    correction_form_text = state.get("correction_form_text", "")
    conversation_id = state.get("conversation_id", "optional-existing-id")
    
    # Get structured LLM for DAP extraction
    structured_llm = get_structured_llm(DAPUpdateSchema)
    
    # Generate DAP data using LLM
    dap_data = _generate_dap_with_llm(
        llm=structured_llm,
        correction_form_text=correction_form_text,
    )
    
    print(f"✅ Generated DAP data: {dap_data.model_dump()}")
    
    # Build API payload
    dap_payload = build_dap_payload(dap_data, conversation_id)
    
    # Update state
    state["dap_data"] = dap_data
    state["dap_payload"] = dap_payload
    state["dap_json"] = json.dumps(dap_payload, ensure_ascii=False, indent=2)
    state["api_endpoint"] = "/api/edit-form/dap"
    state["current_inci"] = dap_data.inci_name
    
    msg = AIMessage(content=f"DAP data extracted for {dap_data.inci_name}: {dap_data.value}{dap_data.unit}")
    state["messages"] = state.get("messages", []) + [msg]
    state["response"] = msg.content
    
    return state


# =============================================================================
# Combined Imputation Node (for "both" case)
# =============================================================================

def toxicity_dual_generate_node(state):
    """
    Generate both NOAEL and DAP payloads from correction form text.
    
    Used when the correction form contains both types of data.
    
    State Input:
        - correction_form_text: str
        - conversation_id: str (optional)
        
    State Output:
        - noael_payload, noael_json (if has_noael_data)
        - dap_payload, dap_json (if has_dap_data)
        - api_requests: list of request configs
    """
    correction_form_text = state.get("correction_form_text", "")
    conversation_id = state.get("conversation_id", "optional-existing-id")
    
    api_requests = []
    
    # Process NOAEL if present
    if state.get("has_noael_data", False):
        structured_llm = get_structured_llm(NOAELUpdateSchema)
        noael_data = _generate_noael_with_llm(structured_llm, correction_form_text)
        noael_payload = build_noael_payload(noael_data, conversation_id)
        
        state["noael_data"] = noael_data
        state["noael_payload"] = noael_payload
        state["noael_json"] = json.dumps(noael_payload, ensure_ascii=False, indent=2)
        
        api_requests.append({
            "endpoint": "/api/edit-form/noael",
            "payload": noael_payload,
        })
        
        print(f"✅ NOAEL: {noael_data.inci_name} = {noael_data.value} {noael_data.unit}")
    
    # Process DAP if present
    if state.get("has_dap_data", False):
        structured_llm = get_structured_llm(DAPUpdateSchema)
        dap_data = _generate_dap_with_llm(structured_llm, correction_form_text)
        dap_payload = build_dap_payload(dap_data, conversation_id)
        
        state["dap_data"] = dap_data
        state["dap_payload"] = dap_payload
        state["dap_json"] = json.dumps(dap_payload, ensure_ascii=False, indent=2)
        
        api_requests.append({
            "endpoint": "/api/edit-form/dap",
            "payload": dap_payload,
        })
        
        print(f"✅ DAP: {dap_data.inci_name} = {dap_data.value}{dap_data.unit}")
    
    state["api_requests"] = api_requests
    
    msg = AIMessage(content=f"Extracted {len(api_requests)} data type(s) for imputation")
    state["messages"] = state.get("messages", []) + [msg]
    state["response"] = msg.content
    
    return state


# =============================================================================
# Error Handler Node
# =============================================================================

def toxicity_error_node(state):
    """
    Handle unknown or error cases in toxicity imputation.
    """
    error_msg = state.get("error", "Unknown task type - unable to process correction form")
    
    msg = AIMessage(content=f"❌ Error: {error_msg}")
    state["messages"] = state.get("messages", []) + [msg]
    state["response"] = msg.content
    
    print(f"❌ Toxicity imputation error: {error_msg}")
    
    return state
