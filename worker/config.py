import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required env var '{key}' is not set. See .env.example.")
    return val

DATABASE_URL = _require("DATABASE_URL")

# LLM provider for the expansion step (long-tail + content gaps).
#   "ollama" (default) — local, unlimited, runs on CPU (qwen2.5:3b-instruct)
#   "groq"             — cloud llama-3.3-70b, smarter but rate-limited (free tier)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")  # only required if LLM_PROVIDER=groq
OLLAMA_EXPAND_MODEL = os.environ.get("OLLAMA_EXPAND_MODEL", "qwen2.5:3b-instruct")

GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
CHRONOS_SERVICE_URL = os.environ.get("CHRONOS_SERVICE_URL", "http://localhost:8001")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TOP_N_FINALISTS = int(os.environ.get("TOP_N_FINALISTS", "50"))
BREAKOUT_THRESHOLD = float(os.environ.get("BREAKOUT_THRESHOLD", "0.5"))
