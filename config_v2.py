"""
School Research Assistant - Configuration (v2)
==============================================
Replaces: config.py

WHAT THIS FILE DOES:
- Stores all settings in one place
- Lets you choose between Claude and OpenAI
- Handles API keys from environment or Streamlit secrets

HOW TO SWITCH LLMs:
- Set LLM_PROVIDER = "anthropic" for Claude
- Set LLM_PROVIDER = "openai" for GPT
"""

import os
from typing import Literal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# LLM CONFIGURATION - CHANGE THIS TO SWITCH BETWEEN CLAUDE AND OPENAI
# =============================================================================

# Options: "anthropic" (Claude) or "openai" (GPT)
LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"

# Model names
MODELS = {
    "anthropic": {
        "primary": "claude-sonnet-4-20250514",      # Main model for conversation starters
        "fast": "claude-sonnet-4-20250514",          # Faster model for simple tasks
    },
    "openai": {
        "primary": "gpt-4o-mini",                    # Main model
        "fast": "gpt-4o-mini",                       # Fast model
    }
}

def get_model(model_type: str = "primary") -> str:
    """Get the model name based on current provider"""
    return MODELS[LLM_PROVIDER][model_type]


# =============================================================================
# API KEYS - These are loaded from environment or Streamlit secrets
# =============================================================================

def get_api_keys() -> dict:
    """
    Get API keys from Streamlit secrets (cloud) or environment (local)
    """
    try:
        import streamlit as st
        return {
            "openai": st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
            "anthropic": st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")),
            "serper": st.secrets.get("SERPER_API_KEY", os.getenv("SERPER_API_KEY")),
            "firecrawl": st.secrets.get("FIRECRAWL_API_KEY", os.getenv("FIRECRAWL_API_KEY")),
        }
    except:
        return {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "serper": os.getenv("SERPER_API_KEY"),
            "firecrawl": os.getenv("FIRECRAWL_API_KEY"),
        }


# =============================================================================
# DATA SOURCE CONFIGURATION
# =============================================================================

# Options: "csv", "databricks"
DATA_SOURCE: Literal["csv", "databricks"] = "csv"

# Path to the CSV file (for POC)
CSV_FILE_PATH = "data/camden_schools_llm_ready.csv"

# Databricks configuration (for future)
DATABRICKS_CONFIG = {
    "host": os.getenv("DATABRICKS_HOST", ""),
    "token": os.getenv("DATABRICKS_TOKEN", ""),
    "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", ""),
    "catalog": "main",
    "schema": "schools",
    "table": "edco_schools"
}


# =============================================================================
# CACHING CONFIGURATION
# =============================================================================

# Enable/disable caching
ENABLE_CACHE = True

# How long to cache conversation starters (in hours)
CACHE_TTL_HOURS = 24

# Cache directory
CACHE_DIR = "cache"


# =============================================================================
# APP SETTINGS
# =============================================================================

# App password (for basic security)
APP_PASSWORD = os.getenv("APP_PASSWORD", "SEG2025AI!")

# Output directory for exports
OUTPUT_DIR = "outputs"

# Logging level
LOG_LEVEL = "INFO"


# =============================================================================
# FEATURE FLAGS - Turn features on/off
# =============================================================================

FEATURES = {
    "conversation_starters": True,      # Generate conversation starters with LLM
    "financial_analysis": True,         # Include financial data in analysis
    "ofsted_analysis": True,            # Include Ofsted data in analysis
    "live_web_search": False,           # For POC, this is OFF (data is pre-loaded)
    "export_to_excel": True,            # Allow Excel export
}


# =============================================================================
# PROMPT SETTINGS
# =============================================================================

# Maximum conversation starters to generate per school
MAX_CONVERSATION_STARTERS = 5

# Temperature for LLM (0 = deterministic, 1 = creative)
LLM_TEMPERATURE = 0.3

# Max tokens for response
LLM_MAX_TOKENS = 1500
