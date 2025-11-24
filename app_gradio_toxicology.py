# app_gradio_toxicology.py
# Gradio UI for Toxicology Data Editor API
# Matches endpoints: /api/edit, /api/edit-form/*, /api/history/*, /api/versions/*, etc.

import gradio as gr
import requests
import json
from typing import Optional, Tuple, Any

# === Configuration ===
API_BASE_URL = "http://localhost:8000"


# === API Helper Functions ===

def api_request(method: str, endpoint: str, json_data: dict = None, params: dict = None) -> Tuple[bool, Any]:
    """Generic API request handler with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=json_data, timeout=30)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Error {response.status_code}: {response.text}"
    
    except requests.exceptions.ConnectionError:
        return False, "❌ Cannot connect to API server. Is it running?"
    except requests.exceptions.Timeout:
        return False, "❌ Request timed out"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# === API Endpoint Functions ===

# --- Edit Endpoints ---

def edit_toxicity_data(instruction: str, inci_name: str, conversation_id: str, initial_data: str):
    """POST /api/edit - Natural language edit"""
    
    # Parse initial_data JSON if provided
    parsed_initial_data = None
    if initial_data and initial_data.strip():
        try:
            parsed_initial_data = json.loads(initial_data)
        except json.JSONDecodeError as e:
            return f"❌ Invalid JSON in Initial Data: {str(e)}", None, "", "❌ JSON Parse Error"
    
    json_data = {
        "instruction": instruction,
        "inci_name": inci_name if inci_name else None,
        "conversation_id": conversation_id if conversation_id else None,
        "initial_data": parsed_initial_data
    }
    
    success, result = api_request("POST", "/api/edit", json_data=json_data)
    
    if success:
        return (
            result.get("raw_response", ""),
            result.get("updated_json", {}),
            result.get("conversation_id", ""),
            f"✅ Edit successful (v{result.get('current_version', '?')})"
        )
    else:
        return result, None, "", "❌ Edit failed"


def edit_noael_form(
    inci_name: str,
    value: float,
    unit: str,
    source: str,
    experiment_target: str,
    study_duration: str,
    reference_title: str,
    note: str,
    reference_link: str,
    statement: str,
    conversation_id: str
):
    """
    POST /api/edit-form/noael - Structured NOAEL edit
    
    Matches NOAELFormRequest:
    - inci_name: str (required)
    - value: float (required, positive)
    - unit: Literal["mg/kg bw/day", "mg/kg", "ppm", "mg/L"] (required)
    - source: str (required)
    - experiment_target: str (required)
    - study_duration: str (required)
    - reference_title: str (required)
    - note: Optional[str]
    - reference_link: Optional[str]
    - statement: Optional[str]
    - conversation_id: Optional[str]
    """
    # Validate required fields
    if not inci_name:
        return None, "", "❌ INCI Name is required"
    if not value:
        return None, "", "❌ NOAEL Value is required"
    if not source:
        return None, "", "❌ Source is required"
    if not experiment_target:
        return None, "", "❌ Experiment Target is required"
    if not study_duration:
        return None, "", "❌ Study Duration is required"
    if not reference_title:
        return None, "", "❌ Reference Title is required"
    
    try:
        value_float = float(value)
    except (ValueError, TypeError):
        return None, "", "❌ NOAEL Value must be a number"
    
    json_data = {
        "inci_name": inci_name,
        "value": value_float,
        "unit": unit,
        "source": source,
        "experiment_target": experiment_target,
        "study_duration": study_duration,
        "reference_title": reference_title,
        "note": note if note else None,
        "reference_link": reference_link if reference_link else None,
        "statement": statement if statement else None,
        "conversation_id": conversation_id if conversation_id else None
    }
    
    success, result = api_request("POST", "/api/edit-form/noael", json_data=json_data)
    
    if success:
        return (
            result.get("updated_json", {}),
            result.get("conversation_id", ""),
            f"✅ NOAEL added: {value} {unit} for {experiment_target} (v{result.get('current_version', '?')})"
        )
    else:
        return None, "", f"❌ Failed: {result}"


def edit_dap_form(
    inci_name: str,
    value: float,
    source: str,
    experiment_target: str,
    study_duration: str,
    reference_title: str,
    note: str,
    reference_link: str,
    statement: str,
    conversation_id: str
):
    """
    POST /api/edit-form/dap - Structured DAP edit
    
    Matches DAPFormRequest:
    - inci_name: str (required)
    - value: float (required, 0-100)
    - source: str (required)
    - experiment_target: str (required)
    - study_duration: str (required)
    - reference_title: str (required)
    - note: Optional[str]
    - reference_link: Optional[str]
    - statement: Optional[str]
    - conversation_id: Optional[str]
    """
    # Validate required fields
    if not inci_name:
        return None, "", "❌ INCI Name is required"
    if not value and value != 0:
        return None, "", "❌ DAP Value is required"
    if not source:
        return None, "", "❌ Source is required"
    if not experiment_target:
        return None, "", "❌ Experiment Target is required"
    if not study_duration:
        return None, "", "❌ Study Duration is required"
    if not reference_title:
        return None, "", "❌ Reference Title is required"
    
    try:
        value_float = float(value)
    except (ValueError, TypeError):
        return None, "", "❌ DAP Value must be a number"
    
    json_data = {
        "inci_name": inci_name,
        "value": value_float,
        "source": source,
        "experiment_target": experiment_target,
        "study_duration": study_duration,
        "reference_title": reference_title,
        "note": note if note else None,
        "reference_link": reference_link if reference_link else None,
        "statement": statement if statement else None,
        "conversation_id": conversation_id if conversation_id else None
    }
    
    success, result = api_request("POST", "/api/edit-form/dap", json_data=json_data)
    
    if success:
        return (
            result.get("updated_json", {}),
            result.get("conversation_id", ""),
            f"✅ DAP added: {value}% for {experiment_target} (v{result.get('current_version', '?')})"
        )
    else:
        return None, "", f"❌ Failed: {result}"


# --- History & Version Endpoints ---

def get_history(conversation_id: str):
    """GET /api/history/{conversation_id}"""
    if not conversation_id:
        return "Please enter a conversation ID", None
    
    success, result = api_request("GET", f"/api/history/{conversation_id}")
    
    if success:
        # Format history for display
        history_text = format_history(result)
        return history_text, result
    else:
        return result, None


def get_version(conversation_id: str, version: str):
    """GET /api/versions/{conversation_id}/{version}"""
    if not conversation_id or not version:
        return "Please enter both conversation ID and version", None
    
    success, result = api_request("GET", f"/api/versions/{conversation_id}/{version}")
    
    if success:
        return f"✅ Version {version} retrieved", result
    else:
        return result, None


def get_timeline(conversation_id: str):
    """GET /api/timeline/{conversation_id}"""
    if not conversation_id:
        return "Please enter a conversation ID", None
    
    success, result = api_request("GET", f"/api/timeline/{conversation_id}")
    
    if success:
        timeline_text = format_timeline(result)
        return timeline_text, result
    else:
        return result, None


def get_diff(conversation_id: str, from_version: str, to_version: str):
    """GET /api/diff/{conversation_id}/{from_version}/{to_version}"""
    if not conversation_id or not from_version or not to_version:
        return "Please enter conversation ID and both versions", None
    
    success, result = api_request(
        "GET", 
        f"/api/diff/{conversation_id}/{from_version}/{to_version}"
    )
    
    if success:
        diff_text = format_diff(result)
        return diff_text, result
    else:
        return result, None


# --- Current State & Reset Endpoints ---

def get_current():
    """GET /api/current - Get current session data"""
    success, result = api_request("GET", "/api/current")
    
    if success:
        return "✅ Current data retrieved", result
    else:
        return result, None


def reset_all():
    """POST /api/reset - Reset entire session"""
    success, result = api_request("POST", "/api/reset")
    
    if success:
        return "✅ Session reset successfully", result
    else:
        return result, None


def reset_to_version(conversation_id: str, version: str):
    """POST /api/reset/{conversation_id}/{version} - Reset to specific version"""
    if not conversation_id or not version:
        return "Please enter both conversation ID and version", None
    
    success, result = api_request("POST", f"/api/reset/{conversation_id}/{version}")
    
    if success:
        return f"✅ Reset to version {version}", result.get("data", {})
    else:
        return result, None


# --- Health & Status Endpoints ---

def check_health():
    """GET /health - Check API health"""
    success, result = api_request("GET", "/health")
    
    if success:
        return f"✅ API is healthy\n{json.dumps(result, indent=2)}"
    else:
        return result


def get_graph():
    """GET /graph - Get workflow graph as image"""
    try:
        response = requests.get(f"{API_BASE_URL}/graph", timeout=30)
        
        if response.status_code == 200:
            # Save image to temp file and return path
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                f.write(response.content)
                return f.name  # Return image path
        else:
            return None
    except Exception as e:
        return None


# === Formatting Helpers ===

def format_history(history_data) -> str:
    """Format history data for display"""
    if not history_data:
        return "No history found"
    
    if isinstance(history_data, list):
        lines = ["### Version History\n"]
        for item in history_data:
            version = item.get("version", "?")
            summary = item.get("modification_summary", "No summary")
            created = item.get("created_at", "Unknown time")
            lines.append(f"**v{version}** ({created})")
            lines.append(f"  - {summary}\n")
        return "\n".join(lines)
    
    return json.dumps(history_data, indent=2)


def format_timeline(timeline_data) -> str:
    """Format timeline data for display"""
    if not timeline_data:
        return "No timeline found"
    
    if isinstance(timeline_data, list):
        lines = ["### Timeline\n"]
        for i, item in enumerate(timeline_data):
            version = item.get("version", i + 1)
            summary = item.get("modification_summary", "Change")
            created = item.get("created_at", "")
            lines.append(f"📍 **v{version}**: {summary}")
            if created:
                lines.append(f"   _{created}_\n")
        return "\n".join(lines)
    
    return json.dumps(timeline_data, indent=2)


def format_diff(diff_data) -> str:
    """Format diff data for display"""
    if not diff_data:
        return "No differences found"
    
    if isinstance(diff_data, dict):
        lines = ["### Differences\n"]
        
        if "changes" in diff_data:
            for change in diff_data["changes"]:
                change_type = change.get("type", "unknown")
                path = change.get("path", "")
                old_val = change.get("old", "")
                new_val = change.get("new", "")
                
                if change_type == "add":
                    lines.append(f"➕ **Added** `{path}`: {new_val}")
                elif change_type == "remove":
                    lines.append(f"➖ **Removed** `{path}`: {old_val}")
                elif change_type == "change":
                    lines.append(f"✏️ **Changed** `{path}`: {old_val} → {new_val}")
        else:
            return json.dumps(diff_data, indent=2)
        
        return "\n".join(lines)
    
    return json.dumps(diff_data, indent=2)


# === Build Gradio UI ===

def create_ui():
    with gr.Blocks(
        title="Toxicology Data Editor",
        theme=gr.themes.Soft(),
        css="""
        .status-success { color: green; }
        .status-error { color: red; }
        .required-field label::after { content: " *"; color: red; }
        """
    ) as demo:
        
        gr.Markdown("# 🧪 Toxicology Data Editor")
        gr.Markdown("Natural language & form-based interface for editing toxicology JSON data")
        
        # Shared state for conversation ID
        shared_conv_id = gr.State(value="")
        
        # ===== TAB 1: Natural Language Editor =====
        with gr.Tab("💬 Natural Language Edit"):
            gr.Markdown("### Edit using natural language instructions")
            
            with gr.Row():
                with gr.Column(scale=1):
                    nl_instruction = gr.Textbox(
                        label="Instruction",
                        placeholder="e.g., Set NOAEL to 200 mg/kg bw/day for Rats",
                        lines=3
                    )
                    nl_inci_name = gr.Textbox(
                        label="INCI Name (optional)",
                        placeholder="e.g., L-MENTHOL"
                    )
                    nl_conv_id = gr.Textbox(
                        label="Conversation ID (optional)",
                        placeholder="Leave empty for new conversation"
                    )
                    nl_initial_data = gr.Textbox(
                        label="Initial Data JSON (optional)",
                        placeholder='Paste existing JSON data here, e.g., {"inci": "L-MENTHOL", "cas": [], ...}',
                        lines=6
                    )
                    
                    with gr.Row():
                        nl_submit_btn = gr.Button("✏️ Submit Edit", variant="primary")
                        nl_clear_btn = gr.Button("🔄 Clear", variant="secondary")
                
                with gr.Column(scale=1):
                    nl_response = gr.Textbox(label="AI Response", lines=4)
                    nl_json_output = gr.JSON(label="Updated JSON")
                    nl_conv_id_output = gr.Textbox(label="Conversation ID", interactive=False)
                    nl_status = gr.Textbox(label="Status", interactive=False)
            
            # Examples
            gr.Markdown("### Quick Examples")
            gr.Examples(
                examples=[
                    ["Set NOAEL to 200 mg/kg bw/day for Rats", "L-MENTHOL", "", ""],
                    ["Add acute toxicity: Oral LD50 500 mg/kg for mice", "CAFFEINE", "", ""],
                    ["Update skin irritation score to non-irritating", "", "", ""],
                    ["Add phototoxicity data: negative in 3T3 NRU assay", "", "", ""],
                ],
                inputs=[nl_instruction, nl_inci_name, nl_conv_id, nl_initial_data]
            )
            
            # Event handlers
            nl_submit_btn.click(
                fn=edit_toxicity_data,
                inputs=[nl_instruction, nl_inci_name, nl_conv_id, nl_initial_data],
                outputs=[nl_response, nl_json_output, nl_conv_id_output, nl_status]
            )
            
            nl_clear_btn.click(
                fn=lambda: ("", "", "", "", "", None, "", ""),
                outputs=[nl_instruction, nl_inci_name, nl_conv_id, nl_initial_data, nl_response, 
                        nl_json_output, nl_conv_id_output, nl_status]
            )
        
        # ===== TAB 2: Form-Based NOAEL Editor =====
        with gr.Tab("📋 NOAEL Form"):
            gr.Markdown("### Add NOAEL data using structured form")
            gr.Markdown("Fields marked with **\\*** are required")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### Required Fields")
                    noael_inci_name = gr.Textbox(
                        label="INCI Name *",
                        placeholder="e.g., L-MENTHOL"
                    )
                    noael_value = gr.Number(
                        label="NOAEL Value *",
                        value=None,
                        minimum=0.001,
                        info="Must be a positive number"
                    )
                    noael_unit = gr.Dropdown(
                        label="Unit *",
                        choices=["mg/kg bw/day", "mg/kg", "ppm", "mg/L"],
                        value="mg/kg bw/day"
                    )
                    noael_source = gr.Textbox(
                        label="Source *",
                        placeholder="e.g., oecd, fda, echa"
                    )
                    noael_experiment_target = gr.Dropdown(
                        label="Experiment Target *",
                        choices=["Rats", "Mice", "Rabbits", "Dogs", "Guinea pigs", "Humans", "Other"],
                        value="Rats",
                        allow_custom_value=True
                    )
                    noael_study_duration = gr.Dropdown(
                        label="Study Duration *",
                        choices=["28-day", "90-day", "chronic", "2-year", "subchronic", "Other"],
                        value="90-day",
                        allow_custom_value=True
                    )
                    noael_reference_title = gr.Textbox(
                        label="Reference Title *",
                        placeholder="e.g., OECD SIDS MENTHOLS UNEP PUBLICATIONS"
                    )
                    
                    gr.Markdown("#### Optional Fields")
                    noael_note = gr.Textbox(
                        label="Note",
                        placeholder="e.g., Based on oral gavage study"
                    )
                    noael_reference_link = gr.Textbox(
                        label="Reference Link",
                        placeholder="https://..."
                    )
                    noael_statement = gr.Textbox(
                        label="Statement",
                        placeholder="e.g., Based on repeated dose toxicity studies"
                    )
                    noael_conv_id = gr.Textbox(
                        label="Conversation ID",
                        placeholder="Leave empty for new (auto-generated)"
                    )
                    
                    noael_submit_btn = gr.Button("➕ Add NOAEL", variant="primary")
                
                with gr.Column(scale=1):
                    noael_json_output = gr.JSON(label="Updated JSON")
                    noael_conv_id_output = gr.Textbox(label="Conversation ID", interactive=False)
                    noael_status = gr.Textbox(label="Status", interactive=False)
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Example Request")
                    gr.Code(
                        value=json.dumps({
                            "inci_name": "L-MENTHOL",
                            "value": 200,
                            "unit": "mg/kg bw/day",
                            "source": "oecd",
                            "experiment_target": "Rats",
                            "study_duration": "90-day",
                            "note": "Based on oral gavage study",
                            "reference_title": "OECD SIDS MENTHOLS",
                            "reference_link": "https://hpvchemicals.oecd.org/...",
                            "statement": "Based on repeated dose toxicity studies"
                        }, indent=2),
                        language="json",
                        interactive=False
                    )
            
            noael_submit_btn.click(
                fn=edit_noael_form,
                inputs=[
                    noael_inci_name, noael_value, noael_unit, noael_source,
                    noael_experiment_target, noael_study_duration, noael_reference_title,
                    noael_note, noael_reference_link, noael_statement, noael_conv_id
                ],
                outputs=[noael_json_output, noael_conv_id_output, noael_status]
            )
        
        # ===== TAB 3: Form-Based DAP Editor =====
        with gr.Tab("📋 DAP Form"):
            gr.Markdown("### Add DAP (Dermal Absorption Percentage) data")
            gr.Markdown("Fields marked with **\\*** are required")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### Required Fields")
                    dap_inci_name = gr.Textbox(
                        label="INCI Name *",
                        placeholder="e.g., L-MENTHOL"
                    )
                    dap_value = gr.Number(
                        label="DAP Value (%) *",
                        value=None,
                        minimum=0,
                        maximum=100,
                        info="Percentage value between 0-100"
                    )
                    dap_source = gr.Textbox(
                        label="Source *",
                        placeholder="e.g., in_vitro, in_vivo, sccs"
                    )
                    dap_experiment_target = gr.Dropdown(
                        label="Experiment Target *",
                        choices=["Human skin", "Rat skin", "Pig skin", "In vitro model", "Other"],
                        value="Human skin",
                        allow_custom_value=True
                    )
                    dap_study_duration = gr.Dropdown(
                        label="Study Duration *",
                        choices=["24-hour", "48-hour", "72-hour", "Single application", "Other"],
                        value="24-hour",
                        allow_custom_value=True
                    )
                    dap_reference_title = gr.Textbox(
                        label="Reference Title *",
                        placeholder="e.g., SCCS Notes of Guidance"
                    )
                    
                    gr.Markdown("#### Optional Fields")
                    dap_note = gr.Textbox(
                        label="Note",
                        placeholder="e.g., Based on Franz cell diffusion study"
                    )
                    dap_reference_link = gr.Textbox(
                        label="Reference Link",
                        placeholder="https://..."
                    )
                    dap_statement = gr.Textbox(
                        label="Statement",
                        placeholder="e.g., Based on in vitro percutaneous absorption study"
                    )
                    dap_conv_id = gr.Textbox(
                        label="Conversation ID",
                        placeholder="Leave empty for new (auto-generated)"
                    )
                    
                    dap_submit_btn = gr.Button("➕ Add DAP", variant="primary")
                
                with gr.Column(scale=1):
                    dap_json_output = gr.JSON(label="Updated JSON")
                    dap_conv_id_output = gr.Textbox(label="Conversation ID", interactive=False)
                    dap_status = gr.Textbox(label="Status", interactive=False)
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Example Request")
                    gr.Code(
                        value=json.dumps({
                            "inci_name": "L-MENTHOL",
                            "value": 40,
                            "source": "in_vitro",
                            "experiment_target": "Human skin",
                            "study_duration": "24-hour",
                            "note": "Franz cell diffusion study",
                            "reference_title": "SCCS Notes of Guidance",
                            "reference_link": "https://...",
                            "statement": "Based on in vitro study"
                        }, indent=2),
                        language="json",
                        interactive=False
                    )
            
            dap_submit_btn.click(
                fn=edit_dap_form,
                inputs=[
                    dap_inci_name, dap_value, dap_source,
                    dap_experiment_target, dap_study_duration, dap_reference_title,
                    dap_note, dap_reference_link, dap_statement, dap_conv_id
                ],
                outputs=[dap_json_output, dap_conv_id_output, dap_status]
            )
        
        # ===== TAB 4: Version History =====
        with gr.Tab("📜 History & Versions"):
            gr.Markdown("### View modification history and versions")
            
            with gr.Row():
                with gr.Column(scale=1):
                    hist_conv_id = gr.Textbox(
                        label="Conversation ID",
                        placeholder="Enter conversation ID"
                    )
                    
                    with gr.Row():
                        hist_btn = gr.Button("📜 Get History", variant="primary")
                        timeline_btn = gr.Button("📍 Get Timeline", variant="secondary")
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Get Specific Version")
                    
                    version_num = gr.Number(
                        label="Version Number",
                        value=1,
                        precision=0
                    )
                    version_btn = gr.Button("📋 Get Version", variant="secondary")
                
                with gr.Column(scale=1):
                    hist_text_output = gr.Markdown(label="History")
                    hist_json_output = gr.JSON(label="Raw Data")
            
            hist_btn.click(
                fn=get_history,
                inputs=[hist_conv_id],
                outputs=[hist_text_output, hist_json_output]
            )
            
            timeline_btn.click(
                fn=get_timeline,
                inputs=[hist_conv_id],
                outputs=[hist_text_output, hist_json_output]
            )
            
            version_btn.click(
                fn=lambda cid, v: get_version(cid, str(int(v))),
                inputs=[hist_conv_id, version_num],
                outputs=[hist_text_output, hist_json_output]
            )
        
        # ===== TAB 5: Diff Viewer =====
        with gr.Tab("🔍 Compare Versions"):
            gr.Markdown("### Compare differences between versions")
            
            with gr.Row():
                with gr.Column(scale=1):
                    diff_conv_id = gr.Textbox(
                        label="Conversation ID",
                        placeholder="Enter conversation ID"
                    )
                    
                    with gr.Row():
                        diff_from_version = gr.Number(
                            label="From Version",
                            value=1,
                            precision=0
                        )
                        diff_to_version = gr.Number(
                            label="To Version",
                            value=2,
                            precision=0
                        )
                    
                    diff_btn = gr.Button("🔍 Compare", variant="primary")
                
                with gr.Column(scale=1):
                    diff_text_output = gr.Markdown(label="Differences")
                    diff_json_output = gr.JSON(label="Raw Diff Data")
            
            diff_btn.click(
                fn=lambda cid, fv, tv: get_diff(cid, str(int(fv)), str(int(tv))),
                inputs=[diff_conv_id, diff_from_version, diff_to_version],
                outputs=[diff_text_output, diff_json_output]
            )
        
        # ===== TAB 6: Current State & Reset =====
        with gr.Tab("⚙️ Session Management"):
            gr.Markdown("### Manage current session and reset options")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### Current Session")
                    current_btn = gr.Button("📄 Get Current Data", variant="primary")
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Reset Options")
                    
                    reset_all_btn = gr.Button("🔄 Reset Entire Session", variant="stop")
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Reset to Specific Version")
                    
                    reset_conv_id = gr.Textbox(
                        label="Conversation ID",
                        placeholder="Enter conversation ID"
                    )
                    reset_version = gr.Number(
                        label="Version to Reset To",
                        value=1,
                        precision=0
                    )
                    reset_version_btn = gr.Button("⏮️ Reset to Version", variant="secondary")
                
                with gr.Column(scale=1):
                    session_status = gr.Textbox(label="Status", lines=2)
                    session_json_output = gr.JSON(label="Data")
            
            current_btn.click(
                fn=get_current,
                inputs=[],
                outputs=[session_status, session_json_output]
            )
            
            reset_all_btn.click(
                fn=reset_all,
                inputs=[],
                outputs=[session_status, session_json_output]
            )
            
            reset_version_btn.click(
                fn=lambda cid, v: reset_to_version(cid, str(int(v))),
                inputs=[reset_conv_id, reset_version],
                outputs=[session_status, session_json_output]
            )
        
        # ===== TAB 7: API Health & Info =====
        with gr.Tab("🔧 System"):
            gr.Markdown("### API Status and Configuration")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### Health Check")
                    health_btn = gr.Button("❤️ Check API Health", variant="primary")
                    health_output = gr.Textbox(label="Health Status", lines=5)
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Workflow Graph")
                    graph_btn = gr.Button("📊 Get Graph", variant="secondary")
                    graph_output = gr.Image(label="Workflow Graph")
                
                with gr.Column(scale=1):
                    gr.Markdown("#### API Configuration")
                    gr.Textbox(
                        label="API Base URL",
                        value=API_BASE_URL,
                        interactive=False
                    )
                    
                    gr.Markdown("""
                    #### Available Endpoints
                    
                    **Edit Operations:**
                    - `POST /api/edit` - Natural language edit
                    - `POST /api/edit-form/noael` - Add NOAEL data
                    - `POST /api/edit-form/dap` - Add DAP data
                    
                    **History & Versions:**
                    - `GET /api/history/{id}` - Get history
                    - `GET /api/versions/{id}/{v}` - Get version
                    - `GET /api/timeline/{id}` - Get timeline
                    - `GET /api/diff/{id}/{v1}/{v2}` - Compare versions
                    
                    **Session:**
                    - `GET /api/current` - Get current data
                    - `POST /api/reset` - Reset session
                    - `POST /api/reset/{id}/{v}` - Reset to version
                    
                    **System:**
                    - `GET /health` - Health check
                    - `GET /graph` - Workflow graph
                    """)
            
            health_btn.click(
                fn=check_health,
                inputs=[],
                outputs=[health_output]
            )
            
            graph_btn.click(
                fn=get_graph,
                inputs=[],
                outputs=[graph_output]
            )
        
        # ===== Footer =====
        gr.Markdown("---")
        gr.Markdown(
            "💡 **Tip:** Start with Natural Language Edit, then use History tab to view changes. "
            "Use Session Management to reset if needed."
        )
    
    return demo


# === Main Entry Point ===

if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Set to True to create public link
    )
