# nodes/parse_instruction.py
"""
Parse Instruction Node - Enhanced with intent classification
"""
import json
import logging
import re
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate

from app.services.text_processing import (
    extract_inci_name,
    extract_toxicology_sections
)
from app.graph.utils.llm_factory import get_llm 

logger = logging.getLogger(__name__)

# =============================================================================
# Helper: Extract JSON from text (handles INCI prefix)
# =============================================================================

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from text, handling cases like:
    - Pure JSON: {"noael": {...}}
    - With INCI prefix: "INCI: NAME\n{"noael": {...}}"
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Try 1: Parse as-is
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Try 2: Find JSON object in text (handles "INCI: NAME\n{...}")
    # Look for { ... } pattern
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    
    return None

# =============================================================================
# Intent Classification (NEW)
# =============================================================================

INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Classify the user input into one of these categories:
- NLI_EDIT: Simple editing instruction (e.g., "Change source to FDA")
- FORM_EDIT_STRUCTURED: Contains JSON or structured form data
- FORM_EDIT_RAW: Raw text with toxicity data needing extraction (NOAEL values, study data, etc.)
- NO_EDIT: Questions or non-edit requests

Respond with ONLY the category name."""),
    ("human", "{user_input}")
])

def classify_intent(user_input: str) -> str:
    """Classify user input intent using heuristics + LLM fallback."""
    if not user_input or not user_input.strip():
        return "NO_EDIT"
    
    input_lower = user_input.lower().strip()
    
    # Heuristic 1: JSON input (handles INCI prefix too)
    parsed_json = extract_json_from_text(user_input)
    if parsed_json:
        # Check if it has form-related keys
        form_keys = ['noael', 'dap', 'noael_payload', 'dap_payload', 'value', 'unit']
        if any(key in parsed_json for key in form_keys):
            logger.info("Classified as FORM_EDIT_STRUCTURED (JSON with form keys)")
            return "FORM_EDIT_STRUCTURED"
    
    # Heuristic 2: NLI edit patterns (CHECK FIRST - takes priority!)
    nli_patterns = ['change ', 'update ', 'set ', 'delete ', 'add ', 'remove ', 
                    'modify ', 'edit ', 'replace ', 'fix ', 'correct ', 'for ']
    if any(input_lower.startswith(p) for p in nli_patterns):
        return "NLI_EDIT"
    
    # Heuristic 3: Questions → NO_EDIT
    if input_lower.endswith('?') or any(input_lower.startswith(p) for p in ['what ', 'how ', 'why ', 'is ', 'can ']):
        return "NO_EDIT"
    
    # Heuristic 4: Raw toxicity data patterns (structured form paste, not NLI)
    # Must have COLON patterns (e.g., "NOAEL: 50") to distinguish from NLI
    raw_indicators = ['noael:', 'loael:', 'pod:', 'hed:', 'species:', 'duration:', 
                      'study type:', 'endpoint:', 'correction form', 'unit-', 'value-']
    if sum(1 for ind in raw_indicators if ind in input_lower) >= 2:
        return "FORM_EDIT_RAW"
    
    # LLM fallback for ambiguous cases
    try:
        llm = get_llm(temperature=0)
        result = (INTENT_PROMPT | llm).invoke({"user_input": user_input})
        intent = result.content.strip().upper()
        if intent in ["NLI_EDIT", "FORM_EDIT_STRUCTURED", "FORM_EDIT_RAW", "NO_EDIT"]:
            return intent
    except Exception as e:
        logger.warning(f"Intent classification LLM failed: {e}")
    
    return "NLI_EDIT"  # Default

def extract_form_payloads(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Extract form payloads from input.
    Handles both pure JSON and JSON with INCI prefix.
    """
    parsed = extract_json_from_text(user_input)
    if not parsed:
        return None
    
    payloads = {}
    
    # Check for noael payload
    if 'noael' in parsed:
        payloads['noael'] = parsed['noael']
    elif 'noael_payload' in parsed:
        payloads['noael'] = parsed['noael_payload']
    
    # Check for dap payload
    if 'dap' in parsed:
        payloads['dap'] = parsed['dap']
    elif 'dap_payload' in parsed:
        payloads['dap'] = parsed['dap_payload']
    
    return payloads if payloads else None

# ============================================================================
# Parse User Input (LANGGRAPH NODE)
# ============================================================================
def parse_instruction_node(state):
    """Parse user instruction and classify intent."""
    user_input = state.get("user_input", "")
    json_data = state.get("json_data", {})

    # Extract INCI name
    current_inci = extract_inci_name(user_input)
    if not current_inci:
        current_inci = json_data.get("inci", "INCI_NAME")

    # Extract toxicology sections
    toxicology_sections = extract_toxicology_sections(user_input)

    # Intent classification
    intent_type = classify_intent(user_input)
    logger.info(f"Intent classified as: {intent_type}")
    
    # Extract form payloads if structured
    form_payloads = None
    if intent_type == "FORM_EDIT_STRUCTURED":
        form_payloads = extract_form_payloads(user_input)
        if form_payloads:
            logger.info(f"Extracted form payloads: {list(form_payloads.keys())}")
        else:
            logger.warning("FORM_EDIT_STRUCTURED but no payloads extracted!")

    # Return state updates
    return {
        "current_inci": current_inci,
        "structured_sections": toxicology_sections,
        "intent_type": intent_type,
        "form_payloads": form_payloads,
    }