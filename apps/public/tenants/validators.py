"""
Validadores para modelos de tenants.

Referencia: https://docs.djangoproject.com/en/stable/ref/validators/
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_schema_name(value: str) -> None:
    """
    Valida que schema_name sea alfanumérico y cumpla con restricciones de PostgreSQL.

    Reglas:
    - Solo caracteres alfanuméricos y guiones bajos
    - No puede empezar ni terminar con guión
    - Máximo 63 caracteres (límite de PostgreSQL)
    - No puede ser 'public' (reservado)

    Args:
        value: Valor a validar

    Raises:
        ValidationError: Si el valor no cumple las reglas
    """
    if not value:
        raise ValidationError(_("schema_name no puede estar vacío"))

    # Normalizar: strip y lower
    normalized = value.strip().lower()

    # Validar longitud
    if len(normalized) > 63:
        raise ValidationError(_("schema_name no puede exceder 63 caracteres"))

    # Validar que no sea 'public' (reservado)
    if normalized == "public":
        raise ValidationError(_("'public' es un esquema reservado"))

    # Validar caracteres alfanuméricos y guiones bajos
    if not re.match(r"^[a-z0-9_]+$", normalized):
        raise ValidationError(
            _("schema_name solo puede contener letras minúsculas, números y guiones bajos")
        )

    # Validar que no empiece ni termine con guión bajo
    if normalized.startswith("_") or normalized.endswith("_"):
        raise ValidationError(_("schema_name no puede empezar ni terminar con guión bajo"))
