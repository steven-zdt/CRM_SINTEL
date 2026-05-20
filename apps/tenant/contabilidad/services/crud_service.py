"""
CRUD Service para la app contabilidad (v3.5).

[ARCHITECTURE v3.5]
- Persistencia pura y operaciones atómicas.
- Centralización de creación, edición y eliminación.
- Uso estricta de @transaction.atomic.
- Validación de integridad referencial básica.
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional
from django.db import transaction
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from apps.tenant.contabilidad.models import (
    AsientoContable, 
    MovimientoContable, 
    CuentaContable, 
    PeriodoContable
)

class ContabilidadCRUDService:
    """Servicio de persistencia para el dominio contable."""

    @staticmethod
    @transaction.atomic
    def crear_asiento(empresa_id: int, data: Dict[str, Any], movimientos: List[Dict[str, Any]]) -> AsientoContable:
        """Crea un asiento y sus movimientos de forma atómica."""
        # 1. Crear el asiento principal
        asiento = AsientoContable.objects.create(
            empresa_id=empresa_id,
            numero=data.get('numero'),
            fecha=data.get('fecha'),
            descripcion=data.get('descripcion'),
            estado=data.get('estado', 'BORRADOR'),
            tipo_comprobante=data.get('tipo_comprobante'),
            tipo_comprobante_ref_id=data.get('tipo_comprobante_id') or data.get('tipo_comprobante_ref_id') or data.get('tipo_comprobante_ref'),
            numero_comprobante=data.get('numero_comprobante'),
            documento_origen_app=data.get('documento_origen_app'),
            documento_origen_modelo=data.get('documento_origen_modelo'),
            documento_origen_id=data.get('documento_origen_id'),
            documento_origen_numero=data.get('documento_origen_numero')
        )

        # 2. Crear movimientos
        total_debe = Decimal('0.00')
        total_haber = Decimal('0.00')
        
        for idx, mov_data in enumerate(movimientos):
            debe = Decimal(str(mov_data.get('debe', 0)))
            haber = Decimal(str(mov_data.get('haber', 0)))
            
            MovimientoContable.objects.create(
                empresa_id=empresa_id,
                asiento=asiento,
                cuenta_id=mov_data['cuenta_id'],
                cuenta_codigo=mov_data.get('cuenta_codigo', ''),
                orden=idx + 1,
                debe=debe,
                haber=haber,
                descripcion=mov_data.get('descripcion', ''),
                tipo_tercero=mov_data.get('tipo_tercero'),
                tercero_id=mov_data.get('tercero_id'),
                tercero_nit=mov_data.get('tercero_nit', ''),
                tercero_razon_social=mov_data.get('tercero_razon_social', ''),
                base_iva=Decimal(str(mov_data.get('base_iva', 0))),
                iva_generado=Decimal(str(mov_data.get('iva_generado', 0))),
                iva_descontable=Decimal(str(mov_data.get('iva_descontable', 0))),
                retefuente=Decimal(str(mov_data.get('retefuente', 0))),
                reteica=Decimal(str(mov_data.get('reteica', 0)))
            )
            total_debe += debe
            total_haber += haber

        # 3. Actualizar totales del asiento (campos primarios + legados)
        asiento.debe_total = total_debe
        asiento.haber_total = total_haber
        asiento.save(update_fields=['debe_total', 'haber_total', 'total_debe', 'total_haber'])
        
        return asiento

    @staticmethod
    @transaction.atomic
    def actualizar_asiento(asiento_id: int, data: Dict[str, Any], movimientos: Optional[List[Dict[str, Any]]] = None) -> AsientoContable:
        """Actualiza un asiento y opcionalmente reemplaza sus movimientos."""
        asiento = AsientoContable.objects.get(id=asiento_id)
        
        # 1. Actualizar campos básicos
        campos_asiento = [
            'numero', 'fecha', 'descripcion', 'estado', 
            'tipo_comprobante', 'tipo_comprobante_ref_id', 'numero_comprobante',
            'documento_origen_app', 'documento_origen_modelo',
            'documento_origen_id', 'documento_origen_numero'
        ]
        if 'tipo_comprobante_id' in data:
            data['tipo_comprobante_ref_id'] = data.pop('tipo_comprobante_id')
        if 'tipo_comprobante_ref' in data:
            data['tipo_comprobante_ref_id'] = data.pop('tipo_comprobante_ref')
        for campo in campos_asiento:
            if campo in data:
                setattr(asiento, campo, data[campo])
        
        # 2. Si hay movimientos, reemplazarlos
        if movimientos is not None:
            asiento.movimientos.all().delete()
            total_debe = Decimal('0.00')
            total_haber = Decimal('0.00')
            
            for idx, mov_data in enumerate(movimientos):
                debe = Decimal(str(mov_data.get('debe', 0)))
                haber = Decimal(str(mov_data.get('haber', 0)))
                
                MovimientoContable.objects.create(
                    empresa_id=asiento.empresa_id,
                    asiento=asiento,
                    cuenta_id=mov_data['cuenta_id'],
                    cuenta_codigo=mov_data.get('cuenta_codigo', ''),
                    orden=idx + 1,
                    debe=debe,
                    haber=haber,
                    descripcion=mov_data.get('descripcion', ''),
                    tipo_tercero=mov_data.get('tipo_tercero'),
                    tercero_id=mov_data.get('tercero_id'),
                    tercero_nit=mov_data.get('tercero_nit', ''),
                    tercero_razon_social=mov_data.get('tercero_razon_social', ''),
                    base_iva=Decimal(str(mov_data.get('base_iva', 0))),
                    iva_generado=Decimal(str(mov_data.get('iva_generado', 0))),
                    iva_descontable=Decimal(str(mov_data.get('iva_descontable', 0))),
                    retefuente=Decimal(str(mov_data.get('retefuente', 0))),
                    reteica=Decimal(str(mov_data.get('reteica', 0)))
                )
                total_debe += debe
                total_haber += haber
            
            asiento.debe_total = total_debe
            asiento.haber_total = total_haber

        asiento.save()
        return asiento

    @staticmethod
    @transaction.atomic
    def crear_asiento_manual(
        empresa_id: int,
        data: Dict[str, Any],
        movimientos: List[Dict[str, Any]],
    ) -> AsientoContable:
        """
        Crea un asiento desde el flujo manual On-Demand.
        Soporta documento_origen_* para trazabilidad y usa debe_total/haber_total
        (nuevos campos) como fuente de verdad, dejando que save() sincronice los legados.
        """
        asiento = AsientoContable.objects.create(
            empresa_id=empresa_id,
            tipo_comprobante_ref_id=data.get('tipo_comprobante_id'),
            periodo_contable_id=data.get('periodo_contable_id'),
            numero=data['numero'],
            fecha=data['fecha'],
            descripcion=data['descripcion'],
            estado=data.get('estado', 'APROBADO'),
            documento_origen_app=data.get('documento_origen_app', ''),
            documento_origen_modelo=data.get('documento_origen_modelo', ''),
            documento_origen_id=data.get('documento_origen_id'),
            documento_origen_numero=data.get('documento_origen_numero', ''),
            debe_total=Decimal('0.00'),
            haber_total=Decimal('0.00'),
        )

        total_debe = Decimal('0.00')
        total_haber = Decimal('0.00')

        for idx, mov in enumerate(movimientos):
            debe = Decimal(str(mov.get('debe', 0)))
            haber = Decimal(str(mov.get('haber', 0)))
            MovimientoContable.objects.create(
                empresa_id=empresa_id,
                asiento=asiento,
                cuenta_id=mov['cuenta_id'],
                cuenta_codigo=mov.get('cuenta_codigo', ''),
                orden=idx + 1,
                debe=debe,
                haber=haber,
                descripcion=mov.get('descripcion', ''),
                tercero_nit=mov.get('tercero_nit', ''),
                tercero_razon_social=mov.get('tercero_razon_social', ''),
                centro_costo_id=mov.get('centro_costo_id'),
            )
            total_debe += debe
            total_haber += haber

        asiento.debe_total = total_debe
        asiento.haber_total = total_haber
        asiento.save(update_fields=['debe_total', 'haber_total', 'total_debe', 'total_haber'])
        return asiento

    @staticmethod
    @transaction.atomic
    def eliminar_asiento(asiento_id: int) -> bool:
        """Elimina un asiento (los movimientos se eliminan por CASCADE)."""
        asiento = AsientoContable.objects.get(id=asiento_id)
        asiento.delete()
        return True

    @staticmethod
    @transaction.atomic
    def crear_cuenta(empresa_id: int, data: Dict[str, Any]) -> CuentaContable:
        """Crea una cuenta contable."""
        data.pop('empresa_id', None)
        return CuentaContable.objects.create(empresa_id=empresa_id, **data)

    @staticmethod
    @transaction.atomic
    def actualizar_cuenta(cuenta_id: int, data: Dict[str, Any]) -> CuentaContable:
        """Actualiza una cuenta contable."""
        cuenta = CuentaContable.objects.get(id=cuenta_id)
        for field, value in data.items():
            setattr(cuenta, field, value)
        cuenta.save()
        return cuenta

    @staticmethod
    @transaction.atomic
    def crear_periodo(empresa_id: int, data: Dict[str, Any]) -> PeriodoContable:
        """Crea un periodo contable."""
        data.pop('empresa_id', None)
        return PeriodoContable.objects.create(empresa_id=empresa_id, **data)

    @staticmethod
    @transaction.atomic
    def actualizar_periodo(periodo_id: int, data: Dict[str, Any]) -> PeriodoContable:
        """Actualiza un periodo contable (ej. cerrar periodo)."""
        periodo = PeriodoContable.objects.get(id=periodo_id)
        if data.get('estado') == 'CERRADO' and periodo.estado != 'CERRADO':
            periodo.fecha_cierre = now()
            
        for field, value in data.items():
            setattr(periodo, field, value)
        periodo.save()
        return periodo

    @staticmethod
    @transaction.atomic
    def crear_movimiento(empresa_id: int, data: Dict[str, Any]) -> MovimientoContable:
        """Crea un movimiento contable individual."""
        data.pop('empresa_id', None)
        # Asegurar uso de suffixes _id para campos ForeignKey si vienen como IDs
        if 'asiento' in data:
            data['asiento_id'] = data.pop('asiento')
        if 'cuenta' in data:
            data['cuenta_id'] = data.pop('cuenta')
            
        return MovimientoContable.objects.create(empresa_id=empresa_id, **data)

    @staticmethod
    @transaction.atomic
    def actualizar_movimiento(movimiento_id: int, data: Dict[str, Any]) -> MovimientoContable:
        """Actualiza un movimiento contable."""
        movimiento = MovimientoContable.objects.get(id=movimiento_id)
        for field, value in data.items():
            setattr(movimiento, field, value)
        movimiento.save()
        return movimiento

    @staticmethod
    @transaction.atomic
    def eliminar_movimiento(movimiento_id: int) -> bool:
        """Elimina un movimiento contable."""
        movimiento = MovimientoContable.objects.get(id=movimiento_id)
        movimiento.delete()
        return True
