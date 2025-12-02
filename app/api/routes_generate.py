"""
API routes for toxicology form conversion
"""
import uuid
import json
from typing import Optional, Literal, List, Dict, Any
from fastapi import APIRouter, HTTPException, FastAPI, Form, UploadFile, File
from pydantic import BaseModel, Field

from app.graph.utils.toxicity_schemas import NOAELUpdateSchema, DAPUpdateSchema
from app.graph.utils.toxicity_utils import (
    _generate_noael_with_llm,
    _generate_dap_with_llm,
    build_noael_payload,
    build_dap_payload,
)
from app.graph.utils.llm_factory import get_structured_llm

router = APIRouter(prefix="/api", tags=["generate"])

# Request/Response Models

class CorrectionFormRequest(BaseModel):
    """Request model for correction form text input"""
    correction_form_text: str = Field(..., description="毒理修正單原文")
    conversation_id: Optional[str] = Field(None, description="Conversation ID (optional)")

class GeneratedPayloadResponse(BaseModel):
    """Response model for generated payload"""
    task_type: str
    inci_name: str
    payload: dict
    json_string: str
    api_endpoint: str


# Endpoints for toxicity form to DAP/NOAEL request conversion

@router.post("/generate/noael", response_model=GeneratedPayloadResponse)
async def generate_noael_payload(req: CorrectionFormRequest):
    """
    Generate NOAEL JSON payload from correction form text (毒理修正單).
    
    This endpoint uses LLM to extract NOAEL data and returns a ready-to-use payload.
    You can then POST the payload to /api/edit-form/noael to update the database.
    
    Example:
        POST /api/generate/noael
        {
            "correction_form_text": "INCI: BUTYL METHOXYDIBENZOYLMETHANE\\nRepeated Dose Toxicity\\n建議的 NOAEL 值為:450.0 mg/kg bw/day..."
        }
    
    Returns:
        Generated NOAEL payload ready for /api/edit-form/noael
    """
    try:
        # Get structured LLM
        structured_llm = get_structured_llm(NOAELUpdateSchema)
        
        # Generate NOAEL data using LLM
        noael_data = _generate_noael_with_llm(
            llm=structured_llm,
            correction_form_text=req.correction_form_text,
        )
        
        # Build payload
        conversation_id = req.conversation_id or str(uuid.uuid4())
        payload = build_noael_payload(noael_data, conversation_id)
        
        return GeneratedPayloadResponse(
            task_type="noael",
            inci_name=noael_data.inci_name,
            payload=payload,
            json_string=json.dumps(payload, ensure_ascii=False, indent=2),
            api_endpoint="/api/edit-form/noael",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate NOAEL payload: {str(e)}"
        )


@router.post("/generate/dap", response_model=GeneratedPayloadResponse)
async def generate_dap_payload(req: CorrectionFormRequest):
    """
    Generate DAP JSON payload from correction form text (毒理修正單).
    
    This endpoint uses LLM to extract DAP data and returns a ready-to-use payload.
    You can then POST the payload to /api/edit-form/dap to update the database.
    
    Example:
        POST /api/generate/dap
        {
            "correction_form_text": "INCI：AMP-ACRYLATES/DIACETONEACRYLAMIDE COPOLYMER\\nPercutaneous Absorption\\n建議的經皮吸收率為: 1.0 %..."
        }
    
    Returns:
        Generated DAP payload ready for /api/edit-form/dap
    """
    try:
        # Get structured LLM
        structured_llm = get_structured_llm(DAPUpdateSchema)
        
        # Generate DAP data using LLM
        dap_data = _generate_dap_with_llm(
            llm=structured_llm,
            correction_form_text=req.correction_form_text,
        )
        
        # Build payload
        conversation_id = req.conversation_id or str(uuid.uuid4())
        payload = build_dap_payload(dap_data, conversation_id)
        
        return GeneratedPayloadResponse(
            task_type="dap",
            inci_name=dap_data.inci_name,
            payload=payload,
            json_string=json.dumps(payload, ensure_ascii=False, indent=2),
            api_endpoint="/api/edit-form/dap",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate DAP payload: {str(e)}"
        )

@router.post("/generate/noael/form", response_model=GeneratedPayloadResponse)
async def generate_noael_payload_form(
    correction_form_text: str = Form(..., description="毒理修正單原文"),
    conversation_id: Optional[str] = Form(None, description="Conversation ID"),
):
    """
    Generate NOAEL JSON payload from correction form text (Form-based, multiline friendly).
    
    Use this endpoint when pasting multiline text directly.
    """
    try:
        structured_llm = get_structured_llm(NOAELUpdateSchema)
        noael_data = _generate_noael_with_llm(
            llm=structured_llm,
            correction_form_text=correction_form_text,
        )
        conv_id = conversation_id or str(uuid.uuid4())
        payload = build_noael_payload(noael_data, conv_id)
        
        return GeneratedPayloadResponse(
            task_type="noael",
            inci_name=noael_data.inci_name,
            payload=payload,
            json_string=json.dumps(payload, ensure_ascii=False, indent=2),
            api_endpoint="/api/edit-form/noael",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate NOAEL payload: {str(e)}")


@router.post("/generate/dap/form", response_model=GeneratedPayloadResponse)
async def generate_dap_payload_form(
    correction_form_text: str = Form(..., description="毒理修正單原文"),
    conversation_id: Optional[str] = Form(None, description="Conversation ID"),
):
    """
    Generate DAP JSON payload from correction form text (Form-based, multiline friendly).
    
    Use this endpoint when pasting multiline text directly.
    """
    try:
        structured_llm = get_structured_llm(DAPUpdateSchema)
        dap_data = _generate_dap_with_llm(
            llm=structured_llm,
            correction_form_text=correction_form_text,
        )
        conv_id = conversation_id or str(uuid.uuid4())
        payload = build_dap_payload(dap_data, conv_id)
        
        return GeneratedPayloadResponse(
            task_type="dap",
            inci_name=dap_data.inci_name,
            payload=payload,
            json_string=json.dumps(payload, ensure_ascii=False, indent=2),
            api_endpoint="/api/edit-form/dap",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DAP payload: {str(e)}")
    
@router.post("/generate/noael/upload", response_model=GeneratedPayloadResponse)
async def generate_noael_from_file(
    file: UploadFile = File(..., description="毒理修正單文字檔 (.txt)"),
    conversation_id: Optional[str] = None,
):
    """
    Generate NOAEL JSON payload from uploaded text file.
    
    Upload a .txt file containing the correction form text.
    """
    try:
        content = await file.read()
        correction_form_text = content.decode("utf-8")
        
        structured_llm = get_structured_llm(NOAELUpdateSchema)
        noael_data = _generate_noael_with_llm(
            llm=structured_llm,
            correction_form_text=correction_form_text,
        )
        
        conv_id = conversation_id or str(uuid.uuid4())
        payload = build_noael_payload(noael_data, conv_id)
        
        return GeneratedPayloadResponse(
            task_type="noael",
            inci_name=noael_data.inci_name,
            payload=payload,
            json_string=json.dumps(payload, ensure_ascii=False, indent=2),
            api_endpoint="/api/edit-form/noael",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate NOAEL: {str(e)}")


@router.post("/generate/dap/upload", response_model=GeneratedPayloadResponse)
async def generate_dap_from_file(
    file: UploadFile = File(..., description="毒理修正單文字檔 (.txt)"),
    conversation_id: Optional[str] = None,
):
    """
    Generate DAP JSON payload from uploaded text file.
    
    Upload a .txt file containing the correction form text.
    """
    try:
        content = await file.read()
        correction_form_text = content.decode("utf-8")
        
        structured_llm = get_structured_llm(DAPUpdateSchema)
        dap_data = _generate_dap_with_llm(
            llm=structured_llm,
            correction_form_text=correction_form_text,
        )
        
        conv_id = conversation_id or str(uuid.uuid4())
        payload = build_dap_payload(dap_data, conv_id)
        
        return GeneratedPayloadResponse(
            task_type="dap",
            inci_name=dap_data.inci_name,
            payload=payload,
            json_string=json.dumps(payload, ensure_ascii=False, indent=2),
            api_endpoint="/api/edit-form/dap",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DAP: {str(e)}")