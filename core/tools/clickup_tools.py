from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from core.integrations.clickup import ClickUpIntegration


def make_clickup_tools(integration: "ClickUpIntegration") -> list:
    """Construye herramientas LangChain que consultan ClickUp en tiempo real."""

    @tool
    def listar_espacios_y_listas() -> str:
        """Lista todos los espacios de trabajo y sus listas disponibles en el workspace de ClickUp.
        Úsala para conocer la estructura antes de filtrar tareas por lista."""
        try:
            lines: list[str] = []
            for team in integration._get_teams():
                lines.append(f"Equipo: {team.get('name', team['id'])}")
                for space in integration._get_spaces(team["id"]):
                    lines.append(f"  Espacio: {space.get('name', space['id'])}")
                    for lst in integration._get_all_lists(space["id"]):
                        count = lst.get("task_count", "?")
                        folder = lst.get("folder_name", "")
                        prefix = f"    Carpeta: {folder} → Lista:" if folder else "    Lista:"
                        lines.append(
                            f"{prefix} {lst.get('name', lst['id'])} "
                            f"(tareas: {count})"
                        )
            return "\n".join(lines) if lines else "No se encontraron espacios en el workspace."
        except Exception as exc:
            return f"Error al obtener estructura del workspace: {exc}"

    @tool
    def listar_tareas(nombre_lista: str = "", estado: str = "") -> str:
        """Lista tareas de ClickUp con filtros opcionales.

        Parámetros:
        - nombre_lista: nombre (parcial) de la lista a consultar. Dejar vacío para todas.
        - estado: estado a filtrar, p.ej. 'open', 'in progress', 'complete'. Dejar vacío para todos.
        """
        try:
            results: list[str] = []
            for team in integration._get_teams():
                for space in integration._get_spaces(team["id"]):
                    for lst in integration._get_all_lists(space["id"]):
                        if nombre_lista and nombre_lista.lower() not in lst.get("name", "").lower():
                            continue
                        for task in integration._get_tasks(lst["id"]):
                            task_status = task.get("status", {}).get("status", "").lower()
                            if estado and estado.lower() not in task_status:
                                continue
                            assignees = (
                                ", ".join(a.get("username", "") for a in task.get("assignees", []))
                                or "Sin asignar"
                            )
                            priority = (
                                task["priority"].get("priority", "sin prioridad")
                                if task.get("priority")
                                else "sin prioridad"
                            )
                            folder = lst.get("folder_name", "")
                            location = f"{folder}/{lst.get('name', '')}" if folder else lst.get('name', '')
                            due_date = integration._format_date(task.get("due_date"))
                            start_date = integration._format_date(task.get("start_date"))
                            results.append(
                                f"• [{task_status}] {task.get('name', '')} "
                                f"| Prioridad: {priority} "
                                f"| Asignado: {assignees} "
                                f"| Inicio: {start_date} "
                                f"| Vencimiento: {due_date} "
                                f"| Lista: {location} "
                                f"| {task.get('url', '')}"
                            )
            if not results:
                return "No se encontraron tareas con los filtros indicados."
            return f"{len(results)} tarea(s) encontrada(s):\n" + "\n".join(results)
        except Exception as exc:
            return f"Error al listar tareas: {exc}"

    @tool
    def buscar_tarea(consulta: str) -> str:
        """Busca tareas en ClickUp cuyo nombre o descripción contengan la consulta dada.

        Parámetros:
        - consulta: texto a buscar (nombre, descripción o palabras clave)
        """
        try:
            q = consulta.lower()
            results: list[str] = []
            for team in integration._get_teams():
                for space in integration._get_spaces(team["id"]):
                    for lst in integration._get_all_lists(space["id"]):
                        for task in integration._get_tasks(lst["id"]):
                            name = task.get("name", "")
                            desc = task.get("description") or ""
                            if q not in name.lower() and q not in desc.lower():
                                continue
                            task_status = task.get("status", {}).get("status", "")
                            assignees = (
                                ", ".join(a.get("username", "") for a in task.get("assignees", []))
                                or "Sin asignar"
                            )
                            folder = lst.get("folder_name", "")
                            location = f"{folder}/{lst.get('name', '')}" if folder else lst.get('name', '')
                            due_date = integration._format_date(task.get("due_date"))
                            results.append(
                                f"• [{task_status}] {name} "
                                f"| Asignado: {assignees} "
                                f"| Vencimiento: {due_date} "
                                f"| Lista: {location} "
                                f"| {task.get('url', '')}"
                            )
            if not results:
                return f"No se encontraron tareas que coincidan con '{consulta}'."
            return f"Tareas que coinciden con '{consulta}':\n" + "\n".join(results)
        except Exception as exc:
            return f"Error al buscar tarea: {exc}"

    @tool
    def ver_detalle_tarea(nombre_tarea: str) -> str:
        """Obtiene todos los detalles de una tarea: descripción completa, comentarios,
        asignados, estado y prioridad.

        Parámetros:
        - nombre_tarea: nombre exacto o parcial de la tarea a consultar
        """
        try:
            for team in integration._get_teams():
                for space in integration._get_spaces(team["id"]):
                    for lst in integration._get_all_lists(space["id"]):
                        for task in integration._get_tasks(lst["id"]):
                            if nombre_tarea.lower() in task.get("name", "").lower():
                                doc = integration._task_to_document(task)
                                folder = lst.get("folder_name", "")
                                location = f"{folder}/{lst.get('name', '')}" if folder else lst.get('name', '')
                                return (
                                    f"Lista: {location}\n"
                                    f"{doc.content}"
                                    f"URL: {doc.url}"
                                )
            return f"No se encontró ninguna tarea con el nombre '{nombre_tarea}'."
        except Exception as exc:
            return f"Error al obtener detalle de la tarea: {exc}"

    @tool
    def ver_historial_proyecto(
        nombre_proyecto: str,
        campo: str = "",
        ultimos_n: int = 5,
    ) -> str:
        """Muestra el historial de cambios de campos de salud y financieros de un proyecto.

        Úsala cuando el usuario pregunte por la evolución, cambios o historial de:
        salud general, salud cronograma, salud presupuesto, salud recursos, salud calidad,
        salud alcance, relación cliente, CSAT, presupuesto delta, presupuesto aprobado,
        horas consumidas o horas presupuestadas.

        Parámetros:
        - nombre_proyecto: nombre parcial del proyecto o lista a consultar.
        - campo: campo específico a filtrar (opcional). Dejar vacío para ver todos los
          campos de salud y financieros. Ejemplos: "Salud general", "CSAT", "Presupuesto Delta".
        - ultimos_n: cantidad de cambios recientes a mostrar (por defecto 5).
        """
        try:
            campos_filtro = {campo.lower()} if campo.strip() else None
            events = integration.get_field_history(
                project_name=nombre_proyecto,
                campos=campos_filtro,
                ultimos_n=ultimos_n,
            )

            if not events:
                return (
                    f"No se encontraron cambios registrados en campos de salud o "
                    f"financieros para el proyecto '{nombre_proyecto}'."
                )

            lines = [
                f"Últimos {len(events)} cambio(s) en '{nombre_proyecto}':\n"
            ]
            for e in events:
                url_part = f"  | {e['url']}" if e.get("url") else ""
                lines.append(
                    f"• [{e['fecha']}] **{e['campo']}**: {e['antes']} → {e['después']}"
                    f"  | Por: {e['usuario']}  | Tarea: {e['tarea']}{url_part}"
                )
            return "\n".join(lines)

        except Exception as exc:
            return f"Error al recuperar historial: {exc}"

    return [
        listar_espacios_y_listas,
        listar_tareas,
        buscar_tarea,
        ver_detalle_tarea,
        ver_historial_proyecto,
    ]
