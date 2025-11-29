"""
School Research Assistant - Configuration (v2)
==============================================
UPDATED: Now points to london_schools_financial_CLEAN.csv

"""

import os
from typing import Literal

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Options: "anthropic" (Claude) or "openai" (GPT)
LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"

MODELS = {
    "anthropic": {
        "primary": "claude-sonnet-4-20250514",
        "fast": "claude-sonnet-4-20250514",
    },
    "openai": {
        "primary": "gpt-4o-mini",
        "fast": "gpt-4o-mini",
    }
}

def get_model(model_type: str = "primary") -> str:
    """Get the model name based on current provider"""
    return MODELS[LLM_PROVIDER][model_type]


def get_api_keys() -> dict:
    """Get API keys from Streamlit secrets (cloud) or environment (local)"""
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
        pass
    
    return keys


# =============================================================================
# DATA SOURCE CONFIGURATION
# =============================================================================

# Options: "csv", "databricks"
DATA_SOURCE: Literal["csv", "databricks"] = "csv"

# UPDATED: Path to the new financial data CSV
# This file contains ALL London schools with total spend values
CSV_FILE_PATH = "data/london_schools_financial_CLEAN.csv"

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
# CACHE CONFIGURATION
# =============================================================================

ENABLE_CACHE = True
CACHE_TTL_HOURS = 24
CACHE_DIR = "cache"


# =============================================================================
# APP CONFIGURATION
# =============================================================================

def get_app_password() -> str:
    """Get app password from secrets or environment"""
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            try:
                return st.secrets["APP_PASSWORD"]
            except (KeyError, FileNotFoundError):
                pass
    except Exception:
        pass
    
    return os.getenv("APP_PASSWORD", "SEG2025AI!")


APP_PASSWORD = "SEG2025AI!"

OUTPUT_DIR = "outputs"
LOG_LEVEL = "INFO"


# =============================================================================
# FEATURE FLAGS
# =============================================================================

FEATURES = {
    "conversation_starters": True,      
    "financial_analysis": True,        
    "ofsted_analysis": True,            
    "live_web_search": False,           
    "export_to_excel": True,            
}


# =============================================================================
# LLM SETTINGS
# =============================================================================

MAX_CONVERSATION_STARTERS = 5
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1500
