from langchain_core.documents import Document as LangchainDoc
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.integrations.base import Document as IntegrationDoc
from config.logging import get_logger

logger = get_logger(__name__)

# Tamaño de chunk
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 150

def _get_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def prepare_documents(
    raw_docs: list[IntegrationDoc],
) -> list[LangchainDoc]:
    """Convierte documentos de integración en chunks indexables.

    Pipeline:
        IntegrationDoc → LangchainDoc → chunks con metadata

    Args:
        raw_docs: Documentos crudos de Google Drive o ClickUp.

    Returns:
        Lista de chunks listos para ingestar en el vectorstore.
    """
    splitter = _get_splitter()
    chunks: list[LangchainDoc] = []

    for doc in raw_docs:
        if not doc.content.strip():
            continue

        langchain_doc = LangchainDoc(
            page_content=doc.content,
            metadata={
                "source": doc.source,
                "title":  doc.title,
                "url":    doc.url,
                **doc.metadata,
            },
        )

        doc_chunks = splitter.split_documents([langchain_doc])
        chunks.extend(doc_chunks)

    logger.info(
        f"Loader: {len(raw_docs)} docs → {len(chunks)} chunks "
        f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})"
    )
    return chunks