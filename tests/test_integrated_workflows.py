"""
Test file for both NLI and Form-based workflows
"""
import pytest
from app.graph.build_graph import build_graph
from app.graph.toxicity_graph import process_correction_form  # Your existing function
from app.graph.nodes.parse_instruction import classify_intent


# =============================================================================
# Test Intent Classification
# =============================================================================

def test_classify_intent_nli():
    """NLI edit patterns should return NLI_EDIT"""
    nli_inputs = [
        "Change the source to FDA",
        "Set NOAEL to 200 mg/kg",
        "For L-MENTHOL, set NOAEL to 200 mg/kg bw/day for Rats",
        "Update the value to 100",
        "Delete the third entry",
        "Add a new NOAEL entry",
    ]
    for inp in nli_inputs:
        result = classify_intent(inp)
        assert result == "NLI_EDIT", f"Expected NLI_EDIT for: {inp}, got: {result}"


def test_classify_intent_form_raw():
    """Raw toxicity data with colon patterns should return FORM_EDIT_RAW"""
    raw_inputs = [
        "NOAEL: 50 mg/kg\nSpecies: Rat\nDuration: 90 days",
        "Study Type: Subchronic\nNOAEL: 100\nSource: ECHA",
    ]
    for inp in raw_inputs:
        result = classify_intent(inp)
        assert result == "FORM_EDIT_RAW", f"Expected FORM_EDIT_RAW for: {inp}, got: {result}"


def test_classify_intent_form_structured():
    """JSON input should return FORM_EDIT_STRUCTURED"""
    json_input = '{"noael": {"value": 100, "unit": "mg/kg"}}'
    result = classify_intent(json_input)
    assert result == "FORM_EDIT_STRUCTURED"


# =============================================================================
# Test Original Toxicity Graph (Still Works!)
# =============================================================================

def test_toxicity_graph_noael():
    """Test original toxicity graph with NOAEL example"""
    noael_text = """
    INCI: BUTYL METHOXYDIBENZOYLMETHANE 
    Repeated Dose Toxicity
    建議的 NOAEL 值為:450.0 mg/kg bw/day 用以計算安全邊際值。
    
    NOAEL
    Note-一項13週重複劑量毒性試驗中...
    Unit-450 mg/kg bw/day
    Experiment_target-Rats
    Source-ECHA
    Type-NOAEL
    Study duration-90 days
    Value-450
    """
    
    result = process_correction_form(noael_text)
    
    assert result['task_type'] in ['noael', 'both'], f"Expected noael task, got: {result['task_type']}"
    assert result['current_inci'] == "BUTYL METHOXYDIBENZOYLMETHANE"
    assert result.get('noael_payload') is not None or result.get('noael_json') is not None


def test_toxicity_graph_dap():
    """Test original toxicity graph with DAP example"""
    dap_text = """
    INCI：AMP-ACRYLATES/DIACETONEACRYLAMIDE COPOLYMER
    Percutaneous Absorption
    建議的經皮吸收率為: 1.0 % 用以計算安全邊際值。
    
    DAP:
    Unit-1%
    Source- CIR
    Type-DAP
    Value-1%
    """
    
    result = process_correction_form(dap_text)
    
    assert result['task_type'] in ['dap', 'both'], f"Expected dap task, got: {result['task_type']}"
    assert "COPOLYMER" in result['current_inci']
    assert result.get('dap_payload') is not None or result.get('dap_json') is not None


# =============================================================================
# Test Integrated Graph - NLI Path
# =============================================================================

def test_integrated_graph_nli_path():
    """Test that NLI edits still go through the existing path"""
    graph = build_graph(use_test_db=True)
    
    test_input = "For L-MENTHOL, set NOAEL to 200 mg/kg bw/day for Rats based on 90-day study."
    config = {"configurable": {"thread_id": "test-nli-001"}}
    
    result = graph.invoke({
        "user_input": test_input,
        "json_data": {"inci": "L-MENTHOL", "NOAEL": []},
        "conversation_id": "test-nli-001"
    }, config=config)
    
    # Should go through NLI path
    assert result.get("intent_type") == "NLI_EDIT", f"Expected NLI_EDIT, got: {result.get('intent_type')}"
    # Should have patches from NLI path
    assert result.get("last_patches") is not None or result.get("fast_patches") is not None


def test_integrated_graph_form_structured():
    """Test that JSON input goes to form API path"""
    graph = build_graph(use_test_db=True)
    
    json_input = '{"noael": {"value": 100, "unit": "mg/kg", "source": "FDA"}}'
    config = {"configurable": {"thread_id": "test-form-001"}}
    
    result = graph.invoke({
        "user_input": json_input,
        "json_data": {"inci": "TEST_INCI", "NOAEL": []},
        "conversation_id": "test-form-001"
    }, config=config)
    
    assert result.get("intent_type") == "FORM_EDIT_STRUCTURED"
    assert result.get("form_payloads") is not None


# =============================================================================
# Run Examples (same as original)
# =============================================================================

if __name__ == "__main__":
    # Test original toxicity graph still works
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
    print("Testing NOAEL Workflow (Original Toxicity Graph)")
    print("=" * 60)
    
    result = process_correction_form(noael_text)
    
    print(f"\nTask Type: {result['task_type']}")
    print(f"INCI: {result['current_inci']}")
    print(f"\nNOAEL JSON:\n{result.get('noael_json', result.get('noael_payload'))}")
    
    # Test intent classification
    print("\n" + "=" * 60)
    print("Testing Intent Classification")
    print("=" * 60)
    
    test_cases = [
        ("For L-MENTHOL, set NOAEL to 200 mg/kg", "NLI_EDIT"),
        ("Change the source to FDA", "NLI_EDIT"),
        ('{"noael": {"value": 100}}', "FORM_EDIT_STRUCTURED"),
        ("NOAEL: 50\nSpecies: Rat\nDuration: 90 days", "FORM_EDIT_RAW"),
    ]
    
    for text, expected in test_cases:
        actual = classify_intent(text)
        status = "✅" if actual == expected else "❌"
        print(f"{status} '{text[:40]}...' → {actual} (expected: {expected})")
