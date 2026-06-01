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
/* ── Hide sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Layout: narrow centered column ── */
.main .block-container {
    max-width: 340px !important;
    padding: 0 1rem !important;
    margin: 0 auto !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 100vh;
}

/* ── Header ── */
.login-header {
    text-align: center;
    margin-bottom: 44px;
}
.login-brand {
    font-size: 0.5rem;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #1A2E48;
    margin: 0 0 12px;
}
.login-title {
    font-size: 2.6rem;
    font-weight: 700;
    margin: 0 0 10px;
    line-height: 1;
    background: linear-gradient(135deg, #3B82F6, #0EA5E9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
}
.login-sub {
    font-size: 0.7rem;
    color: #2E4860;
    margin: 0;
    letter-spacing: 0.2px;
}

/* ── Section label ── */
.section-label {
    font-size: 0.5rem;
    font-weight: 600;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #1A2E48;
    margin: 0 0 10px;
}

/* ── Card: two-line info left, pill right ── */
.yilo-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #0C1522;
    border: 1px solid #162336;
    border-radius: 8px;
    padding: 13px 14px;
    margin-bottom: 20px;
    transition: border-color 0.2s ease;
}
.yilo-card.done   { border-color: rgba(34,197,94,0.3); }
.yilo-card.locked { opacity: 0.3; pointer-events: none; }

.card-info { display: flex; align-items: center; gap: 11px; }
.card-info img { opacity: 0.65; flex-shrink: 0; }

.card-service {
    font-size: 0.8rem;
    font-weight: 500;
    color: #7A9BBD;
    margin: 0 0 2px;
    line-height: 1;
}
.card-desc {
    font-size: 0.62rem;
    color: #253A52;
    margin: 0;
    line-height: 1;
}
.card-desc.ok { color: rgba(34,197,94,0.7); }

/* ── Pill buttons ── */
.yilo-btn {
    display: inline-block;
    padding: 5px 11px;
    border-radius: 5px;
    font-size: 0.68rem;
    font-weight: 500;
    text-decoration: none;
    white-space: nowrap;
    flex-shrink: 0;
    transition: background 0.15s ease;
    letter-spacing: 0.1px;
}
.yilo-btn.active {
    background: #1D4ED8;
    color: #D4E4FF !important;
    border: none;
}
.yilo-btn.active:hover { background: #2563EB; color: #fff !important; }
.yilo-btn.done-btn {
    background: transparent;
    color: rgba(34,197,94,0.6) !important;
    border: 1px solid rgba(34,197,94,0.15);
    cursor: default;
    pointer-events: none;
}
.yilo-btn.disabled-btn {
    background: transparent;
    color: #1A2E48 !important;
    border: 1px solid #162336;
    cursor: not-allowed;
    pointer-events: none;
}

/* ── Enter button (Streamlit native) ── */
div[data-testid="stButton"] > button[kind="primary"] {
    height: 36px !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    border-radius: 7px !important;
    letter-spacing: 0.3px !important;
    background: #1D4ED8 !important;
    border: none !important;
    box-shadow: none !important;
    color: #D4E4FF !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #2563EB !important;
    color: #fff !important;
}
div[data-testid="stButton"] > button[kind="primary"]:disabled {
    background: transparent !important;
    color: #1A2E48 !important;
    border: 1px solid #162336 !important;
    opacity: 1 !important;
}
</style>
"""


def _auth_link(label: str, url: str) -> str:
    return f"<a href='{url}' target='_self' class='yilo-btn active'>{label}</a>"


def _done_link(label: str) -> str:
    return f"<span class='yilo-btn done-btn'>{label}</span>"


def _disabled_link(label: str) -> str:
    return f"<span class='yilo-btn disabled-btn'>{label}</span>"


def _handle_callback() -> None:
    """Detect OAuth callbacks in query params and exchange the code."""

    # ── Pass 2: process a code saved from the previous run ───────────────
    if "_pending_oauth_code" in st.session_state:
        code  = st.session_state.pop("_pending_oauth_code")
        state = st.session_state.pop("_pending_oauth_state", "")

        if state.startswith("google_"):
            with st.spinner("Conectando con Google..."):
                try:
                    user = google_exchange(code)
                    st.session_state.google_connected = True
                    st.session_state.current_user     = user
                    logger.info(f"Google login OK | {user['email']}")
                except Exception as exc:
                    logger.error(f"Google exchange error: {exc}")
                    st.session_state["_oauth_error"] = f"Error al conectar Google: {exc}"
            st.rerun()
            return

        elif state.startswith("clickup_"):
            with st.spinner("Conectando con ClickUp..."):
                try:
                    clickup_exchange(code)
                    st.session_state.clickup_connected = True
                    logger.info("ClickUp login OK")
                except Exception as exc:
                    logger.error(f"ClickUp exchange error: {exc}")
                    st.session_state["_oauth_error"] = f"Error al conectar ClickUp: {exc}"
            st.rerun()
            return

        else:
            logger.warning(f"OAuth callback con state desconocido: {state!r}")
            st.rerun()
            return

    # ── Pass 1: detect incoming redirect and stash the code ──────────────
    error = st.query_params.get("error")
    if error:
        st.query_params.clear()
        st.session_state["_oauth_error"] = f"Autorización denegada: {error}"
        st.rerun()
        return

    code  = st.query_params.get("code")
    state = st.query_params.get("state", "")
    if not code:
        return

    st.session_state["_pending_oauth_code"]  = code
    st.session_state["_pending_oauth_state"] = state
    st.query_params.clear()
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

    # ── Header ────────────────────────────────────────────────────────────
    st.markdown("""
        <div class='login-header'>
            <p class='login-brand'>The Builder Ops</p>
            <h1 class='login-title'>Yilo</h1>
            <p class='login-sub'>El asistente Inteligente de TS4</p>
        </div>
    """, unsafe_allow_html=True)

    # ── Section label ─────────────────────────────────────────────────────
    st.markdown("<p class='section-label'>Conectar cuentas</p>", unsafe_allow_html=True)

    # ── Paso 1 — Google ───────────────────────────────────────────────────
    g_class = "yilo-card done" if is_google else "yilo-card"
    g_desc  = (
        f"<p class='card-desc ok'>conectado como {user.get('name', '—')}</p>"
        if is_google else "<p class='card-desc'>identidad · Drive</p>"
    )
    g_btn = _done_link("✓") if is_google else _auth_link("Conectar", google_auth_url())

    st.markdown(f"""
        <div class='{g_class}'>
            <div class='card-info'>
                <img src='https://www.google.com/favicon.ico' width='15' style='border-radius:2px;'/>
                <div class='card-text'>
                    <p class='card-service'>Google</p>
                    {g_desc}
                </div>
            </div>
            {g_btn}
        </div>
    """, unsafe_allow_html=True)

    # ── Paso 2 — ClickUp ──────────────────────────────────────────────────
    cu_class = "yilo-card done" if is_clickup else ("yilo-card" if is_google else "yilo-card locked")
    cu_desc  = (
        "<p class='card-desc ok'>conectado</p>"
        if is_clickup else "<p class='card-desc'>gestión de tareas</p>"
    )
    if is_clickup:
        cu_btn = _done_link("✓")
    elif is_google:
        cu_btn = _auth_link("Conectar", clickup_auth_url())
    else:
        cu_btn = _disabled_link("Conectar")

    st.markdown(f"""
        <div class='{cu_class}'>
            <div class='card-info'>
                <img src='https://clickup.com/favicon.ico' width='15' style='border-radius:2px;'/>
                <div class='card-text'>
                    <p class='card-service'>ClickUp</p>
                    {cu_desc}
                </div>
            </div>
            {cu_btn}
        </div>
        <div style='height:22px'></div>
    """, unsafe_allow_html=True)

    # ── Entrar ────────────────────────────────────────────────────────────
    both_done = is_google and is_clickup
    if st.button(
        "Entrar →",
        use_container_width=True,
        type="primary",
        key="btn_enter",
        disabled=not both_done,
    ):
        st.session_state.authenticated = True
        st.rerun()
