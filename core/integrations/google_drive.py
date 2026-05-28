import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

from core.integrations.base import BaseIntegration, Document
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_PATH = "credentials/gdrive_token.json"

# Tipos de archivo soportados para extracción de texto
SUPPORTED_MIME_TYPES = {
    "application/vnd.google-apps.document": "text/plain",           # Google Docs
    "application/vnd.google-apps.spreadsheet": "text/csv",          # Google Sheets
    "application/vnd.google-apps.presentation": "text/plain",       # Google Slides
    "application/pdf": None,                                         # PDF directo
    "text/plain": None,                                              # TXT directo
}


class GoogleDriveIntegration(BaseIntegration):

    def __init__(self):
        self._service = None

    def _get_service(self):
        """Inicializa o reutiliza el cliente autenticado de Drive."""
        if self._service:
            return self._service

        creds = None

        # Token guardado de sesiones anteriores
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        # Refrescar o autenticar de nuevo
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

            # Guardar token para la próxima vez
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        self._service = build("drive", "v3", credentials=creds)
        logger.info("Google Drive autenticado correctamente")
        return self._service

    def _extract_text(self, service, file_id: str, mime_type: str) -> str:
        """Extrae el contenido de texto de un archivo de Drive."""
        try:
            export_mime = SUPPORTED_MIME_TYPES.get(mime_type)

            if export_mime:
                # Archivos de Google Workspace — exportar como texto
                response = service.files().export(
                    fileId=file_id, mimeType=export_mime
                ).execute()
                return response.decode("utf-8") if isinstance(response, bytes) else response

            elif mime_type == "text/plain":
                # Archivos de texto plano — descargar directo
                request = service.files().get_media(fileId=file_id)
                buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(buffer, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                return buffer.getvalue().decode("utf-8")

        except Exception as e:
            logger.warning(f"No se pudo extraer texto del archivo {file_id}: {e}")
            return ""

    def fetch_documents(self, max_files: int = 50) -> list[Document]:
        """Recupera y extrae texto de todos los archivos soportados en Drive."""
        service = self._get_service()
        docs = []

        mime_filter = " or ".join(
            [f"mimeType='{m}'" for m in SUPPORTED_MIME_TYPES.keys()]
        )
        query = f"({mime_filter}) and trashed=false"

        try:
            results = service.files().list(
                q=query,
                pageSize=max_files,
                fields="files(id, name, mimeType, webViewLink, modifiedTime)",
            ).execute()

            files = results.get("files", [])
            logger.info(f"Google Drive: {len(files)} archivos encontrados")

            for file in files:
                content = self._extract_text(
                    service, file["id"], file["mimeType"]
                )
                if content.strip():
                    docs.append(Document(
                        content=content,
                        source="google_drive",
                        title=file.get("name", "Sin título"),
                        url=file.get("webViewLink", ""),
                        metadata={
                            "file_id": file["id"],
                            "mime_type": file["mimeType"],
                            "modified": file.get("modifiedTime", ""),
                        },
                    ))

        except Exception as e:
            logger.error(f"Error al recuperar archivos de Drive: {e}")

        logger.info(f"Google Drive: {len(docs)} documentos procesados")
        return docs

    def search(self, query: str) -> list[Document]:
        """Busca archivos en Drive cuyo nombre o contenido coincida."""
        service = self._get_service()
        docs = []

        try:
            results = service.files().list(
                q=f"fullText contains '{query}' and trashed=false",
                pageSize=10,
                fields="files(id, name, mimeType, webViewLink)",
            ).execute()

            for file in results.get("files", []):
                content = self._extract_text(
                    service, file["id"], file["mimeType"]
                )
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