"""Optional model adapters kept outside Cortex's provider-neutral core."""

from .ollama_local import OllamaLocalAdapter

__all__ = ["OllamaLocalAdapter"]
