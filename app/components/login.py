import streamlit as st

from core.auth.google_oauth import (
    get_auth_url  as google_auth_url,
    exchange_code as google_exchange,
    is_authenticated as google_is_authenticated,
    get_user_info as google_get_user_info,
)
from core.auth.clickup_oauth import (
    get_auth_url  as clickup_auth_url,
    exchange_code as clickup_exchange,
    is_authenticated as clickup_is_authenticated,
)
from config.logging import get_logger

logger = get_logger(__name__)

_LOGIN_CSS = """
<style>
/* ── Hide sidebar on the login page ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Center the login card ── */
.main .block-container {
    max-width: 460px !important;
    padding: 48px 2rem 40px !important;
    margin: 0 auto !important;
}

/* ── Step cards ── */
.yilo-card {
    background: linear-gradient(135deg, #0F1828 0%, #0D1A2E 100%);
    border: 1px solid #1E3050;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 10px;
    transition: border-color 0.3s ease, background 0.3s ease;
}
.yilo-card.done {
    border-color: rgba(34,197,94,0.55);
    background: linear-gradient(135deg, rgba(34,197,94,0.06) 0%, #0D1A2E 100%);
}
.yilo-card.locked { opacity: 0.45; }

.step-label {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #3A5070;
    margin-bottom: 8px;
}
.card-title {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 6px;
}
.card-title span { color: #C8D8F0; font-size: 0.88rem; font-weight: 500; }
.status-ok   { color: #22C55E; font-size: 0.8rem; font-weight: 500; }
.status-idle { color: #3A5070; font-size: 0.8rem; }

/* ── OAuth anchor buttons ── */
.yilo-btn {
    display: block;
    width: 100%;
    text-align: center;
    padding: 9px 0;
    border-radius: 10px;
    font-size: 0.88rem;
    font-weight: 600;
    text-decoration: none;
    margin-bottom: 4px;
    box-sizing: border-box;
    transition: all 0.25s ease;
}
.yilo-btn.active {
    background: linear-gradient(135deg, #6C3FD4, #9B6DFF);
    color: #fff !important;
    border: none;
    box-shadow: 0 0 14px rgba(108,63,212,0.35);
}
.yilo-btn.active:hover {
    background: linear-gradient(135deg, #7C4FE4, #AF8DFF);
    box-shadow: 0 0 24px rgba(108,63,212,0.55);
    transform: translateY(-1px);
}
.yilo-btn.done-btn {
    background: rgba(34,197,94,0.1);
    color: #22C55E !important;
    border: 1px solid rgba(34,197,94,0.3);
    cursor: default;
    pointer-events: none;
}
.yilo-btn.disabled-btn {
    background: rgba(30,48,80,0.6);
    color: #3A5070 !important;
    border: 1px solid #1E3050;
    cursor: not-allowed;
    pointer-events: none;
}
.yilo-btn.enter {
    padding: 11px 0;
    font-size: 0.95rem;
    margin-top: 6px;
}
</style>
"""


def _auth_link(label: str, url: str) -> str:
    """Return an active OAuth button as an HTML anchor (same-tab navigation)."""
    return (
        f"<a href='{url}' target='_self' class='yilo-btn active'>{label}</a>"
    )


def _done_link(label: str) -> str:
    return f"<div class='yilo-btn done-btn'>{label}</div>"


def _disabled_link(label: str) -> str:
    return f"<div class='yilo-btn disabled-btn'>{label}</div>"


def _handle_callback() -> None:
    """Detect OAuth callbacks in query params and exchange the code."""
    code  = st.query_params.get("code")
    state = st.query_params.get("state", "")
    error = st.query_params.get("error")

    if error:
        st.query_params.clear()
        st.session_state["_oauth_error"] = f"Autorización denegada: {error}"
        st.rerun()

    if not code:
        return

    st.query_params.clear()

    if state.startswith("google_"):
        try:
            user = google_exchange(code)
            st.session_state.google_connected = True
            st.session_state.current_user     = user
            logger.info(f"Google login OK | {user['email']}")
        except Exception as exc:
            logger.error(f"Google exchange error: {exc}")
            st.session_state["_oauth_error"] = f"Error al conectar Google: {exc}"
        st.rerun()

    elif state.startswith("clickup_"):
        try:
            clickup_exchange(code)
            st.session_state.clickup_connected = True
            logger.info("ClickUp login OK")
        except Exception as exc:
            logger.error(f"ClickUp exchange error: {exc}")
            st.session_state["_oauth_error"] = f"Error al conectar ClickUp: {exc}"
        st.rerun()


def _init_from_disk() -> None:
    """Restore auth state from saved token files on the first render."""
    if "google_connected" not in st.session_state:
        st.session_state.google_connected = google_is_authenticated()
        if st.session_state.google_connected:
            info = google_get_user_info()
            if info:
                st.session_state.current_user = info

    if "clickup_connected" not in st.session_state:
        st.session_state.clickup_connected = clickup_is_authenticated()


# ── Public entry point ────────────────────────────────────────────────────────

def render_login() -> None:
    """
    Full-page login screen.
    Sets st.session_state.authenticated = True when the user clicks
    "Entrar a Yilo" after both services are connected.
    """
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    _handle_callback()
    _init_from_disk()

    is_google  = st.session_state.google_connected
    is_clickup = st.session_state.clickup_connected
    user       = st.session_state.get("current_user", {})

    # ── Error banner ──────────────────────────────────────────────────────
    if err := st.session_state.pop("_oauth_error", None):
        st.error(err)

    # ── Logo + title ──────────────────────────────────────────────────────
    st.markdown("""
        <div style='text-align:center; padding:4px 0 28px;'>
            <div style='font-size:2.8rem; line-height:1;'>🤖</div>
            <h1 style='
                font-size:2.1rem; font-weight:800; margin:10px 0 4px;
                background: linear-gradient(135deg,#6C3FD4,#9B6DFF);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                letter-spacing:-0.5px;
            '>Yilo</h1>
            <p style='color:#3A5070; font-size:0.86rem; margin:0;'>
                Tu asistente empresarial inteligente
            </p>
        </div>
        <p style='color:#8AAAC8;font-size:0.82rem;text-align:center;margin-bottom:18px;'>
            Conecta tus herramientas para comenzar
        </p>
    """, unsafe_allow_html=True)

    # ── Paso 1 — Google ───────────────────────────────────────────────────
    g_class  = "yilo-card done" if is_google else "yilo-card"
    g_status = (
        f"<span class='status-ok'>✓ Conectado como <strong>{user.get('name','')}</strong></span>"
        if is_google else "<span class='status-idle'>No conectado</span>"
    )
    if is_google:
        g_btn = _done_link("✓  Google conectado")
    else:
        g_btn = _auth_link("Continuar con Google", google_auth_url())

    st.markdown(f"""
        <div class='{g_class}'>
            <div class='step-label'>Paso 1</div>
            <div class='card-title'>
                <img src='https://www.google.com/favicon.ico'
                     width='16' style='border-radius:3px;'/>
                <span>Google — Identidad + Drive</span>
            </div>
            {g_status}
        </div>
        {g_btn}
        <div style='height:10px'></div>
    """, unsafe_allow_html=True)

    # ── Paso 2 — ClickUp ──────────────────────────────────────────────────
    cu_class = "yilo-card done" if is_clickup else ("yilo-card" if is_google else "yilo-card locked")
    cu_status = (
        "<span class='status-ok'>✓ Conectado</span>"
        if is_clickup else "<span class='status-idle'>No conectado</span>"
    )
    if is_clickup:
        cu_btn = _done_link("✓  ClickUp conectado")
    elif is_google:
        cu_btn = _auth_link("Conectar ClickUp", clickup_auth_url())
    else:
        cu_btn = _disabled_link("Conectar ClickUp")

    st.markdown(f"""
        <div class='{cu_class}'>
            <div class='step-label'>Paso 2</div>
            <div class='card-title'>
                <img src='https://clickup.com/favicon.ico'
                     width='16' style='border-radius:3px;'/>
                <span>ClickUp — Tareas</span>
            </div>
            {cu_status}
        </div>
        {cu_btn}
        <div style='height:18px'></div>
    """, unsafe_allow_html=True)

    # ── Entrar a Yilo ─────────────────────────────────────────────────────
    both_done = is_google and is_clickup
    if st.button(
        "Entrar a Yilo  →",
        use_container_width=True,
        type="primary",
        key="btn_enter",
        disabled=not both_done,
    ):
        st.session_state.authenticated = True
        st.rerun()
