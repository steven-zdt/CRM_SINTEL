"""
Business Service para Gastos - Lógica de negocio y orquestación.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO lógica de negocio (validaciones, cálculos, orquestación).
- Delega persistencia a crud_service.py.
- Todas las funciones son @staticmethod.
"""
import logging
import re
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.gastos.models import Gasto, ResolucionDIAN, DocumentoSoporte
from apps.tenant.gastos.services.crud_service import (
    GastoCRUDService,
    ResolucionCRUDService,
    DocumentoCRUDService,
    ItemGastoCRUDService,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# UTILIDADES
# ==============================================================================

def normalize_document_number(value: str | None) -> str | None:
    """Limpia y normaliza identificadores legales."""
    if not value:
        return None
    return re.sub(r'\s+', '', str(value)).strip()


def _normalizar_porcentaje_retefuente(value: Decimal) -> str:
    """Convierte porcentaje UI (4) o base-1 (0.04) a choice del modelo."""
    valor = Decimal(str(value or 0))
    opciones = {
        '0': '0.00', '0.00': '0.00',
        '4': '0.04', '4.0': '0.04', '4.00': '0.04', '0.04': '0.04',
        '6': '0.06', '6.0': '0.06', '6.00': '0.06', '0.06': '0.06',
        '10': '0.10', '10.0': '0.10', '10.00': '0.10', '0.10': '0.10',
        '11': '0.11', '11.0': '0.11', '11.00': '0.11', '0.11': '0.11',
    }
    clave = format(valor.normalize(), 'f')
    return opciones.get(clave, '0.00')


def _normalizar_porcentaje_reteica(value: Decimal) -> str:
    """Convierte porcentaje UI (0.966) o base-1 (0.00966) a choice del modelo."""
    valor = Decimal(str(value or 0))
    opciones = {
        '0': '0.00', '0.0': '0.00', '0.00': '0.00',
        '0.69': '0.0069', '0.690': '0.0069', '0.0069': '0.0069',
        '0.966': '0.00966', '0.9660': '0.00966', '0.00966': '0.00966',
        '1.104': '0.01104', '1.1040': '0.01104', '0.01104': '0.01104',
    }
    clave = format(valor.normalize(), 'f')
    return opciones.get(clave, '0.00')


# ==============================================================================
# SERVICIOS DE NEGOCIO
# ==============================================================================

class GastoBusinessService:
    """Lógica de negocio para Gasto."""

    @staticmethod
    def calcular_retenciones(
        subtotal: Decimal,
        retefuente_pct: Decimal,
        reteica_pct: Decimal
    ) -> Dict[str, Decimal]:
        """
        Calcula retenciones según normativa colombiana.
        
        Args:
            subtotal: Base gravable
            retefuente_pct: Porcentaje ReteFuente (ej: 4 para 4%)
            reteica_pct: Porcentaje ReteICA (ej: 0.966 para 0.966%)
        
        Returns:
            Dict con retenciones calculadas y total
        """
        # Convertir porcentajes de formato UI a decimal
        retefuente_decimal = Decimal(_normalizar_porcentaje_retefuente(retefuente_pct))
        reteica_decimal = Decimal(_normalizar_porcentaje_reteica(reteica_pct))

        retefuente_valor = (subtotal * retefuente_decimal).quantize(Decimal('0.01'))
        reteica_valor = (subtotal * reteica_decimal).quantize(Decimal('0.01'))

        total_retenciones = retefuente_valor + reteica_valor
        total_neto = (subtotal - total_retenciones).quantize(Decimal('0.01'))

        return {
            'subtotal': subtotal,
            'retefuente_porcentaje': retefuente_pct,
            'retefuente_valor': retefuente_valor,
            'reteica_porcentaje': reteica_pct,
            'reteica_valor': reteica_valor,
            'total_retenciones': total_retenciones,
            'total': total_neto
        }

    @staticmethod
    def validar_proveedor(
        empresa: Any,
        proveedor_uuid: str,
        tipo_documento: str
    ) -> Dict[str, Any]:
        """
        Valida y obtiene snapshot de proveedor.
        
        Returns:
            Dict con datos del proveedor validado
        """
        from apps.tenant.proveedores.services.services import ProveedorBusinessService

        if not proveedor_uuid:
            raise ValidationError({'proveedor_uuid': ['Debe seleccionar un proveedor']})

        snapshot = ProveedorBusinessService.obtener_snapshot_proveedor(
            empresa=empresa,
            proveedor_uuid=proveedor_uuid,
            tipo_documento=tipo_documento
        )

        return snapshot

    @staticmethod
    def validar_cuenta_contable(
        empresa_id: int,
        cuenta_uuid: str
    ) -> Dict[str, Any]:
        """
        Valida que la cuenta contable exista y sea de tipo GASTO.
        
        Returns:
            Dict con datos de la cuenta validada
        """
        from apps.tenant.contabilidad.services.contabilidad_business_service import (
            ContabilidadBusinessService
        )

        try:
            cuenta_uuid_normalizado = str(UUID(cuenta_uuid))
        except (ValueError, TypeError):
            raise ValidationError({'cuenta_contable_uuid': ['UUID inválido']})

        contabilidad_service = ContabilidadBusinessService()
        cuentas_gasto = contabilidad_service.obtener_cuentas_gasto_disponibles(
            empresa_id=empresa_id
        )

        cuenta_match = next(
            (
                cuenta for cuenta in cuentas_gasto
                if str(cuenta.get('uuid') or '').strip() == cuenta_uuid_normalizado
            ),
            None
        )

        if not cuenta_match:
            raise ValidationError({
                'cuenta_contable_uuid': [
                    'La categoría contable no existe o no es de tipo GASTO'
                ]
            })

        return cuenta_match

    @staticmethod
    @transaction.atomic
    def procesar_gasto(
        empresa: Any,
        data: Dict[str, Any]
    ) -> Gasto:
        """
        Orquesta el procesamiento completo de un gasto:
        - Validaciones de negocio
        - Cálculo de retenciones
        - Creación de documento soporte
        - Creación de gasto
        - Materialización contable
        """
        # 1. Validar resolución vigente
        resolucion = ResolucionBusinessService.obtener_vigente(empresa.id)
        if not resolucion:
            raise ValidationError("No hay resolución DIAN activa configurada")

        # 2. Validar y obtener proveedor
        proveedor_uuid = str(data.get('proveedor_uuid') or '').strip()
        tipo_documento = str(data.get('tipo_documento') or '').strip().upper()

        proveedor_snapshot = GastoBusinessService.validar_proveedor(
            empresa, proveedor_uuid, tipo_documento
        )

        # 3. Validar cuenta contable
        cuenta_uuid = str(data.get('cuenta_contable_uuid') or '').strip()
        cuenta_match = GastoBusinessService.validar_cuenta_contable(
            empresa.id, cuenta_uuid
        )

        # 4. Extraer y validar datos financieros
        subtotal = Decimal(str(data.get('subtotal', 0)))
        if subtotal <= 0:
            raise ValidationError({'subtotal': ['El subtotal debe ser mayor a 0']})

        retefuente_pct = Decimal(str(data.get('retefuente_porcentaje', 0) or 0))
        reteica_pct = Decimal(str(data.get('reteica_porcentaje', 0) or 0))

        # 5. Calcular retenciones
        retenciones = GastoBusinessService.calcular_retenciones(
            subtotal, retefuente_pct, reteica_pct
        )

        # 6. Validar total del cliente vs servidor
        total_cliente = Decimal(str(data.get('total_neto', 0) or 0))
        if abs(total_cliente - retenciones['total']) > Decimal('0.01'):
            raise ValidationError({
                'total_neto': ['El total no coincide con el cálculo del servidor']
            })

        # 7. Crear documento soporte
        doc_data = {
            'fecha': data.get('fecha'),
            'vendedor_nombre': proveedor_snapshot.get('nombre', ''),
            'vendedor_tipo_documento': tipo_documento,
            'vendedor_numero_documento': proveedor_snapshot.get('numero_documento', ''),
            'subtotal': subtotal,
            'retefuente_porcentaje': _normalizar_porcentaje_retefuente(retefuente_pct),
            'retefuente_valor': retenciones['retefuente_valor'],
            'reteica_porcentaje': _normalizar_porcentaje_reteica(reteica_pct),
            'reteica_valor': retenciones['reteica_valor'],
            'total': retenciones['total'],
            'anulado': False
        }

        documento = DocumentoCRUDService.crear_documento(
            data=doc_data,
            empresa=empresa,
            resolucion=resolucion
        )

        # 8. Crear gasto
        gasto_data = {
            'periodo': data.get('periodo'),
            'centro_costo': data.get('centro_costo', ''),
            'categoria_contable': data.get('categoria_contable'),
            'descripcion': data.get('descripcion', ''),
            'observaciones': data.get('observaciones', ''),
            'cuenta_contable_uuid': str(UUID(cuenta_uuid)),
            'cuenta_contable_display': f"[{cuenta_match.get('codigo')}] - {cuenta_match.get('nombre')}",
        }

        gasto = GastoCRUDService.crear_gasto(
            data=gasto_data,
            empresa=empresa,
            documento_soporte=documento
        )

        # 9. Crear ítem genérico
        ItemGastoCRUDService.crear_item(
            data={
                'descripcion': data.get('descripcion') or 'Gasto operativo',
                'cantidad': 1,
                'valor_unitario': subtotal,
                'valor_total': subtotal
            },
            empresa=empresa,
            gasto=gasto,
            documento=documento
        )

        logger.info(f"[GastoBusiness] Procesado gasto ID={gasto.id}")
        return gasto


class ResolucionBusinessService:
    """Lógica de negocio para ResolucionDIAN."""

    @staticmethod
    def obtener_vigente(empresa_id: int) -> ResolucionDIAN | None:
        """Obtiene la resolución vigente para una empresa."""
        return ResolucionDIAN.objects.filter(
            empresa_id=empresa_id,
            vigente=True
        ).first()

    @staticmethod
    def validar_resolucion_para_gasto(
        empresa: Any,
        resolucion_id: int = None
    ) -> ResolucionDIAN:
        """
        Valida y retorna resolución para crear un gasto.
        Si no se proporciona, busca la vigente.
        """
        if resolucion_id:
            try:
                resolucion = ResolucionDIAN.objects.get(
                    id=resolucion_id,
                    empresa=empresa
                )
            except ResolucionDIAN.DoesNotExist:
                raise ValidationError("La resolución especificada no existe")
        else:
            resolucion = ResolucionBusinessService.obtener_vigente(empresa.id)

        if not resolucion:
            raise ValidationError("No hay resolución DIAN configurada")

        if not resolucion.vigente:
            raise ValidationError("La resolución no está vigente")

        if not resolucion.esta_dentro_de_fecha():
            raise ValidationError("La resolución ha expirado")

        return resolucion


class ProveedorSnapshotService:
    """Servicio para obtener snapshots de proveedores."""

    @staticmethod
    def obtener_snapshot(
        empresa: Any,
        proveedor_uuid: str,
        tipo_documento: str
    ) -> Dict[str, Any]:
        """
        Obtiene snapshot validado de un proveedor.
        """
        from apps.tenant.proveedores.services.services import ProveedorBusinessService

        return ProveedorBusinessService.obtener_snapshot_proveedor(
            empresa=empresa,
            proveedor_uuid=proveedor_uuid,
            tipo_documento=tipo_documento
        )
