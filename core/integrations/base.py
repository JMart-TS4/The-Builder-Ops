from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class Document:
    """Unidad de contenido recuperado de cualquier fuente externa."""
    content: str
    source: str                          # 'google_drive' | 'clickup'
    title: str = ""
    url: str = ""
    metadata: dict = field(default_factory=dict)

class BaseIntegration(ABC):
    """Interfaz común para todas las integraciones externas.

    Cada conector implementa estos métodos. El resto del sistema
    solo conoce esta interfaz, nunca los detalles de cada API.
    """
    @abstractmethod
    def fetch_documents(self) -> list[Document]:
        """Recupera todos los documentos disponibles de la fuente."""
        ...

    @abstractmethod
    def search(self, query: str) -> list[Document]:
        """Busca documentos relevantes para una consulta específica."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica que la conexión con la API esté activa."""
        ...