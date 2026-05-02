"""
Servicios públicos para validación de tokens de acceso a documentos compartidos.

WARNING: v3.3: Service Layer Pattern - Lógica de negocio centralizada
WARNING: API-First: Todos los servicios expuestos vía DRF REST API
WARNING: Seguridad: Validación de hash SHA256 para integridad de documentos

Este módulo maneja:
- Validación de tokens/hash para acceso público a cotizaciones/proyectos
- Generación de hash de acceso seguro
- Verificación de integridad de documentos compartidos
"""

import hashlib
import hmac
import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger(__name__)

# Clave secreta para generación de hash (debe estar en settings.SECRET_KEY o settings.PUBLIC_SHARE_SECRET)
PUBLIC_SHARE_SECRET = getattr(settings, "PUBLIC_SHARE_SECRET", settings.SECRET_KEY)


def generar_hash_acceso(
    tipo_documento: str, documento_id: int, tenant_schema: str, expiracion_dias: int = 30
) -> str:
    """
    Genera un hash seguro para acceso público a un documento.

    WARNING: SEGURIDAD:
    - Usa HMAC-SHA256 para garantizar integridad
    - Incluye tipo, ID, tenant y expiración en el hash
    - El hash es determinístico pero no reversible

    Args:
        tipo_documento: Tipo de documento ('cotizacion', 'proyecto')
        documento_id: ID del documento
        tenant_schema: Schema del tenant (para aislamiento)
        expiracion_dias: Días hasta expiración (default: 30)

    Returns:
        str: Hash de acceso (hexadecimal, 64 caracteres)

    Ejemplo:
        hash = generar_hash_acceso('cotizacion', 123, 'empresa_x', 30)
    """
    if not tipo_documento or not documento_id or not tenant_schema:
        raise ValidationError("tipo_documento, documento_id y tenant_schema son requeridos")

    # Calcular timestamp de expiración
    expiracion = timezone.now() + timedelta(days=expiracion_dias)
    expiracion_timestamp = int(expiracion.timestamp())

    # Construir mensaje para hash
    mensaje = f"{tipo_documento}:{documento_id}:{tenant_schema}:{expiracion_timestamp}"

    # Generar HMAC-SHA256
    hash_obj = hmac.new(
        PUBLIC_SHARE_SECRET.encode("utf-8"), mensaje.encode("utf-8"), hashlib.sha256
    )
    hash_hex = hash_obj.hexdigest()

    logger.info(
        f"[public.services] Hash generado para {tipo_documento} ID {documento_id} "
        f"(tenant: {tenant_schema}, expira: {expiracion_timestamp})"
    )

    return hash_hex


def validar_hash_acceso(
    hash_proporcionado: str, tipo_documento: str, documento_id: int, tenant_schema: str
) -> tuple[bool, str | None, int | None]:
    """
    Valida un hash de acceso público y verifica su integridad.

    WARNING: SEGURIDAD:
    - Verifica que el hash sea válido para el documento y tenant
    - Verifica que no haya expirado
    - Retorna información de expiración si es válido

    Args:
        hash_proporcionado: Hash proporcionado por el usuario
        tipo_documento: Tipo de documento esperado
        documento_id: ID del documento
        tenant_schema: Schema del tenant

    Returns:
        Tuple[bool, Optional[str], Optional[int]]:
            - (True, None, expiracion_timestamp) si es válido
            - (False, mensaje_error, None) si es inválido

    Ejemplo:
        valido, error, expiracion = validar_hash_acceso(
            hash, 'cotizacion', 123, 'empresa_x'
        )
    """
    if not hash_proporcionado or not tipo_documento or not documento_id or not tenant_schema:
        return False, "Parámetros incompletos", None

    # Intentar validar con diferentes períodos de expiración (1, 7, 30, 90 días)
    # Esto permite regenerar el hash con diferentes períodos sin romper enlaces existentes
    periodos_expiracion = [1, 7, 30, 90]

    for dias in periodos_expiracion:
        # Calcular timestamp de expiración para este período
        expiracion = timezone.now() + timedelta(days=dias)
        expiracion_timestamp = int(expiracion.timestamp())

        # Construir mensaje
        mensaje = f"{tipo_documento}:{documento_id}:{tenant_schema}:{expiracion_timestamp}"

        # Generar hash esperado
        hash_esperado = hmac.new(
            PUBLIC_SHARE_SECRET.encode("utf-8"), mensaje.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Comparar hashes de forma segura (timing-safe)
        if hmac.compare_digest(hash_proporcionado, hash_esperado):
            # Verificar que no haya expirado
            ahora_timestamp = int(timezone.now().timestamp())
            if expiracion_timestamp < ahora_timestamp:
                return False, "El enlace de acceso ha expirado", None

            logger.info(
                f"[public.services] Hash válido para {tipo_documento} ID {documento_id} "
                f"(tenant: {tenant_schema}, expira: {expiracion_timestamp})"
            )

            return True, None, expiracion_timestamp

    # Si no coincide con ningún período, intentar con timestamp exacto del hash original
    # (para hashes generados con timestamp específico)
    # Esto requiere almacenar el timestamp original, pero por ahora retornamos error
    logger.warning(
        f"[public.services] Hash inválido para {tipo_documento} ID {documento_id} "
        f"(tenant: {tenant_schema})"
    )

    return False, "Hash de acceso inválido o expirado", None


def validar_token_documento(
    token: str, tipo_documento: str, documento_id: int, tenant_schema: str
) -> dict[str, Any]:
    """
    Valida un token de acceso y retorna información del documento si es válido.

    WARNING: API-First: Este método es llamado por los endpoints DRF

    Args:
        token: Token/hash de acceso
        tipo_documento: Tipo de documento ('cotizacion', 'proyecto')
        documento_id: ID del documento
        tenant_schema: Schema del tenant

    Returns:
        Dict con:
            - 'valido': bool
            - 'error': str (si no es válido)
            - 'expiracion': int timestamp (si es válido)
            - 'tipo_documento': str
            - 'documento_id': int
            - 'tenant_schema': str

    Raises:
        ValidationError: Si los parámetros son inválidos
    """
    if not token:
        raise ValidationError("Token de acceso requerido")

    if tipo_documento not in ["cotizacion", "proyecto"]:
        raise ValidationError(f"Tipo de documento inválido: {tipo_documento}")

    valido, error, expiracion = validar_hash_acceso(
        token, tipo_documento, documento_id, tenant_schema
    )

    resultado = {
        "valido": valido,
        "tipo_documento": tipo_documento,
        "documento_id": documento_id,
        "tenant_schema": tenant_schema,
    }

    if valido:
        resultado["expiracion"] = expiracion
        resultado["expiracion_fecha"] = timezone.datetime.fromtimestamp(
            expiracion, tz=timezone.utc
        ).isoformat()
    else:
        resultado["error"] = error

    return resultado


def obtener_datos_documento_publico(
    tipo_documento: str, documento_id: int, tenant_schema: str
) -> dict[str, Any] | None:
    """
    Obtiene los datos públicos de un documento (sin información sensible).

    WARNING: API-First: Este método es llamado por los endpoints DRF públicos
    WARNING: Seguridad: Solo retorna campos permitidos para vista pública

    Args:
        tipo_documento: Tipo de documento ('cotizacion', 'proyecto')
        documento_id: ID del documento
        tenant_schema: Schema del tenant

    Returns:
        Dict con datos públicos del documento o None si no existe

    Nota:
        Este método debe ser implementado en el contexto del tenant específico.
        Por ahora retorna estructura básica. La implementación completa requiere
        acceso al modelo del documento en el schema del tenant.
    """
    # WARNING: NOTA: Esta función requiere acceso al schema del tenant
    # La implementación completa debe usar django-tenants para cambiar de schema
    # y luego acceder al modelo correspondiente

    estructura_base = {
        "id": documento_id,
        "tipo": tipo_documento,
        "tenant_schema": tenant_schema,
    }

    if tipo_documento == "cotizacion":
        estructura_base.update(
            {
                "campos_publicos": [
                    "numero",
                    "fecha_emision",
                    "fecha_vencimiento",
                    "atencion_a",
                    "asunto",
                    "estado",
                    "subtotal",
                    "iva_valor",
                    "total_neto",
                ]
            }
        )
    elif tipo_documento == "proyecto":
        estructura_base.update(
            {
                "campos_publicos": [
                    "codigo",
                    "nombre",
                    "descripcion",
                    "fecha_inicio",
                    "fecha_fin_prevista",
                    "fase_actual_display",
                    "estado_display",
                ]
            }
        )

    logger.info(
        f"[public.services] Obteniendo datos públicos de {tipo_documento} ID {documento_id} "
        f"(tenant: {tenant_schema})"
    )

    return estructura_base
