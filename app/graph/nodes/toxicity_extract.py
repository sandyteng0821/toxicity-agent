"""
Toxicity Extract Node - Calls process_correction_form() for raw text extraction
"""
import logging

logger = logging.getLogger(__name__)


def toxicity_extract_node(state):
    """
    Extract structured data from raw text using existing toxicity graph.
    
    Input: state with user_input containing raw form text
    Output: state with form_payloads populated
    """
    from app.graph.toxicity_graph import process_correction_form
    
    user_input = state.get("user_input", "")
    
    if not user_input:
        logger.warning("No user_input for toxicity extraction")
        return {
            "error": "No text to extract",
            "response": "No input provided for extraction."
        }
    
    try:
        logger.info("Extracting toxicity data from raw text...")
        result = process_correction_form(user_input)
        
        # Build form_payloads from result
        form_payloads = {}
        
        if result.get("noael_payload"):
            form_payloads["noael"] = result["noael_payload"]
            logger.info(f"Extracted NOAEL payload")
        
        if result.get("dap_payload"):
            form_payloads["dap"] = result["dap_payload"]
            logger.info(f"Extracted DAP payload")
        
        # Update current_inci if extracted
        current_inci = result.get("current_inci") or state.get("current_inci")
        
        if form_payloads:
            return {
                "form_payloads": form_payloads,
                "current_inci": current_inci,
                "response": f"Extracted {list(form_payloads.keys())} from text.",
            }
        else:
            return {
                "error": "No toxicity data found in text",
                "response": "Could not extract NOAEL or DAP data from the provided text.",
            }
        
    except Exception as e:
        logger.error(f"Toxicity extraction failed: {e}")
        return {
            "error": str(e),
            "response": f"Extraction failed: {str(e)}"
        }
