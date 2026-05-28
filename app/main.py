import streamlit as st
from config.logging import setup_logging
from app.styles import apply_styles
from app.session import init_session
from app.components.sidebar import render_sidebar
from app.components.chat_window import render_chat

# Configuración de la página
st.set_page_config(
    page_title="The Builder Ops - Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializar logging una sola vez
setup_logging()

# Aplicar estilos personalizados
apply_styles()

# Inicializar estado de sesión
init_session()

# Renderizar UI
render_sidebar()
render_chat()