"""Configuration and environment variable management."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # API Keys
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")

    # Pinecone
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "bug-hunter")

    # Upload
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Supported file types
    CODE_EXTENSIONS: set = {".py", ".js", ".ts"}
    IMAGE_EXTENSIONS: set = {".png", ".jpg", ".jpeg"}
    DATA_EXTENSIONS: set = {".csv"}
    ALLOWED_EXTENSIONS: set = CODE_EXTENSIONS | IMAGE_EXTENSIONS | DATA_EXTENSIONS

    # LLM Endpoints
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    GEMINI_URL: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    GROQ_URL: str = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def has_openrouter(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def has_pinecone(self) -> bool:
        return bool(self.PINECONE_API_KEY)

    @property
    def has_any_llm(self) -> bool:
        return self.has_openrouter or self.has_gemini or self.has_groq

    def ensure_upload_dir(self):
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_upload_dir()
