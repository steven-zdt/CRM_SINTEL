"""
RetencionesService - Lógica de negocio para retenciones (v3.7.1).

Responsabilidades:
- Obtener configuración de retenciones por tercero (CLIENTE, PROVEEDOR)
- Calcular montos de retención
- Crear registros de retención
- Listar retenciones por documento
- Reversar retenciones (notas de crédito)

Pull Model:
- Cada retención está vinculada a un documento en otra app (Factura, Gasto, etc.)
- Las retenciones se consultan vía HTTP API, no con imports directos
- Contabilidad es el SSoT para cálculos y configuración
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Q, Sum
from django.utils.translation import gettext_lazy as _

from apps.tenant.contabilidad.models import (
    ConfiguracionRetenciones,
    Retencion,
)


class RetencionesService:
    """
    Servicio centralizado para gestión de retenciones en Contabilidad.
    """

    @staticmethod
    def obtener_retenciones_desde_tercero(
        nit: Optional[str],
        tipo_tercero: str,
        naturaleza: str = 'VENTA',
        empresa_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Obtiene configuración de retenciones para un tercero específico.

        Lógica:
        1. Busca configuración específica por (tipo_tercero, nit, naturaleza)
        2. Si no existe, busca default (tipo_tercero, nit=None, naturaleza)
        3. Si no existe default, retorna dict con todos los ceros

        Args:
            nit: NIT del tercero (normalizado: sin puntos ni guiones)
            tipo_tercero: 'CLIENTE', 'PROVEEDOR', 'EMPLEADO'
            naturaleza: 'VENTA', 'COMPRA'
            empresa_id: ID de empresa (para contexto, no usado en filtro)

        Returns:
            Dict con estructura:
            {
                'aplica_retefuente': bool,
                'retefuente_porcentaje': Decimal,
                'aplica_reteica': bool,
                'reteica_porcentaje': Decimal,
                'aplica_reteiva': bool,
                'reteiva_porcentaje': Decimal,
            }
        """
        if not nit or not tipo_tercero:
            return {
                'aplica_retefuente': False,
                'retefuente_porcentaje': Decimal('0.00'),
                'aplica_reteica': False,
                'reteica_porcentaje': Decimal('0.00'),
                'aplica_reteiva': False,
                'reteiva_porcentaje': Decimal('0.00'),
            }

        # Normalizar NIT (remover puntos, guiones, espacios)
        nit_normalizado = str(nit).strip().replace('.', '').replace('-', '')

        resultado = {
            'aplica_retefuente': False,
            'retefuente_porcentaje': Decimal('0.00'),
            'aplica_reteica': False,
            'reteica_porcentaje': Decimal('0.00'),
            'aplica_reteiva': False,
            'reteiva_porcentaje': Decimal('0.00'),
        }

        # Buscar retenciones específicas por NIT
        for tipo_ret in ['RETEFUENTE', 'RETEICA', 'RETEIVA']:
            config = ConfiguracionRetenciones.objects.filter(
                tipo_tercero=tipo_tercero,
                naturaleza=naturaleza,
                tipo_retencion=tipo_ret,
                activa=True,
                nit_tercero=nit_normalizado,
            ).first()

            if not config:
                # Buscar default (nit_tercero=None)
                config = ConfiguracionRetenciones.objects.filter(
                    tipo_tercero=tipo_tercero,
                    naturaleza=naturaleza,
                    tipo_retencion=tipo_ret,
                    activa=True,
                    nit_tercero__isnull=True,
                ).first()

            if config and config.porcentaje_por_defecto > 0:
                key_aplica = f'aplica_{tipo_ret.lower()}'
                key_porcentaje = f'{tipo_ret.lower()}_porcentaje'
                resultado[key_aplica] = True
                resultado[key_porcentaje] = config.porcentaje_por_defecto

        return resultado

    @staticmethod
    def calcular_monto_retencion(
        tipo: str,
        porcentaje: Decimal,
        base: Decimal,
    ) -> Decimal:
        """
        Calcula el monto de una retención.

        Formula: monto = (base * porcentaje) / 100

        Args:
            tipo: RETEFUENTE, RETEICA, RETEIVA (solo informativo)
            porcentaje: Tasa de retención (ej: 3.5)
            base: Monto base para calcular (ej: subtotal)

        Returns:
            Monto retenido (Decimal)
        """
        if not porcentaje or porcentaje == 0 or not base:
            return Decimal('0.00')

        monto = (Decimal(str(base)) * Decimal(str(porcentaje))) / Decimal('100')
        return monto.quantize(Decimal('0.01'))

    @staticmethod
    def crear_retencion(
        tipo: str,
        porcentaje: Decimal,
        base: Decimal,
        documento_origen_app: str,
        documento_origen_modelo: str,
        documento_origen_id: int,
        configuracion: Optional[ConfiguracionRetenciones] = None,
        aplicada_por_cliente: bool = False,
        aplicada_por_proveedor: bool = False,
        notas: str = '',
    ) -> Retencion:
        """
        Crea un nuevo registro de retención.

        Args:
            tipo: RETEFUENTE, RETEICA, RETEIVA
            porcentaje: Tasa aplicada (ej: 3.5)
            base: Monto base
            documento_origen_app: ej: 'facturas'
            documento_origen_modelo: ej: 'Factura', 'ItemFactura', 'DocumentoSoporte'
            documento_origen_id: ej: 123
            configuracion: ConfiguracionRetenciones usada (opcional)
            aplicada_por_cliente: Si es requerida por el cliente
            aplicada_por_proveedor: Si es requerida por el proveedor
            notas: Notas de auditoría

        Returns:
            Retencion creada (sin guardar si quieres hacer cambios)
        """
        monto = RetencionesService.calcular_monto_retencion(tipo, porcentaje, base)

        retencion = Retencion(
            tipo=tipo,
            porcentaje=Decimal(str(porcentaje)),
            base=Decimal(str(base)),
            monto=monto,
            documento_origen_app=documento_origen_app,
            documento_origen_modelo=documento_origen_modelo,
            documento_origen_id=documento_origen_id,
            configuracion=configuracion,
            aplicada_por_cliente=aplicada_por_cliente,
            aplicada_por_proveedor=aplicada_por_proveedor,
            notas=notas,
        )

        retencion.save()
        return retencion

    @staticmethod
    def crear_retenciones_desde_dict(
        retenciones_dict: Dict[str, Any],
        documento_origen_app: str,
        documento_origen_modelo: str,
        documento_origen_id: int,
        base: Decimal = None,
    ) -> List[Retencion]:
        """
        Crea múltiples retenciones desde un diccionario.

        Dict esperado (ej: desde ItemFactura o Factura):
        {
            'retefuente': 10.50,  # monto o porcentaje
            'retefuente_porcentaje': 3.5,  # si existe, usar este
            'reteica': 5.25,
            'reteica_porcentaje': 1.5,
            'reteiva': 0.00,
            'reteiva_porcentaje': 0.00,
        }

        Args:
            retenciones_dict: Dict con montos/porcentajes
            documento_origen_app: ej: 'facturas'
            documento_origen_modelo: ej: 'Factura'
            documento_origen_id: ID del documento
            base: Monto base (si hay porcentajes pero no montos)

        Returns:
            Lista de Retencion creadas
        """
        retenciones = []

        for tipo in ['RETEFUENTE', 'RETEICA', 'RETEIVA']:
            tipo_lower = tipo.lower()
            key_monto = tipo_lower
            key_porcentaje = f'{tipo_lower}_porcentaje'

            # Extraer valores
            monto = retenciones_dict.get(key_monto, Decimal('0.00'))
            porcentaje = retenciones_dict.get(key_porcentaje, Decimal('0.00'))

            if not monto and not porcentaje:
                continue

            # Convertir a Decimal
            monto = Decimal(str(monto or 0))
            porcentaje = Decimal(str(porcentaje or 0))

            # Si hay porcentaje pero no monto, calcular
            if porcentaje and not monto and base:
                monto = RetencionesService.calcular_monto_retencion(tipo, porcentaje, base)

            if monto > 0:
                retencion = RetencionesService.crear_retencion(
                    tipo=tipo,
                    porcentaje=porcentaje,
                    base=base or monto,  # Si no hay base, usar el monto como base
                    documento_origen_app=documento_origen_app,
                    documento_origen_modelo=documento_origen_modelo,
                    documento_origen_id=documento_origen_id,
                )
                retenciones.append(retencion)

        return retenciones

    @staticmethod
    def listar_retenciones_por_documento(
        documento_origen_app: str,
        documento_origen_modelo: str,
        documento_origen_id: int,
        incluir_reversadas: bool = False,
    ) -> List[Retencion]:
        """
        Lista todas las retenciones de un documento específico.

        Args:
            documento_origen_app: ej: 'facturas'
            documento_origen_modelo: ej: 'Factura'
            documento_origen_id: ID del documento
            incluir_reversadas: Si False, excluye reversadas

        Returns:
            Lista de Retencion
        """
        qs = Retencion.objects.filter(
            documento_origen_app=documento_origen_app,
            documento_origen_modelo=documento_origen_modelo,
            documento_origen_id=documento_origen_id,
        )

        if not incluir_reversadas:
            qs = qs.filter(reversada=False)

        return list(qs.order_by('tipo'))

    @staticmethod
    def total_retenciones_por_documento(
        documento_origen_app: str,
        documento_origen_modelo: str,
        documento_origen_id: int,
        tipo: Optional[str] = None,
    ) -> Decimal:
        """
        Suma todos los montos de retención de un documento.

        Args:
            documento_origen_app: ej: 'facturas'
            documento_origen_modelo: ej: 'Factura'
            documento_origen_id: ID del documento
            tipo: Si se especifica, solo suma ese tipo (RETEFUENTE, RETEICA, RETEIVA)

        Returns:
            Total retenido (Decimal)
        """
        qs = Retencion.objects.filter(
            documento_origen_app=documento_origen_app,
            documento_origen_modelo=documento_origen_modelo,
            documento_origen_id=documento_origen_id,
            reversada=False,
        )

        if tipo:
            qs = qs.filter(tipo=tipo)

        result = qs.aggregate(total=Sum('monto'))
        return result['total'] or Decimal('0.00')

    @staticmethod
    def reversar_retencion(
        retencion: Retencion,
        documento_reversada_app: str = None,
        documento_reversada_modelo: str = None,
        documento_reversada_id: int = None,
    ) -> 'Retencion':
        """
        Reversa una retención (típicamente desde una nota de crédito).

        Args:
            retencion: Retencion a reversar
            documento_reversada_app: App del documento que reversa (ej: 'facturas')
            documento_reversada_modelo: Modelo que reversa (ej: 'NotaCredito')
            documento_reversada_id: ID del documento que reversa

        Returns:
            Nueva Retencion de reversal
        """
        if retencion.reversada:
            raise ValueError('Retencion ya está reversada')

        # Crear retención de reversal (monto negativo)
        retencion_reversal = Retencion(
            tipo=retencion.tipo,
            porcentaje=-retencion.porcentaje,  # Negativo para reversal
            base=retencion.base,
            monto=-retencion.monto,  # Negativo
            documento_origen_app=documento_reversada_app or retencion.documento_origen_app,
            documento_origen_modelo=documento_reversada_modelo or retencion.documento_origen_modelo,
            documento_origen_id=documento_reversada_id or retencion.documento_origen_id,
            configuracion=retencion.configuracion,
            aplicada_por_cliente=retencion.aplicada_por_cliente,
            aplicada_por_proveedor=retencion.aplicada_por_proveedor,
            notas=f'Reversal de Retencion#{retencion.uuid}',
        )
        retencion_reversal.save()

        # Marcar original como reversada
        retencion.reversada = True
        retencion.retencion_reversada_por = retencion_reversal
        retencion.save(update_fields=['reversada', 'retencion_reversada_por'])

        return retencion_reversal

    @staticmethod
    def obtener_retencion_por_uuid(uuid: str) -> Optional[Retencion]:
        """
        Obtiene una retención por su UUID.

        Args:
            uuid: UUID de la retención

        Returns:
            Retencion o None
        """
        try:
            return Retencion.objects.get(uuid=uuid)
        except Retencion.DoesNotExist:
            return None
