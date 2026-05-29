from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import Runnable

from core.llm.factory import get_llm
from core.chat.memory import get_session_history
from core.chat.prompts import CHAT_PROMPT, CHAT_WITH_CONTEXT_PROMPT
from config.logging import get_logger

logger = get_logger(__name__)


def build_chat_chain(provider: str | None = None, with_context: bool = False) -> Runnable:
    llm = get_llm(provider)
    prompt = CHAT_WITH_CONTEXT_PROMPT if with_context else CHAT_PROMPT
    chain = prompt | llm

    logger.info(f"Cadena de chat construida | proveedor={provider or 'default'} | rag={with_context}")

    return RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )
