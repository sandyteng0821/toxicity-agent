# test_node.py
# from your_graph_file import build_graph, db
import sys
import json
from pathlib import Path
from langchain_core.messages import HumanMessage
# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.build_graph import build_graph, db

graph = build_graph()

# Use your actual template
template = {
    "inci": "TEST_INGREDIENT",
    "cas": [],
    "isSkip": False,
    "category": "OTHERS",
    "acute_toxicity": [],
    "skin_irritation": [],
    "skin_sensitization": [],
    "ocular_irritation": [],
    "phototoxicity": [],
    "repeated_dose_toxicity": [],
    "percutaneous_absorption": [],
    "ingredient_profile": [],
    "NOAEL": [],
    "DAP": [],
    "inci_ori": "TEST_INGREDIENT"
}

conv_id = "simple-test"
db.save_version(conv_id, template, "Initial")

config = {"configurable": {"thread_id": conv_id}}

# Test edit
result = graph.invoke({
    "messages": [HumanMessage(content="Change category to FRAGRANCE")],
    "conversation_id": conv_id,
    "user_input": "Change category to FRAGRANCE",
    "json_data": {},
    "response": "",
    "current_inci": "",
    "edit_history": None,
    "error": None
}, config=config)

# Verify
latest = db.get_current_version(conv_id)
data = json.loads(latest.data)

print(f"✅ Test passed!" if data["category"] == "FRAGRANCE" else "❌ Test failed!")
print(f"Version: {latest.version}")
print(f"Category: {data['category']}")
print(f"Messages: {len(result['messages'])}")