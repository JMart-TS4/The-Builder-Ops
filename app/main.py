import streamlit as st
from config.logging import setup_logging
from app.styles import apply_styles

st.set_page_config(
    page_title="Yilo — The Builder Ops",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

setup_logging()
apply_styles()

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated", False):
    from app.components.login import render_login
    render_login()
    st.stop()

# ── Main app (only reached when authenticated) ────────────────────────────────
from app.session import init_session
from app.components.sidebar import render_sidebar
from app.components.chat_window import render_chat

init_session()
render_sidebar()
render_chat()
