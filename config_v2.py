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

IMPORTANT: API keys are loaded LAZILY (only when needed)
to avoid Streamlit Cloud import issues.
"""

import os
from typing import Literal

# Try to load dotenv, but don't fail if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
# API KEYS - LAZY LOADING (only fetched when needed, not at import time)
# =============================================================================

def get_api_keys() -> dict:
    """
    Get API keys from Streamlit secrets (cloud) or environment (local)
    
    IMPORTANT: This function is called LAZILY, not at import time.
    This prevents crashes on Streamlit Cloud during the import phase.
    """
    keys = {
        "openai": None,
        "anthropic": None,
        "serper": None,
        "firecrawl": None,
    }
    
    # First, try environment variables
    keys["openai"] = os.getenv("OPENAI_API_KEY")
    keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
    keys["serper"] = os.getenv("SERPER_API_KEY")
    keys["firecrawl"] = os.getenv("FIRECRAWL_API_KEY")
    
    # Then, try Streamlit secrets (only if running in Streamlit)
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            # Use dictionary-style access with fallback
            try:
                keys["openai"] = st.secrets["OPENAI_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
            try:
                keys["anthropic"] = st.secrets["ANTHROPIC_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
            try:
                keys["serper"] = st.secrets["SERPER_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
            try:
                keys["firecrawl"] = st.secrets["FIRECRAWL_API_KEY"]
            except (KeyError, FileNotFoundError):
                pass
    except Exception:
        # If anything goes wrong with Streamlit, just use env vars
        pass
    
    return keys


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

def get_app_password() -> str:
    """Get app password from secrets or environment"""
    # Try Streamlit secrets first
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            try:
                return st.secrets["APP_PASSWORD"]
            except (KeyError, FileNotFoundError):
                pass
    except Exception:
        pass
    
    # Fall back to environment variable or default
    return os.getenv("APP_PASSWORD", "SEG2025AI!")


# For backward compatibility
APP_PASSWORD = "SEG2025AI!"  # Default value, get_app_password() should be used

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
