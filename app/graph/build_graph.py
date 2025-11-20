"""
LangGraph workflow construction
"""
import aiosqlite
import sqlite3
from contextlib import contextmanager
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.graph.state import JSONEditState
# from app.graph.nodes.llm_edit_node import llm_edit_node
# from app.graph.nodes.llm_edit_node_with_patch import llm_edit_node_with_patch
# from app.graph.nodes.edit_orchestrator import llm_edit_node_with_patch
from app.graph.nodes.load_json import load_json_node
from app.graph.nodes.parse_instruction import parse_instruction_node
from app.graph.nodes.fast_update import fast_update_node
from app.graph.nodes.patch_generate import patch_generate_node
from app.graph.nodes.patch_apply import patch_apply_node
from app.graph.nodes.fallback_full import fallback_full_node
from app.graph.nodes.save_json import save_json_node

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

def build_graph(use_test_db=False):
    """
    Build and compile the toxicology editing workflow with chat history
    
    Returns:
        Compiled LangGraph application with SqliteSaver checkpointer
    """
    graph = StateGraph(JSONEditState)
    
    # Add nodes
    graph.add_node("LOAD_JSON", load_json_node)
    graph.add_node("PARSE_INSTRUCTION", parse_instruction_node)
    graph.add_node("FAST_UPDATE", fast_update_node)
    graph.add_node("PATCH_GEN", patch_generate_node)
    graph.add_node("PATCH_APPLY", patch_apply_node)
    graph.add_node("FALLBACK", fallback_full_node)
    graph.add_node("SAVE", save_json_node)

    # graph.add_node("edit", llm_edit_node)
    # graph.add_node("edit", llm_edit_node_with_patch) # deprecated
    
    # Set entry point
    graph.set_entry_point("LOAD_JSON")
    # graph.set_entry_point("edit") # deprecated

    # transitions
    graph.add_edge("LOAD_JSON", "PARSE_INSTRUCTION")
    graph.add_edge("PARSE_INSTRUCTION", "FAST_UPDATE")
    
    # If fast-path updated anything → skip LLM
    graph.add_conditional_edges(
        "FAST_UPDATE",
        lambda s: "PATCH_GEN" if not s.get("fast_done") else "SAVE",
        {
            "PATCH_GEN": "PATCH_GEN",
            "SAVE": "SAVE"
        }
    )

    graph.add_edge("PATCH_GEN", "PATCH_APPLY")


    graph.add_edge("PATCH_GEN", "PATCH_APPLY")

    graph.add_conditional_edges(
        "PATCH_APPLY",
        lambda s: "SAVE" if s["patch_success"] else "FALLBACK",
        {
            "SAVE": "SAVE",
            "FALLBACK": "FALLBACK",
        }
    )

    graph.add_edge("FALLBACK", "SAVE")

    # # Add edges
    # graph.add_conditional_edges(
    #     "edit",
    #     _should_continue,
    #     {
    #         "end": END
    #     }
    # )

    # Use different database for tests
    if use_test_db:
        # Option 1: In-memory (doesn't persist, can't get corrupted)
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        checkpointer = SqliteSaver(conn=conn)
    else:
        # Option 2: Production database # Create connection and pass to SqliteSaver
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