"""
Logic for updating toxicology data structures
"""
from typing import Dict, List, Any

def update_toxicology_data(
    current_data: List[Dict], 
    new_data: List[Dict]
) -> List[Dict]:
    """
    Update toxicology data by merging new entries with existing
    
    Args:
        current_data: Existing data array
        new_data: New entries to add/merge
        
    Returns:
        Updated data array
    """
    updated_data = current_data.copy()

    for new_entry in new_data:
        # Check if similar entry exists (same source and reference title)
        existing_index = -1
        for i, existing_entry in enumerate(updated_data):
            if (existing_entry.get('source') == new_entry.get('source') and
                existing_entry.get('reference', {}).get('title') == 
                new_entry.get('reference', {}).get('title')):
                existing_index = i
                break

        if existing_index >= 0:
            # Update existing entry
            updated_data[existing_index].update(new_entry)
        else:
            # Add new entry
            updated_data.append(new_entry)

    return updated_data

def fix_common_llm_errors(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix common mistakes LLMs make in JSON structure
    
    Args:
        updates: Raw updates from LLM
        
    Returns:
        Corrected updates
    """
    corrected = updates.copy()
    
    # Fix 1: INCI → inci
    if "INCI" in corrected and "inci" not in corrected:
        print("⚠️ Fixing: INCI → inci")
        corrected["inci"] = corrected.pop("INCI")
    
    # Fix 2: Unnest toxicology object
    if "toxicology" in corrected:
        print("⚠️ Fixing: unnesting toxicology")
        toxicology = corrected.pop("toxicology")
        corrected.update(toxicology)
    
    # Fix 3: Remove placeholder arrays
    for key, value in list(corrected.items()):
        if isinstance(value, list) and len(value) == 1 and value[0] == "...":
            print(f"⚠️ Removing placeholder for {key}")
            del corrected[key]
    
    return corrected

def merge_json_updates(
    base_json: Dict[str, Any], 
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge updates into base JSON with smart array handling
    
    Args:
        base_json: Current JSON structure
        updates: Updates to apply
        
    Returns:
        Merged JSON
    """
    from app.config import TOXICOLOGY_FIELDS
    
    merged = base_json.copy()
    updates = fix_common_llm_errors(updates)
    
    for key, value in updates.items():
        if key == "inci":
            merged["inci"] = value
            merged["inci_ori"] = value
            print(f"✅ Updated inci: {value}")
            
        elif key in merged:
            if isinstance(value, list) and value:
                # Toxicology fields: append
                if key in TOXICOLOGY_FIELDS:
                    merged[key] = update_toxicology_data(merged[key], value)
                    print(f"✅ Appended to {key}: {len(value)} entries")
                else:
                    # Metric fields (NOAEL, DAP): replace
                    merged[key] = value
                    print(f"✅ Replaced {key}: {len(value)} entries")
            else:
                merged[key] = value
                print(f"✅ Updated {key}")
        else:
            merged[key] = value
            print(f"✅ Added new field: {key}")
    
    return merged