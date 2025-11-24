"""
API routes for toxicology editing
"""
import uuid
import json
from typing import Optional, Literal, List, Dict, Any
from fastapi import APIRouter, HTTPException, FastAPI
from pydantic import BaseModel, Field
from jsonpatch import JsonPatch
from langchain_core.messages import HumanMessage

from app.graph.build_graph import build_graph
from app.services.json_io import read_json, write_json
from app.config import JSON_TEMPLATE, JSON_TEMPLATE_PATH
from app.api.helper import _is_duplicate_entry
from core.database import ToxicityDB, ToxicityRepository

router = APIRouter(prefix="/api", tags=["edit"])

repo = ToxicityRepository(db_path="toxicity_data.db")
db = ToxicityDB()
graph = build_graph()

class EditRequest(BaseModel):
    """Request model for edit endpoint"""
    instruction: str
    inci_name: Optional[str] = None
    conversation_id: Optional[str] = None
    initial_data: Optional[dict] = None  # Only for first request

class EditResponse(BaseModel):
    """Response model for edit endpoint"""
    inci: str
    updated_json: dict
    raw_response: str
    conversation_id: str
    current_version: int

# ============================================================================
# Form-based Request Models
# ============================================================================

class NOAELFormRequest(BaseModel):
    """NOAEL form-based input with required fields"""
    inci_name: str = Field(..., description="成分名稱 (INCI name)")
    value: float = Field(..., gt=0, description="NOAEL 數值 (must be positive)")
    unit: Literal["mg/kg bw/day", "mg/kg", "ppm", "mg/L"] = Field(
        ..., 
        description="單位"
    )
    source: str = Field(..., description="來源 (e.g., oecd, fda, echa)")
    experiment_target: str = Field(..., description="實驗對象 (e.g., Rats, Mice, Rabbits)")
    study_duration: str = Field(..., description="研究時長 (e.g., 90-day, 28-day, chronic)")
    note: Optional[str] = Field(None, description="備註 (optional)")
    reference_title: str = Field(..., description="參考文獻標題")
    reference_link: Optional[str] = Field(None, description="參考文獻連結 (optional)")
    statement: Optional[str] = Field(None, description="說明 (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "inci_name": "L-MENTHOL",
                "value": 200,
                "unit": "mg/kg bw/day",
                "source": "oecd",
                "experiment_target": "Rats",
                "study_duration": "90-day",
                "note": "Based on oral gavage study",
                "reference_title": "OECD SIDS MENTHOLS UNEP PUBLICATIONS",
                "reference_link": "https://hpvchemicals.oecd.org/ui/handler.axd?id=463ce644-e5c8-42e8-962d-3a917f32ab90",
                "statement": "Based on repeated dose toxicity studies"
            }
        }

# app/api/routes_edit.py - Add this after the NOAEL endpoint

class DAPFormRequest(BaseModel):
    """DAP form-based input with required fields"""
    inci_name: str = Field(..., description="成分名稱")
    value: float = Field(..., ge=0, le=100, description="DAP 百分比 (0-100)")
    source: str = Field(..., description="來源 (e.g., expert, study, literature)")
    experiment_target: str = Field(..., description="實驗對象")
    study_duration: str = Field(..., description="研究時長")
    reference_title: str = Field(..., description="參考文獻標題")
    note: Optional[str] = Field(None, description="備註")
    reference_link: Optional[str] = Field(None, description="參考文獻連結")
    statement: Optional[str] = Field(None, description="說明")

    class Config:
        json_schema_extra = {
            "example": {
                "inci_name": "L-MENTHOL",
                "value": 5,
                "source": "expert",
                "experiment_target": "Human skin",
                "study_duration": "in vitro",
                "reference_title": "Expert Assessment of Dermal Absorption",
                "note": "Based on molecular weight and lipophilicity",
                "reference_link": None,
                "statement": "Conservative estimate based on physicochemical properties"
            }
        }

@router.post("/edit", response_model=EditResponse)
async def edit_json(req: EditRequest):
    """
    Edit toxicology JSON based on natural language instruction
    
    Args:
        req: Edit request containing instruction and optional INCI name
        
    Returns:
        Updated JSON and processing details
    """
    try:
        # ============================================
        # NEW: Conversation & Memory Setup
        # ============================================
        conv_id = req.conversation_id or str(uuid.uuid4())
        # NEW: Save initial data if provided
        if req.initial_data:
            db.save_version(
                conversation_id=conv_id,
                data=req.initial_data,
                modification_summary="Initial data"
            )
        
        # NEW: Configure thread for memory 
        config = {"configurable": {"thread_id": conv_id}}
        # ============================================
        # MODIFY: Load current data from DB (not file)
        # ============================================
        current_version_obj = db.get_current_version(conv_id)
        # If no data in DB, fall back to file (for backward compatibility)
        if current_version_obj:
            current_json = json.loads(current_version_obj.data)
        else:
            # Fallback: Load from file and save as version 1
            current_json = read_json()
            db.save_version(
                conversation_id=conv_id,
                data=current_json,
                modification_summary="Load from file"
            )

        # ============================================
        # KEEP: Prepare user input (your existing logic)
        # ============================================
        user_input = req.instruction
        if req.inci_name:
            user_input = f"INCI: {req.inci_name}\n{user_input}"

        # Run graph
        result = graph.invoke({
            "messages": [HumanMessage(content=user_input)],  # NEW: Add message
            "conversation_id": conv_id,  # NEW
            "json_data": current_json,
            "user_input": user_input,
            "response": "",
            "current_inci": req.inci_name or current_json.get('inci', 'INCI_NAME'),
            "edit_history": None,
            "error": None
        }, config=config)
        
        db.save_version(
            conversation_id=conv_id,
            data=result["json_data"],
            modification_summary=result.get("response", "Modified data")[:200]  # Truncate if long
        )

        # Save result (to file) => for backward compatibility
        write_json(result["json_data"], str(JSON_TEMPLATE_PATH))
        # Get latest version from DB
        latest = db.get_current_version(conv_id)
        
        return EditResponse(
            inci=result["current_inci"],
            updated_json=result["json_data"],
            raw_response=result["response"],
            conversation_id=conv_id,
            current_version=latest.version,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Form-based Endpoints
# ============================================================================

@router.post("/edit-form/noael")
async def edit_noael_form(req: NOAELFormRequest):
    """
    Form-based NOAEL update (zero LLM errors, guaranteed correct)
    
    Required fields:
    - inci_name: Ingredient name
    - value: NOAEL value (positive number)
    - unit: Unit of measurement
    - source: Data source (e.g., oecd, fda, echa)
    - experiment_target: Test subject (e.g., Rats, Mice)
    - study_duration: Study length (e.g., 90-day, 28-day)
    - reference_title: Reference document title
    
    Optional fields:
    - note: Additional notes
    - reference_link: URL to reference
    - statement: Summary statement
    
    Example request:
    {
      "inci_name": "L-MENTHOL",
      "value": 200,
      "unit": "mg/kg bw/day",
      "source": "oecd",
      "experiment_target": "Rats",
      "study_duration": "90-day",
      "note": "Based on oral gavage study",
      "reference_title": "OECD SIDS MENTHOLS",
      "reference_link": "https://...",
      "statement": "Based on repeated dose toxicity studies"
    }
    
    Returns:
    {
      "message": "✅ NOAEL updated successfully",
      "inci": "L-MENTHOL",
      "updated_json": { ... }
    }
    """
    try:
        # Read current JSON
        current_json = read_json()
        
        # Create NOAEL entry with required fields
        noael_entry = {
            "note": req.note,  # Optional
            "unit": req.unit,
            "experiment_target": req.experiment_target,  # Now required
            "source": req.source.lower().replace(" ", "_"),
            "type": "NOAEL",
            "study_duration": req.study_duration,  # Now required
            "value": req.value
        }
        
        # Create repeated_dose_toxicity entry
        repeated_dose_entry = {
            "reference": {
                "title": req.reference_title,
                "link": req.reference_link  # Can be None
            },
            "data": [
                f"NOAEL of {req.value} {req.unit} established in {req.experiment_target} "
                f"({req.study_duration} study) based on {req.source} assessment"
            ],
            "source": req.source.lower().replace(" ", "_"),
            "statement": req.statement or f"Based on {req.source} assessment",
            "replaced": {
                "replaced_inci": "",
                "replaced_type": ""
            }
        }
        
        # Update JSON
        current_json["inci"] = req.inci_name
        current_json["inci_ori"] = req.inci_name
        current_json["NOAEL"] = [noael_entry]  # Replace (not append)
        
        # Append to repeated_dose_toxicity (check for duplicates)
        if not _is_duplicate_entry(
            current_json.get("repeated_dose_toxicity", []),
            repeated_dose_entry
        ):
            current_json["repeated_dose_toxicity"].append(repeated_dose_entry)
        
        # Save to file
        write_json(current_json, str(JSON_TEMPLATE_PATH))
        
        return {
            "message": "✅ NOAEL updated successfully (form-based, no LLM)",
            "inci": req.inci_name,
            "updated_json": current_json
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update NOAEL: {str(e)}"
        )

@router.post("/edit-form/dap")
async def edit_dap_form(req: DAPFormRequest):
    """Form-based DAP update"""
    try:
        current_json = read_json()
        
        # DAP entry
        dap_entry = {
            "note": req.note,
            "unit": "%",
            "experiment_target": req.experiment_target,
            "source": req.source.lower().replace(" ", "_"),
            "type": "DAP",
            "study_duration": req.study_duration,
            "value": req.value
        }
        
        # Percutaneous absorption entry
        pa_entry = {
            "reference": {
                "title": req.reference_title,
                "link": req.reference_link
            },
            "data": [
                f"Dermal absorption estimated at {req.value}% in {req.experiment_target} "
                f"({req.study_duration} study) based on {req.source} assessment"
            ],
            "source": req.source.lower().replace(" ", "_"),
            "statement": req.statement or f"Based on {req.source} assessment",
            "replaced": {"replaced_inci": "", "replaced_type": ""}
        }
        
        # Update JSON
        current_json["inci"] = req.inci_name
        current_json["inci_ori"] = req.inci_name
        current_json["DAP"] = [dap_entry]
        
        if not _is_duplicate_entry(current_json.get("percutaneous_absorption", []), pa_entry):
            current_json["percutaneous_absorption"].append(pa_entry)
        
        write_json(current_json, str(JSON_TEMPLATE_PATH))
        
        return {
            "message": "✅ DAP updated successfully (form-based, no LLM)",
            "inci": req.inci_name,
            "updated_json": current_json
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update DAP: {str(e)}")

@router.get("/history/{conversation_id}", response_model=List[Dict[str, Any]])
async def get_history(conversation_id: str):
    """Retrieves ALL versions for a given conversation ID."""
    history = repo.get_conversation_versions(conversation_id)
    
    if not history:
        raise HTTPException(status_code=404, detail=f"No history found for conversation: {conversation_id}")
        
    return history

@router.get("/versions/{conversation_id}/{version}", response_model=Dict[str, Any])
async def get_specific_version(conversation_id: str, version: str):
    """Retrieves a single, specific version of the data."""
    data = repo.get_version(conversation_id, version)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Version '{version}' not found for conversation: {conversation_id}")
        
    return data

@router.get("/timeline/{conversation_id}", response_model=List[Dict[str, Any]])
async def get_timeline(conversation_id: str):
    """
    Retrieves summary information for all versions to build a timeline/list.
    This usually excludes the large 'data' and 'patch_operations' fields for speed.
    """
    # **Action Recommended:** Add a new query method in ToxicityRepository 
    # that SELECTs only summary columns (id, version, created_at, summary).
    # For now, we will use the full data and strip unnecessary fields.
    full_history = repo.get_conversation_versions(conversation_id)
    
    if not full_history:
        raise HTTPException(status_code=404, detail=f"No history found for conversation: {conversation_id}")
        
    timeline_summary = []
    for entry in full_history:
        # Create a light-weight summary object
        timeline_summary.append({
            "id": entry["id"],
            "version": entry["version"],
            "created_at": entry["created_at"],
            "modification_summary": entry["modification_summary"],
            "has_data": "data" in entry and bool(entry["data"]) # check for content existence
        })
        
    return timeline_summary

@router.get("/diff/{conversation_id}/{from_version}/{to_version}")
async def get_diff(conversation_id: str, from_version: str, to_version: str):
    """
    Calculates the difference (JSON Patch) between two versions.
    """
    # 1. Fetch both versions' data field
    v1_data = repo.get_version(conversation_id, from_version)
    v2_data = repo.get_version(conversation_id, to_version)

    if not v1_data or not v2_data:
        raise HTTPException(status_code=404, detail="One or both versions not found.")
    
    # 2. Get the core toxicity data (which is a dict)
    data1 = v1_data.get('data', {})
    data2 = v2_data.get('data', {})
    
    # 3. Calculate the diff
    diff = JsonPatch.from_diff(data1, data2)
    return {"diff": diff.patch}
    
    # Placeholder response since we cannot use an external library here:
    # return {
    #     "from_version": from_version,
    #     "to_version": to_version,
    #     "diff_note": "Logic requires an external library (e.g., jsonpatch) to compare the 'data' field content.",
    #     "data1_keys": list(data1.keys()),
    #     "data2_keys": list(data2.keys()),
    # }

@router.get("/current")
async def get_current_json():
    """Get the current JSON data"""
    return read_json()

@router.post("/reset")
async def reset_json():
    """Reset to template structure"""
    write_json(JSON_TEMPLATE, str(JSON_TEMPLATE_PATH))
    return {
        "message": "Reset to template successful",
        "data": JSON_TEMPLATE
    }

@router.post("/reset/{conversation_id}/{version}")
async def reset_version(conversation_id: str, version: str):
    """Reset JSON data for a given conversation_id to a specified version"""
    data = repo.get_version(conversation_id, version)

    if not data:
        raise HTTPException(status_code=404, detail="One or both versions not found.")
    
    json_data = data.get('data', {})
    message = f"Reset to version {version} for {conversation_id} successful"

    db.save_version(
        conversation_id=conversation_id,
        data=json_data,
        modification_summary=message
    )

    write_json(json_data, str(JSON_TEMPLATE_PATH))
    return {
        "message": message,
        "data": json_data
    }