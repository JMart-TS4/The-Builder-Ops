import re
import uuid
from pathlib import Path

import streamlit as st

from services.chat_service import ChatService
from services.document_service import DocumentService
from services.integration_service import IntegrationService
from core.auth.google_oauth import get_user_info as google_get_user_info
from core.auth.clickup_oauth import get_saved_token as clickup_get_token

GDRIVE_TOKEN_PATH  = "credentials/gdrive_token.json"
GOOGLE_USER_PATH   = "credentials/google_user.json"
CLICKUP_TOKEN_PATH = "credentials/clickup_token_login.json"


def _user_id_from_email(email: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", email.lower())


def _new_conversation() -> dict:
    return {"id": str(uuid.uuid4()), "title": "Sin título...", "messages": []}


def _get_clickup_integration():
    """Crea una instancia de ClickUpIntegration con el token guardado, o None."""
    token = clickup_get_token()
    if not token:
        return None
    try:
        from core.integrations.clickup import ClickUpIntegration
        return ClickUpIntegration(user_id="login", access_token=token)
    except Exception:
        return None


def init_session() -> None:
    """Inicializa el estado de sesión de Streamlit tras el login."""

    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = "anthropic"

    # Identidad del usuario (preferir Google OAuth)
    if "current_user" not in st.session_state:
        st.session_state.current_user = google_get_user_info() or {
            "name": "Usuario", "email": "", "avatar": "",
        }

    if "user_id" not in st.session_state:
        email = st.session_state.current_user.get("email", "")
        st.session_state.user_id = _user_id_from_email(email) if email else "default"

    # Integración ClickUp (reutilizable por ChatService y DocumentService)
    if "clickup_integration" not in st.session_state:
        st.session_state.clickup_integration = _get_clickup_integration()

    # DocumentService debe inicializarse ANTES que ChatService para pasarlo como tool
    if "doc_service" not in st.session_state:
        has_drive     = Path(GDRIVE_TOKEN_PATH).exists()
        clickup_token = clickup_get_token()
        user_id       = st.session_state.user_id

        integration = IntegrationService(
            google_access_token=("from_file" if has_drive else None),
            clickup_user_id="login",
            clickup_access_token=clickup_token,
        )
        st.session_state.doc_service = DocumentService(integration, user_id)

    # ChatService — incluye herramientas de ClickUp y Drive si están disponibles
    if "chat_service" not in st.session_state:
        st.session_state.chat_service = ChatService(
            provider=st.session_state.llm_provider,
            clickup_integration=st.session_state.clickup_integration,
            doc_service=st.session_state.doc_service,
        )

    if "conversations" not in st.session_state:
        first = _new_conversation()
        st.session_state.conversations = [first]
        st.session_state.active_id     = first["id"]


# ── Conversation helpers ──────────────────────────────────────────────────────

def get_active_conversation() -> dict:
    for conv in st.session_state.conversations:
        if conv["id"] == st.session_state.active_id:
            return conv
    return st.session_state.conversations[0]


def create_new_conversation() -> None:
    new_conv = _new_conversation()
    st.session_state.conversations.insert(0, new_conv)
    st.session_state.active_id = new_conv["id"]


def switch_conversation(conv_id: str) -> None:
    st.session_state.active_id = conv_id


def update_conversation_title(conv_id: str, first_message: str) -> None:
    title = first_message[:40] + "..." if len(first_message) > 40 else first_message
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            conv["title"] = title
            break


def logout() -> None:
    """Elimina tokens OAuth y limpia la sesión para regresar al login."""
    for path in (GDRIVE_TOKEN_PATH, GOOGLE_USER_PATH, CLICKUP_TOKEN_PATH):
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass
    st.session_state.clear()
