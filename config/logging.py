import logging
import sys
from config.settings import settings

def setup_logging() -> None:
    """Configura el logger raíz de la aplicación. Llamar una sola vez en main.py"""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger con el nombre del módulo que lo llama.

    Uso:
        from config.logging import get_logger
        logger = get_logger(__name__)
        logger.info("mensaje")
    """
    return logging.getLogger(name)