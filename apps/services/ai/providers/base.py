"""
Contrato de proveedor de IA (Fase 5). El dominio (engine, tools) nunca
importa un SDK de proveedor directamente -- solo este contrato.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AIResponse:
    """Respuesta normalizada, independiente del proveedor."""
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict = field(default_factory=dict)


class AIProvider(ABC):
    """
    Contrato que todo proveedor (Anthropic, OpenAI, local) debe cumplir.

    No expone tool-calling nativo del SDK como parte del contrato --
    el AIEngine decide que tool ejecutar a partir del texto/decision
    del modelo; esto evita acoplar el dominio a la forma exacta de
    function-calling de un proveedor especifico. Si un proveedor
    soporta tool-calling nativo, su implementacion puede usarlo
    internamente sin cambiar este contrato.
    """

    name: str

    @abstractmethod
    def complete(self, system: str, user_message: str, *, max_tokens: int = 1024) -> AIResponse:
        """Genera una respuesta de una sola llamada (sin streaming)."""
        raise NotImplementedError
