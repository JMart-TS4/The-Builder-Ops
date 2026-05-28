from typing import Generator
from core.chat.chain import build_chat_chain
from core.chat.memory import clear_session_history
from config.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Orquesta la cadena de chat con soporte de streaming.

    Es la única clase que los componentes de Streamlit deben conocer.
    Encapsula toda la lógica de LangChain detrás de una interfaz simple.
    """

    def __init__(self, provider: str | None = None):
        self.provider = provider
        self.chain = build_chat_chain(provider)
        logger.info(f"ChatService iniciado | proveedor={provider or 'default'}")

    def stream_response(
        self,
        message: str,
        session_id: str,
    ) -> Generator[str, None, None]:
        """Genera la respuesta en chunks para streaming en Streamlit.

        Compatible directamente con st.write_stream().

        Args:
            message: Mensaje del usuario.
            session_id: ID único de la sesión de Streamlit.

        Yields:
            Chunks de texto conforme el LLM los genera.
        """
        config = {"configurable": {"session_id": session_id}}
        logger.info(f"Stream iniciado | session_id={session_id[:8]}...")

        try:
            for chunk in self.chain.stream({"input": message}, config=config):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error en stream | session_id={session_id[:8]}... | {e}")
            yield "Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta de nuevo."

    def clear_history(self, session_id: str) -> None:
        """Limpia el historial de conversación de una sesión."""
        clear_session_history(session_id)
        logger.info(f"Historial limpiado | session_id={session_id[:8]}...")

    def change_provider(self, provider: str) -> None:
        """Cambia el proveedor LLM y reconstruye la cadena.

        Permite al usuario cambiar entre Anthropic y Gemini
        desde la sidebar sin reiniciar la app.
        """
        if provider != self.provider:
            self.provider = provider
            self.chain = build_chat_chain(provider)
            logger.info(f"Proveedor cambiado | nuevo={provider}")