"""
School Research Assistant - Configuration (v2)
==============================================
Replaces: config.py

"""

import os
from typing import Literal

# Try to load dotenv, but don't fail if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Options: "anthropic" (Claude) or "openai" (GPT)
LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"


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




def get_api_keys() -> dict:
    """
    Get API keys from Streamlit secrets (cloud) or environment (local)
    
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
    
    # Then, try Streamlit secrets
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



# Enable/disable caching
ENABLE_CACHE = True

# How long to cache conversation starters (in hours)
CACHE_TTL_HOURS = 24

# Cache directory
CACHE_DIR = "cache"


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


APP_PASSWORD = "SEG2025AI!"  

# Output directory for exports
OUTPUT_DIR = "outputs"

# Logging level
LOG_LEVEL = "INFO"


FEATURES = {
    "conversation_starters": True,      
    "financial_analysis": True,        
    "ofsted_analysis": True,            
    "live_web_search": False,           
    "export_to_excel": True,            
}


MAX_CONVERSATION_STARTERS = 5

# Temperature for LLM (0 = deterministic, 1 = creative)
LLM_TEMPERATURE = 0.3

# Max tokens for response
LLM_MAX_TOKENS = 1500
