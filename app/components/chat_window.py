import streamlit as st
from app.session import get_active_conversation, update_conversation_title

WELCOME_MESSAGE = """¡Hola! Soy **Yilo**, el asistente inteligente de TS4 👋

Puedo ayudarte con:
- 📂 Consultar documentos y archivos sobre tus proyectos
- ✅ Revisar tareas y proyectos en ClickUp
- 💬 Responder preguntas sobre tu operación

¿En qué te puedo ayudar hoy?"""

USER_BUBBLE_STYLE = """
    display: flex;
    justify-content: flex-end;
    margin-bottom: 14px;
"""

USER_MSG_STYLE = """
    background: linear-gradient(135deg, rgba(108,63,212,0.25), rgba(155,109,255,0.2));
    border: 1px solid rgba(155,109,255,0.35);
    border-radius: 14px 14px 2px 14px;
    padding: 10px 14px;
    max-width: 72%;
    color: #E8E8F0;
    font-size: 0.95rem;
    line-height: 1.5;
    text-align: left;
"""


def _render_user_message(content: str) -> None:
    st.markdown(
        f"<div style='{USER_BUBBLE_STYLE}'>"
        f"<div style='{USER_MSG_STYLE}'>{content}</div>"
        f"<div style='font-size:1.5rem; margin-left:8px; align-self:flex-end;'>👤</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _get_context(query: str) -> str | None:
    """Recupera contexto RAG si el usuario tiene documentos sincronizados."""
    doc_svc = st.session_state.get("doc_service")
    if not doc_svc:
        return None
    try:
        ctx = doc_svc.get_context(query)
        return ctx if ctx != "No se encontró contexto relevante." else None
    except Exception:
        return None


def render_chat() -> None:
    conv = get_active_conversation()

    # ── Mensaje de bienvenida ────────────────────────
    if not conv["messages"]:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(WELCOME_MESSAGE)

    # ── Historial de mensajes ────────────────────────
    for msg in conv["messages"]:
        if msg["role"] == "user":
            _render_user_message(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])

    # ── Input del usuario ────────────────────────────
    if prompt := st.chat_input("Escríbele a Yilo..."):

        if not conv["messages"]:
            update_conversation_title(conv["id"], prompt)

        conv["messages"].append({"role": "user", "content": prompt})
        _render_user_message(prompt)

        # Solo pre-fetch de contexto RAG cuando no hay agente activo.
        # Con agente, Drive se consulta directamente via la tool consultar_documentos.
        chat_svc = st.session_state.chat_service
        context  = None if chat_svc.has_agent else _get_context(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            placeholder = st.empty()
            full_response = ""
            with st.spinner("Yilo está pensando..."):
                for chunk in st.session_state.chat_service.stream_response(
                    message=prompt,
                    session_id=conv["id"],
                    context=context,
                ):
                    full_response += chunk
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            response = full_response

        conv["messages"].append({"role": "assistant", "content": response})