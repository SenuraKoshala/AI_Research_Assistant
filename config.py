import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# Search
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Agent limits
MAX_PAPERS = 10
MAX_LLM_CALLS_PER_SESSION = 50
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Paths
SESSIONS_DIR = "sessions"
REPORTS_DIR = "reports"
CHROMA_DIR = "chroma_db"