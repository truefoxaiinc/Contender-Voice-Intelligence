import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
TEST_CALLS_DIR = DATA_DIR / "test_calls"
VECTOR_DB_DIR = BASE_DIR / "vector_db"

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Model Configuration
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-4o-mini")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "openai/text-embedding-3-small")
TEMPERATURE = 0.0  # Low temperature for deterministic output
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "base.en")
WHISPER_CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "4"))
PRELOAD_WHISPER = os.getenv("PRELOAD_WHISPER", "true").lower() in {"1", "true", "yes"}

# Ensure required directories exist
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
TEST_CALLS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
