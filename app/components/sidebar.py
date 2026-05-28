import streamlit as st
from app.session import (
    create_new_conversation,
    switch_conversation,
    get_active_conversation,
)

MOCK_USER = {
    "name": "Jhonny",
    "email": "jhonny@thebuilder.com",
    "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=Jhonny&backgroundColor=1D4ED8&textColor=ffffff",
}

def _spacer(px: int = 12) -> None:
    st.markdown(f"<div style='margin-top:{px}px'></div>", unsafe_allow_html=True)

def _section_label(text: str) -> None:
    st.markdown(f"""
        <p style='font-size:0.65rem; color:#3A5070;
        letter-spacing:1.2px; margin:0 0 4px 0;'>{text}</p>
    """, unsafe_allow_html=True)


def render_sidebar() -> None:
    with st.sidebar:

        st.markdown("""
        <style>
        section[data-testid="stSidebar"] > div:first-child {
            overflow-y: auto;
            padding-top: 0 !important;
        }
        section[data-testid="stSidebar"] > div:first-child > div:first-child {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        section[data-testid="stSidebar"] .stMarkdown:first-of-type {
            margin-top: 0 !important;
        }
        [data-testid="stSidebar"] .stButton button[kind="secondary"] {
            font-size: 0.78rem !important;
            padding: 5px 10px !important;
        }
        [data-testid="stSidebar"] .stSelectbox > div > div {
            font-size: 0.78rem !important;
            min-height: 34px !important;
        }
        [data-testid="stSidebar"] .stButton button[kind="primary"] {
            padding: 6px 10px !important;
            font-size: 0.8rem !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # ── Selector de modelo ───────────────────────
        _section_label("MODELO")
        _spacer(4)

        provider = st.selectbox(
            label="Proveedor",
            options=["anthropic", "gemini"],
            index=0 if st.session_state.llm_provider == "anthropic" else 1,
            format_func=lambda x: "Claude (Anthropic)" if x == "anthropic" else "Gemini (Google)",
            label_visibility="collapsed",
        )

        if provider != st.session_state.llm_provider:
            st.session_state.llm_provider = provider
            st.session_state.chat_service.change_provider(provider)
            st.rerun()

        _spacer(8)

        if st.button("Nueva conversación", use_container_width=True, type="primary"):
            create_new_conversation()
            st.rerun()

        _spacer(8)
        st.divider()
        _spacer(4)

        # ── Conversaciones ───────────────────────────
        _section_label("CONVERSACIONES")
        _spacer(4)

        active_conv = get_active_conversation()

        for conv in st.session_state.conversations:
            is_active = conv["id"] == active_conv["id"]
            if is_active:
                st.markdown(f"""
                    <div style='
                        background: linear-gradient(135deg,
                            rgba(29,78,216,0.35), rgba(59,130,246,0.2));
                        border: 1px solid rgba(59,130,246,0.5);
                        border-radius: 8px;
                        padding: 6px 10px;
                        margin-bottom: 4px;
                        color: #93C5FD;
                        font-size: 0.78rem;
                        font-weight: 600;
                    '>&nbsp;&nbsp;{conv["title"]}</div>
                """, unsafe_allow_html=True)
            else:
                if st.button(
                    f"   {conv['title']}",
                    key=f"conv_{conv['id']}",
                    use_container_width=True,
                    type="secondary",
                ):
                    switch_conversation(conv["id"])
                    st.rerun()

        # ── Perfil ───────────────────────────────────
        _spacer(12)
        st.divider()
        _spacer(6)

        user = st.session_state.get("current_user", MOCK_USER)

        col_avatar, col_info = st.columns([1, 4])
        with col_avatar:
            st.image(user["avatar"], width=34)
        with col_info:
            st.markdown(f"""
                <div style='line-height:1.3; padding-top:2px;'>
                    <div style='font-size:0.78rem; font-weight:600;
                        color:#E8EEF8;'>{user["name"]}</div>
                    <div style='font-size:0.68rem; color:#3A5070;
                        overflow:hidden; text-overflow:ellipsis;
                        white-space:nowrap;'>{user["email"]}</div>
                </div>
            """, unsafe_allow_html=True)

        _spacer(8)

        if st.button("🚪  Cerrar sesión", use_container_width=True, key="logout_btn"):
            st.session_state.clear()
            st.rerun()
