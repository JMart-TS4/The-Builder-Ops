from dataclasses import dataclass, field
from core.integrations.base import Document
from core.integrations.google_drive import GoogleDriveIntegration
from core.integrations.clickup import ClickUpIntegration
from config.logging import get_logger

logger = get_logger(__name__)

@dataclass
class SyncResult:
    """Resultado de una sincronización de fuentes externas."""
    drive_docs:   list[Document] = field(default_factory=list)
    clickup_docs: list[Document] = field(default_factory=list)
    errors:       list[str]      = field(default_factory=list)

    @property
    def all_docs(self) -> list[Document]:
        return self.drive_docs + self.clickup_docs

    @property
    def total(self) -> int:
        return len(self.all_docs)


class IntegrationService:
    """Orquesta la sincronización de Google Drive y ClickUp.

    Es el único punto del sistema que instancia los conectores.
    El resto del código (RAG, chat) solo interactúa con esta clase.
    """

    def __init__(
        self,
        google_access_token: str | None = None,
        clickup_user_id: str = "default",
        clickup_access_token: str | None = None,
    ):
        self._drive   = (
            GoogleDriveIntegration()
            if google_access_token else None
        )
        self._clickup = ClickUpIntegration(
            user_id=clickup_user_id,
            access_token=clickup_access_token,
        )

    # ── Estado de conexiones ─────────────────────────────────────────────────

    @property
    def drive_connected(self) -> bool:
        return self._drive is not None and self._drive.health_check()

    @property
    def clickup_connected(self) -> bool:
        return self._clickup.is_authenticated() and self._clickup.health_check()

    def status(self) -> dict:
        return {
            "google_drive": self.drive_connected,
            "clickup":      self.clickup_connected,
        }

    # ── Sincronización ───────────────────────────────────────────────────────

    def sync(self) -> SyncResult:
        """Recupera todos los documentos disponibles de ambas fuentes."""
        result = SyncResult()

        if self._drive:
            try:
                result.drive_docs = self._drive.fetch_documents()
                logger.info(f"Drive sincronizado: {len(result.drive_docs)} docs")
            except Exception as e:
                msg = f"Error sincronizando Drive: {e}"
                result.errors.append(msg)
                logger.error(msg)

        if self._clickup.is_authenticated():
            try:
                result.clickup_docs = self._clickup.fetch_documents()
                logger.info(f"ClickUp sincronizado: {len(result.clickup_docs)} docs")
            except Exception as e:
                msg = f"Error sincronizando ClickUp: {e}"
                result.errors.append(msg)
                logger.error(msg)

        logger.info(f"Sync completo: {result.total} documentos totales")
        return result

    def search(self, query: str) -> list[Document]:
        """Busca en ambas fuentes y combina los resultados."""
        results = []

        if self._drive:
            try:
                results += self._drive.search(query)
            except Exception as e:
                logger.error(f"Error buscando en Drive: {e}")

        if self._clickup.is_authenticated():
            try:
                results += self._clickup.search(query)
            except Exception as e:
                logger.error(f"Error buscando en ClickUp: {e}")

        logger.info(f"Search '{query}': {len(results)} resultados totales")
        return results