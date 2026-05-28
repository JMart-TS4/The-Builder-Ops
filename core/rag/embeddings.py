from langchain_core.embeddings import Embeddings
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)

_DEFAULTS = {
    "gemini": "models/gemini-embedding-001",
    "voyage": "voyage-3",
    "openai": "text-embedding-3-small",
}


def get_embeddings() -> Embeddings:
    provider = settings.embedding_provider
    model = settings.embedding_model or _DEFAULTS[provider]
    logger.info(f"Inicializando embeddings | proveedor={provider} modelo={model}")

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=settings.google_api_key,
        )

    if provider == "voyage":
        try:
            from langchain_voyageai import VoyageAIEmbeddings
        except ImportError:
            raise ImportError(
                "Instala el paquete: uv add langchain-voyageai"
            )
        return VoyageAIEmbeddings(
            model=model,
            voyage_api_key=settings.voyage_api_key,
        )

    if provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            raise ImportError(
                "Instala el paquete: uv add langchain-openai"
            )
        return OpenAIEmbeddings(
            model=model,
            openai_api_key=settings.openai_api_key,
        )

    raise ValueError(f"Proveedor de embeddings desconocido: {provider!r}")
