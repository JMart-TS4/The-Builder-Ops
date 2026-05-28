from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import settings
from config.logging import get_logger
from core.llm.config import get_provider_config

logger = get_logger(__name__)


def get_llm(provider: str | None = None) -> BaseChatModel:
    """Factory: instancia y retorna el LLM configurado.

    Args:
        provider: 'anthropic' | 'gemini'. Si es None usa el default del .env.

    Returns:
        Instancia de BaseChatModel lista para usar en cadenas LangChain.

    Raises:
        ValueError: Si el proveedor no está soportado o falta la API key.
    """
    provider = provider or settings.default_llm_provider
    config = get_provider_config(provider)

    logger.info(f"Inicializando LLM | proveedor={provider} | modelo={config.model}")

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY no está configurada en el .env")
        return ChatAnthropic(
            model=config.model,
            api_key=settings.anthropic_api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            streaming=config.streaming,
        )

    if provider == "gemini":
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY no está configurada en el .env")
        return ChatGoogleGenerativeAI(
            model=config.model,
            google_api_key=settings.google_api_key,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            streaming=config.streaming,
        )

    raise ValueError(f"Proveedor '{provider}' no implementado en el factory.")