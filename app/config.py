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
# -----------------------------------------------------------------------------
# Provider selection
# -----------------------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")  
# Options: "local" | "openai" | "anthropic" | "gemini"

# -----------------------------------------------------------------------------
# Local model (Ollama)
# -----------------------------------------------------------------------------
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")
LOCAL_EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", "nomic-embed-text")

# -----------------------------------------------------------------------------
# OpenAI
# -----------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# -----------------------------------------------------------------------------
# Anthropic
# -----------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet")

# -----------------------------------------------------------------------------
# Google Gemini
# -----------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

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