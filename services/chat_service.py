from typing import Generator

from core.chat.chain import build_chat_chain
from core.chat.memory import get_session_history, clear_session_history
from config.logging import get_logger

logger = get_logger(__name__)


def _extract_text(value) -> str:
    """Normaliza la salida del agente a un string plano.

    langchain-anthropic puede devolver el output como bloques de contenido
    crudos (list[dict] con 'type'/'text') en lugar de un string directo.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_extract_text(item) for item in value)
    if isinstance(value, dict):
        if value.get("type") == "text":
            return value.get("text", "")
        for key in ("text", "content", "output"):
            if key in value:
                return _extract_text(value[key])
    return str(value)


class ChatService:
    """Orquesta el chat con soporte de streaming, RAG y herramientas de ClickUp/Drive.

    - Sin herramientas: usa una cadena simple (prompt | LLM) con historial y RAG pre-fetched.
    - Con herramientas: usa un AgentExecutor que consulta Drive y ClickUp vía tools.
    """

    def __init__(
        self,
        provider: str | None = None,
        clickup_integration=None,
        doc_service=None,
    ):
        self.provider      = provider
        self._doc_service  = doc_service
        self._chain        = build_chat_chain(provider, with_context=False)
        self._chain_rag    = build_chat_chain(provider, with_context=True)
        self._agent        = None
        self._build_agent(provider, clickup_integration, doc_service)
        logger.info(
            f"ChatService iniciado | proveedor={provider or 'default'} "
            f"| tools={'on' if self._agent else 'off'}"
        )

    @property
    def has_agent(self) -> bool:
        return self._agent is not None

    # ── Inicialización del agente ─────────────────────────────────────────────

    def _build_agent(self, provider, clickup_integration, doc_service) -> None:
        tools = []

        if clickup_integration and clickup_integration.is_authenticated():
            try:
                from core.tools.clickup_tools import make_clickup_tools
                tools.extend(make_clickup_tools(clickup_integration))
            except Exception as exc:
                logger.error(f"No se pudieron cargar herramientas de ClickUp: {exc}")

        if doc_service:
            try:
                from core.tools.drive_tools import make_drive_tools
                tools.extend(make_drive_tools(doc_service))
            except Exception as exc:
                logger.error(f"No se pudieron cargar herramientas de Drive: {exc}")

        if not tools:
            return

        try:
            from core.chat.agent import build_agent_executor
            self._agent = build_agent_executor(provider, tools)
        except Exception as exc:
            logger.error(f"No se pudo inicializar el agente: {exc}")

    # ── API pública ───────────────────────────────────────────────────────────

    def stream_response(
        self,
        message: str,
        session_id: str,
        context: str | None = None,
    ) -> Generator[str, None, None]:
        if self._agent:
            yield from self._stream_agent(message, session_id)
        else:
            yield from self._stream_chain(message, session_id, context)

    def clear_history(self, session_id: str) -> None:
        clear_session_history(session_id)
        logger.info(f"Historial limpiado | session_id={session_id[:8]}...")

    def change_provider(
        self,
        provider: str,
        clickup_integration=None,
        doc_service=None,
    ) -> None:
        if provider == self.provider:
            return
        self.provider     = provider
        self._doc_service = doc_service or self._doc_service
        self._chain       = build_chat_chain(provider, with_context=False)
        self._chain_rag   = build_chat_chain(provider, with_context=True)
        self._agent       = None
        self._build_agent(provider, clickup_integration, self._doc_service)
        logger.info(f"Proveedor cambiado | nuevo={provider}")

    # ── Implementaciones internas ─────────────────────────────────────────────

    def _stream_agent(
        self,
        message: str,
        session_id: str,
    ) -> Generator[str, None, None]:
        """El agente consulta Drive y ClickUp directamente via tools — sin contexto pre-fetched."""
        history      = get_session_history(session_id)
        chat_history = list(history.messages)

        try:
            result = self._agent.invoke(
                {"input": message, "chat_history": chat_history}
            )
            output: str = _extract_text(result.get("output", ""))
            history.add_user_message(message)
            history.add_ai_message(output)
            logger.info(
                f"Agent completado | session_id={session_id[:8]}... "
                f"| output_len={len(output)}"
            )
            yield output
        except Exception as exc:
            logger.error(f"Error en agent | session_id={session_id[:8]}... | {exc}")
            yield "Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta de nuevo."

    def _stream_chain(
        self,
        message: str,
        session_id: str,
        context: str | None,
    ) -> Generator[str, None, None]:
        config  = {"configurable": {"session_id": session_id}}
        has_rag = bool(context and context.strip())
        chain   = self._chain_rag if has_rag else self._chain
        payload = {"input": message}
        if has_rag:
            payload["context"] = context

        logger.info(
            f"Stream iniciado | session_id={session_id[:8]}... "
            f"| rag={'on' if has_rag else 'off'}"
        )

        try:
            for chunk in chain.stream(payload, config=config):
                text = _extract_text(chunk.content)
                if text:
                    yield text
        except Exception as exc:
            logger.error(f"Error en stream | session_id={session_id[:8]}... | {exc}")
            yield "Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta de nuevo."
