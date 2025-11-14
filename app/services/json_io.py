"""
JSON file I/O operations
"""
import json
import os
from typing import Dict, Any
from pathlib import Path

from app.config import JSON_TEMPLATE, JSON_TEMPLATE_PATH

def read_json(filepath: str = None) -> Dict[str, Any]:
    """
    Read JSON file with error handling
    
    Args:
        filepath: Path to JSON file (defaults to template path)
        
    Returns:
        Dict containing JSON data
    """
    if filepath is None:
        filepath = str(JSON_TEMPLATE_PATH)
    
    try:
        if not os.path.exists(filepath):
            # Create template if doesn't exist
            write_json(JSON_TEMPLATE, filepath)
            return JSON_TEMPLATE

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
            
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {filepath}: {e}")
        return {"error": f"Failed to read JSON: {str(e)}"}

def write_json(data: Dict[str, Any], filepath: str = None) -> bool:
    """
    Write JSON file with error handling
    
    Args:
        data: Data to write
        filepath: Path to write to (defaults to template path)
        
    Returns:
        True if successful, False otherwise
    """
    if filepath is None:
        filepath = str(JSON_TEMPLATE_PATH)
    
    try:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ JSON successfully saved to {filepath}")
        return True
        
    except IOError as e:
        print(f"❌ Error writing {filepath}: {e}")
        return False

def validate_json_structure(data: Dict[str, Any]) -> bool:
    """
    Validate that JSON has required fields
    
    Args:
        data: JSON data to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["inci", "cas", "category"]
    return all(field in data for field in required_fields)