import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required env var '{key}' is not set. See .env.example.")
    return val

DATABASE_URL = _require("DATABASE_URL")
GROQ_API_KEY = _require("GROQ_API_KEY")
REDDIT_CLIENT_ID = _require("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _require("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = _require("REDDIT_USER_AGENT")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
CHRONOS_SERVICE_URL = os.environ.get("CHRONOS_SERVICE_URL", "http://localhost:8001")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TOP_N_FINALISTS = int(os.environ.get("TOP_N_FINALISTS", "30"))
BREAKOUT_THRESHOLD = float(os.environ.get("BREAKOUT_THRESHOLD", "0.5"))
