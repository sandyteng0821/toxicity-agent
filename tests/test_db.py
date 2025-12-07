# test_db.py
# from database import ToxicityDB
import sys
from pathlib import Path
# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import ToxicityDB

db = ToxicityDB()

# Save initial version
initial_data = {"toxicity_score": 0.8, "categories": {"hate": 0.9}}
# db.save_version(conversation_id="test-conv", inci_name="test-conv-inci", data=initial_data, modification_summary="Initial data")
# --- START MIGRATION ---
db.save_modification( # Replaced db.save_version
    item_id="test-conv", # Renamed from conversation_id
    inci_name="test-conv-inci", 
    data=initial_data, 
    instruction="Initial data via test script", # Replaced modification_summary
    patch_operations=None, # Not a patch operation
    is_batch_item=False,
    patch_success=True
)
# --- END MIGRATION ---

# Get it back
version = db.get_current_version("test-conv")
print(f"Version {version.version}: {version.data}")