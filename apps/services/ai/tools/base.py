"""
Contrato base de herramientas del AI Engine (Fase 4/12).

REGLA ABSOLUTA 4: prohibido exponer herramientas genericas
(execute_sql, update_model, delete_record, arbitrary_request). Toda
subclase de BaseTool debe ser semantica (un verbo+sustantivo de
negocio real: buscar_cliente, validar_factura, crear_cotizacion).

REGLA ABSOLUTA 5: separar READ / SUGGEST / VALIDATE / WRITE -- lo
codifica ToolKind, no una convencion de nombres suelta.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from apps.services.ai.context import AIContext


class ToolKind(str, Enum):
    READ = "READ"
    SUGGEST = "SUGGEST"
    VALIDATE = "VALIDATE"
    WRITE = "WRITE"


class ToolRisk(str, Enum):
    """Fase 3/26 -- clasificacion de riesgo, determina si requiere aprobacion."""
    SAFE_READ = "SAFE_READ"
    SENSITIVE_READ = "SENSITIVE_READ"
    SAFE_WRITE = "SAFE_WRITE"
    SENSITIVE_WRITE = "SENSITIVE_WRITE"
    HIGH_RISK = "HIGH_RISK"


# Kinds que SIEMPRE se ejecutan automaticamente (Fase 26) -- WRITE
# nunca esta en este conjunto, sin excepcion, aunque su ToolRisk sea
# SAFE_WRITE: toda escritura pasa por aprobacion explicita del
# usuario (Regla Absoluta 7), la automatizacion es solo para lectura.
AUTO_APPROVED_KINDS = frozenset({ToolKind.READ, ToolKind.SUGGEST, ToolKind.VALIDATE})


@dataclass(frozen=True)
class ToolResult:
    """
    Resultado normalizado de un tool call -- nunca un traceback, nunca
    SQL, nunca un secreto (Fase 34). `status` distingue exactamente lo
    que Regla Absoluta 10 exige poder distinguir.
    """
    status: str  # OK | VALIDATION_ERROR | PERMISSION_DENIED | NOT_FOUND | CONFLICT | DOMAIN_ERROR
    data: dict | list | None = None
    message: str = ""


class BaseTool(ABC):
    """Toda tool real hereda de aqui. name/description/domain/kind/risk son metadata para AIToolRegistry."""

    name: str
    description: str
    domain: str
    kind: ToolKind
    risk: ToolRisk
    confirmation_required: bool = False
    idempotent: bool = True

    @abstractmethod
    def run(self, context: AIContext, **kwargs) -> ToolResult:
        """
        Ejecuta la tool. DEBE usar exclusivamente Service/Selector ya
        existentes de la app propietaria del dominio -- nunca ORM
        directo sobre modelos de otra app, nunca SQL crudo (Regla
        Absoluta 1). DEBE filtrar toda consulta por
        context.empresa_id (Regla Absoluta 2/24).
        """
        raise NotImplementedError
