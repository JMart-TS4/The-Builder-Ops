#!/bin/bash
# Ejecutar desde la raíz del proyecto: bash setup_project.sh

echo "Creando estructura del proyecto..."

# Directorios
mkdir -p app/components
mkdir -p core/llm
mkdir -p core/chat
mkdir -p core/rag
mkdir -p core/integrations
mkdir -p services
mkdir -p config
mkdir -p credentials
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p .streamlit

# __init__.py en cada módulo Python
touch app/__init__.py
touch app/components/__init__.py
touch core/__init__.py
touch core/llm/__init__.py
touch core/chat/__init__.py
touch core/rag/__init__.py
touch core/integrations/__init__.py
touch services/__init__.py
touch config/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

# Archivos vacíos — se irán llenando por fase
touch app/main.py
touch app/session.py
touch app/components/chat_window.py
touch app/components/sidebar.py
touch app/components/file_uploader.py

touch core/llm/factory.py
touch core/llm/config.py
touch core/chat/chain.py
touch core/chat/memory.py
touch core/chat/prompts.py
touch core/rag/retriever.py
touch core/rag/embeddings.py
touch core/rag/vectorstore.py
touch core/rag/loader.py
touch core/integrations/base.py
touch core/integrations/google_drive.py
touch core/integrations/clickup.py

touch services/chat_service.py
touch services/document_service.py
touch services/integration_service.py

touch config/settings.py
touch config/logging.py

touch tests/unit/test_llm_factory.py
touch tests/unit/test_chain.py
touch tests/unit/test_memory.py
touch tests/integration/test_google_drive.py
touch tests/integration/test_clickup.py

echo "Estructura creada."
