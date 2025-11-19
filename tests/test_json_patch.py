import os
from langgraph.graph import StateGraph, END

from app.graph.build_graph import build_graph
from app.graph.state import JSONEditState
from app.services.json_io import write_json

# Import your field definitions
from app.config import TOXICOLOGY_FIELDS, METRIC_FIELDS

def test_json_patch_integration():
    """Test JSON Patch integration with toxicology data"""
    
    # ✨ Generate test data instead of reading from file
    test_json = {
        "inci": "INCI_NAME",
        "cas": [],
        "isSkip": False,
        "category": "OTHERS",
        **{field: [] for field in TOXICOLOGY_FIELDS},
        **{field: [] for field in METRIC_FIELDS},
        "inci_ori": "inci_name"
    }
    
    # Output path
    outputjson = "./data/toxicity_data_template-blank-patched.json"
    
    # Setup
    graph = build_graph(use_test_db=True)

    # Test: Natural language input
    test_input = "For L-MENTHOL, set NOAEL to 200 mg/kg bw/day for Rats based on 90-day oral gavage study. Source: OECD SIDS."
    conv_id = "test-jsonpatch-001"
    config = {"configurable": {"thread_id": conv_id}} 

    # Run graph
    result = graph.invoke({
        "user_input": test_input,
        "json_data": test_json,  # ✨ Use generated test data
        "conversation_id": conv_id
    }, config=config)

    # Save output
    os.makedirs(os.path.dirname(outputjson), exist_ok=True)
    write_json(result["json_data"], outputjson)
    print(f"📝 Output saved to: {outputjson}")
    
    # Verify
    assert "NOAEL" in result["json_data"], "NOAEL not found in result"
    assert result.get("last_patches") is not None, "last_patches not found in result"
    assert len(result["last_patches"]) > 0, "No patches were generated"
    
    print("✅ Test passed: JSON Patch working!")
    print(f"Generated patch: {result['last_patches'][0].model_dump()}")


if __name__ == "__main__":
    """Run test directly without pytest"""
    # test command: python3 -m tests.test_json_patch
    
    # ✨ Generate test data
    test_json = {
        "inci": "INCI_NAME",
        "cas": [],
        "isSkip": False,
        "category": "OTHERS",
        **{field: [] for field in TOXICOLOGY_FIELDS},
        **{field: [] for field in METRIC_FIELDS},
        "inci_ori": "inci_name"
    }
    
    outputjson = "./data/manual_toxicity_data_template-blank-patched.json"
    
    graph = build_graph(use_test_db=True)

    test_input = "For L-MENTHOL, set NOAEL to 200 mg/kg bw/day for Rats based on 90-day oral gavage study. Source: OECD SIDS."
    conv_id = "test-jsonpatch-manual"
    config = {"configurable": {"thread_id": conv_id}} 

    result = graph.invoke({
        "user_input": test_input,
        "json_data": test_json,  # ✨ Use generated test data
        "conversation_id": conv_id
    }, config=config)

    # Save output
    os.makedirs(os.path.dirname(outputjson), exist_ok=True)
    write_json(result["json_data"], outputjson)
    print(f"📝 Output saved to: {outputjson}")

    # Verify
    assert "NOAEL" in result["json_data"]
    assert result.get("last_patches") is not None
    
    print("✅ Test passed: JSON Patch working!")
    print(f"Generated patch: {result['last_patches'][0].model_dump()}")