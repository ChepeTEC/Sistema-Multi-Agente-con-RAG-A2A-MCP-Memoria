from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AI Agents RAG System")

    BASE_DIR: Path = Path(__file__).resolve().parents[2]

    NOTES_DIR: Path = BASE_DIR / os.getenv("NOTES_DIR", "data/notes")
    PROCESSED_DIR: Path = BASE_DIR / os.getenv("PROCESSED_DIR", "data/processed")
    VECTOR_DB_DIR: Path = BASE_DIR / os.getenv("VECTOR_DB_DIR", "vector_store/chroma")

    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "course_notes")
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    RAG_LLM_MODEL: str = os.getenv(
        "RAG_LLM_MODEL",
        "gemini-2.5-flash"
    )
    ORCHESTRATOR_LLM_MODEL: str = os.getenv(
        "ORCHESTRATOR_LLM_MODEL",
        "gemini-2.5-pro"
    )
    WEB_SEARCH_LLM_MODEL: str = os.getenv(
        "WEB_SEARCH_LLM_MODEL",
        "gemini-2.5-flash"
    )


settings = Settings()
