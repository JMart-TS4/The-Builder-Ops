from langchain_core.documents import Document as LangchainDoc
from core.rag.vectorstore import get_vectorstore
from config.logging import get_logger

logger = get_logger(__name__)

# Número de chunks relevantes a recuperar por consulta
TOP_K = 5

def retrieve(query: str, user_id: str, k: int = TOP_K) -> list[LangchainDoc]:
    """Recupera los chunks más relevantes para una consulta.

    Args:
        query:   Pregunta o mensaje del usuario.
        user_id: Slug del usuario — determina la colección de Chroma.
        k:       Número de resultados a retornar.

    Returns:
        Lista de chunks ordenados por relevancia semántica.
    """
    try:
        vs      = get_vectorstore(user_id)
        results = vs.similarity_search(query, k=k)
        logger.info(f"Retriever: '{query[:40]}...' → {len(results)} chunks")
        return results
    except Exception as e:
        logger.error(f"Error en retriever: {e}")
        return []


def format_context(docs: list[LangchainDoc]) -> str:
    """Formatea los chunks recuperados como contexto para el LLM.

    Cada chunk incluye su fuente y título para que el LLM
    pueda citar correctamente la información.
    """
    if not docs:
        return "No se encontró contexto relevante."

    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "desconocido")
        title  = doc.metadata.get("title", "Sin título")
        url    = doc.metadata.get("url", "")

        parts.append(
            f"[{i}] {title} ({source})"
            + (f"\n{url}" if url else "")
            + f"\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(parts)