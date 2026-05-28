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

    # ClickUp
    clickup_api_token: str = Field(default="", alias="CLICKUP_API_TOKEN")
    clickup_workspace_id: str = Field(default="", alias="CLICKUP_WORKSPACE_ID")

    # RAG / Vectorstore
    vectorstore_path: str = Field(default=".vectorstore", alias="VECTORSTORE_PATH")
    embedding_model: str = Field(
        default="models/embedding-001", alias="EMBEDDING_MODEL"
    )

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