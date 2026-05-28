import streamlit as st


def apply_styles() -> None:
    st.markdown("""
    <style>
    /* ── Fuente y fondo global ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A0F1E 0%, #0D1A2E 100%);
        border-right: 1px solid #1A2A42;
    }

    /* ── Botón primario (Nueva conversación) ── */
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #1D4ED8, #3B82F6);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.25s ease;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.3);
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2563EB, #60A5FA);
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
        transform: translateY(-1px);
    }

    /* ── Botones de conversación ── */
    [data-testid="stSidebar"] .stButton button[kind="secondary"] {
        background: rgba(255,255,255,0.03);
        color: #8AAAC8;
        border: 1px solid #1E3050;
        border-radius: 8px;
        text-align: left;
        font-size: 0.85rem;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
        background: rgba(59, 130, 246, 0.12);
        border-color: #3B82F6;
        color: #93C5FD;
        transform: translateX(3px);
    }

    /* ── Botón Cerrar sesión ── */
    [data-testid="stSidebar"] .stButton button[key="logout_btn"],
    [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:last-of-type {
        background: rgba(220, 80, 96, 0.08) !important;
        color: #E07A88 !important;
        border: 1px solid rgba(220, 80, 96, 0.35) !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] .stButton button[key="logout_btn"]:hover {
        background: rgba(220, 80, 96, 0.18) !important;
        border-color: rgba(220, 80, 96, 0.65) !important;
        color: #FF8FA0 !important;
    }

    /* ── Selectbox de modelo ── */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid #1E3255 !important;
        border-radius: 8px !important;
        color: #8AAAC8 !important;
        font-size: 0.78rem !important;
        min-height: 34px !important;
    }
    [data-testid="stSidebar"] .stSelectbox > div > div:hover {
        border-color: #3B82F6 !important;
    }

    /* ── Mensajes del chat ── */
    [data-testid="stChatMessage"] {
        background: #0F1828;
        border: 1px solid #1E3050;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
        transition: border-color 0.2s ease;
    }
    [data-testid="stChatMessage"]:hover {
        border-color: #2A4470;
    }

    /* ── Título principal ── */
    h1 {
        background: linear-gradient(135deg, #3B82F6, #0EA5E9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }

    /* ── Layout general sin padding innecesario ── */
    .main .block-container {
        padding: 0 1.5rem 90px 1.5rem !important;
        max-width: 100% !important;
    }

    .main .block-container {
        padding-bottom: 90px !important;
    }

    /* ── Mensajes del usuario alineados a la derecha ── */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
    [data-testid="stChatMessage"]:has(.stChatMessageUser) {
        flex-direction: row-reverse !important;
        text-align: right !important;
        background: rgba(59, 130, 246, 0.08) !important;
        border-left: none !important;
        border-right: 2px solid #3B82F6 !important;
        margin-left: 15% !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stChatMessageContent"] {
        align-items: flex-end !important;
    }

    /* ── Mensajes del asistente con límite de ancho ── */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarBot"]) {
        margin-right: 15% !important;
    }

    /* ── Chat input fijo al fondo ── */
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 0 !important;
        left: var(--sidebar-width, 21rem) !important;
        right: 0 !important;
        z-index: 999 !important;
        background: #0A0F1E !important;
        border: none !important;
        box-shadow: none !important;
        padding: 12px 1.5rem 16px !important;
    }
    [data-testid="stChatInput"] > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    [data-testid="stChatInput"] textarea {
        background: #0F1828 !important;
        border: 1px solid #1E3A60 !important;
        border-radius: 12px !important;
        color: #E8EEF8 !important;
        font-size: 0.95rem !important;
        padding: 10px 16px !important;
        box-shadow: none !important;
        outline: none !important;
        resize: none !important;
        line-height: 1.5 !important;
        min-height: 44px !important;
        max-height: 120px !important;
        overflow-y: auto !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
    }

    /* ── Ocultar elementos de Streamlit innecesarios ── */
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    /* ── Ocultar botón de colapso de la barra lateral ── */
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #0A0F1E; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(#1D4ED8, #0EA5E9);
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)
