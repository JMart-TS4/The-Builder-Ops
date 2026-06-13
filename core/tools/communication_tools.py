from langchain_core.tools import tool


def _coerce_str(value) -> str:
    """Normaliza cualquier valor a string plano (maneja listas/dicts de Anthropic)."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n\n".join(_coerce_str(item) for item in value)
    if isinstance(value, dict):
        return value.get("text", str(value))
    if hasattr(value, "text"):
        return str(value.text)
    return str(value)


def make_communication_tools() -> list:
    """Crea herramientas LangChain para redactar correos y mensajes para clientes."""

    @tool
    def crear_correo_cliente(
        destinatario: str,
        asunto: str,
        cuerpo: str,
        remitente: str = "",
    ) -> str:
        """Genera el contenido de un correo electrónico ejecutivo listo para enviar.

        Usala DESPUES de consultar la informacion relevante en Drive o ClickUp,
        cuando el usuario pida redactar, preparar o crear un correo para un cliente.

        El correo siempre usa tono ejecutivo: directo, conciso, sin emojis y profesional.

        Args:
            destinatario: Nombre o empresa a quien va dirigido el correo.
            asunto: Linea de asunto del correo. Debe ser clara y directa.
            cuerpo: Contenido principal del correo con la informacion ya redactada.
                    Debe ser conciso, sin relleno y orientado al cliente.
            remitente: Nombre del remitente. Dejar vacio si no se especifica.
        """
        destinatario = _coerce_str(destinatario)
        asunto       = _coerce_str(asunto)
        cuerpo       = _coerce_str(cuerpo)
        remitente    = _coerce_str(remitente)

        firma = f"\n\n{remitente}" if remitente else ""

        return (
            f"**Para:** {destinatario}\n\n"
            f"**Asunto:** {asunto}\n\n"
            f"---\n\n"
            f"{destinatario},\n\n"
            f"{cuerpo}\n\n"
            f"Quedo disponible para cualquier consulta.\n\n"
            f"Atentamente,{firma}"
        )

    @tool
    def crear_mensaje_cliente(
        destinatario: str,
        contenido: str,
        canal: str = "general",
    ) -> str:
        """Genera un mensaje corto y profesional para enviar a un cliente por WhatsApp,
        Slack, Teams u otro canal de mensajeria.

        Usala DESPUES de consultar la informacion relevante en Drive o ClickUp,
        cuando el usuario pida redactar un mensaje, actualizacion rapida o notificacion
        para un cliente (no un correo formal).

        Args:
            destinatario: Nombre o empresa destinataria del mensaje.
            contenido: Texto principal del mensaje con la informacion a comunicar.
                       Debe ser directo, sin emojis y profesional.
            canal: Canal de envio. Opciones: "whatsapp", "slack", "teams", "general".
        """
        destinatario = _coerce_str(destinatario)
        contenido    = _coerce_str(contenido)
        canal        = _coerce_str(canal)

        canal_l    = canal.lower()
        encabezado = f"@{destinatario}" if canal_l in ("slack", "teams") else f"{destinatario},"

        return (
            f"**Canal:** {canal.capitalize()}\n\n"
            f"---\n\n"
            f"{encabezado}\n\n"
            f"{contenido}\n\n"
            f"Quedamos a su disposicion ante cualquier consulta."
        )

    return [crear_correo_cliente, crear_mensaje_cliente]
