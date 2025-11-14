"""
Tests to verify refactored code works correctly
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.json_io import read_json, write_json
from app.services.text_processing import extract_inci_name, clean_llm_json_output
from app.services.data_updater import fix_common_llm_errors, merge_json_updates
from app.graph.build_graph import build_graph

def test_json_io():
    """Test JSON read/write"""
    test_data = {"inci": "TEST", "cas": []}
    assert write_json(test_data, "test.json")
    loaded = read_json("test.json")
    assert loaded["inci"] == "TEST"

def test_extract_inci():
    """Test INCI extraction"""
    assert extract_inci_name("inci_name = PETROLATUM") == "PETROLATUM"
    assert extract_inci_name("INCI: WATER") == "WATER"

def test_clean_llm_output():
    """Test LLM output cleaning"""
    raw = '```json\n{"inci": "TEST"}\n```'
    cleaned = clean_llm_json_output(raw)
    assert cleaned == '{"inci": "TEST"}'

def test_fix_llm_errors():
    """Test error fixing"""
    errors = {"INCI": "TEST", "toxicology": {"NOAEL": []}}
    fixed = fix_common_llm_errors(errors)
    assert "inci" in fixed
    assert "INCI" not in fixed
    assert "NOAEL" in fixed

def test_graph_builds():
    """Test graph compilation"""
    graph = build_graph()
    assert graph is not None

def test_graph_invoke():
    """Test graph execution"""
    from app.graph.state import JSONEditState
    
    graph = build_graph()
    state = JSONEditState(
        json_data={"inci": "TEST", "NOAEL": []},
        user_input="Update INCI name to PETROLATUM",
        response="",
        current_inci="TEST",
        edit_history=None,
        error=None
    )
    
    result = graph.invoke(state)
    assert "json_data" in result
    assert "response" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])