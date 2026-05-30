import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = os.environ["REDDIT_USER_AGENT"]
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
CHRONOS_SERVICE_URL = os.environ.get("CHRONOS_SERVICE_URL", "http://localhost:8001")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TOP_N_FINALISTS = int(os.environ.get("TOP_N_FINALISTS", "30"))
BREAKOUT_THRESHOLD = float(os.environ.get("BREAKOUT_THRESHOLD", "0.5"))
