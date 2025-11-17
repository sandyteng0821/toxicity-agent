"""
LangGraph workflow construction
"""
import aiosqlite
import sqlite3
from contextlib import contextmanager
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.graph.state import JSONEditState
from app.graph.nodes.llm_edit_node import llm_edit_node
from core.database import ToxicityDB

# Global connection (reused across requests)
_db_connection = None

def get_db_connection():
    """Get or create global DB connection"""
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect(
            "chat_memory.db", 
            check_same_thread=False,
            timeout=30
        )
    return _db_connection

def build_graph():
    """
    Build and compile the toxicology editing workflow with chat history
    
    Returns:
        Compiled LangGraph application with SqliteSaver checkpointer
    """
    graph = StateGraph(JSONEditState)
    
    # Add nodes
    graph.add_node("edit", llm_edit_node)
    
    # Set entry point
    graph.set_entry_point("edit")
    
    # Add edges
    graph.add_conditional_edges(
        "edit",
        _should_continue,
        {
            "end": END
        }
    )

    # Create connection and pass to SqliteSaver
    conn = get_db_connection() # Use global connection for checkpointer
    checkpointer = SqliteSaver(conn=conn)

    return graph.compile(checkpointer=checkpointer)

def _should_continue(state: JSONEditState) -> str:
    """
    Determine if workflow should continue
    
    Args:
        state: Current state
        
    Returns:
        "end" to finish workflow
    """
    return "end"

def view_graph(save_path: str = "graph_plot.png", display_image: bool = True):
    """
    Visualize the workflow graph
    
    Args:
        save_path: Path to save PNG
        display_image: Whether to display inline (Jupyter)
        
    Returns:
        PNG image data
    """
    app = build_graph()
    png_data = app.get_graph().draw_mermaid_png()
    
    with open(save_path, "wb") as f:
        f.write(png_data)
    print(f"✅ Graph saved to: {save_path}")
    
    if display_image:
        try:
            from IPython.display import Image, display
            display(Image(png_data))
        except ImportError:
            print(f"⚠️ IPython not available. Open {save_path} to view graph.")
    
    return png_data