from langchain_core.tools import tool

_SEPARADOR = "─" * 60

_SALUDO_CORREO = "{destinatario},"
_CIERRE_CORREO = "Quedo disponible para cualquier consulta.\n\nAtentamente,"


def make_communication_tools() -> list:
    """Crea herramientas LangChain para redactar correos y mensajes para clientes."""

    @tool
    def crear_correo_cliente(
        destinatario: str,
        asunto: str,
        cuerpo: str,
        remitente: str = "",
    ) -> str:
        """Genera una plantilla de correo electrónico ejecutivo lista para enviar.

        Úsala DESPUÉS de consultar la información relevante en Drive o ClickUp,
        cuando el usuario pida redactar, preparar o crear un correo para un cliente.

        El correo siempre usa tono ejecutivo: directo, conciso, sin emojis y profesional.

        Args:
            destinatario: Nombre o empresa a quien va dirigido el correo.
            asunto: Línea de asunto del correo. Debe ser clara y directa.
            cuerpo: Contenido principal del correo con la información ya redactada.
                    Debe ser conciso, sin relleno y orientado al cliente.
                    Evita emojis, frases de relleno y lenguaje informal.
            remitente: Nombre del remitente. Dejar vacío si no se especifica.
        """
        saludo = _SALUDO_CORREO.format(destinatario=destinatario)
        firma  = f"\n{remitente}" if remitente else ""

        plantilla = (
            f"PLANTILLA DE CORREO\n"
            f"{_SEPARADOR}\n"
            f"Para: {destinatario}\n"
            f"Asunto: {asunto}\n"
            f"{_SEPARADOR}\n\n"
            f"{saludo}\n\n"
            f"{cuerpo}\n\n"
            f"{_CIERRE_CORREO}{firma}\n"
            f"{_SEPARADOR}"
        )
        return plantilla

    @tool
    def crear_mensaje_cliente(
        destinatario: str,
        contenido: str,
        canal: str = "general",
    ) -> str:
        """Genera un mensaje corto y profesional para enviar a un cliente por WhatsApp,
        Slack, Teams u otro canal de mensajería.

        Úsala DESPUÉS de consultar la información relevante en Drive o ClickUp,
        cuando el usuario pida redactar un mensaje, actualización rápida o notificación
        para un cliente (no un correo formal).

        Args:
            destinatario: Nombre o empresa destinataria del mensaje.
            contenido: Texto principal del mensaje con la información a comunicar.
                       Debe ser directo, sin emojis y profesional.
            canal: Canal de envío. Opciones: "whatsapp", "slack", "teams", "general"
                   (por defecto).
        """
        canal_l = canal.lower()

        if canal_l in ("slack", "teams"):
            encabezado = f"@{destinatario}"
        else:
            encabezado = f"{destinatario},"

        pie = "Quedamos a su disposición ante cualquier consulta."

        plantilla = (
            f"MENSAJE PARA CLIENTE (via {canal.capitalize()})\n"
            f"{_SEPARADOR}\n"
            f"{encabezado}\n\n"
            f"{contenido}\n\n"
            f"{pie}\n"
            f"{_SEPARADOR}"
        )
        return plantilla

    return [crear_correo_cliente, crear_mensaje_cliente]
