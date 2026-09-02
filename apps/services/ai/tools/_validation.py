"""
Fase AI-04 (Validation Engine): helper compartido por todas las tools
`validar_*`. NO reimplementa reglas de negocio -- ejecuta el mismo
Serializer DRF que ya usa el endpoint real de creacion de cada
dominio (`<Modelo>DetailSerializer.is_valid()`), que es donde vive
hoy la validacion real (campos requeridos, formatos, y reglas de
negocio explicitas como duplicidad de documento -- ej.
`ClienteDetailSerializer.validate()`, `AI_TOOL_REGISTRY.md` Fase 14:
"reutiliza las validaciones YA existentes... nunca reimplementa
reglas de negocio, las invoca").

`Serializer(...).is_valid()` nunca escribe en la base de datos (solo
`.save()` lo hace, y esta tool nunca lo llama) -- las unicas consultas
que dispara son SELECT de unicidad (ej. verificar que el numero de
documento no exista ya), igual que hace el endpoint real antes de
persistir. Por eso esta clase de tool es segura como `VALIDATE`
(auto-aprobada, `AUTO_APPROVED_KINDS`) sin tocar Regla Absoluta 6/7
(WRITE nunca se auto-aprueba).

Contrato de salida (ya documentado en AI_TOOL_REGISTRY.md Fase 14,
implementado aqui por primera vez):
`{"valid": bool, "warnings": [...], "missing_data": [...]}`.
"""
from __future__ import annotations

from apps.services.ai.context import AIContext

from .base import ToolResult


def validar_via_serializer(
    serializer_class, context: AIContext, data: dict, extra_context: dict | None = None
) -> ToolResult:
    serializer_context = {"empresa_id": context.empresa_id}
    if extra_context:
        serializer_context.update(extra_context)
    serializer = serializer_class(data=data, context=serializer_context)

    if serializer.is_valid():
        return ToolResult(status="OK", data={"valid": True, "warnings": [], "missing_data": []})

    missing_data = []
    warnings = []
    for field, errors in serializer.errors.items():
        for err in errors:
            if getattr(err, "code", None) == "required":
                missing_data.append(field)
            else:
                warnings.append(f"{field}: {err}")

    return ToolResult(
        status="OK",
        data={"valid": False, "warnings": warnings, "missing_data": missing_data},
    )
