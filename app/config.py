"""
Global configuration for the toxicity agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# File paths
JSON_TEMPLATE_PATH = DATA_DIR / "toxicity_data_template.json"
EDITOR_JSON_PATH = DATA_DIR / "editor.json"

# LLM configuration
DEFAULT_LLM_MODEL = "llama3.1:8b"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Toxicology field names
TOXICOLOGY_FIELDS = [
    "acute_toxicity",
    "skin_irritation",
    "skin_sensitization",
    "ocular_irritation",
    "phototoxicity",
    "repeated_dose_toxicity",
    "percutaneous_absorption",
    "ingredient_profile"
]

METRIC_FIELDS = ["NOAEL", "DAP"]

# Template structure
JSON_TEMPLATE = {
    "inci": "INCI_NAME",
    "cas": [],
    "isSkip": False,
    "category": "OTHERS",
    **{field: [] for field in TOXICOLOGY_FIELDS},
    **{field: [] for field in METRIC_FIELDS},
    "inci_ori": "inci_name"
}