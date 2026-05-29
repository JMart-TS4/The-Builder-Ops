from langchain_core.documents import Document as LangchainDoc
from core.rag.vectorstore import get_vectorstore
from config.logging import get_logger

logger = get_logger(__name__)

TOP_K = 5


def retrieve(
    query: str,
    user_id: str,
    k: int = TOP_K,
    project_filter: str | None = None,
) -> list[LangchainDoc]:
    """Recupera los chunks más relevantes para una consulta.

    Args:
        query:          Pregunta o mensaje del usuario.
        user_id:        Slug del usuario — determina la colección de Chroma.
        k:              Número de resultados a retornar.
        project_filter: Si se indica, restringe la búsqueda a esa Unidad Compartida.
    """
    try:
        vs     = get_vectorstore(user_id)
        where  = {"project": project_filter} if project_filter else None
        results = vs.similarity_search(query, k=k, filter=where)
        logger.info(
            f"Retriever: '{query[:40]}...' → {len(results)} chunks"
            + (f" | proyecto='{project_filter}'" if project_filter else "")
        )
        return results
    except Exception as e:
        logger.error(f"Error en retriever: {e}")
        return []


def format_context(docs: list[LangchainDoc]) -> str:
    """Formatea los chunks recuperados como contexto para el LLM.

    Incluye proyecto y ruta de carpeta para que el LLM pueda
    citar y ubicar correctamente la información.
    """
    if not docs:
        return "No se encontró contexto relevante."

    parts = []
    for i, doc in enumerate(docs, 1):
        title       = doc.metadata.get("title", "Sin título")
        project     = doc.metadata.get("project", "")
        folder_path = doc.metadata.get("folder_path", "")
        url         = doc.metadata.get("url", "")

        location = " > ".join(filter(None, [project, folder_path, title]))

        parts.append(
            f"[{i}] {location}"
            + (f"\n{url}" if url else "")
            + f"\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(parts)
