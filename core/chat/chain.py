from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import Runnable

from core.llm.factory import get_llm
from core.chat.memory import get_session_history
from core.chat.prompts import CHAT_PROMPT
from config.logging import get_logger

logger = get_logger(__name__)


def build_chat_chain(provider: str | None = None) -> Runnable:
    """Construye y retorna la cadena de chat con historial.

    La cadena sigue el patrón LCEL (LangChain Expression Language):
        prompt | llm

    RunnableWithMessageHistory inyecta automáticamente el historial
    de la sesión en cada llamada usando session_id.

    Args:
        provider: 'anthropic' | 'gemini' | None (usa default del .env)

    Returns:
        Cadena lista para invocar o hacer streaming.
    """
    llm = get_llm(provider)
    chain = CHAT_PROMPT | llm

    logger.info(f"Cadena de chat construida | proveedor={provider or 'default'}")

    return RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )