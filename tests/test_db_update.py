# test_db_update.py
import pytest
import json
from pathlib import Path
from sqlalchemy import text

from core.database import ToxicityDB


@pytest.fixture
def test_db():
    """Create a test database instance with separate test database"""
    import os
    
    test_db_path = "test_toxicity_data.db"
    
    # Remove old test database if exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Create test database
    db = ToxicityDB(db_path=test_db_path)
    
    yield db
    
    # Cleanup: Remove test database after tests
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def test_data():
    """Sample test data"""
    return {
        "inci": "Test Chemical",
        "acute_toxicity": []
    }


@pytest.fixture
def test_patches():
    """Sample test patches"""
    return [
        {
            "op": "add",
            "path": "/acute_toxicity/-",
            "value": {
                "reference": "Test",
                "data": "LD50=500",
                "source": "",
                "statement": "",
                "replaced": False
            }
        }
    ]


def test_save_version_with_patches(test_db, test_data, test_patches):
    """Test saving a version with patch operations"""
    
    # --- START MIGRATION 1/5 ---
    # Save with patches
    version = test_db.save_modification( # Replaced save_version
        item_id="test-001",              # Replaced conversation_id
        inci_name="test-inci-001",
        data=test_data,
        instruction="Test save with patches", # Replaced modification_summary
        patch_operations=test_patches,
        is_batch_item=False,             # Added flag
        patch_success=True               # Added flag
    )
    # --- END MIGRATION 1/5 ---
    
    # Verify version was saved
    assert version.id is not None
    assert version.patch_operations is not None
    
    print(f"✅ Saved version {version.id}")
    print(f"Patch operations: {version.patch_operations}")


def test_retrieve_version_patches(test_db, test_data, test_patches):
    """Test retrieving patch operations from a version"""
    
    # --- START MIGRATION 2/5 ---
    # First save a version with patches
    test_db.save_modification( # Replaced save_version
        item_id="test-002",
        inci_name="test-inci-002",
        data=test_data,
        instruction="Test save with patches",
        patch_operations=test_patches,
        is_batch_item=False,
        patch_success=True
    )
    # --- END MIGRATION 2/5 ---
    
    # Retrieve patches
    retrieved_patches = test_db.get_version_patches("test-002")
    
    # Verify
    assert retrieved_patches is not None
    assert len(retrieved_patches) > 0
    assert retrieved_patches[0]["op"] == "add"
    assert retrieved_patches[0]["path"] == "/acute_toxicity/-"
    
    print(f"✅ Retrieved patches: {retrieved_patches}")


def test_modification_history_with_patches(test_db, test_data, test_patches):
    """Test getting modification history with patch details"""
    
    # --- START MIGRATION 3a/5 ---
    # Save multiple versions with patches (Version 1)
    test_db.save_modification( # Replaced save_version
        item_id="test-003",
        inci_name="test-inci-003",
        data=test_data,
        instruction="First update",
        patch_operations=test_patches,
        is_batch_item=False,
        patch_success=True
    )
    # --- END MIGRATION 3a/5 ---
    
    # --- START MIGRATION 3b/5 ---
    # Save another version (Version 2)
    test_db.save_modification( # Replaced save_version
        item_id="test-003",
        inci_name="test-inci-003",
        data=test_data,
        instruction="Second update",
        patch_operations=test_patches,
        is_batch_item=False,
        patch_success=True
    )
    # --- END MIGRATION 3b/5 ---
    
    # Get history with patches
    history = test_db.get_modification_history_with_patches("test-003")
    
    # Verify
    assert len(history) == 2
    assert "patches" in history[0]
    assert "patch_count" in history[0]
    assert history[0]["patch_count"] > 0
    
    print(f"✅ History with patches: {json.dumps(history, indent=2)}")


def test_save_version_without_patches(test_db, test_data):
    """Test saving a version without patches (backward compatibility)"""
    
    # --- START MIGRATION 4/5 ---
    # Save without patches
    version = test_db.save_modification( # Replaced save_version
        item_id="test-004",
        inci_name="test-inci-004",
        data=test_data,
        instruction="Test save without patches",
        patch_operations=None, # Explicitly pass None or omit (if default is None)
        is_batch_item=False,
        patch_success=True
    )
    # --- END MIGRATION 4/5 ---
    
    # Verify
    assert version.id is not None
    assert version.patch_operations is None  # Should be None when not provided
    
    print(f"✅ Saved version without patches: {version.id}")


if __name__ == "__main__":
    """Run tests directly without pytest"""
    
    print("Running database tests manually...\n")
    
    db = ToxicityDB()
    
    test_data = {
        "inci": "Test Chemical",
        "acute_toxicity": []
    }
    
    test_patches = [
        {
            "op": "add",
            "path": "/acute_toxicity/-",
            "value": {
                "reference": "Test",
                "data": "LD50=500",
                "source": "",
                "statement": "",
                "replaced": False
            }
        }
    ]
    
    # Test 1: Save with patches
    print("Test 1: Save with patches")
    # --- START MIGRATION 5/5 (Manual Run) ---
    version = db.save_modification( # Replaced save_version
        item_id="manual-test-001",
        inci_name="manual-test-inci-001",
        data=test_data,
        instruction="Test save with patches",
        patch_operations=test_patches,
        is_batch_item=False,
        patch_success=True
    )
    # --- END MIGRATION 5/5 ---
    print(f"✅ Saved version {version.id}")
    print(f"Patch operations: {version.patch_operations}\n")
    
    # Test 2: Retrieve patches (No change needed here as it calls get_version_patches)
    print("Test 2: Retrieve patches")
    retrieved_patches = db.get_version_patches("manual-test-001")
    print(f"✅ Retrieved patches: {retrieved_patches}\n")
    
    # Test 3: Get history with patches (No change needed here as it calls get_modification_history_with_patches)
    print("Test 3: Get history with patches")
    history = db.get_modification_history_with_patches("manual-test-001")
    print(f"✅ History with patches: {json.dumps(history, indent=2)}\n")
    
    print("All manual tests passed! ✅")