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
    background: linear-gradient(135deg, rgba(29,78,216,0.25), rgba(59,130,246,0.2));
    border: 1px solid rgba(59,130,246,0.35);
    border-radius: 14px 14px 2px 14px;
    padding: 10px 14px;
    max-width: 72%;
    color: #E8EEF8;
    font-size: 0.95rem;
    line-height: 1.5;
    text-align: left;
"""


def _render_user_message(content: str) -> None:
    """Renderiza un mensaje del usuario alineado a la derecha."""
    st.markdown(
        f"<div style='{USER_BUBBLE_STYLE}'>"
        f"<div style='{USER_MSG_STYLE}'>{content}</div>"
        f"<div style='font-size:1.5rem; margin:10px; align-self:flex-end;'>👤</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_chat() -> None:
    """Renderiza la ventana del chat de la conversación activa."""
    conv = get_active_conversation()

    # ── Mensaje de bienvenida si la conversación está vacía ──
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

        # Mostrar mensaje del usuario inmediatamente
        conv["messages"].append({"role": "user", "content": prompt})
        _render_user_message(prompt)

        # Generar respuesta en streaming
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Yilo está pensando..."):
                response = st.write_stream(
                    st.session_state.chat_service.stream_response(
                        message=prompt,
                        session_id=conv["id"],
                    )
                )

        conv["messages"].append({"role": "assistant", "content": response})