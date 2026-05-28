import re
import time
from langchain_chroma import Chroma
from langchain_core.documents import Document as LangchainDoc
from core.rag.embeddings import get_embeddings
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


def _collection_name(user_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "_", user_id.lower())
    return f"docs_{slug}"


def get_vectorstore(user_id: str) -> Chroma:
    return Chroma(
        collection_name=_collection_name(user_id),
        embedding_function=get_embeddings(),
        persist_directory=settings.vectorstore_path,
    )


def _add_batch_with_retry(vs: Chroma, batch: list[LangchainDoc], max_retries: int = 4, base_delay: float = 5.0) -> None:
    for attempt in range(max_retries):
        try:
            vs.add_documents(batch)
            return
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries - 1:
                    wait = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit (429), reintentando en {wait:.0f}s… (intento {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
            raise
    raise RuntimeError(f"Fallo al indexar batch tras {max_retries} intentos")


def ingest_documents(docs: list[LangchainDoc], user_id: str) -> int:
    """Ingesta completa: limpia la colección del usuario y re-indexa todo."""
    if not docs:
        logger.warning("Ingest: no hay documentos para indexar")
        return 0

    vs = get_vectorstore(user_id)
    vs.reset_collection()

    batch_size = settings.embedding_batch_size
    batch_delay = settings.embedding_batch_delay
    total = len(docs)
    indexed = 0

    for i in range(0, total, batch_size):
        batch = docs[i : i + batch_size]
        _add_batch_with_retry(vs, batch)
        indexed += len(batch)
        logger.info(f"Vectorstore: {indexed}/{total} chunks indexados")
        if i + batch_size < total:
            time.sleep(batch_delay)

    logger.info(f"Vectorstore: {total} documentos indexados (completado)")
    return total


def ingest_documents_incremental(docs: list[LangchainDoc], user_id: str) -> int:
    """Ingesta incremental: elimina chunks existentes de los docs modificados y re-indexa."""
    if not docs:
        logger.info("Ingest incremental: sin documentos nuevos o modificados")
        return 0

    vs = get_vectorstore(user_id)

    # Eliminar chunks obsoletos de cada doc que viene actualizado
    doc_ids = {c.metadata["doc_id"] for c in docs if c.metadata.get("doc_id")}
    for doc_id in doc_ids:
        try:
            vs.delete(where={"doc_id": doc_id})
        except Exception as e:
            logger.warning(f"No se pudieron eliminar chunks de doc_id={doc_id}: {e}")

    batch_size = settings.embedding_batch_size
    batch_delay = settings.embedding_batch_delay
    total = len(docs)
    indexed = 0

    for i in range(0, total, batch_size):
        batch = docs[i : i + batch_size]
        _add_batch_with_retry(vs, batch)
        indexed += len(batch)
        logger.info(f"Vectorstore incremental: {indexed}/{total} chunks indexados")
        if i + batch_size < total:
            time.sleep(batch_delay)

    logger.info(f"Vectorstore incremental: {total} chunks actualizados (completado)")
    return total
