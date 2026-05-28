import os
import json
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
from core.integrations.base import BaseIntegration, Document
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.clickup.com/api/v2"
TOKEN_DIR = "credentials"


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _OAuthCallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Autenticacion exitosa. Puedes cerrar esta ventana.</h2></body></html>"
            )
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: no se recibio el codigo de autorizacion.")

    def log_message(self, format, *args):
        pass


class ClickUpIntegration(BaseIntegration):

    def __init__(self, user_id: str = "default", access_token: str = None):
        self.user_id = user_id
        self._token_path = os.path.join(TOKEN_DIR, f"clickup_token_{user_id}.json")
        self._teams = None

        self._access_token = access_token or self._load_token()
        self.headers = {
            "Authorization": self._access_token or "",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _load_token(self) -> str | None:
        if os.path.exists(self._token_path):
            with open(self._token_path) as f:
                return json.load(f).get("access_token")
        return None

    def _save_token(self, access_token: str):
        os.makedirs(TOKEN_DIR, exist_ok=True)
        with open(self._token_path, "w") as f:
            json.dump({"access_token": access_token}, f)

    OAUTH_PORT = 8765

    def authenticate(self) -> bool:
        """Abre el browser para el flujo OAuth de ClickUp y guarda el token del usuario."""
        _OAuthCallbackHandler.code = None
        redirect_uri = f"http://localhost:{self.OAUTH_PORT}"
        server = HTTPServer(("localhost", self.OAUTH_PORT), _OAuthCallbackHandler)

        auth_url = (
            f"https://app.clickup.com/api?"
            f"client_id={settings.clickup_client_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        )

        logger.info(f"Abriendo browser para autenticacion ClickUp (usuario '{self.user_id}')")
        webbrowser.open(auth_url)

        server.handle_request()
        server.server_close()

        code = _OAuthCallbackHandler.code
        if not code:
            logger.error("No se recibio el codigo de autorizacion de ClickUp")
            return False

        resp = requests.post(
            f"{BASE_URL}/oauth/token",
            params={
                "client_id": settings.clickup_client_id,
                "client_secret": settings.clickup_client_secret,
                "code": code,
            },
            timeout=15,
        )

        if not resp.ok:
            logger.error(f"Error al obtener token ClickUp: {resp.text}")
            return False

        access_token = resp.json().get("access_token")
        if not access_token:
            logger.error("Respuesta de ClickUp no contiene access_token")
            return False

        self._access_token = access_token
        self.headers["Authorization"] = access_token
        self._save_token(access_token)
        logger.info(f"Token ClickUp guardado para usuario '{self.user_id}'")
        return True

    def is_authenticated(self) -> bool:
        return bool(self._access_token)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: dict = None) -> dict:
        try:
            r = requests.get(
                f"{BASE_URL}/{endpoint}",
                headers=self.headers,
                params=params or {},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error(f"Error en petición ClickUp [{endpoint}]: {e}")
            return {}

    # ------------------------------------------------------------------
    # Data fetchers — workspace IDs vienen de la API, no de settings
    # ------------------------------------------------------------------

    def _get_teams(self) -> list[dict]:
        if self._teams is None:
            self._teams = self._get("team").get("teams", [])
        return self._teams

    def _get_spaces(self, team_id: str) -> list[dict]:
        return self._get(f"team/{team_id}/space", {"archived": False}).get("spaces", [])

    def _get_lists(self, space_id: str) -> list[dict]:
        return self._get(f"space/{space_id}/list", {"archived": False}).get("lists", [])

    def _get_tasks(self, list_id: str) -> list[dict]:
        return self._get(f"list/{list_id}/task", {
            "archived": False,
            "include_closed": True,
            "subtasks": True,
        }).get("tasks", [])

    def _get_comments(self, task_id: str) -> list[str]:
        comments = self._get(f"task/{task_id}/comment").get("comments", [])
        return [c.get("comment_text", "") for c in comments if c.get("comment_text")]

    def _task_to_document(self, task: dict) -> Document:
        comments = self._get_comments(task["id"])
        comments_text = "\n".join(f"- {c}" for c in comments) if comments else "Sin comentarios"
        assignees = (
            ", ".join(a.get("username", "") for a in task.get("assignees", []))
            or "Sin asignar"
        )
        content = (
            f"Tarea: {task.get('name', '')}\n"
            f"Estado: {task.get('status', {}).get('status', 'desconocido')}\n"
            f"Prioridad: {task.get('priority', {}).get('priority', 'sin prioridad') if task.get('priority') else 'sin prioridad'}\n"
            f"Asignado a: {assignees}\n"
            f"Descripción: {task.get('description') or 'Sin descripción'}\n"
            f"Comentarios:\n{comments_text}\n"
        )
        return Document(
            content=content,
            source="clickup",
            title=task.get("name", "Sin título"),
            url=task.get("url", ""),
            metadata={
                "task_id": task["id"],
                "status": task.get("status", {}).get("status", ""),
                "list_id": task.get("list", {}).get("id", ""),
            },
        )

    # ------------------------------------------------------------------
    # BaseIntegration interface
    # ------------------------------------------------------------------

    def fetch_documents(self) -> list[Document]:
        docs = []
        for team in self._get_teams():
            for space in self._get_spaces(team["id"]):
                for lst in self._get_lists(space["id"]):
                    for task in self._get_tasks(lst["id"]):
                        docs.append(self._task_to_document(task))
        logger.info(f"ClickUp: {len(docs)} tareas procesadas (usuario '{self.user_id}')")
        return docs

    def search(self, query: str) -> list[Document]:
        q = query.lower()
        results = [d for d in self.fetch_documents() if q in d.title.lower() or q in d.content.lower()]
        logger.info(f"ClickUp search '{query}': {len(results)} resultados")
        return results

    def health_check(self) -> bool:
        try:
            return "teams" in self._get("team")
        except Exception:
            return False
