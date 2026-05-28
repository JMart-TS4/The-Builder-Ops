from langchain_chroma import Chroma
from langchain_core.documents import Document as LangchainDoc
from core.rag.embeddings import get_embeddings
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)

def get_vectorstore() -> Chroma:
    """Retorna el vectorstore Chroma persistido en disco."""
    return Chroma(
        collection_name="yilo_docs",
        embedding_function=get_embeddings(),
        persist_directory=settings.vectorstore_path,
    )

def ingest_documents(docs: list[LangchainDoc]) -> int:
    """Ingesta una lista de documentos LangChain en el vectorstore.

    Limpia la colección antes de reingestar para evitar duplicados.

    Args:
        docs: Documentos ya procesados por el loader.

    Returns:
        Número de documentos indexados.
    """
    if not docs:
        logger.warning("Ingest: no hay documentos para indexar")
        return 0

    vs = get_vectorstore()

    # Limpiar colección antes de reingestar
    vs.reset_collection()
    vs.add_documents(docs)

    logger.info(f"Vectorstore: {len(docs)} documentos indexados")
    return len(docs)