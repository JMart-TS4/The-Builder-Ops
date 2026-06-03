import os
import json
import webbrowser
import urllib.parse
from datetime import datetime, timezone
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

    def _get_folders(self, space_id: str) -> list[dict]:
        return self._get(f"space/{space_id}/folder", {"archived": False}).get("folders", [])

    def _get_lists_in_folder(self, folder_id: str) -> list[dict]:
        return self._get(f"folder/{folder_id}/list", {"archived": False}).get("lists", [])

    def _get_all_lists(self, space_id: str) -> list[dict]:
        """Returns all lists in a space: folderless + lists inside folders."""
        lists = self._get(f"space/{space_id}/list", {"archived": False}).get("lists", [])
        for folder in self._get_folders(space_id):
            for lst in self._get_lists_in_folder(folder["id"]):
                lst.setdefault("folder_name", folder.get("name", ""))
                lists.append(lst)
        return lists

    def _get_lists(self, space_id: str) -> list[dict]:
        return self._get_all_lists(space_id)

    def _get_tasks(self, list_id: str, since=None) -> list[dict]:
        params = {
            "archived": False,
            "include_closed": True,
            "subtasks": True,
        }
        if since is not None:
            params["date_updated_gt"] = int(since.timestamp() * 1000)
        return self._get(f"list/{list_id}/task", params).get("tasks", [])

    def _get_comments(self, task_id: str) -> list[str]:
        comments = self._get(f"task/{task_id}/comment").get("comments", [])
        return [c.get("comment_text", "") for c in comments if c.get("comment_text")]

    @staticmethod
    def _format_date(ms_timestamp: str | int | None) -> str:
        """Convierte un timestamp en milisegundos (ClickUp) a fecha legible DD/MM/YYYY."""
        if not ms_timestamp:
            return "Sin fecha"
        try:
            ts = int(ms_timestamp) / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m/%Y")
        except (ValueError, OSError):
            return "Fecha inválida"

    @staticmethod
    def _parse_custom_field_value(field: dict) -> str | None:
        """Extrae el valor legible de un custom field de ClickUp según su tipo.

        Retorna None si el campo no tiene valor asignado.
        """
        value = field.get("value")
        field_type = field.get("type", "")
        type_config = field.get("type_config") or {}

        if value is None or value == "":
            return None

        # Texto plano, URL, email, teléfono
        if field_type in ("text", "url", "email", "phone"):
            return str(value)

        # Número y moneda
        if field_type in ("number", "currency"):
            return str(value)

        # Checkbox / boolean
        if field_type == "checkbox":
            return "Sí" if value else "No"

        # Rating (número entero)
        if field_type == "rating":
            return str(value)

        # Fecha (timestamp en ms)
        if field_type == "date":
            return ClickUpIntegration._format_date(value)

        # Drop-down: value es el id de la opción seleccionada
        if field_type == "drop_down":
            options = type_config.get("options", [])
            # ClickUp puede enviar el índice (int) o el id (str)
            for opt in options:
                if str(opt.get("id")) == str(value) or opt.get("orderindex") == value:
                    return opt.get("name", str(value))
            return str(value)

        # Labels: value es una lista de ids de opciones
        if field_type == "labels":
            options = type_config.get("options", [])
            id_to_label = {str(o.get("id")): o.get("label", "") for o in options}
            if isinstance(value, list):
                return ", ".join(id_to_label.get(str(v), str(v)) for v in value)
            return str(value)

        # Users / People: lista de objetos usuario
        if field_type in ("users", "people"):
            if isinstance(value, list):
                return ", ".join(
                    u.get("username") or u.get("email") or str(u)
                    for u in value
                    if isinstance(u, dict)
                )
            return str(value)

        # Relaciones y tipos no contemplados: serializar como string
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    def _extract_custom_fields(self, task: dict) -> tuple[str, dict]:
        """Devuelve (bloque_texto, dict_metadata) con todos los custom fields con valor."""
        lines: list[str] = []
        meta: dict[str, str] = {}

        for field in task.get("custom_fields", []):
            name = field.get("name", "Campo sin nombre")
            parsed = self._parse_custom_field_value(field)
            if parsed is None:
                continue
            lines.append(f"{name}: {parsed}")
            meta[f"cf_{name.lower().replace(' ', '_')}"] = parsed

        block = "\n".join(lines) if lines else "Sin campos personalizados"
        return block, meta

    def _task_to_document(self, task: dict) -> Document:
        comments = self._get_comments(task["id"])
        comments_text = "\n".join(f"- {c}" for c in comments) if comments else "Sin comentarios"
        assignees = (
            ", ".join(a.get("username", "") for a in task.get("assignees", []))
            or "Sin asignar"
        )
        start_date = self._format_date(task.get("start_date"))
        due_date = self._format_date(task.get("due_date"))
        date_created = self._format_date(task.get("date_created"))
        date_updated = self._format_date(task.get("date_updated"))
        custom_fields_text, custom_fields_meta = self._extract_custom_fields(task)

        content = (
            f"Tarea: {task.get('name', '')}\n"
            f"Estado: {task.get('status', {}).get('status', 'desconocido')}\n"
            f"Prioridad: {task.get('priority', {}).get('priority', 'sin prioridad') if task.get('priority') else 'sin prioridad'}\n"
            f"Asignado a: {assignees}\n"
            f"Fecha de inicio: {start_date}\n"
            f"Fecha de vencimiento: {due_date}\n"
            f"Creado el: {date_created}\n"
            f"Última actualización: {date_updated}\n"
            f"Campos personalizados:\n{custom_fields_text}\n"
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
                "start_date": start_date,
                "due_date": due_date,
                "date_created": date_created,
                "date_updated": date_updated,
                **custom_fields_meta,
            },
        )

    # ------------------------------------------------------------------
    # Historial de campos
    # ------------------------------------------------------------------

    # Campos de interés para seguimiento histórico
    CAMPOS_HISTORICO = {
        "salud general", "salud cronograma", "salud presupuesto",
        "salud recursos", "salud calidad", "salud alcance",
        "relación cliente", "relacion cliente",
        "presupuesto delta", "presupuesto aprobado",
        "csat", "horas consumidas", "horas presupuestadas",
    }

    def _get_task_history(self, task_id: str) -> list[dict]:
        return self._get(f"task/{task_id}/activity").get("history", [])

    def _parse_history_entry(self, entry: dict) -> dict | None:
        """Extrae un registro legible de un evento de historial de ClickUp.

        Retorna None si el campo no está en CAMPOS_HISTORICO o no tiene valores.
        """
        field_name = (
            (entry.get("custom_field") or {}).get("name")
            or entry.get("field", "")
        ).strip()

        if field_name.lower() not in self.CAMPOS_HISTORICO:
            return None

        def _resolve(raw) -> str:
            if raw is None:
                return "—"
            if isinstance(raw, dict):
                # Dropdown resuelto: puede venir en 'status', 'name' o 'value'
                return (
                    raw.get("status")
                    or raw.get("name")
                    or raw.get("value")
                    or str(raw)
                )
            return str(raw)

        before = _resolve(entry.get("before"))
        after = _resolve(entry.get("after"))

        if before == after:
            return None

        user = (entry.get("user") or {}).get("username", "desconocido")
        date = self._format_date(entry.get("date"))

        return {
            "campo": field_name,
            "antes": before,
            "después": after,
            "fecha": date,
            "usuario": user,
        }

    def get_field_history(
        self,
        project_name: str,
        campos: set[str] | None = None,
        ultimos_n: int = 5,
    ) -> list[dict]:
        """Recupera el historial de cambios de campos de salud y financieros
        para todas las tareas de tipo Control que coincidan con `project_name`.

        Args:
            project_name: nombre parcial del proyecto a buscar.
            campos: subconjunto de CAMPOS_HISTORICO a filtrar. None = todos.
            ultimos_n: cuántos cambios recientes retornar por campo.
        """
        filtro = {c.lower() for c in campos} if campos else self.CAMPOS_HISTORICO
        events: list[dict] = []

        for team in self._get_teams():
            for space in self._get_spaces(team["id"]):
                for lst in self._get_all_lists(space["id"]):
                    for task in self._get_tasks(lst["id"]):
                        # Solo tareas del proyecto buscado
                        if project_name.lower() not in task.get("name", "").lower():
                            # También buscar en el nombre de la lista/folder
                            list_name = lst.get("name", "")
                            folder_name = lst.get("folder_name", "")
                            location = f"{folder_name} {list_name}".lower()
                            if project_name.lower() not in location:
                                continue

                        # Solo ítems de tipo Control
                        tipo = ""
                        for cf in task.get("custom_fields", []):
                            if cf.get("name", "").lower() == "tipo de item":
                                tipo = self._parse_custom_field_value(cf) or ""
                                break
                        if tipo.lower() not in ("control", ""):
                            continue

                        for entry in self._get_task_history(task["id"]):
                            parsed = self._parse_history_entry(entry)
                            if parsed and parsed["campo"].lower() in filtro:
                                parsed["tarea"] = task.get("name", "")
                                parsed["url"]   = task.get("url", "")
                                events.append(parsed)

        # Ordenar por fecha descendente y limitar
        events.sort(key=lambda e: e["fecha"], reverse=True)
        return events[:ultimos_n]

    # ------------------------------------------------------------------
    # BaseIntegration interface
    # ------------------------------------------------------------------

    def fetch_documents(self, since=None) -> list[Document]:
        """Recupera tareas de ClickUp.

        Args:
            since: datetime opcional — filtra tareas actualizadas después de esta fecha.
        """
        docs = []
        for team in self._get_teams():
            for space in self._get_spaces(team["id"]):
                for lst in self._get_lists(space["id"]):
                    for task in self._get_tasks(lst["id"], since=since):
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
