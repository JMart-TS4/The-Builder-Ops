import os
import re
import uuid
import streamlit as st
from services.chat_service import ChatService
from services.document_service import DocumentService
from services.integration_service import IntegrationService

_GDRIVE_TOKEN_PATH = "credentials/gdrive_token.json"

MOCK_USER = {
    "name": "Jhonny",
    "email": "jhonny@thebuilder.com",
    "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=Jhonny&backgroundColor=1D4ED8&textColor=ffffff",
}


def _user_id_from_email(email: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", email.lower())


def _new_conversation() -> dict:
    """Crea una nueva conversación vacía."""
    return {
        "id": str(uuid.uuid4()),
        "title": "Sin título...",
        "messages": [],
    }


def init_session() -> None:
    """Inicializa el estado de sesión de Streamlit."""

    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = "anthropic"

    if "chat_service" not in st.session_state:
        st.session_state.chat_service = ChatService(
            provider=st.session_state.llm_provider
        )

    if "current_user" not in st.session_state:
        st.session_state.current_user = MOCK_USER

    if "user_id" not in st.session_state:
        st.session_state.user_id = _user_id_from_email(
            st.session_state.current_user["email"]
        )

    if "doc_service" not in st.session_state:
        user_id = st.session_state.user_id
        integration_svc = IntegrationService(
            google_access_token="from_file" if os.path.exists(_GDRIVE_TOKEN_PATH) else None,
            clickup_user_id=user_id,
        )
        st.session_state.doc_service = DocumentService(integration_svc, user_id)

    if "conversations" not in st.session_state:
        first = _new_conversation()
        st.session_state.conversations = [first]
        st.session_state.active_id = first["id"]


def get_active_conversation() -> dict:
    """Retorna la conversación activa."""
    for conv in st.session_state.conversations:
        if conv["id"] == st.session_state.active_id:
            return conv
    return st.session_state.conversations[0]


def create_new_conversation() -> None:
    """Crea una nueva conversación y la activa."""
    new_conv = _new_conversation()
    st.session_state.conversations.insert(0, new_conv)
    st.session_state.active_id = new_conv["id"]


def switch_conversation(conv_id: str) -> None:
    """Cambia la conversación activa."""
    st.session_state.active_id = conv_id


def update_conversation_title(conv_id: str, first_message: str) -> None:
    """Genera un título corto a partir del primer mensaje del usuario."""
    title = first_message[:40] + "..." if len(first_message) > 40 else first_message
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            conv["title"] = title
            break
