from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from config.logging import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────
# Store en memoria (Solo para la demo)
# Escalar: reemplazar por RedisChatMessageHistory
#         o SQLChatMessageHistory sin tocar nada más
# ─────────────────────────────────────────
_session_store: dict[str, BaseChatMessageHistory] = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Retorna el historial de mensajes para una sesión dada.

    Si la sesión no existe, la crea automáticamente.
    Cada usuario de Streamlit tiene su propio session_id único.
    """
    if session_id not in _session_store:
        logger.info(f"Nueva sesión creada | session_id={session_id}")
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]

def clear_session_history(session_id: str) -> None:
    """Limpia el historial de una sesión específica."""
    if session_id in _session_store:
        _session_store.pop(session_id)
        logger.info(f"Sesión eliminada | session_id={session_id}")

def get_active_sessions() -> list[str]:
    """Retorna los IDs de todas las sesiones activas en memoria."""
    return list(_session_store.keys())