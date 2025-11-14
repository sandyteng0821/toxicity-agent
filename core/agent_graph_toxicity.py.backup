import json
from typing import Dict, Any, TypedDict, List, Optional
import os
import re

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from IPython.display import Image, display

load_dotenv()

class JSONEditState(TypedDict):
    json_data: Dict[str, Any]
    user_input: str
    response: str
    current_inci: str

class ToxicologyData(TypedDict):
    data: List[str]
    reference: Dict[str, Optional[str]]
    replaced: Dict[str, str]
    source: str
    statement: Optional[str]

def read_json(filepath="toxicity_data_template.json"):
    """Read JSON file with error handling"""
    try:
        if not os.path.exists(filepath):
            # Create template structure if file doesn't exist
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
            write_json(template, filepath)
            return template

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {filepath}: {e}")
        return {"error": f"Failed to read JSON: {str(e)}"}

def write_json(data, filepath="edited.json"):
    """Write JSON file with error handling"""
    try:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON successfully saved to {filepath}")
    except IOError as e:
        print(f"Error writing {filepath}: {e}")

def extract_toxicology_sections(text: str) -> Dict[str, List[ToxicologyData]]:
    """Extract toxicology data from the instruction text"""
    sections = {}

    # Pattern to match toxicology sections like "acute_toxicity", "skin_irritation", etc.
    patterns = {
        'acute_toxicity': r'"acute_toxicity":\s*\[(.*?)\]',
        'skin_irritation': r'"skin_irritation":\s*\[(.*?)\]',
        'skin_sensitization': r'"skin_sensitization":\s*\[(.*?)\]',
        'ocular_irritation': r'"ocular_irritation":\s*\[(.*?)\]',
        'phototoxicity': r'"phototoxicity":\s*\[(.*?)\]',
        'repeated_dose_toxicity': r'"repeated_dose_toxicity":\s*\[(.*?)\]',
        'percutaneous_absorption': r'"percutaneous_absorption":\s*\[(.*?)\]',
        'ingredient_profile': r'"ingredient_profile":\s*\[(.*?)\]',
        'NOAEL': r'"NOAEL":\s*\[(.*?)\]',
        'DAP': r'"DAP":\s*\[(.*?)\]'
    }

    for section, pattern in patterns.items():
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            try:
                # Try to parse the JSON array
                json_str = f"[{matches[0]}]"
                data = json.loads(json_str)
                sections[section] = data
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {section} data as JSON")
                continue

    return sections

def update_toxicology_data(current_data: List[Dict], new_data: List[Dict]) -> List[Dict]:
    """Update toxicology data by adding new entries or merging with existing ones"""
    updated_data = current_data.copy()

    for new_entry in new_data:
        # Check if similar entry already exists (based on source and reference title)
        existing_index = -1
        for i, existing_entry in enumerate(updated_data):
            if (existing_entry.get('source') == new_entry.get('source') and
                existing_entry.get('reference', {}).get('title') == new_entry.get('reference', {}).get('title')):
                existing_index = i
                break

        if existing_index >= 0:
            # Update existing entry
            updated_data[existing_index].update(new_entry)
        else:
            # Add new entry
            updated_data.append(new_entry)

    return updated_data

def llm_edit_node(state: JSONEditState):
    """Process user input and update JSON using LLM with toxicology-specific logic"""
    llm = ChatOllama(model="llama3.1:8b")
    json_str = json.dumps(state["json_data"], indent=2, ensure_ascii=False)

    # Extract INCI name from instruction
    inci_match = re.search(r'inci_name\s*=\s*["\']?([^"\'\n]+)["\']?', state["user_input"])
    current_inci = inci_match.group(1) if inci_match else state["json_data"].get("inci", "INCI_NAME")
    state["current_inci"] = current_inci

    # Try to extract structured toxicology data first
    toxicology_sections = extract_toxicology_sections(state["user_input"])

    if toxicology_sections:
        updated_json = state["json_data"].copy()
        for section, data in toxicology_sections.items():
            if section in updated_json:
                updated_json[section] = update_toxicology_data(updated_json[section], data)

        state["json_data"] = updated_json
        state["response"] = f"Successfully updated toxicology data for {current_inci}"
        return state

    # Enhanced prompt - ask for ONLY updated fields
    prompt = f"""You are a toxicology data specialist for cosmetic ingredients. Update JSON for INCI: {current_inci}

Current JSON Structure:
{json_str}

User Instruction:
{state['user_input']}

COMMON MODIFICATION TYPES:

TYPE 1 - Toxicology Data Addition (毒理資料差補):
- Add complete entry to toxicology array (acute_toxicity, skin_irritation, etc.)
- Required fields: reference, data, source, statement, replaced
- Action: Return ONLY the new entry to append

TYPE 2 - DAP Update:
- Update "DAP" array with new value
- Update "percutaneous_absorption" array with supporting data
- Return: {{"DAP": [...], "percutaneous_absorption": [...]}}

TYPE 3 - NOAEL Update:
- Update "NOAEL" array with new value
- Update "repeated_dose_toxicity" array with supporting data
- Return: {{"NOAEL": [...], "repeated_dose_toxicity": [...]}}

CRITICAL RULES:
1. Return ONLY the fields that need to be updated
2. Do NOT use [...] or "..." placeholders - provide actual complete data
3. Do NOT return the entire JSON - only changed fields
4. Field names must be lowercase ("inci", not "INCI")
5. Return valid JSON only, no explanations

EXAMPLES:

Example 1 (TYPE 3 - NOAEL Update):
Input: "Set NOAEL to 800 mg/kg bw/day from ECHA, add repeated dose toxicity study"
Output:
{{
  "inci": "PETROLATUM",
  "NOAEL": [
    {{
      "note": null,
      "unit": "mg/kg bw/day",
      "experiment_target": "Rats",
      "source": "echa",
      "type": "NOAEL",
      "study_duration": "90-day",
      "value": 800
    }}
  ],
  "repeated_dose_toxicity": [
    {{
      "reference": {{
        "title": "ECHA Registration Dossier",
        "link": "https://echa.europa.eu"
      }},
      "data": ["90-day oral toxicity study in rats showed NOAEL of 800 mg/kg bw/day"],
      "source": "echa",
      "statement": "Based on repeated dose toxicity studies",
      "replaced": {{
        "replaced_inci": "",
        "replaced_type": ""
      }}
    }}
  ]
}}

Example 2 (TYPE 2 - DAP Update):
Input: "Set DAP to 10% based on expert judgment"
Output:
{{
  "inci": "INGREDIENT_NAME",
  "DAP": [
    {{
      "note": "Expert assessment",
      "unit": "%",
      "experiment_target": null,
      "source": "expert",
      "type": "DAP",
      "study_duration": null,
      "value": 10
    }}
  ],
  "percutaneous_absorption": [
    {{
      "reference": {{
        "title": "Expert Assessment",
        "link": null
      }},
      "data": ["Dermal absorption estimated at 10% based on molecular properties"],
      "source": "expert",
      "statement": "Conservative estimate for safety assessment",
      "replaced": {{
        "replaced_inci": "",
        "replaced_type": ""
      }}
    }}
  ]
}}

Now analyze the instruction and return ONLY the fields to update with COMPLETE data (no [...] placeholders):
"""

    result = llm.invoke(prompt)
    state["response"] = result.content

    try:
        # Clean the response
        clean_content = result.content.strip()

        # Remove any leading text before JSON
        json_start = -1
        for i, char in enumerate(clean_content):
            if char in ['{', '[']:
                json_start = i
                break
        
        if json_start > 0:
            clean_content = clean_content[json_start:]

        # Remove markdown
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        elif clean_content.startswith("```"):
            clean_content = clean_content[3:]
            
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
        clean_content = clean_content.strip()

        # Remove trailing text
        json_end = -1
        for i in range(len(clean_content) - 1, -1, -1):
            if clean_content[i] in ['}', ']']:
                json_end = i + 1
                break
        
        if json_end > 0:
            clean_content = clean_content[:json_end]

        print(f"DEBUG: Cleaned JSON (first 500 chars):\n{clean_content[:500]}")

        # Parse the updates
        updates = json.loads(clean_content)
        
        # Merge with existing JSON
        merged_json = state["json_data"].copy()

        # Fix common LLM errors
        if "INCI" in updates and "inci" not in updates:
            print("⚠️ Fixing: INCI → inci")
            updates["inci"] = updates.pop("INCI")
        
        if "toxicology" in updates:
            print("⚠️ Fixing: unnesting toxicology")
            toxicology = updates.pop("toxicology")
            updates.update(toxicology)

        # Apply updates
        for key, value in updates.items():
            if key == "inci":
                merged_json["inci"] = value
                merged_json["inci_ori"] = value
                print(f"✅ Updated inci: {value}")
            elif key in merged_json:
                if isinstance(value, list) and value:
                    # Check for [...] placeholder
                    if len(value) == 1 and value[0] == "...":
                        print(f"⚠️ Skipping placeholder for {key}")
                        continue
                    
                    # Toxicology arrays: append
                    toxicology_keys = [
                        "acute_toxicity", "skin_irritation", "skin_sensitization",
                        "ocular_irritation", "phototoxicity", "repeated_dose_toxicity",
                        "percutaneous_absorption", "ingredient_profile"
                    ]
                    if key in toxicology_keys:
                        merged_json[key] = update_toxicology_data(merged_json[key], value)
                        print(f"✅ Appended to {key}: {len(value)} entries")
                    else:
                        # NOAEL, DAP: replace
                        merged_json[key] = value
                        print(f"✅ Replaced {key}: {len(value)} entries")
                else:
                    merged_json[key] = value
                    print(f"✅ Updated {key}")
            else:
                merged_json[key] = value
                print(f"✅ Added new field: {key}")

        state["json_data"] = merged_json
        state["response"] = f"Successfully updated {list(updates.keys())} for {current_inci}"
        print(f"DEBUG: Final JSON has {len(merged_json)} fields")

    except json.JSONDecodeError as e:
        error_msg = f"⚠️ LLM output was not valid JSON: {str(e)}\nCleaned content: {clean_content[:500]}\nOriginal LLM output: {result.content[:500]}"
        state["response"] = error_msg
        print(error_msg)

    return state

# def llm_edit_node(state: JSONEditState):
#     """Process user input and update JSON using LLM with toxicology-specific logic"""
#     # llm = ChatOllama(model="llama3.2")
#     llm = ChatOllama(model="llama3.1:8b") # preferred local model  
#     # llm = ChatOllama(model="qwen2.5:14b") # too slow & incorrect
#     # llm = ChatOllama(model="gpt-oss:20b") # too slow
#     # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # It works. # need to have API key in .env
#     json_str = json.dumps(state["json_data"], indent=2, ensure_ascii=False)

#     # Extract INCI name from instruction if present
#     inci_match = re.search(r'inci_name\s*=\s*["\']?([^"\'\n]+)["\']?', state["user_input"])
#     current_inci = inci_match.group(1) if inci_match else state["json_data"].get("inci", "INCI_NAME")
#     state["current_inci"] = current_inci

#     # Try to extract structured toxicology data first
#     toxicology_sections = extract_toxicology_sections(state["user_input"])

#     if toxicology_sections:
#         # If we found structured data, update the JSON directly
#         updated_json = state["json_data"].copy()
#         for section, data in toxicology_sections.items():
#             if section in updated_json:
#                 updated_json[section] = update_toxicology_data(updated_json[section], data)

#         state["json_data"] = updated_json
#         state["response"] = f"Successfully updated toxicology data for {current_inci}"
#         # write_json(updated_json) # deprecated
#         return state

#     # If no structured data found, use LLM for natural language processing
#     prompt = f"""
# You are a toxicology data specialist for cosmetic ingredients. Your task is to update JSON data for INCI: {current_inci}

# Current JSON Structure:
# {json_str}

# User Instruction:
# {state['user_input']}

# CRITICAL RULES - YOU MUST FOLLOW EXACTLY:
# 1. Keep the EXACT same JSON structure - DO NOT add nested objects or change field names
# 2. The top-level field MUST be "inci" (lowercase), NOT "INCI"
# 3. Arrays like "acute_toxicity", "NOAEL", "DAP" MUST be at the top level, NOT nested under "toxicology"
# 4. Only UPDATE the specific fields mentioned in the instruction
# 5. Keep ALL other existing data unchanged
# 6. Return ONLY valid JSON, no explanations, no markdown code blocks

# Example of CORRECT structure:
# {{
#   "inci": "INGREDIENT_NAME",
#   "cas": [],
#   "acute_toxicity": [...],
#   "NOAEL": [...],
#   "DAP": [...]
# }}

# Example of WRONG structure (DO NOT DO THIS):
# {{
#   "INCI": "...",           // ❌ Wrong: uppercase
#   "toxicology": {{         // ❌ Wrong: nested
#     "NOAEL": [...]
#   }}
# }}

# Now update the JSON:
# """

#     result = llm.invoke(prompt)
#     state["response"] = result.content

#     try:
#         # Clean the response
#         clean_content = result.content.strip()

#         # 移除任何前導文字说明（如 "Here is the updated JSON:"）
#         # 查找第一个 { 或 [ 的位置
#         json_start = -1
#         for i, char in enumerate(clean_content):
#             if char in ['{', '[']:
#                 json_start = i
#                 break
        
#         if json_start > 0:
#             clean_content = clean_content[json_start:]

#         # Remove markdown
#         if clean_content.startswith("```json"):
#             clean_content = clean_content[7:]
#         if clean_content.endswith("```"):
#             clean_content = clean_content[:-3]
#         clean_content = clean_content.strip()

#         # 移除任何结尾的文字说明
#         # 查找最后一个 } 或 ] 的位置
#         json_end = -1
#         for i in range(len(clean_content) - 1, -1, -1):
#             if clean_content[i] in ['}', ']']:
#                 json_end = i + 1
#                 break
        
#         if json_end > 0:
#             clean_content = clean_content[:json_end]

#         print(f"DEBUG: Cleaned JSON (first 200 chars): {clean_content[:200]}")

#         new_json = json.loads(clean_content)
#         # state["json_data"] = new_json # deprecated 
        
#         # merge the existing and the generated JSON files
#         merged_json = state["json_data"].copy()

#         # fix common llm error
#         if "INCI" in new_json and "inci" not in new_json:
#             print("⚠️ Fixing: INCI → inci")
#             new_json["inci"] = new_json.pop("INCI")
        
#         if "toxicology" in new_json:
#             print("⚠️ Fixing: unnesting toxicology")
#             toxicology = new_json.pop("toxicology")
#             new_json.update(toxicology)

#         # update JSON (merged_json)
#         for key, value in new_json.items():
#             if key in merged_json:
#                 if isinstance(value, list) and value:  # update when existing data is available
#                     merged_json[key] = value
#                 else:
#                     merged_json[key] = value
#             else:
#                 merged_json[key] = value

#         state["json_data"] = merged_json
#         state["response"] = f"Successfully updated data for {current_inci}"
#         print(f"DEBUG: Merged JSON has {len(merged_json)} fields")
#         # write_json(new_json) # deprecated # 移除這裡的 write_json，讓 API 端點统一保存

#     except json.JSONDecodeError as e:
#         error_msg = f"⚠️ LLM output was not valid JSON: {str(e)}\nCleaned content: {clean_content[:500]}\nOriginal LLM output: {result.content[:500]}"
#         state["response"] = error_msg
#         print(error_msg)

#     return state

def should_continue(state: JSONEditState) -> str:
    """Determine if we should continue or end"""
    return "end"

def build_graph():
    graph = StateGraph(JSONEditState)
    graph.add_node("edit", llm_edit_node)
    graph.set_entry_point("edit")

    graph.add_conditional_edges(
        "edit",
        should_continue,
        {
            "end": END
        }
    )

    return graph.compile()

def view_plot(save_path="graph_plot.png", display_image=True):
    """
    View and/or save the graph visualization

    Args:
        save_path: Path to save the PNG file (default: "graph_plot.png")
        display_image: Whether to display the image inline (default: True)

    Returns:
        bytes: The PNG image data
    """
    app = build_graph()
    png_data = app.get_graph().draw_mermaid_png()

    # Save to file
    with open(save_path, "wb") as f:
        f.write(png_data)
    print(f"✅ Graph saved to: {save_path}")

    # Display if requested (for Jupyter notebooks)
    if display_image:
        try:
            from IPython.display import Image, display
            display(Image(png_data))
        except ImportError:
            print("⚠️ IPython not available. Image saved but not displayed.")
            print(f"   Open {save_path} to view the graph.")

    return png_data

# Interactive function for testing
def run_toxicology_editor():
    """Interactive function to run the toxicology editor"""
    app = build_graph()

    initial_data = read_json("editor.json")

    print("=== Cosmetic Ingredient Toxicology Editor ===")
    print(f"Current INCI: {initial_data.get('inci', 'INCI_NAME')}")
    print(f"Current JSON: {json.dumps(initial_data, indent=2, ensure_ascii=False)}")

    while True:
        user_input = input("\nEnter toxicology data or modification (or 'quit' to exit): ").strip()

        if user_input.lower() in ['quit', 'exit', 'q']:
            break

        if not user_input:
            continue

        initial_state = JSONEditState(
            json_data=initial_data,
            user_input=user_input,
            response="",
            current_inci=initial_data.get('inci', 'INCI_NAME')
        )

        result = app.invoke(initial_state)

        print(f"\nResponse: {result['response']}")
        print(f"Updated INCI: {result['current_inci']}")
        print(f"Updated JSON: {json.dumps(result['json_data'], indent=2, ensure_ascii=False)}")

        initial_data = result['json_data']

if __name__ == "__main__":
    run_toxicology_editor()
