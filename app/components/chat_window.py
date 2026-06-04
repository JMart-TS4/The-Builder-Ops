import markdown as _md_lib
import streamlit as st
from app.session import get_active_conversation, update_conversation_title

# ── Paleta (sincronizada con .streamlit/config.toml) ────────────────────────
# primaryColor            #3B82F6  → rgb(59, 130, 246)
# backgroundColor         #0A0F1E
# secondaryBackgroundColor #0F1828
# textColor               #E8EEF8

_PRIMARY     = "59, 130, 246"   # #3B82F6 — blue  (ClickUp)
_DRIVE_COLOR = "129, 140, 248"  # #818CF8 — indigo (Drive)
_TEXT        = "#E8EEF8"
_MUTED       = "#64748B"
_MUTED_RGB   = "100, 116, 139"

_BOT_AVATAR_HTML = (
    "<div style='"
    "width:28px;height:28px;border-radius:50%;"
    "background:linear-gradient(135deg,rgba(59,130,246,0.2),rgba(59,130,246,0.1));"
    "border:1px solid rgba(59,130,246,0.22);"
    "display:flex;align-items:center;justify-content:center;"
    "font-size:0.82rem;margin-top:2px;flex-shrink:0;"
    "'>🤖</div>"
)

# ── CSS global (inyectado una vez por sesión) ────────────────────────────────
_GLOBAL_CSS = """
<style>
/* Barra de progreso indeterminada */
@keyframes yilo-bar-a {
    0%   { left: -35%;  right: 100%; }
    55%  { left: 100%;  right: -25%; }
    100% { left: 100%;  right: -25%; }
}
@keyframes yilo-bar-b {
    0%   { left: -200%; right: 100%; }
    50%  { left:  10%;  right: -8%;  }
    100% { left: 107%;  right: -8%;  }
}
.yilo-track {
    position: relative;
    height: 2px;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 9px;
}
.yilo-bar-a, .yilo-bar-b {
    position: absolute;
    top: 0; bottom: 0;
    border-radius: 2px;
}
.yilo-bar-a { animation: yilo-bar-a 2s cubic-bezier(.65,.815,.735,.395) infinite; }
.yilo-bar-b { animation: yilo-bar-b 2s cubic-bezier(.165,.84,.44,1) infinite .15s; }
</style>
"""

# ── Mensajes de bienvenida y usuario ────────────────────────────────────────
def _welcome_message() -> str:
    user = st.session_state.get("current_user", {})
    name = user.get("name", "").split()[0] if user.get("name") else ""
    greeting = f"Hola, **{name}**." if name else "Hola."
    return f"""{greeting} Soy **Yilo**, el asistente de visibilidad operativa de TS4.

Estoy conectado en tiempo real a **ClickUp** y **Google Drive**, por lo que puedo darte información actualizada sobre cualquier proyecto del portafolio sin necesidad de consultar múltiples herramientas.

Algunos ejemplos de lo que puedes preguntarme:

- 📊 ¿Cuál es el estado de salud del portafolio esta semana?
- ⚠️ ¿Qué riesgos críticos siguen abiertos en [nombre del proyecto]?
- 📅 ¿Hay hitos próximos que todavía estén pendientes?
- ✉️ Redacta un correo de actualización para el cliente de [proyecto].

¿Con qué proyecto o iniciativa quieres comenzar?"""

USER_BUBBLE_STYLE = "display:flex;justify-content:flex-end;margin-bottom:14px;"

USER_MSG_STYLE = (
    f"background:linear-gradient(135deg,rgba({_PRIMARY},0.18),rgba({_PRIMARY},0.09));"
    f"border:1px solid rgba({_PRIMARY},0.28);"
    "border-radius:14px 14px 2px 14px;"
    "padding:10px 14px;"
    "max-width:72%;"
    f"color:{_TEXT};"
    "font-size:0.95rem;"
    "line-height:1.55;"
    "text-align:left;"
)

BOT_MSG_STYLE = (
    f"background:linear-gradient(135deg,rgba({_MUTED_RGB},0.18),rgba({_MUTED_RGB},0.09));"
    f"border:1px solid rgba({_MUTED_RGB},0.28);"
    "border-radius:4px 14px 14px 14px;"
    "padding:10px 14px;"
    f"color:{_TEXT};"
    "font-size:0.95rem;"
    "line-height:1.55;"
    "display:flow-root;"
    "margin-bottom:14px;"
)

# ── Metadatos de herramientas ────────────────────────────────────────────────
_TOOL_META: dict[str, dict] = {
    "listar_tareas": {
        "label":  "Consultando tareas",
        "source": "ClickUp",
        "rgb":    _PRIMARY,
    },
    "buscar_tarea": {
        "label":  "Buscando tarea",
        "source": "ClickUp",
        "rgb":    _PRIMARY,
    },
    "ver_detalle_tarea": {
        "label":  "Cargando detalle de tarea",
        "source": "ClickUp",
        "rgb":    _PRIMARY,
    },
    "ver_historial_proyecto": {
        "label":  "Consultando historial del proyecto",
        "source": "ClickUp",
        "rgb":    _PRIMARY,
    },
    "listar_espacios_y_listas": {
        "label":  "Explorando estructura del workspace",
        "source": "ClickUp",
        "rgb":    _PRIMARY,
    },
    "resolver_proyecto": {
        "label":  "Buscando proyecto en ClickUp",
        "source": "ClickUp",
        "rgb":    _PRIMARY,
    },
    "consultar_campos_proyecto": {
        "label":  "Consultando campos del proyecto",
        "source": "ClickUp",
        "rgb":    _PRIMARY,
    },
    "consultar_documentos": {
        "label":  "Buscando en documentos",
        "source": "Google Drive",
        "rgb":    _DRIVE_COLOR,
    },
    "crear_correo_cliente": {
        "label":  "Redactando correo",
        "source": "Comunicación",
        "rgb":    "52, 211, 153",
    },
    "crear_mensaje_cliente": {
        "label":  "Redactando mensaje",
        "source": "Comunicación",
        "rgb":    "52, 211, 153",
    },
}


# ── Helpers de visualización ─────────────────────────────────────────────────

def _md_to_html(text: str) -> str:
    return _md_lib.markdown(text, extensions=["tables", "fenced_code"])


def _inject_styles() -> None:
    if not st.session_state.get("_chat_css_injected"):
        st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
        st.session_state["_chat_css_injected"] = True


def _progress_bar(rgb: str) -> str:
    return (
        f"<div class='yilo-track' style='background:rgba({rgb},0.15);'>"
        f"<div class='yilo-bar-a' style='background:rgba({rgb},0.8);'></div>"
        f"<div class='yilo-bar-b' style='background:rgba({rgb},0.8);'></div>"
        f"</div>"
    )


def _thinking_html() -> str:
    return (
        f"<div style='"
        f"background:rgba({_MUTED_RGB},0.07);"
        f"border-radius:6px;"
        f"padding:10px 14px;"
        f"margin:6px 0;"
        f"'>"
        f"{_progress_bar(_MUTED_RGB)}"
        f"<span style='color:{_MUTED};font-size:0.82rem;'>Procesando</span>"
        f"</div>"
    )


def _format_tool_detail(tool_name: str, tool_input) -> str:
    if not isinstance(tool_input, dict):
        return str(tool_input) if tool_input else ""

    if tool_name == "buscar_tarea":
        return tool_input.get("consulta", "")
    if tool_name == "ver_detalle_tarea":
        return tool_input.get("nombre_tarea", "")
    if tool_name == "listar_tareas":
        parts = []
        if v := tool_input.get("nombre_lista"):
            parts.append(f"lista: {v}")
        if v := tool_input.get("estado"):
            parts.append(f"estado: {v}")
        return " · ".join(parts)
    if tool_name == "ver_historial_proyecto":
        parts = [tool_input.get("nombre_proyecto", "")]
        if v := tool_input.get("campo"):
            parts.append(f"campo: {v}")
        return " · ".join(filter(None, parts))
    if tool_name == "consultar_documentos":
        parts = [tool_input.get("consulta", "")]
        if v := tool_input.get("proyecto"):
            parts.append(f"proyecto: {v}")
        return " · ".join(filter(None, parts))
    return ""


def _render_tool_card(tool_name: str, tool_input) -> str:
    meta = _TOOL_META.get(tool_name, {
        "label":  f"Ejecutando {tool_name}",
        "source": "Sistema",
        "rgb":    _MUTED_RGB,
    })
    r      = meta["rgb"]
    detail = _format_tool_detail(tool_name, tool_input)

    detail_html = (
        f"<div style='"
        f"color:{_MUTED};"
        f"font-size:0.76rem;"
        f"font-family:monospace;"
        f"margin-top:4px;"
        f"letter-spacing:0.01em;"
        f"'>{detail}</div>"
    ) if detail else ""

    return (
        f"<div style='"
        f"background:rgba({r},0.07);"
        f"border-radius:6px;"
        f"padding:10px 14px;"
        f"margin:6px 0;"
        f"'>"
        # Barra de progreso animada
        f"{_progress_bar(r)}"
        # Header: source badge
        f"<div style='margin-bottom:4px;'>"
        f"<span style='"
        f"font-size:0.65rem;font-weight:700;letter-spacing:0.1em;"
        f"color:rgba({r},0.85);text-transform:uppercase;"
        f"'>{meta['source']}</span>"
        f"</div>"
        # Label
        f"<div style='color:{_TEXT};font-size:0.88rem;font-weight:500;'>{meta['label']}</div>"
        # Params (monospace, muted)
        f"{detail_html}"
        f"</div>"
    )


def _user_avatar_html() -> str:
    user    = st.session_state.get("current_user", {})
    avatar  = user.get("avatar", "")
    name    = user.get("name", "")
    if avatar:
        return (
            f"<img src='{avatar}' width='28' height='28' "
            f"style='border-radius:50%;object-fit:cover;flex-shrink:0;"
            f"margin-left:8px;align-self:flex-end;margin-bottom:2px;'/>"
        )
    initial = name[0].upper() if name else "?"
    return (
        f"<div style='"
        f"width:28px;height:28px;border-radius:50%;"
        f"background:#1D4ED8;"
        f"display:flex;align-items:center;justify-content:center;"
        f"font-size:0.72rem;font-weight:700;color:#E8EEF8;"
        f"flex-shrink:0;margin-left:8px;align-self:flex-end;margin-bottom:2px;"
        f"'>{initial}</div>"
    )


def _render_assistant_message(content: str) -> None:
    col_av, col_msg = st.columns([1, 16], gap="small")
    with col_av:
        st.markdown(_BOT_AVATAR_HTML, unsafe_allow_html=True)
    with col_msg:
        st.markdown(
            f"<div style='{BOT_MSG_STYLE}'>{_md_to_html(content)}</div>",
            unsafe_allow_html=True,
        )


def _render_user_message(content: str) -> None:
    st.markdown(
        f"<div style='{USER_BUBBLE_STYLE}'>"
        f"<div style='{USER_MSG_STYLE}'>{content}</div>"
        f"{_user_avatar_html()}"
        f"</div>",
        unsafe_allow_html=True,
    )


def _get_context(query: str) -> str | None:
    doc_svc = st.session_state.get("doc_service")
    if not doc_svc:
        return None
    try:
        ctx = doc_svc.get_context(query)
        return ctx if ctx != "No se encontró contexto relevante." else None
    except Exception:
        return None


# ── Render principal ─────────────────────────────────────────────────────────

def render_chat() -> None:
    _inject_styles()
    conv = get_active_conversation()

    if not conv["messages"]:
        col_av, col_msg = st.columns([1, 16], gap="small")
        with col_av:
            st.markdown(_BOT_AVATAR_HTML, unsafe_allow_html=True)
        with col_msg:
            st.markdown(
                f"<div style='{BOT_MSG_STYLE}'>{_md_to_html(_welcome_message())}</div>",
                unsafe_allow_html=True,
            )

    # Historial
    for msg in conv["messages"]:
        if msg["role"] == "user":
            _render_user_message(msg["content"])
        else:
            _render_assistant_message(msg["content"])

    # Input
    if prompt := st.chat_input("Escríbele a Yilo..."):

        if not conv["messages"]:
            update_conversation_title(conv["id"], prompt)

        conv["messages"].append({"role": "user", "content": prompt})
        _render_user_message(prompt)

        chat_svc = st.session_state.chat_service
        context  = None if chat_svc.has_agent else _get_context(prompt)

        col_av, col_msg = st.columns([1, 16], gap="small")
        with col_av:
            st.markdown(_BOT_AVATAR_HTML, unsafe_allow_html=True)
        with col_msg:
            status_area   = st.empty()
            placeholder   = st.empty()
            full_response = ""

            if chat_svc.has_agent:
                status_area.markdown(_thinking_html(), unsafe_allow_html=True)

                for chunk in chat_svc.stream_response(
                    message=prompt,
                    session_id=conv["id"],
                    context=None,
                ):
                    if isinstance(chunk, dict):
                        ctype = chunk["type"]
                        if ctype == "tool_start":
                            status_area.markdown(
                                _render_tool_card(chunk["tool"], chunk["input"]),
                                unsafe_allow_html=True,
                            )
                        elif ctype == "tool_end":
                            status_area.markdown(
                                _thinking_html(), unsafe_allow_html=True
                            )
                        elif ctype == "output":
                            full_response = chunk["text"]
                    else:
                        full_response += chunk
                        placeholder.markdown(full_response + "▌")

                status_area.empty()

            else:
                with st.spinner("Yilo está pensando..."):
                    for chunk in chat_svc.stream_response(
                        message=prompt,
                        session_id=conv["id"],
                        context=context,
                    ):
                        if isinstance(chunk, str):
                            full_response += chunk
                            placeholder.markdown(full_response + "▌")

            placeholder.markdown(
                f"<div style='{BOT_MSG_STYLE}'>{_md_to_html(full_response)}</div>",
                unsafe_allow_html=True,
            )
            response = full_response

        conv["messages"].append({"role": "assistant", "content": response})
