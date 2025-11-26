# ============================================================================
# Unified Toxicology Endpoint - Dynamic Field Handling
# ============================================================================

"""
Single endpoint that handles ALL toxicology fields dynamically.

Usage:
POST /edit-form/toxicity-data/skin_irritation
POST /edit-form/toxicity-data/skin_sensitization
POST /edit-form/toxicity-data/ocular_irritation
POST /edit-form/toxicity-data/phototoxicity
POST /edit-form/toxicity-data/repeated_dose_toxicity
POST /edit-form/toxicity-data/percutaneous_absorption
POST /edit-form/toxicity-data/acute_toxicity
POST /edit-form/toxicity-data/ingredient_profile
"""

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import json
from pathlib import Path as FilePath

from app.services.json_io import read_json, write_json
from app.config import JSON_TEMPLATE, JSON_TEMPLATE_PATH

# ============================================================================
# Configuration
# ============================================================================

# JSON_TEMPLATE_PATH = FilePath("./data/toxicology_template.json")

router = APIRouter(prefix="/api/v1", tags=["toxicology"])


# ============================================================================
# Enums for Validation
# ============================================================================

class ToxicologyField(str, Enum):
    """Valid toxicology field names"""
    ACUTE_TOXICITY = "acute_toxicity"
    SKIN_IRRITATION = "skin_irritation"
    SKIN_SENSITIZATION = "skin_sensitization"
    OCULAR_IRRITATION = "ocular_irritation"
    PHOTOTOXICITY = "phototoxicity"
    REPEATED_DOSE_TOXICITY = "repeated_dose_toxicity"
    PERCUTANEOUS_ABSORPTION = "percutaneous_absorption"
    INGREDIENT_PROFILE = "ingredient_profile"


# ============================================================================
# Helper Functions
# ============================================================================

# def read_json() -> dict:
#     """Read the current JSON template"""
#     try:
#         with open(JSON_TEMPLATE_PATH, "r", encoding="utf-8") as f:
#             return json.load(f)
#     except FileNotFoundError:
#         return {
#             "inci": "",
#             "cas": [],
#             "isSkip": False,
#             "category": "OTHERS",
#             "acute_toxicity": [],
#             "skin_irritation": [],
#             "skin_sensitization": [],
#             "ocular_irritation": [],
#             "phototoxicity": [],
#             "repeated_dose_toxicity": [],
#             "percutaneous_absorption": [],
#             "ingredient_profile": [],
#             "NOAEL": [],
#             "DAP": [],
#             "inci_ori": ""
#         }


# def write_json(data: dict, filepath: str) -> None:
#     """Write data to JSON file"""
#     with open(filepath, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)


def _is_duplicate_entry(existing_entries: List[dict], new_entry: dict) -> bool:
    """Check if new_entry is a duplicate"""
    for entry in existing_entries:
        if (entry.get("reference", {}).get("title") == 
            new_entry.get("reference", {}).get("title")):
            if entry.get("source") == new_entry.get("source"):
                if (entry.get("data", []) and new_entry.get("data", []) and
                    len(entry["data"]) > 0 and len(new_entry["data"]) > 0 and
                    entry["data"][0] == new_entry["data"][0]):
                    return True
    return False


# ============================================================================
# Unified Pydantic Model
# ============================================================================

class ToxicologyDataRequest(BaseModel):
    """
    Unified model for all toxicology fields.
    
    Required fields:
    - inci_name: Ingredient name
    - data: List of data points (findings, observations)
    - source: Data source (e.g., echa, oecd, fda)
    - reference_title: Reference document title
    
    Optional fields (common to all fields):
    - reference_link: URL to reference
    - statement: Summary statement
    - metadata: Additional field-specific data
    """
    inci_name: str = Field(..., description="成分名稱 (INCI name)")
    data: List[str] = Field(..., min_items=1, description="資料列表 (list of data points/findings)")
    source: str = Field(..., description="來源 (e.g., echa, oecd, fda, pubchem)")
    reference_title: str = Field(..., description="參考文獻標題")
    reference_link: Optional[str] = Field(None, description="參考文獻連結 (optional)")
    statement: Optional[str] = Field(None, description="說明 (optional - auto-generated if not provided)")
    
    # Optional metadata for field-specific information
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Field-specific metadata (e.g., test_subject, test_guideline, concentration, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "inci_name": "L-MENTHOL",
                "data": [
                    "選定化合物：L-薄荷醇 (L-Menthol)",
                    "摘要：L-薄荷醇被發現對皮膚有刺激性",
                    "兔子：根據OECD 404指導方針進行測試"
                ],
                "source": "echa",
                "reference_title": "ECHA CAS: 89-78-1",
                "reference_link": "https://echa.europa.eu/registration-dossier/-/registered-dossier/15383/7/6/1",
                "statement": "Based on ECHA skin irritation assessment",
                "metadata": {
                    "test_subject": "Rabbits",
                    "test_guideline": "OECD 404",
                    "concentration": "50%",
                    "study_duration": "14 days"
                }
            }
        }


# ============================================================================
# Unified Endpoint
# ============================================================================

@router.post("/edit-form/toxicity-data/{toxicology_field}")
async def edit_toxicology_data(
    toxicology_field: ToxicologyField = Path(
        ..., 
        description="Toxicology field name",
        example="skin_irritation"
    ),
    req: ToxicologyDataRequest = None
):
    """
    ✨ Unified endpoint for ALL toxicology fields
    
    **Supported fields:**
    - acute_toxicity
    - skin_irritation
    - skin_sensitization
    - ocular_irritation
    - phototoxicity
    - repeated_dose_toxicity
    - percutaneous_absorption
    - ingredient_profile
    
    **Required fields:**
    - inci_name: Ingredient name
    - data: List of data points (at least 1 item)
    - source: Data source (e.g., echa, oecd, fda)
    - reference_title: Reference document title
    
    **Optional fields:**
    - reference_link: URL to reference
    - statement: Summary statement (auto-generated if not provided)
    - metadata: Field-specific data (test_subject, test_guideline, etc.)
    
    **Example request:**
    ```json
    POST /edit-form/toxicity-data/skin_irritation
    {
      "inci_name": "L-MENTHOL",
      "data": [
        "Finding 1",
        "Finding 2"
      ],
      "source": "echa",
      "reference_title": "ECHA Study",
      "reference_link": "https://...",
      "statement": "Based on assessment",
      "metadata": {
        "test_subject": "Rabbits",
        "test_guideline": "OECD 404",
        "concentration": "50%"
      }
    }
    ```
    
    **Returns:**
    ```json
    {
      "message": "✅ skin_irritation updated successfully",
      "inci": "L-MENTHOL",
      "field": "skin_irritation",
      "updated_json": { ... }
    }
    ```
    """
    try:
        # Read current JSON
        current_json = read_json()
        
        # Validate field exists in JSON structure
        field_name = toxicology_field.value
        if field_name not in current_json:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid field: {field_name} not found in JSON template"
            )
        
        # Build statement if not provided
        final_statement = req.statement
        if not final_statement:
            statement_parts = [f"Based on {req.source} assessment"]
            
            # Add metadata to statement if available
            if req.metadata:
                if req.metadata.get("test_subject"):
                    statement_parts.append(f"with {req.metadata['test_subject']}")
                if req.metadata.get("test_guideline"):
                    statement_parts.append(f"following {req.metadata['test_guideline']}")
                if req.metadata.get("concentration"):
                    statement_parts.append(f"at {req.metadata['concentration']} concentration")
                if req.metadata.get("study_duration"):
                    statement_parts.append(f"over {req.metadata['study_duration']}")
            
            final_statement = " ".join(statement_parts)
        
        # Create entry
        entry = {
            "reference": {
                "title": req.reference_title,
                "link": req.reference_link
            },
            "data": req.data,
            "statement": final_statement,
            "replaced": {
                "replaced_inci": "",
                "replaced_type": ""
            },
            "source": req.source
        }
        
        # Add metadata to entry if provided (for reference/documentation)
        if req.metadata:
            entry["_metadata"] = req.metadata
        
        # Update JSON
        current_json["inci"] = req.inci_name
        current_json["inci_ori"] = req.inci_name
        
        # Check for duplicates
        if _is_duplicate_entry(current_json.get(field_name, []), entry):
            return {
                "message": f"⚠️ Duplicate entry detected in {field_name} - not added",
                "inci": req.inci_name,
                "field": field_name,
                "updated_json": current_json
            }
        
        # Append to the specified field
        current_json[field_name].append(entry)
        
        # Save to file
        write_json(current_json, str(JSON_TEMPLATE_PATH))
        
        return {
            "message": f"✅ {field_name} updated successfully (form-based, no LLM)",
            "inci": req.inci_name,
            "field": field_name,
            "entries_count": len(current_json[field_name]),
            "updated_json": current_json
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update {toxicology_field.value}: {str(e)}"
        )


# ============================================================================
# Additional Helper Endpoints
# ============================================================================

@router.get("/toxicity-data/{toxicology_field}")
async def get_toxicology_data(
    toxicology_field: ToxicologyField = Path(..., description="Toxicology field name")
):
    """
    Get all entries for a specific toxicology field
    
    Example: GET /toxicity-data/skin_irritation
    """
    try:
        current_json = read_json()
        field_name = toxicology_field.value
        
        if field_name not in current_json:
            raise HTTPException(status_code=404, detail=f"Field {field_name} not found")
        
        return {
            "field": field_name,
            "inci": current_json.get("inci", ""),
            "entries": current_json.get(field_name, []),
            "count": len(current_json.get(field_name, []))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/toxicity-data/{toxicology_field}/{entry_index}")
async def delete_toxicology_entry(
    toxicology_field: ToxicologyField = Path(..., description="Toxicology field name"),
    entry_index: int = Path(..., ge=0, description="Entry index to delete")
):
    """
    Delete a specific entry from a toxicology field
    
    Example: DELETE /toxicity-data/skin_irritation/0
    """
    try:
        current_json = read_json()
        field_name = toxicology_field.value
        
        if field_name not in current_json:
            raise HTTPException(status_code=404, detail=f"Field {field_name} not found")
        
        entries = current_json.get(field_name, [])
        
        if entry_index >= len(entries):
            raise HTTPException(
                status_code=404, 
                detail=f"Entry index {entry_index} out of range (max: {len(entries)-1})"
            )
        
        deleted_entry = entries.pop(entry_index)
        write_json(current_json, str(JSON_TEMPLATE_PATH))
        
        return {
            "message": f"✅ Entry {entry_index} deleted from {field_name}",
            "deleted_entry": deleted_entry,
            "remaining_count": len(entries)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields/list")
async def list_available_fields():
    """
    List all available toxicology fields
    """
    return {
        "fields": [field.value for field in ToxicologyField],
        "count": len(ToxicologyField)
    }


# ============================================================================
# Usage Examples
# ============================================================================

"""
# Example 1: Add skin irritation data
POST /edit-form/toxicity-data/skin_irritation
{
  "inci_name": "L-MENTHOL",
  "data": ["Finding 1", "Finding 2"],
  "source": "echa",
  "reference_title": "ECHA Study",
  "metadata": {
    "test_subject": "Rabbits",
    "test_guideline": "OECD 404"
  }
}

# Example 2: Add skin sensitization data
POST /edit-form/toxicity-data/skin_sensitization
{
  "inci_name": "L-MENTHOL",
  "data": ["No sensitization observed"],
  "source": "oecd",
  "reference_title": "OECD LLNA Study",
  "metadata": {
    "test_method": "LLNA",
    "test_subject": "Mice"
  }
}

# Example 3: Add phototoxicity data
POST /edit-form/toxicity-data/phototoxicity
{
  "inci_name": "L-MENTHOL",
  "data": ["No phototoxic potential"],
  "source": "oecd",
  "reference_title": "OECD 432 Study",
  "metadata": {
    "test_method": "3T3 NRU PT",
    "uv_wavelength": "UVA 320-400nm"
  }
}

# Example 4: Get all entries for a field
GET /toxicity-data/skin_irritation

# Example 5: Delete an entry
DELETE /toxicity-data/skin_irritation/0

# Example 6: List all available fields
GET /fields/list
"""