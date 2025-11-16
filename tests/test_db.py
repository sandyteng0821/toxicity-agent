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
db.save_version("test-conv", initial_data, "Initial data")

# Get it back
version = db.get_current_version("test-conv")
print(f"Version {version.version}: {version.data}")