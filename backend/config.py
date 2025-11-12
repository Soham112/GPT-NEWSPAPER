"""
Configuration for models, API settings, and cost control.
"""
import os

# Model Configuration
DISCOVERY_MODEL = "llama-3.1-8b-instant"  # For discovery/curation
SUMMARY_MODEL = "llama-3.1-8b-instant"  # For summarization
PREMIUM_MODEL = "llama-3.3-70b-versatile"  # For premium runs (optional)

# Generation Settings
MAX_TOKENS = 700  # For summarization
MAX_TOKENS_CURATION = 500  # For curation
TEMPERATURE = 0.2

# Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Rate Limiting
THREAD_POOL_SIZE = 3
LLM_CALL_DELAY_SECONDS = (0.8, 1.5)  # Random sleep between Groq calls

# Retrieval Settings
TAVILY_DEFAULT_TIME_RANGE = "week"
TAVILY_FALLBACK_TIME_RANGE = "month"
MIN_SOURCES_REQUIRED = 3
MAX_SOURCES_TO_CURATE = 5

# Domain Filters (per vertical - can be extended)
DOMAIN_FILTERS = {
    "energy": ["utilitydive.com", "environmentenergyleader.com", "solarpowerworldonline.com"],
    "tech": ["techcrunch.com", "theverge.com", "arstechnica.com"],
    # Add more as needed
}

# Cost Control
ENABLE_COST_TRACKING = True
MAX_COST_PER_REQUEST = 0.50  # $0.50 hard limit per request

# Caching
ENABLE_CACHE = True
CACHE_TTL_HOURS = 24

# Critic Loop (disabled by default)
ENABLE_CRITIC_LOOP = False
CRITIC_MIN_SOURCES = 4  # Only enable if sources >= this

