from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# System prompt principal
SYSTEM_PROMPT = """Eres un asistente empresarial inteligente y preciso.

Tienes acceso al contexto de documentos y tareas de la empresa cuando es relevante.
Usa ese contexto para dar respuestas específicas y accionables.

Lineamientos:
- Responde siempre en el idioma del usuario
- Sé conciso pero completo
- Si no tienes suficiente información, dilo claramente
- Nunca inventes datos, fechas o nombres de personas
"""

# Template principal del chat
CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

# Template con contexto RAG
CHAT_WITH_CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT + """
Contexto relevante recuperado de los documentos de la empresa:

{context}

Usa este contexto para responder si es relevante. 
Si el contexto no es suficiente, responde con tu conocimiento general.
"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])