# app/graph/utils/toxicity_utils.py
# =============================================================================
# Toxicity Imputation Utility Functions
# =============================================================================

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from .toxicity_schemas import (
    NOAELUpdateSchema,
    DAPUpdateSchema,
    ToxicityTaskClassification,
)


# =============================================================================
# Prompt Templates
# =============================================================================

NOAEL_SYSTEM_PROMPT = """You are a toxicology data extraction specialist. 
Your task is to extract NOAEL (No Observed Adverse Effect Level) information from toxicity correction forms (毒理修正單).

Extract the following fields from the provided text:
- inci_name: The INCI name of the ingredient (in UPPERCASE)
- value: The NOAEL numeric value only (e.g., 450, not "450 mg/kg bw/day")
- unit: Usually "mg/kg bw/day"
- experiment_target: Test species (e.g., "Rats", "Mice")
- source: Data source (e.g., "CIR", "ECHA", "OECD", "SCCS")
- study_duration: Study duration (e.g., "90-day", "28-day")
- note: The detailed study description (keep in Chinese if provided in Chinese)
- reference_title: Title of the reference document
- reference_link: URL if provided
- statement: A brief English summary of the study basis

Be precise and extract exactly what is in the text. Do not infer or add information not present."""

NOAEL_USER_TEMPLATE = """Extract NOAEL information from this toxicity correction form:

{correction_form_text}

Return structured NOAEL data."""


DAP_SYSTEM_PROMPT = """You are a toxicology data extraction specialist.
Your task is to extract DAP (Dermal Absorption Percentage) information from toxicity correction forms (毒理修正單).

Extract the following fields from the provided text:
- inci_name: The INCI name of the ingredient (in UPPERCASE)
- value: The DAP numeric value only (e.g., 1, not "1%")
- unit: Usually "%"
- experiment_target: Usually "Human skin"
- source: Data source (e.g., "CIR", "ECHA", "SCCS", "expert")
- study_duration: Study type (e.g., "in vitro", "in vivo", "theoretical")
- note: The detailed explanation (keep in Chinese if provided in Chinese)
- reference_title: Title of the reference document
- reference_link: URL if provided
- statement: A brief English summary of the determination basis

Be precise and extract exactly what is in the text. Do not infer or add information not present."""

DAP_USER_TEMPLATE = """Extract DAP (Percutaneous Absorption) information from this toxicity correction form:

{correction_form_text}

Return structured DAP data."""


CLASSIFICATION_SYSTEM_PROMPT = """You are a toxicology data classifier.
Analyze the provided toxicity correction form and determine what type of data it contains.

Look for these indicators:
- NOAEL indicators: "NOAEL", "Repeated Dose Toxicity", "重複劑量毒性", "mg/kg bw/day"
- DAP indicators: "DAP", "Percutaneous Absorption", "經皮吸收", "吸收率", "%"

Classify the task type:
- "noael": Only contains NOAEL/Repeated Dose Toxicity data
- "dap": Only contains DAP/Percutaneous Absorption data  
- "both": Contains both NOAEL and DAP data
- "unknown": Cannot determine the data type

Also extract the INCI name if present."""

CLASSIFICATION_USER_TEMPLATE = """Classify this toxicity correction form:

{correction_form_text}

Determine the task type and extract INCI name."""


# =============================================================================
# LLM Extraction Functions
# =============================================================================

def _generate_noael_with_llm(
    llm,
    correction_form_text: str,
) -> NOAELUpdateSchema:
    """
    Generate NOAEL structured data using LLM.
    
    Args:
        llm: Structured LLM with NOAELUpdateSchema output
        correction_form_text: Raw text from correction form
        
    Returns:
        NOAELUpdateSchema with extracted data
    """
    messages = [
        SystemMessage(content=NOAEL_SYSTEM_PROMPT),
        HumanMessage(content=NOAEL_USER_TEMPLATE.format(
            correction_form_text=correction_form_text
        )),
    ]
    
    result = llm.invoke(messages)
    return result


def _generate_dap_with_llm(
    llm,
    correction_form_text: str,
) -> DAPUpdateSchema:
    """
    Generate DAP structured data using LLM.
    
    Args:
        llm: Structured LLM with DAPUpdateSchema output
        correction_form_text: Raw text from correction form
        
    Returns:
        DAPUpdateSchema with extracted data
    """
    messages = [
        SystemMessage(content=DAP_SYSTEM_PROMPT),
        HumanMessage(content=DAP_USER_TEMPLATE.format(
            correction_form_text=correction_form_text
        )),
    ]
    
    result = llm.invoke(messages)
    return result


def _classify_task_with_llm(
    llm,
    correction_form_text: str,
) -> ToxicityTaskClassification:
    """
    Classify the task type using LLM.
    
    Args:
        llm: Structured LLM with ToxicityTaskClassification output
        correction_form_text: Raw text from correction form
        
    Returns:
        ToxicityTaskClassification with task type
    """
    messages = [
        SystemMessage(content=CLASSIFICATION_SYSTEM_PROMPT),
        HumanMessage(content=CLASSIFICATION_USER_TEMPLATE.format(
            correction_form_text=correction_form_text
        )),
    ]
    
    result = llm.invoke(messages)
    return result


# =============================================================================
# Payload Builders
# =============================================================================

def build_noael_payload(
    noael_data: NOAELUpdateSchema,
    conversation_id: str = "optional-existing-id",
) -> dict:
    """
    Build NOAEL API payload from structured data.
    
    Args:
        noael_data: NOAELUpdateSchema instance
        conversation_id: Optional conversation ID
        
    Returns:
        Dict ready for POST /api/edit-form/noael
    """
    return {
        "conversation_id": conversation_id,
        "inci_name": noael_data.inci_name,
        "value": noael_data.value,
        "unit": noael_data.unit,
        "experiment_target": noael_data.experiment_target,
        "source": noael_data.source,
        "study_duration": noael_data.study_duration,
        "note": noael_data.note,
        "reference_title": noael_data.reference_title,
        "reference_link": noael_data.reference_link or "",
        "statement": noael_data.statement,
    }


def build_dap_payload(
    dap_data: DAPUpdateSchema,
    conversation_id: str = "optional-existing-id",
) -> dict:
    """
    Build DAP API payload from structured data.
    
    Args:
        dap_data: DAPUpdateSchema instance
        conversation_id: Optional conversation ID
        
    Returns:
        Dict ready for POST /api/edit-form/dap
    """
    return {
        "conversation_id": conversation_id,
        "inci_name": dap_data.inci_name,
        "value": dap_data.value,
        "unit": dap_data.unit,
        "experiment_target": dap_data.experiment_target,
        "source": dap_data.source,
        "study_duration": dap_data.study_duration,
        "note": dap_data.note,
        "reference_title": dap_data.reference_title,
        "reference_link": dap_data.reference_link or "",
        "statement": dap_data.statement,
    }
