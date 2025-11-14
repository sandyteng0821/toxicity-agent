def _is_duplicate_entry(existing_entries: list, new_entry: dict) -> bool:
    """
    Check if entry already exists (based on source and reference title)
    
    Args:
        existing_entries: List of existing entries
        new_entry: New entry to check
        
    Returns:
        True if duplicate found, False otherwise
    """
    new_source = new_entry.get("source")
    new_ref_title = new_entry.get("reference", {}).get("title")
    
    for entry in existing_entries:
        if (entry.get("source") == new_source and
            entry.get("reference", {}).get("title") == new_ref_title):
            return True
    
    return False