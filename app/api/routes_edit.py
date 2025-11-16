"""
API routes for toxicology editing
"""
import uuid
import json
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from app.graph.build_graph import build_graph
from app.services.json_io import read_json, write_json
from app.config import JSON_TEMPLATE, JSON_TEMPLATE_PATH
from app.api.helper import _is_duplicate_entry
from core.database import ToxicityDB

router = APIRouter(prefix="/api", tags=["edit"])

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