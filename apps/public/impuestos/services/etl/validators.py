"""
Validadores de negocio para entidades tributarias.

Valida porcentajes, códigos DIAN, solapes de vigencia, etc.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError


def validate_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    """
    Valida el payload completo antes de upsert.

    Raises:
        ValidationError si hay errores de validación
    """
    errors = []

    # Validar tipos
    for tipo in payload.get("tipos", []):
        errors.extend(_validate_tipo_impuesto(tipo))

    # Validar tarifas
    for tarifa in payload.get("tarifas", []):
        errors.extend(_validate_tarifa_iva(tarifa))

    # Validar retenciones
    for retencion in payload.get("retenciones", []):
        errors.extend(_validate_retencion(retencion))

    # Validar códigos
    for codigo in payload.get("codigos", []):
        errors.extend(_validate_codigo_tributario(codigo))

    # Validar actividades
    for actividad in payload.get("actividades", []):
        errors.extend(_validate_actividad_economica(actividad))

    # Validar normas
    for norma in payload.get("normas", []):
        errors.extend(_validate_norma(norma))

    # Validar solapes de vigencia
    errors.extend(_validate_vigencia_overlaps(payload))

    if errors:
        raise ValidationError(errors)


def _validate_tipo_impuesto(tipo: dict) -> list[str]:
    """Valida un tipo de impuesto."""
    errors = []

    if not tipo.get("codigo"):
        errors.append("Tipo de impuesto requiere código")

    if not tipo.get("nombre"):
        errors.append("Tipo de impuesto requiere nombre")

    if not tipo.get("fecha_vigencia"):
        errors.append("Tipo de impuesto requiere fecha de vigencia")

    # Validar formato de código (alfanumérico, max 10 caracteres)
    codigo = tipo.get("codigo", "")
    if len(codigo) > 10:
        errors.append(f"Código de tipo de impuesto excede 10 caracteres: {codigo}")

    return errors


def _validate_tarifa_iva(tarifa: dict) -> list[str]:
    """Valida una tarifa de IVA."""
    errors = []

    if not tarifa.get("codigo"):
        errors.append("Tarifa IVA requiere código")

    porcentaje = tarifa.get("porcentaje")
    if porcentaje is not None:
        try:
            porcentaje_decimal = Decimal(str(porcentaje))
            if porcentaje_decimal < 0 or porcentaje_decimal > 100:
                errors.append(f"Porcentaje de tarifa IVA fuera de rango (0-100): {porcentaje}")
        except (InvalidOperation, ValueError):
            errors.append(f"Porcentaje de tarifa IVA inválido: {porcentaje}")

    if not tarifa.get("fecha_vigencia"):
        errors.append("Tarifa IVA requiere fecha de vigencia")

    # Validar que vigencia_hasta sea posterior a vigencia_desde
    vigencia_desde = tarifa.get("fecha_vigencia")
    vigencia_hasta = tarifa.get("fecha_fin_vigencia")
    if vigencia_desde and vigencia_hasta and vigencia_hasta < vigencia_desde:
        errors.append(
            f"Fecha fin de vigencia anterior a fecha inicio: {vigencia_hasta} < {vigencia_desde}"
        )

    return errors


def _validate_retencion(retencion: dict) -> list[str]:
    """Valida un concepto de retención."""
    errors = []

    if not retencion.get("codigo"):
        errors.append("Concepto de retención requiere código")

    porcentaje = retencion.get("porcentaje")
    if porcentaje is not None:
        try:
            porcentaje_decimal = Decimal(str(porcentaje))
            if porcentaje_decimal < 0 or porcentaje_decimal > 100:
                errors.append(f"Porcentaje de retención fuera de rango (0-100): {porcentaje}")
        except (InvalidOperation, ValueError):
            errors.append(f"Porcentaje de retención inválido: {porcentaje}")

    base_minima = retencion.get("base_minima")
    if base_minima is not None:
        try:
            base_decimal = Decimal(str(base_minima))
            if base_decimal < 0:
                errors.append(f"Base mínima de retención negativa: {base_minima}")
        except (InvalidOperation, ValueError):
            errors.append(f"Base mínima de retención inválida: {base_minima}")

    if not retencion.get("fecha_vigencia"):
        errors.append("Concepto de retención requiere fecha de vigencia")

    return errors


def _validate_codigo_tributario(codigo: dict) -> list[str]:
    """Valida un código tributario."""
    errors = []

    if not codigo.get("codigo"):
        errors.append("Código tributario requiere código")

    if not codigo.get("tipo"):
        errors.append("Código tributario requiere tipo")

    return errors


def _validate_actividad_economica(actividad: dict) -> list[str]:
    """Valida una actividad económica."""
    errors = []

    if not actividad.get("codigo"):
        errors.append("Actividad económica requiere código")

    # Validar formato CIIU (4 dígitos)
    codigo = actividad.get("codigo", "")
    if not codigo.isdigit() or len(codigo) != 4:
        errors.append(f"Código CIIU debe ser 4 dígitos: {codigo}")

    return errors


def _validate_norma(norma: dict) -> list[str]:
    """Valida una norma tributaria."""
    errors = []

    if not norma.get("texto_plano"):
        errors.append("Norma tributaria requiere texto")

    vigencia_desde = norma.get("vigencia_desde")
    vigencia_hasta = norma.get("vigencia_hasta")
    if vigencia_desde and vigencia_hasta and vigencia_hasta < vigencia_desde:
        errors.append(
            f"Fecha fin de vigencia anterior a fecha inicio: {vigencia_hasta} < {vigencia_desde}"
        )

    return errors


def _validate_vigencia_overlaps(payload: dict) -> list[str]:
    """
    Valida que no haya solapes de vigencia para la misma llave natural.

    Nota: Esta validación se hace a nivel de aplicación.
    La base de datos también puede tener constraints.
    """
    errors = []

    # Validar solapes en tarifas (mismo código)
    tarifas_by_codigo = {}
    for tarifa in payload.get("tarifas", []):
        codigo = tarifa.get("codigo")
        if codigo:
            if codigo not in tarifas_by_codigo:
                tarifas_by_codigo[codigo] = []
            tarifas_by_codigo[codigo].append(tarifa)

    for codigo, tarifas in tarifas_by_codigo.items():
        if len(tarifas) > 1:
            # Verificar solapes
            for i, t1 in enumerate(tarifas):
                for t2 in tarifas[i + 1 :]:
                    if _dates_overlap(
                        t1.get("fecha_vigencia"),
                        t1.get("fecha_fin_vigencia"),
                        t2.get("fecha_vigencia"),
                        t2.get("fecha_fin_vigencia"),
                    ):
                        errors.append(
                            f"Solape de vigencia en tarifa {codigo}: "
                            f"{t1.get('fecha_vigencia')}-{t1.get('fecha_fin_vigencia')} vs "
                            f"{t2.get('fecha_vigencia')}-{t2.get('fecha_fin_vigencia')}"
                        )

    # Similar para retenciones
    retenciones_by_codigo = {}
    for retencion in payload.get("retenciones", []):
        codigo = retencion.get("codigo")
        if codigo:
            if codigo not in retenciones_by_codigo:
                retenciones_by_codigo[codigo] = []
            retenciones_by_codigo[codigo].append(retencion)

    for codigo, retenciones in retenciones_by_codigo.items():
        if len(retenciones) > 1:
            for i, r1 in enumerate(retenciones):
                for r2 in retenciones[i + 1 :]:
                    if _dates_overlap(
                        r1.get("fecha_vigencia"),
                        r1.get("fecha_fin_vigencia"),
                        r2.get("fecha_vigencia"),
                        r2.get("fecha_fin_vigencia"),
                    ):
                        errors.append(
                            f"Solape de vigencia en retención {codigo}: "
                            f"{r1.get('fecha_vigencia')}-{r1.get('fecha_fin_vigencia')} vs "
                            f"{r2.get('fecha_vigencia')}-{r2.get('fecha_fin_vigencia')}"
                        )

    return errors


def _dates_overlap(
    start1: date | None, end1: date | None, start2: date | None, end2: date | None
) -> bool:
    """Verifica si dos intervalos de fechas se solapan."""
    if not start1 or not start2:
        return False

    # Si no hay fin, considerar como vigente indefinidamente
    if not end1:
        end1 = date.max
    if not end2:
        end2 = date.max

    return start1 <= end2 and start2 <= end1
