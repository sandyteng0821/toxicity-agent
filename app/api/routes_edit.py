"""
API routes for toxicology editing
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.graph.build_graph import build_graph
from app.services.json_io import read_json, write_json
from app.config import JSON_TEMPLATE, JSON_TEMPLATE_PATH

router = APIRouter(prefix="/api", tags=["edit"])
graph = build_graph()

class EditRequest(BaseModel):
    """Request model for edit endpoint"""
    instruction: str
    inci_name: Optional[str] = None

class EditResponse(BaseModel):
    """Response model for edit endpoint"""
    inci: str
    updated_json: dict
    raw_response: str

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
        current_json = read_json()
        
        # Prepare user input
        user_input = req.instruction
        if req.inci_name:
            user_input = f"INCI: {req.inci_name}\n{user_input}"
        
        # Run graph
        result = graph.invoke({
            "json_data": current_json,
            "user_input": user_input,
            "response": "",
            "current_inci": req.inci_name or current_json.get('inci', 'INCI_NAME'),
            "edit_history": None,
            "error": None
        })
        
        # Save result
        write_json(result["json_data"], str(JSON_TEMPLATE_PATH))
        
        return EditResponse(
            inci=result["current_inci"],
            updated_json=result["json_data"],
            raw_response=result["response"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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