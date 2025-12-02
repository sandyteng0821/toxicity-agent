# app/graph/toxicity_graph.py
# =============================================================================
# Toxicity Imputation LangGraph Workflow
# =============================================================================
"""
Workflow for processing toxicity correction forms (毒理修正單).

Flow:
    修正單 → classify → route → noael/dap/dual → api_request

Usage:
    from app.graph.toxicity_graph import get_toxicity_app
    
    app = get_toxicity_app()
    result = app.invoke({
        "correction_form_text": "...",
        "conversation_id": "xxx",
    })
"""

from typing import TypedDict, Literal, Optional, Any
from langgraph.graph import StateGraph, END

from .nodes.toxicity_imputation_nodes import (
    toxicity_classify_node,
    noael_generate_node,
    dap_generate_node,
    toxicity_dual_generate_node,
    toxicity_error_node,
)


# =============================================================================
# State Definition
# =============================================================================

class ToxicityImputationState(TypedDict, total=False):
    """State for toxicity imputation workflow."""
    
    # Input
    correction_form_text: str
    conversation_id: str
    
    # Classification output
    task_type: str  # "noael", "dap", "both", "unknown"
    has_noael_data: bool
    has_dap_data: bool
    current_inci: str
    
    # NOAEL output
    noael_data: Any  # NOAELUpdateSchema
    noael_payload: dict
    noael_json: str
    
    # DAP output
    dap_data: Any  # DAPUpdateSchema
    dap_payload: dict
    dap_json: str
    
    # API
    api_endpoint: str
    api_requests: list
    
    # Messages
    messages: list
    response: str
    error: str


# =============================================================================
# Routing Function
# =============================================================================

def route_by_task_type(state: ToxicityImputationState) -> Literal["noael", "dap", "dual", "error"]:
    """Route to appropriate node based on task type."""
    task_type = state.get("task_type", "unknown")
    
    if task_type == "noael":
        return "noael"
    elif task_type == "dap":
        return "dap"
    elif task_type == "both":
        return "dual"
    else:
        return "error"


# =============================================================================
# Build Workflow Graph
# =============================================================================

def build_toxicity_graph() -> StateGraph:
    """
    Build the toxicity imputation workflow graph.
    
    Graph Structure:
        ┌─────────┐
        │ classify│
        └────┬────┘
             │
        ┌────┴────┐
        │  route  │
        └────┬────┘
             │
    ┌────────┼────────┬────────┐
    ▼        ▼        ▼        ▼
  noael     dap     dual    error
    │        │        │        │
    └────────┴────────┴────────┘
                 │
                END
    """
    
    # Create graph
    workflow = StateGraph(ToxicityImputationState)
    
    # Add nodes
    workflow.add_node("classify", toxicity_classify_node)
    workflow.add_node("noael", noael_generate_node)
    workflow.add_node("dap", dap_generate_node)
    workflow.add_node("dual", toxicity_dual_generate_node)
    workflow.add_node("error", toxicity_error_node)
    
    # Set entry point
    workflow.set_entry_point("classify")
    
    # Add conditional routing after classification
    workflow.add_conditional_edges(
        "classify",
        route_by_task_type,
        {
            "noael": "noael",
            "dap": "dap",
            "dual": "dual",
            "error": "error",
        }
    )
    
    # All terminal nodes go to END
    workflow.add_edge("noael", END)
    workflow.add_edge("dap", END)
    workflow.add_edge("dual", END)
    workflow.add_edge("error", END)
    
    return workflow


# =============================================================================
# Compiled App
# =============================================================================

def get_toxicity_app():
    """Get compiled toxicity imputation app."""
    workflow = build_toxicity_graph()
    return workflow.compile()


# =============================================================================
# Convenience Functions
# =============================================================================

def process_correction_form(
    correction_form_text: str,
    conversation_id: str = "optional-existing-id",
) -> dict:
    """
    Process a toxicity correction form and return payloads.
    
    Args:
        correction_form_text: Raw text from 毒理修正單
        conversation_id: Optional conversation ID
        
    Returns:
        Dict with task_type, payloads, and json strings
    """
    app = get_toxicity_app()
    
    result = app.invoke({
        "correction_form_text": correction_form_text,
        "conversation_id": conversation_id,
    })
    
    return {
        "task_type": result.get("task_type"),
        "current_inci": result.get("current_inci"),
        "noael_payload": result.get("noael_payload"),
        "noael_json": result.get("noael_json"),
        "dap_payload": result.get("dap_payload"),
        "dap_json": result.get("dap_json"),
        "api_requests": result.get("api_requests", []),
        "response": result.get("response"),
        "error": result.get("error"),
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test with NOAEL example
    noael_text = """
    INCI: BUTYL METHOXYDIBENZOYLMETHANE 
    Repeated Dose Toxicity
    建議的 NOAEL 值為:450.0 mg/kg bw/day 用以計算安全邊際值。
    ECHA-
    https://echa.europa.eu/sl/registration-dossier/-/registered-dossier/14835/7/6/2
    
    一項13週重複劑量毒性試驗中，Butyl methoxydibenzoylmethane（BMDBM）以 0、200、450、1000 mg/kg bw/day 方式餵食大鼠。
    
    NOAEL
    Note-一項13週重複劑量毒性試驗中...
    Unit-450 mg/kg bw/day
    Experiment_target-Rats
    Source-ECHA
    Type-NOAEL
    Study duration-90 days
    Value-450
    """
    
    print("=" * 60)
    print("Testing NOAEL Workflow")
    print("=" * 60)
    
    result = process_correction_form(noael_text)
    
    print(f"\nTask Type: {result['task_type']}")
    print(f"INCI: {result['current_inci']}")
    print(f"\nNOAEL JSON:\n{result['noael_json']}")
    
    # Test with DAP example
    dap_text = """
    INCI：AMP-ACRYLATES/DIACETONEACRYLAMIDE COPOLYMER
    Percutaneous Absorption
    建議的經皮吸收率為: 1.0 % 用以計算安全邊際值。
    CIR
    https://www.cir-safety.org/sites/default/files/Acrylamide%20Acrylate%20Copolymers.pdf
    
    AMP-Acrylates/Diacetoneacrylamide Copolymer屬於丙烯酸酯/丙烯醯胺共聚物家族...
    
    DAP:
    Unit-1%
    Source- CIR
    Type-DAP
    Value-1%
    """
    
    print("\n" + "=" * 60)
    print("Testing DAP Workflow")
    print("=" * 60)
    
    result = process_correction_form(dap_text)
    
    print(f"\nTask Type: {result['task_type']}")
    print(f"INCI: {result['current_inci']}")
    print(f"\nDAP JSON:\n{result['dap_json']}")
