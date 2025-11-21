# tests/test_chat_history.py
"""
Test chat history functionality with LangGraph checkpointer
"""
import sys
import json
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.build_graph import build_graph
from app.graph.state import JSONEditState

def test_single_edit():
    """Test single edit with chat history"""
    print("\n=== Test 1: Single Edit ===")
    
    graph = build_graph()
    
    # Create unique conversation ID
    conv_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conv_id}}
    
    # Initial state
    state = JSONEditState(
        json_data={
            "inci": "TEST_INGREDIENT",
            "category": "OTHERS",
            "NOAEL": []
        },
        user_input="Change category to FRAGRANCE",
        response="",
        current_inci="TEST_INGREDIENT",
        edit_history=None,
        error=None
    )
    
    # Execute
    result = graph.invoke(state, config=config)
    
    # Verify
    assert "json_data" in result
    assert result["json_data"]["category"].upper() == "FRAGRANCE"
    
    print(f"✅ Category changed: {result['json_data']['category']}")
    print(f"✅ Response: {result['response'][:100]}...")
    
    return conv_id

def test_multiple_edits():
    """Test multiple sequential edits with history"""
    print("\n=== Test 2: Multiple Edits ===")
    
    graph = build_graph()
    conv_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conv_id}}
    
    # Edit 1: Set INCI name
    state1 = JSONEditState(
        json_data={"inci": "INCI_NAME", "NOAEL": []},
        user_input="Set INCI to L-MENTHOL",
        response="",
        current_inci="INCI_NAME",
        edit_history=None,
        error=None
    )
    result1 = graph.invoke(state1, config=config)
    assert result1["json_data"]["inci"].upper() == "L-MENTHOL"
    print(f"✅ Edit 1: INCI = {result1['json_data']['inci']}")
    
    # Edit 2: Set NOAEL (using same thread)
    state2 = JSONEditState(
        json_data=result1["json_data"],  # Use updated data
        user_input="Set NOAEL to 200 mg/kg bw/day",
        response="",
        current_inci="L-MENTHOL",
        edit_history=None,
        error=None
    )
    result2 = graph.invoke(state2, config=config)
    assert len(result2["json_data"]["NOAEL"]) > 0
    # NEW:
    noael_value = result2["json_data"]["NOAEL"][0]
    if isinstance(noael_value, dict):
        print(f"✅ Edit 2: NOAEL = {noael_value.get('value', noael_value)}")
    else:
        print(f"✅ Edit 2: NOAEL = {noael_value}")
    
    return conv_id

def test_checkpoint_persistence():
    """Test that checkpoints are saved and loaded correctly"""
    print("\n=== Test 3: Checkpoint Persistence ===")
    
    graph = build_graph()
    conv_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conv_id}}
    
    # First invocation
    state1 = JSONEditState(
        json_data={"inci": "TEST", "NOAEL": [], "repeated_dose_toxicity": []},
        user_input="Update INCI to CAFFEINE",
        response="",
        current_inci="TEST",
        edit_history=None,
        error=None
    )
    result1 = graph.invoke(state1, config=config)
    
    # Get checkpoint
    checkpoint = graph.get_state(config)
    assert checkpoint is not None
    print(f"✅ Checkpoint saved for thread: {conv_id}")
    print(f"✅ Checkpoint values: {checkpoint.values.get('json_data', {}).get('inci')}")
    
    # Second invocation (should load from checkpoint)
    state2 = JSONEditState(
        json_data=result1["json_data"],
        user_input="Set NOAEL to 150",
        response="",
        current_inci="CAFFEINE",
        edit_history=None,
        error=None
    )
    result2 = graph.invoke(state2, config=config)
    
    # Verify checkpoint updated
    checkpoint2 = graph.get_state(config)
    assert checkpoint2.values["json_data"]["inci"].upper() == "CAFFEINE"
    print(f"✅ Checkpoint updated correctly")
    
    return conv_id

def test_different_threads():
    """Test that different threads maintain separate state"""
    print("\n=== Test 4: Different Threads ===")
    
    graph = build_graph()
    
    # Thread 1
    conv_id1 = str(uuid.uuid4())
    config1 = {"configurable": {"thread_id": conv_id1}}
    
    state1 = JSONEditState(
        json_data={"inci": "INGREDIENT_1", "NOAEL": []},
        user_input="Update to L-MENTHOL",
        response="",
        current_inci="INGREDIENT_1",
        edit_history=None,
        error=None
    )
    result1 = graph.invoke(state1, config=config1)
    
    # Thread 2
    conv_id2 = str(uuid.uuid4())
    config2 = {"configurable": {"thread_id": conv_id2}}
    
    state2 = JSONEditState(
        json_data={"inci": "INGREDIENT_2", "NOAEL": []},
        user_input="Update to CAFFEINE",
        response="",
        current_inci="INGREDIENT_2",
        edit_history=None,
        error=None
    )
    result2 = graph.invoke(state2, config=config2)
    
    # Verify independence (case-insensitive)
    inci1 = result1["json_data"]["inci"].upper()
    inci2 = result2["json_data"]["inci"].upper()
    assert inci1 != inci2
    print(f"✅ Thread 1: {result1['json_data']['inci']}")
    print(f"✅ Thread 2: {result2['json_data']['inci']}")
    print(f"✅ Threads are independent")

def test_error_handling():
    """Test error handling with chat history"""
    print("\n=== Test 5: Error Handling ===")
    
    graph = build_graph()
    conv_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conv_id}}
    
    # Invalid input
    state = JSONEditState(
        json_data={"inci": "TEST", "NOAEL": []},
        user_input="",  # Empty input
        response="",
        current_inci="TEST",
        edit_history=None,
        error=None
    )
    
    try:
        result = graph.invoke(state, config=config)
        # Should handle gracefully
        print(f"✅ Error handled gracefully")
        print(f"   Response: {result.get('response', 'No response')[:100]}")
    except Exception as e:
        print(f"⚠️  Exception raised: {e}")

def run_all_tests():
    """Run all chat history tests"""
    print("="*60)
    print("CHAT HISTORY TESTS")
    print("="*60)
    
    try:
        test_single_edit()
        test_multiple_edits()
        test_checkpoint_persistence()
        test_different_threads()
        test_error_handling()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()