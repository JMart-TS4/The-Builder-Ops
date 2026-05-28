from dataclasses import dataclass

@dataclass
class LLMProviderConfig:
    model: str
    temperature: float
    max_tokens: int
    streaming: bool = True


# Configuración por proveedor
PROVIDER_CONFIGS: dict[str, LLMProviderConfig] = {
    "anthropic": LLMProviderConfig(
        model="claude-sonnet-4-6",
        temperature=0.7,
        max_tokens=4096,
    ),
    "gemini": LLMProviderConfig(
        model="gemini-2.5-flash",
        temperature=0.7,
        max_tokens=4096,
    ),
}


def get_provider_config(provider: str) -> LLMProviderConfig:
    """Retorna la configuración del proveedor solicitado."""
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(
            f"Proveedor '{provider}' no soportado. "
            f"Opciones válidas: {list(PROVIDER_CONFIGS.keys())}"
        )
    return PROVIDER_CONFIGS[provider]