from dataclasses import dataclass
from datetime import datetime, timezone
from core.rag.loader import prepare_documents
from core.rag.vectorstore import ingest_documents, ingest_documents_incremental
from core.rag.retriever import retrieve, format_context
from core.sync_state import get_last_sync, save_last_sync
from services.integration_service import IntegrationService, SyncResult
from config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IngestResult:
    """Resultado del pipeline completo de ingesta."""
    synced_docs:   int = 0
    indexed_chunks: int = 0
    errors:        list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def success(self) -> bool:
        return self.indexed_chunks > 0 and not self.errors


class DocumentService:
    """Pipeline completo: fuentes externas → chunks → vectorstore → contexto.

    Es el único punto del sistema que conoce tanto las integraciones
    como el RAG. El chat service solo llama a get_context().
    """

    def __init__(self, integration_service: IntegrationService, user_id: str):
        self._integrations = integration_service
        self._user_id = user_id

    def ingest(self) -> IngestResult:
        """Sincronización completa: re-indexa todos los documentos del usuario."""
        result = IngestResult()

        sync: SyncResult = self._integrations.sync()
        result.synced_docs = sync.total
        result.errors      = sync.errors

        if not sync.all_docs:
            logger.warning("Ingest: no se obtuvieron documentos de ninguna fuente")
            return result

        chunks = prepare_documents(sync.all_docs)
        if not chunks:
            logger.warning("Ingest: no se generaron chunks")
            return result

        result.indexed_chunks = ingest_documents(chunks, self._user_id)

        logger.info(
            f"Ingest completo | docs={result.synced_docs} "
            f"chunks={result.indexed_chunks} errores={len(result.errors)}"
        )
        return result

    def ingest_incremental(self) -> IngestResult:
        """Sincronización incremental: solo indexa docs nuevos o modificados.

        En el primer uso (sin last_sync guardado) se comporta igual que ingest().
        """
        result = IngestResult()

        last_sync = get_last_sync(self._user_id)
        sync: SyncResult = self._integrations.sync(since=last_sync)
        result.synced_docs = sync.total
        result.errors      = sync.errors

        now = datetime.now(timezone.utc)

        if not sync.all_docs:
            logger.info("Ingest incremental: sin cambios desde la última sync")
            save_last_sync(self._user_id, now)
            return result

        chunks = prepare_documents(sync.all_docs)
        if not chunks:
            logger.warning("Ingest incremental: no se generaron chunks")
            save_last_sync(self._user_id, now)
            return result

        result.indexed_chunks = ingest_documents_incremental(chunks, self._user_id)
        save_last_sync(self._user_id, now)

        logger.info(
            f"Ingest incremental | docs={result.synced_docs} "
            f"chunks={result.indexed_chunks} errores={len(result.errors)}"
        )
        return result

    def get_context(self, query: str, k: int = 5) -> str:
        """Recupera y formatea contexto relevante para una consulta."""
        docs = retrieve(query, self._user_id, k=k)
        return format_context(docs)

    def status(self) -> dict:
        """Retorna el estado de las conexiones externas."""
        return self._integrations.status()
