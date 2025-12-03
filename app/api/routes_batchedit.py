# app/api/routes_batchedit.py
"""
API routes for batch editing
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.graph.build_graph import build_graph
from app.services.data_updater import update_toxicology_data
from app.services.json_io import read_json
from core.database import ToxicityDB

router = APIRouter(prefix="/api", tags=["batchedit"])
db = ToxicityDB()
graph = build_graph()

class BatchEditRequest(BaseModel):
    """Request model for batchedit endpoint"""
    conversation_id: Optional[str] = None
    edits: List[Dict[str, Any]]  
    """
    edits = [
        {
            "inci_name": "L-MENTHOL",
            "instruction": "update NOAEL to 200 mg/kg",
        },
        {
            "inci_name": "GLYCERIN",
            "instruction": "add acute toxicity oral LD50 500",
        }
    ]
    """

class BatchEditResponse(BaseModel):
    """Response model for batchedit endpoint"""
    batch_id: str # ⬅️ 新增：方便查詢
    patch_success_data: List[bool] # patch status (this flag will be set to True if a valid patch is generated)
    fallback_used_data: List[bool] # node status tracker (if fallback node is called)
    updated_data: List[Dict]
    data_count: int
    inci_thread_map: Dict[str, str] # ⬅️ 新增：INCI → thread_id 對照
    # raw_response: str
    # conversation_id: str
    # current_version: Optional[int] = None


@router.post("/edit/batch", response_model=BatchEditResponse)
async def batch_edit(request: BatchEditRequest):
    json_results, fall_back_states, patch_success_states = [], [], []
    
    batch_id = request.conversation_id or str(uuid.uuid4())
    inci_thread_map: Dict[str, str] = {} # track each INCI (use same thread for the same INCI)
    inci_json_cache: Dict[str, Dict] = {} # track json_data for each INCI

    for item in request.edits:
        inci_name = item.get("inci_name", None)
        instruction = item.get("instruction", "")
        
        if inci_name in inci_thread_map: # same inci => same thread id
            item_id = inci_thread_map[inci_name]
            current_json = inci_json_cache[inci_name]
        else:
            item_id = str(uuid.uuid4())
            inci_thread_map[inci_name] = item_id
            current_json = read_json() # load template for the first time
        
        config = {"configurable": {"thread_id": item_id}} # ISOLATED THREAD
        
        # Run graph # Call the existing LangGraph workflow (== /edit)
        output_state = graph.invoke(
            {
                "user_input": instruction, 
                "current_inci": inci_name,
                "json_data": current_json,
                # "messages": [],
                "conversation_id": item_id
            },
            config=config
        )

        # Collect updated toxicity data
        json_data = output_state.get("json_data")
        fallback_used = output_state.get("fallback_used")
        patch_success = output_state.get("patch_success")
        patch_ops = output_state.get("patch_operations") # pass the actual patch ops from your graph output

        # Update cache (same INCI => edit using cache data for the same INCI)
        inci_json_cache[inci_name] = json_data

        # DB Call to save batch item
        db.save_batch_item(
            batch_id=batch_id,
            item_id=item_id,
            inci_name=inci_name,
            data=json_data,
            instruction=instruction,
            patch_operations=patch_ops,
            patch_success=patch_success,
            fallback_used=fallback_used
        )
        
        json_results.append(json_data)
        fall_back_states.append(fallback_used or False)
        patch_success_states.append(patch_success or False)

    return BatchEditResponse(
        batch_id=batch_id, 
        patch_success_data=patch_success_states,
        fallback_used_data=fall_back_states,
        updated_data=json_results,
        data_count=len(json_results),
        inci_thread_map=inci_thread_map
    )

# endpoint to query batch update 
@router.get("/edit/batch/{batch_id}")
async def get_batch_results(batch_id: str):
    """Get all results for a batch by batch_id (or thread_id)"""
    results = db.get_batch_items(batch_id) # try to query via batch_id first 

    if not results:
        results = db.get_modification_history_with_patches(batch_id) # try to query via item_id (thread_id) # fallback approach 

    if not results:
        raise HTTPException(status_code=404, detail=f"No data found for batch: {batch_id}")
    
    return results

# endpoint to query inci update 
@router.get("/edit/inci/{inci_name}")
async def get_inci_history(inci_name: str):
    """Get all modification history for a specific INCI name"""
    results = db.get_by_inci_name(inci_name.upper())
    
    if not results:
        raise HTTPException(status_code=404, detail=f"No data found for INCI: {inci_name}")
    
    return results