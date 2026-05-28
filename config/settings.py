from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):

    # LLM Providers
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    default_llm_provider: Literal["anthropic", "gemini"] = Field(
        default="anthropic", alias="DEFAULT_LLM_PROVIDER"
    )

    # Google Drive
    google_drive_credentials_path: str = Field(
        default="credentials/gdrive.json",
        alias="GOOGLE_DRIVE_CREDENTIALS_PATH"
    )

    # ClickUp OAuth
    clickup_client_id: str = Field(default="", alias="CLICKUP_CLIENT_ID")
    clickup_client_secret: str = Field(default="", alias="CLICKUP_CLIENT_SECRET")
    clickup_redirect_uri: str = Field(default="http://localhost", alias="CLICKUP_REDIRECT_URI")

    # RAG / Vectorstore
    vectorstore_path: str = Field(default=".vectorstore", alias="VECTORSTORE_PATH")
    embedding_provider: Literal["gemini", "voyage", "openai"] = Field(
        default="gemini", alias="EMBEDDING_PROVIDER"
    )
    embedding_model: str = Field(default="", alias="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(default=100, alias="EMBEDDING_BATCH_SIZE")
    embedding_batch_delay: float = Field(default=1.0, alias="EMBEDDING_BATCH_DELAY")
    voyage_api_key: str = Field(default="", alias="VOYAGE_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # App
    app_env: Literal["development", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }

# Instancia global — importar desde cualquier módulo
settings = Settings()