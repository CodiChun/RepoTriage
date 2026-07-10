import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "owner/repo_name")

LLM_PROVIDER = os.getenv("LLM_PROVIDER") or (
    "openai" if os.getenv("OPENAI_API_KEY") else "anthropic"
)
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "gpt-4o-mini" if LLM_PROVIDER == "openai" else "claude-sonnet-4-20250514",
)

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'repotriage.db'}")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.85"))
