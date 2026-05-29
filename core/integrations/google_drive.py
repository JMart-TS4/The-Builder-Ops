import io
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from core.integrations.base import BaseIntegration, Document
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)

SCOPES     = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_PATH = "credentials/gdrive_token.json"

SUPPORTED_MIME_TYPES = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
    "application/pdf": None,
    "text/plain":      None,
}


class GoogleDriveIntegration(BaseIntegration):

    def __init__(self):
        self._service = None

    # ── Autenticación ─────────────────────────────────────────────────────────

    def _get_service(self):
        if self._service:
            return self._service

        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.google_drive_credentials_path, SCOPES
                )
                creds = flow.run_local_server(
                    port=0,
                    prompt="select_account",
                    access_type="offline",
                )
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        self._service = build("drive", "v3", credentials=creds)
        logger.info("Google Drive autenticado correctamente")
        return self._service

    # ── Unidades Compartidas ──────────────────────────────────────────────────

    def _get_shared_drives(self, service) -> list[dict]:
        """Lista todas las Unidades Compartidas accesibles por la cuenta."""
        drives = []
        page_token = None
        while True:
            resp = service.drives().list(
                pageSize=100,
                fields="nextPageToken, drives(id, name)",
                pageToken=page_token,
            ).execute()
            drives.extend(resp.get("drives", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        logger.info(f"Google Drive: {len(drives)} unidades compartidas encontradas")
        return drives

    # ── Resolución de rutas de carpetas ───────────────────────────────────────

    def _get_folders_in_drive(self, service, drive_id: str) -> dict[str, dict]:
        """Pre-carga todas las carpetas de una unidad para resolver rutas sin API extra."""
        folders: dict[str, dict] = {}
        page_token = None
        while True:
            resp = service.files().list(
                corpora="drive",
                driveId=drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="nextPageToken, files(id, name, parents)",
                pageToken=page_token,
            ).execute()
            for f in resp.get("files", []):
                folders[f["id"]] = {
                    "name":    f["name"],
                    "parents": f.get("parents", []),
                }
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return folders

    def _resolve_folder_path(
        self, parent_id: str, drive_id: str, folders: dict
    ) -> str:
        """Construye la ruta completa desde el parent hasta la raíz de la unidad."""
        parts: list[str] = []
        current_id = parent_id
        visited: set[str] = set()
        while current_id and current_id != drive_id and current_id not in visited:
            visited.add(current_id)
            folder = folders.get(current_id)
            if not folder:
                break
            parts.append(folder["name"])
            parents = folder.get("parents", [])
            current_id = parents[0] if parents else None
        return "/".join(reversed(parts))

    # ── Extracción de texto ───────────────────────────────────────────────────

    def _extract_text(self, service, file_id: str, mime_type: str) -> str:
        try:
            export_mime = SUPPORTED_MIME_TYPES.get(mime_type)

            if export_mime:
                response = service.files().export(
                    fileId=file_id,
                    mimeType=export_mime,
                ).execute()
                return response.decode("utf-8") if isinstance(response, bytes) else response

            else:
                request = service.files().get_media(
                    fileId=file_id,
                    supportsAllDrives=True,
                )
                buf = io.BytesIO()
                downloader = MediaIoBaseDownload(buf, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                raw = buf.getvalue()

                if mime_type == "application/pdf":
                    return self._extract_pdf_text(raw)
                return raw.decode("utf-8", errors="ignore")

        except Exception as e:
            logger.warning(f"No se pudo extraer texto del archivo {file_id}: {e}")

        return ""

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("pypdf no instalado — PDFs no serán indexados. Instalar con: uv add pypdf")
        except Exception as e:
            logger.warning(f"Error extrayendo texto de PDF: {e}")
        return ""

    # ── API pública ───────────────────────────────────────────────────────────

    def fetch_documents(self, max_files: int = 200, since=None) -> list[Document]:
        """Recupera documentos de todas las Unidades Compartidas.

        Cada documento incluye `project` (nombre de la unidad) y
        `folder_path` (ruta de subcarpetas dentro de la unidad).
        """
        service = self._get_service()
        docs: list[Document] = []

        shared_drives = self._get_shared_drives(service)
        if not shared_drives:
            logger.warning("No se encontraron Unidades Compartidas — verificar permisos.")

        mime_filter = " or ".join(f"mimeType='{m}'" for m in SUPPORTED_MIME_TYPES)
        base_query  = f"({mime_filter}) and trashed=false"
        if since is not None:
            base_query += f" and modifiedTime > '{since.strftime('%Y-%m-%dT%H:%M:%SZ')}'"

        for drive in shared_drives:
            drive_id   = drive["id"]
            drive_name = drive["name"]

            folders = self._get_folders_in_drive(service, drive_id)
            drive_docs: list[Document] = []

            try:
                page_token = None
                while True:
                    resp = service.files().list(
                        corpora="drive",
                        driveId=drive_id,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        q=base_query,
                        pageSize=100,
                        fields=(
                            "nextPageToken, "
                            "files(id, name, mimeType, webViewLink, modifiedTime, parents)"
                        ),
                        pageToken=page_token,
                    ).execute()

                    for file in resp.get("files", []):
                        content = self._extract_text(service, file["id"], file["mimeType"])
                        if not content.strip():
                            continue

                        parents     = file.get("parents", [])
                        folder_path = (
                            self._resolve_folder_path(parents[0], drive_id, folders)
                            if parents else ""
                        )

                        drive_docs.append(Document(
                            content=content,
                            source="google_drive",
                            title=file.get("name", "Sin título"),
                            url=file.get("webViewLink", ""),
                            metadata={
                                "file_id":     file["id"],
                                "mime_type":   file["mimeType"],
                                "modified":    file.get("modifiedTime", ""),
                                "project":     drive_name,
                                "drive_id":    drive_id,
                                "folder_path": folder_path,
                            },
                        ))

                    page_token = resp.get("nextPageToken")
                    if not page_token or len(drive_docs) >= max_files:
                        break

            except Exception as e:
                logger.error(f"Error al procesar unidad '{drive_name}': {e}")

            docs.extend(drive_docs)
            logger.info(f"Drive '{drive_name}': {len(drive_docs)} documentos procesados")

        logger.info(
            f"Google Drive total: {len(docs)} documentos "
            f"de {len(shared_drives)} unidades compartidas"
        )
        return docs

    def search(self, query: str) -> list[Document]:
        """Búsqueda full-text en todas las Unidades Compartidas."""
        service = self._get_service()
        docs: list[Document] = []
        try:
            results = service.files().list(
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                q=f"fullText contains '{query}' and trashed=false",
                pageSize=10,
                fields="files(id, name, mimeType, webViewLink)",
            ).execute()

            for file in results.get("files", []):
                content = self._extract_text(service, file["id"], file["mimeType"])
                if content.strip():
                    docs.append(Document(
                        content=content,
                        source="google_drive",
                        title=file.get("name", ""),
                        url=file.get("webViewLink", ""),
                        metadata={"file_id": file["id"]},
                    ))

        except Exception as e:
            logger.error(f"Error en búsqueda de Drive: {e}")

        return docs

    def health_check(self) -> bool:
        try:
            self._get_service().files().list(pageSize=1).execute()
            return True
        except Exception:
            return False
