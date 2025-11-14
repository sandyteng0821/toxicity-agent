from typing import Optional

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

from core.agent_graph_toxicity import build_graph, read_json, write_json

app = FastAPI(
    title="Cosmetic Ingredient Toxicology Editor API",
    description="API for managing toxicology data of cosmetic ingredients",
    version="1.0.0"
)
graph = build_graph()

class EditRequest(BaseModel):
    instruction: str
    inci_name: Optional[str] = None

# @app.post("/edit")
# async def edit_json(req: EditRequest):
#     current_json = read_json()

#     # Prepare user input with INCI context
#     user_input = req.instruction
#     if req.inci_name:
#         user_input = f"INCI: {req.inci_name}\n{user_input}"

#     result = graph.invoke({
#         "json_data": current_json,
#         "user_input": user_input,
#         "response": "",
#         "current_inci": req.inci_name or current_json.get('inci', 'INCI_NAME')
#     })

#     return {
#         "inci": result["current_inci"],
#         "updated_json": result["json_data"],
#         "raw_response": result["response"]
#     }

@app.post("/edit")
async def edit_json(req: EditRequest):
    current_json = read_json()

    # Prepare user input with INCI context
    user_input = req.instruction
    if req.inci_name:
        user_input = f"INCI: {req.inci_name}\n{user_input}"

    result = graph.invoke({
        "json_data": current_json,
        "user_input": user_input,
        "response": "",
        "current_inci": req.inci_name or current_json.get('inci', 'INCI_NAME')
    })

    # 确保保存到文件
    write_json(result["json_data"], "toxicity_data_template.json")

    return {
        "inci": result["current_inci"],
        "updated_json": result["json_data"],
        "raw_response": result["response"]
    }

@app.get("/current")
async def get_current_json():
    """Get the current JSON data"""
    return read_json()

@app.post("/reset")
async def reset_json():
    """Reset to template structure"""
    template = {
        "inci": "INCI_NAME",
        "cas": [],
        "isSkip": False,
        "category": "OTHERS",
        "acute_toxicity": [],
        "skin_irritation": [],
        "skin_sensitization": [],
        "ocular_irritation": [],
        "phototoxicity": [],
        "repeated_dose_toxicity": [],
        "percutaneous_absorption": [],
        "ingredient_profile": [],
        "NOAEL": [],
        "DAP": [],
        "inci_ori": "inci_name"
    }
    # from agent_graph import write_json
    # write_json(template, "editor.json")
    # write_json(template, "edited.json")
    write_json(template, "toxicity_data_template.json")
    return {"message": "Reset to template successful", "data": template}

@app.get("/graph")
async def get_graph_visualization():
    """Get the workflow graph visualization"""
    # from fastapi.responses import Response

    app_graph = build_graph()
    png_data = app_graph.get_graph().draw_mermaid_png()

    return Response(content=png_data, media_type="image/png")

@app.get("/")
def root():
    return {"message": "Cosmetic Ingredient Toxicology Editor API is running"}

if __name__ == "__main__":
    import uvicorn
    import socket

    # Try to get WSL/actual IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"

    print(f"\n📍 API available at: http://{local_ip}:8000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
