"""Configuration lue depuis l'environnement (voir .env.example)."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://grc:change-me@localhost:5432/grc")
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "corpus_grc")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")   # ollama | anthropic | openai | google_genai
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:7b")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))


settings = Settings()
