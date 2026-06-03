from langchain_core.tools import tool

_TONOS_CORREO = {
    "formal": {
        "saludo": "Estimado/a {destinatario}",
        "cierre": "Quedo a su disposición para cualquier consulta.\n\nAtentamente,",
    },
    "amigable": {
        "saludo": "Hola {destinatario}",
        "cierre": "Cualquier duda, con gusto te ayudo.\n\n¡Saludos!",
    },
    "ejecutivo": {
        "saludo": "{destinatario}",
        "cierre": "Quedo disponible.\n\nSaludos,",
    },
}

_SEPARADOR = "─" * 60


def make_communication_tools() -> list:
    """Crea herramientas LangChain para redactar correos y mensajes para clientes."""

    @tool
    def crear_correo_cliente(
        destinatario: str,
        asunto: str,
        cuerpo: str,
        tono: str = "formal",
        remitente: str = "",
    ) -> str:
        """Genera una plantilla de correo electrónico profesional lista para enviar.

        Úsala DESPUÉS de consultar la información relevante en Drive o ClickUp,
        cuando el usuario pida redactar, preparar o crear un correo para un cliente.

        Args:
            destinatario: Nombre o empresa a quien va dirigido el correo.
            asunto: Línea de asunto del correo.
            cuerpo: Contenido principal del correo con la información ya redactada.
                    Incluye todos los puntos, datos o actualizaciones necesarios.
            tono: Tono del correo. Opciones: "formal" (por defecto), "amigable", "ejecutivo".
            remitente: Nombre del remitente. Dejar vacío si no se especifica.
        """
        estilo = _TONOS_CORREO.get(tono.lower(), _TONOS_CORREO["formal"])
        saludo = estilo["saludo"].format(destinatario=destinatario)
        cierre = estilo["cierre"]
        firma  = f"\n{remitente}" if remitente else ""

        plantilla = (
            f"📧 **PLANTILLA DE CORREO**\n"
            f"{_SEPARADOR}\n"
            f"**Para:** {destinatario}\n"
            f"**Asunto:** {asunto}\n"
            f"{_SEPARADOR}\n\n"
            f"{saludo},\n\n"
            f"{cuerpo}\n\n"
            f"{cierre}{firma}\n"
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
            canal: Canal de envío. Opciones: "whatsapp", "slack", "teams", "general"
                   (por defecto). Ajusta el tono y formato del mensaje.
        """
        canal_l = canal.lower()

        if canal_l == "whatsapp":
            encabezado = f"Hola {destinatario} 👋"
            pie        = "_Quedamos atentos ante cualquier consulta._"
        elif canal_l in ("slack", "teams"):
            encabezado = f"Hola @{destinatario}"
            pie        = "Cualquier duda, avísanos."
        else:
            encabezado = f"Hola {destinatario},"
            pie        = "Quedamos a tu disposición."

        plantilla = (
            f"💬 **MENSAJE PARA CLIENTE** *(vía {canal.capitalize()})*\n"
            f"{_SEPARADOR}\n"
            f"{encabezado}\n\n"
            f"{contenido}\n\n"
            f"{pie}\n"
            f"{_SEPARADOR}"
        )
        return plantilla

    return [crear_correo_cliente, crear_mensaje_cliente]
