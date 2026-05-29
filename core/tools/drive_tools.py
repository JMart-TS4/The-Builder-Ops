from langchain_core.tools import tool


def make_drive_tools(doc_service) -> list:
    """Crea herramientas LangChain para consultar documentos de Google Drive."""

    @tool
    def consultar_documentos(consulta: str, proyecto: str = "") -> str:
        """Busca información en los documentos de Google Drive (Unidades Compartidas).

        Úsala cuando el usuario pregunte sobre contenido de documentos, propuestas,
        contratos, informes, presentaciones o cualquier archivo almacenado en Drive.

        Args:
            consulta: La pregunta o términos a buscar en los documentos.
            proyecto: Nombre exacto de la Unidad Compartida para filtrar la búsqueda.
                      Deja vacío para buscar en todas las unidades disponibles.
        """
        project_filter = proyecto.strip() or None
        context = doc_service.get_context(consulta, project_filter=project_filter)
        if context == "No se encontró contexto relevante.":
            suffix = f" en el proyecto '{proyecto}'" if proyecto else ""
            return f"No se encontraron documentos relevantes para '{consulta}'{suffix}."
        return context

    return [consultar_documentos]
