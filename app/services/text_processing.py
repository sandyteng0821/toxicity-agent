"""
Text processing utilities for toxicology data extraction
"""
import re
import json
from typing import Dict, List

def extract_inci_name(text: str) -> str:
    """
    Extract INCI name from instruction text
    
    Args:
        text: User instruction containing INCI name
        
    Returns:
        Extracted INCI name or empty string
    """
    inci_match = re.search(r'inci_name\s*=\s*["\']?([^"\'\n]+)["\']?', text)
    if inci_match:
        return inci_match.group(1)
    
    # Try alternative pattern
    inci_match = re.search(r'INCI:\s*([^\n]+)', text)
    if inci_match:
        return inci_match.group(1).strip()
    
    return ""

def extract_toxicology_sections(text: str) -> Dict[str, List[Dict]]:
    """
    Extract structured toxicology data from instruction text
    
    Args:
        text: Instruction text potentially containing JSON sections
        
    Returns:
        Dict mapping section names to data arrays
    """
    sections = {}

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
                json_str = f"[{matches[0]}]"
                data = json.loads(json_str)
                sections[section] = data
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse {section} as JSON")
                continue

    return sections

def clean_llm_json_output(content: str) -> str:
    """
    Clean LLM output to extract valid JSON
    
    Args:
        content: Raw LLM output
        
    Returns:
        Cleaned JSON string
    """
    clean_content = content.strip()

    # Remove leading text before JSON
    json_start = -1
    for i, char in enumerate(clean_content):
        if char in ['{', '[']:
            json_start = i
            break
    
    if json_start > 0:
        clean_content = clean_content[json_start:]

    # Remove markdown code blocks
    if clean_content.startswith("```json"):
        clean_content = clean_content[7:]
    elif clean_content.startswith("```"):
        clean_content = clean_content[3:]
        
    if clean_content.endswith("```"):
        clean_content = clean_content[:-3]
    
    clean_content = clean_content.strip()

    # Remove trailing text after JSON
    json_end = -1
    for i in range(len(clean_content) - 1, -1, -1):
        if clean_content[i] in ['}', ']']:
            json_end = i + 1
            break
    
    if json_end > 0:
        clean_content = clean_content[:json_end]

    return clean_content