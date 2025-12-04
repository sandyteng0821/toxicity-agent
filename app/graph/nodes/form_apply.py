"""
Form Apply Node - Applies form payloads to json_data
Matches the exact logic of /api/edit-form/noael and /api/edit-form/dap
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _is_duplicate_entry(existing_entries: List[Dict], new_entry: Dict) -> bool:
    """Check if entry already exists (by reference title)."""
    new_title = new_entry.get("reference", {}).get("title", "")
    for entry in existing_entries:
        if entry.get("reference", {}).get("title") == new_title:
            return True
    return False


def apply_noael(payload: Dict[str, Any], json_data: Dict[str, Any], inci_name: str) -> Dict[str, Any]:
    """
    Apply NOAEL form data - matches /api/edit-form/noael logic exactly.
    
    Creates:
    1. noael_entry → REPLACES json_data["NOAEL"]
    2. repeated_dose_entry → APPENDS to json_data["repeated_dose_toxicity"]
    """
    # Extract values with defaults
    value = payload.get("value", 0)
    unit = payload.get("unit", "mg/kg bw/day")
    source = (payload.get("source") or "").lower().replace(" ", "_")
    experiment_target = payload.get("experiment_target", "")
    study_duration = payload.get("study_duration", "")
    note = payload.get("note")
    reference_title = payload.get("reference_title", "")
    reference_link = payload.get("reference_link")
    statement = payload.get("statement")
    
    # 1. Create NOAEL entry (matches endpoint exactly)
    noael_entry = {
        "note": note,
        "unit": unit,
        "experiment_target": experiment_target,
        "source": source,
        "type": "NOAEL",
        "study_duration": study_duration,
        "value": value
    }
    
    # 2. Create repeated_dose_toxicity entry (matches endpoint exactly)
    repeated_dose_entry = {
        "reference": {
            "title": reference_title,
            "link": reference_link
        },
        "data": [
            f"NOAEL of {value} {unit} established in {experiment_target} "
            f"({study_duration} study) based on {source} assessment"
        ],
        "source": source,
        "statement": statement or f"Based on {source} assessment",
        "replaced": {
            "replaced_inci": "",
            "replaced_type": ""
        }
    }
    
    # Apply to json_data
    json_data["inci"] = inci_name
    json_data["inci_ori"] = inci_name
    
    # REPLACE NOAEL list (same as endpoint)
    json_data["NOAEL"] = [noael_entry]
    
    # APPEND to repeated_dose_toxicity (with duplicate check)
    if "repeated_dose_toxicity" not in json_data:
        json_data["repeated_dose_toxicity"] = []
    
    if not _is_duplicate_entry(json_data["repeated_dose_toxicity"], repeated_dose_entry):
        json_data["repeated_dose_toxicity"].append(repeated_dose_entry)
    
    return json_data


def apply_dap(payload: Dict[str, Any], json_data: Dict[str, Any], inci_name: str) -> Dict[str, Any]:
    """
    Apply DAP form data - matches /api/edit-form/dap logic exactly.
    
    Creates:
    1. dap_entry → REPLACES json_data["DAP"]
    2. pa_entry → APPENDS to json_data["percutaneous_absorption"]
    """
    # Extract values
    value = payload.get("value", 0)
    source = (payload.get("source") or "").lower().replace(" ", "_")
    experiment_target = payload.get("experiment_target", "")
    study_duration = payload.get("study_duration", "")
    note = payload.get("note")
    reference_title = payload.get("reference_title", "")
    reference_link = payload.get("reference_link")
    statement = payload.get("statement")
    
    # 1. Create DAP entry
    dap_entry = {
        "note": note,
        "unit": "%",
        "experiment_target": experiment_target,
        "source": source,
        "type": "DAP",
        "study_duration": study_duration,
        "value": value
    }
    
    # 2. Create percutaneous_absorption entry
    pa_entry = {
        "reference": {
            "title": reference_title,
            "link": reference_link
        },
        "data": [
            f"Dermal absorption estimated at {value}% in {experiment_target} "
            f"({study_duration} study) based on {source} assessment"
        ],
        "source": source,
        "statement": statement or f"Based on {source} assessment",
        "replaced": {
            "replaced_inci": "",
            "replaced_type": ""
        }
    }
    
    # Apply to json_data
    json_data["inci"] = inci_name
    json_data["inci_ori"] = inci_name
    
    # REPLACE DAP list
    json_data["DAP"] = [dap_entry]
    
    # APPEND to percutaneous_absorption
    if "percutaneous_absorption" not in json_data:
        json_data["percutaneous_absorption"] = []
    
    if not _is_duplicate_entry(json_data["percutaneous_absorption"], pa_entry):
        json_data["percutaneous_absorption"].append(pa_entry)
    
    return json_data


def form_apply_node(state):
    """
    Apply form payloads to json_data.
    
    Matches exact behavior of /api/edit-form/noael and /api/edit-form/dap:
    - NOAEL/DAP entries REPLACE existing (not append)
    - repeated_dose_toxicity/percutaneous_absorption entries APPEND
    """
    form_payloads = state.get("form_payloads", {})
    json_data = state.get("json_data", {}).copy()  # Don't mutate original
    current_inci = state.get("current_inci") or json_data.get("inci", "INCI_NAME")
    
    if not form_payloads:
        logger.warning("No form_payloads to apply")
        return {
            "response": "No form data to apply.",
            "error": "Empty form_payloads"
        }
    
    applied = []
    errors = []
    
    # Apply NOAEL
    if form_payloads.get("noael"):
        try:
            json_data = apply_noael(form_payloads["noael"], json_data, current_inci)
            applied.append("NOAEL")
            logger.info(f"Applied NOAEL: {form_payloads['noael'].get('value')} {form_payloads['noael'].get('unit')}")
        except Exception as e:
            errors.append(f"NOAEL: {str(e)}")
            logger.error(f"Failed to apply NOAEL: {e}")
    
    # Apply DAP
    if form_payloads.get("dap"):
        try:
            json_data = apply_dap(form_payloads["dap"], json_data, current_inci)
            applied.append("DAP")
            logger.info(f"Applied DAP: {form_payloads['dap'].get('value')}%")
        except Exception as e:
            errors.append(f"DAP: {str(e)}")
            logger.error(f"Failed to apply DAP: {e}")
    
    # Build response
    if applied and not errors:
        response = f"✅ Form data applied: {', '.join(applied)} (replaces existing)"
    elif applied:
        response = f"⚠️ Partial. Applied: {', '.join(applied)}. Errors: {'; '.join(errors)}"
    else:
        response = f"❌ Failed: {'; '.join(errors)}"
    
    return {
        "json_data": json_data,
        "form_types_processed": applied,
        "response": response,
        "error": "; ".join(errors) if errors else None,
    }
