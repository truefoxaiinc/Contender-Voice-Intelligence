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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Configuration
LLM_MODEL_NAME = "gpt-4o-mini"  # Or your chosen commercial/local model
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
TEMPERATURE = 0.0  # Low temperature for deterministic output

# Ensure required directories exist
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
TEST_CALLS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)