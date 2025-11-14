"""
FastAPI application entrypoint
"""
import socket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.routes_edit import router as edit_router
from app.graph.build_graph import build_graph

app = FastAPI(
    title="Cosmetic Ingredient Toxicology Editor API",
    description="API for managing toxicology data of cosmetic ingredients",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(edit_router)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Cosmetic Ingredient Toxicology Editor API is running",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "toxicity-agent"
    }

@app.get("/graph")
async def get_graph_visualization():
    """Get workflow graph visualization"""
    app_graph = build_graph()
    png_data = app_graph.get_graph().draw_mermaid_png()
    return Response(content=png_data, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    from app.config import API_HOST, API_PORT
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    
    print(f"\n📍 API available at: http://{local_ip}:{API_PORT}/docs\n")
    uvicorn.run(app, host=API_HOST, port=API_PORT)