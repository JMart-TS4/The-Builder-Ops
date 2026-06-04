from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool
from core.integrations.clickup import _match_score

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
                        if nombre_lista and _match_score(
                            nombre_lista, lst.get("name", ""), lst.get("folder_name", "")
                        ) == 0:
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
        """Busca tareas en ClickUp cuyo nombre o descripción sean relevantes para la consulta.

        Usa coincidencia por palabras clave: encuentra tareas que contengan al menos
        una de las palabras significativas de la consulta, y las ordena por relevancia.

        Parámetros:
        - consulta: palabras clave o frase a buscar (nombre, proyecto, tipo de ítem, etc.)
        """
        import unicodedata

        def _normalizar(texto: str) -> str:
            """Minúsculas y sin tildes para comparación tolerante."""
            return unicodedata.normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()

        _STOPWORDS = {
            "de", "del", "la", "el", "los", "las", "en", "y", "a", "o", "que",
            "con", "por", "para", "es", "son", "hay", "un", "una", "al", "lo",
            "se", "su", "me", "te", "nos", "si", "no", "más", "mas",
        }

        q_norm = _normalizar(consulta)
        palabras = [p for p in q_norm.split() if len(p) > 2 and p not in _STOPWORDS]

        # Si no quedan palabras útiles, caer a búsqueda exacta de la consulta completa
        if not palabras:
            palabras = [q_norm]

        scored: list[tuple[int, str]] = []

        try:
            for team in integration._get_teams():
                for space in integration._get_spaces(team["id"]):
                    for lst in integration._get_all_lists(space["id"]):
                        for task in integration._get_tasks(lst["id"]):
                            name = task.get("name", "")
                            desc = task.get("description") or ""
                            haystack = _normalizar(name + " " + desc)

                            # Coincidencia exacta de frase → puntuación máxima
                            if q_norm in haystack:
                                score = len(palabras) + 2
                            else:
                                score = sum(1 for p in palabras if p in haystack)

                            if score == 0:
                                continue

                            task_status = task.get("status", {}).get("status", "")
                            assignees = (
                                ", ".join(a.get("username", "") for a in task.get("assignees", []))
                                or "Sin asignar"
                            )
                            folder = lst.get("folder_name", "")
                            location = (
                                f"{folder}/{lst.get('name', '')}" if folder else lst.get("name", "")
                            )
                            due_date = integration._format_date(task.get("due_date"))
                            scored.append((
                                score,
                                f"• [{task_status}] {name} "
                                f"| Asignado: {assignees} "
                                f"| Vencimiento: {due_date} "
                                f"| Lista: {location} "
                                f"| {task.get('url', '')}",
                            ))

            if not scored:
                return f"No se encontraron tareas relacionadas con '{consulta}'."

            scored.sort(key=lambda x: x[0], reverse=True)
            lines = [r[1] for r in scored]
            return f"Tareas relacionadas con '{consulta}' ({len(lines)} resultado(s)):\n" + "\n".join(lines)

        except Exception as exc:
            return f"Error al buscar tarea: {exc}"

    @tool
    def ver_detalle_tarea(nombre_tarea: str) -> str:
        """Obtiene todos los detalles de una tarea: descripción completa, comentarios,
        asignados, estado y prioridad.

        Busca la tarea más parecida al nombre indicado, tolerando tildes y diferencias
        de capitalización.

        Parámetros:
        - nombre_tarea: nombre exacto o parcial de la tarea a consultar
        """
        import unicodedata

        def _normalizar(texto: str) -> str:
            return unicodedata.normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()

        q = _normalizar(nombre_tarea)
        mejor: tuple[int, object, object] | None = None  # (score, task, lst)

        try:
            for team in integration._get_teams():
                for space in integration._get_spaces(team["id"]):
                    for lst in integration._get_all_lists(space["id"]):
                        for task in integration._get_tasks(lst["id"]):
                            name_norm = _normalizar(task.get("name", ""))
                            if q in name_norm:
                                score = len(q)  # mayor longitud coincidente = mejor match
                                if mejor is None or score > mejor[0]:
                                    mejor = (score, task, lst)

            if not mejor:
                return f"No se encontró ninguna tarea con el nombre '{nombre_tarea}'."

            _, task, lst = mejor
            doc = integration._task_to_document(task)
            folder = lst.get("folder_name", "")
            location = f"{folder}/{lst.get('name', '')}" if folder else lst.get("name", "")
            return (
                f"Lista: {location}\n"
                f"{doc.content}"
                f"URL: {doc.url}"
            )
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

    @tool
    def resolver_proyecto(nombre: str) -> str:
        """Encuentra el nombre exacto con el que está registrado un proyecto en ClickUp.

        Úsala SIEMPRE antes de cualquier otra consulta cuando el usuario mencione un
        proyecto específico y no estés seguro de cómo está registrado en ClickUp.

        Resultado:
        - CONFIANZA ALTA → un único ganador claro; úsalo directamente en las siguientes
          herramientas sin preguntar al usuario.
        - MÚLTIPLES COINCIDENCIAS → dos o más candidatos similares; DETENTE,
          presenta las opciones numeradas al usuario y espera que elija antes de continuar.

        Parámetros:
        - nombre: nombre aproximado del proyecto tal como lo mencionó el usuario.
        """
        scored: list[tuple[int, str, str]] = []  # (score, nombre_exacto, ubicacion)

        try:
            for team in integration._get_teams():
                for space in integration._get_spaces(team["id"]):
                    space_name = space.get("name", "")
                    score_space = _match_score(nombre, space_name)
                    if score_space > 0:
                        scored.append((score_space, space_name, f"Espacio: {space_name}"))

                    for lst in integration._get_all_lists(space["id"]):
                        list_name   = lst.get("name", "")
                        folder_name = lst.get("folder_name", "")
                        score_lst   = _match_score(nombre, list_name, folder_name)
                        if score_lst > 0:
                            ubicacion = (
                                f"Carpeta: {folder_name} → Lista: {list_name}"
                                if folder_name else f"Lista: {list_name}"
                            )
                            scored.append((score_lst, list_name, ubicacion))

            if not scored:
                return (
                    f"No se encontró ningún proyecto o lista parecido a '{nombre}' en ClickUp. "
                    "Usa listar_espacios_y_listas para ver todos los proyectos disponibles."
                )

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:5]

            best_score  = top[0][0]
            second_score = top[1][0] if len(top) > 1 else 0

            # Alta confianza: coincidencia exacta de frase, único candidato,
            # o margen de ≥ 3 puntos respecto al segundo mejor.
            high_confidence = (
                best_score == 100
                or len(top) == 1
                or best_score >= second_score + 3
            )

            _, best_name, best_loc = top[0]

            if high_confidence:
                return (
                    f"CONFIANZA ALTA — Proyecto encontrado:\n"
                    f"Nombre exacto: **{best_name}** | {best_loc}\n"
                    f"Usa este nombre en las siguientes herramientas."
                )

            # Múltiples candidatos similares → el agente debe preguntar al usuario
            lines = [
                f"MÚLTIPLES COINCIDENCIAS para '{nombre}'. "
                f"Presenta estas opciones al usuario y espera su elección antes de continuar:\n"
            ]
            for i, (_, exact_name, ubicacion) in enumerate(top, 1):
                lines.append(f"{i}. **{exact_name}** — {ubicacion}")
            return "\n".join(lines)

        except Exception as exc:
            return f"Error al resolver el nombre del proyecto: {exc}"

    @tool
    def consultar_campos_proyecto(
        nombre_proyecto: str,
        tipo_item: str = "",
    ) -> str:
        """Devuelve los campos personalizados (salud, presupuesto, CSAT, riesgos, hitos, etc.)
        de las tareas de un proyecto específico.

        Úsala cuando el usuario pregunte por campos concretos de un proyecto:
        presupuesto, salud general, CSAT, relación con el cliente, riesgos, hitos,
        horas, resumen ejecutivo, severidad, impacto, plan de mitigación, etc.

        IMPORTANTE: usa el nombre exacto devuelto por resolver_proyecto.

        Parámetros:
        - nombre_proyecto: nombre exacto del proyecto tal como está en ClickUp
          (obtenido previamente con resolver_proyecto).
        - tipo_item: filtra por tipo de ítem. Valores válidos:
            "Control"    → salud general, presupuesto, CSAT, horas, resumen ejecutivo
            "Riesgo"     → severidad, probabilidad, impacto, plan de mitigación
            "Hito"       → tipo de hito, fechas, estado de entrega
            "Escalacion" → escalaciones activas, impacto, plan de acción
            "Facturacion"→ datos de facturación
            ""           → devuelve todos los tipos
        """
        resultados: list[str] = []

        try:
            for team in integration._get_teams():
                for space in integration._get_spaces(team["id"]):
                    for lst in integration._get_all_lists(space["id"]):
                        if _match_score(
                            nombre_proyecto,
                            lst.get("name", ""),
                            lst.get("folder_name", ""),
                        ) == 0:
                            continue

                        for task in integration._get_tasks(lst["id"]):
                            # Filtro por Tipo de Item si se especificó
                            if tipo_item:
                                campo_tipo = ""
                                for cf in task.get("custom_fields", []):
                                    if cf.get("name", "").lower() == "tipo de item":
                                        campo_tipo = (
                                            integration._parse_custom_field_value(cf) or ""
                                        )
                                        break
                                if tipo_item.lower() not in campo_tipo.lower():
                                    continue

                            doc = integration._task_to_document(task)
                            resultados.append(
                                f"---\n"
                                f"🔗 Tarea: {task.get('name', '')} | {task.get('url', '')}\n"
                                f"{doc.content}"
                            )

            if not resultados:
                filtro_txt = f" (Tipo de Item: {tipo_item})" if tipo_item else ""
                return (
                    f"No se encontraron tareas para '{nombre_proyecto}'{filtro_txt}. "
                    "Verifica el nombre con resolver_proyecto."
                )

            encabezado = (
                f"{len(resultados)} tarea(s) encontrada(s) en '{nombre_proyecto}'"
                + (f" — Tipo: {tipo_item}" if tipo_item else "")
                + ":\n\n"
            )
            return encabezado + "\n".join(resultados)

        except Exception as exc:
            return f"Error al consultar campos del proyecto: {exc}"

    return [
        listar_espacios_y_listas,
        resolver_proyecto,
        consultar_campos_proyecto,
        listar_tareas,
        buscar_tarea,
        ver_detalle_tarea,
        ver_historial_proyecto,
    ]
