"""
Business Service para la app contabilidad (v3.5).

[ARCHITECTURE v3.5]
- Orquestación de lógica de negocio y validaciones semánticas.
- SSoT para reglas de dominio (Partida Doble, Periodos Cerrados, Inmutabilidad).
- Fachada para operaciones complejas y materialización.
"""
import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.contabilidad.models import AsientoContable, CuentaContable, MovimientoContable
from apps.tenant.contabilidad.services.selectors import verificar_periodo_cerrado
from apps.tenant.contabilidad.services.crud_service import ContabilidadCRUDService

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES DE MAPEO (Normativa NIIF Colombia)
# ============================================================================

MAPEO_CUENTAS = {
    'VENTA': {
        'clientes': '130505',
        'ingresos': '413501',
        'iva': '240801',
    },
    'COMPRA': {
        'compras': '613501',
        'proveedores': '220501',
        'iva': '240802',
    },
    'GASTO': {
        'gastos': '519595',
        'proveedores': '233595',
        'retefuente': '236540',
        'reteica': '236801',
    }
}

class ContabilidadBusinessService:
    """Servicio de orquestación y reglas de negocio contable."""

    def __init__(self):
        self.crud = ContabilidadCRUDService()

    # ============================================================================
    # HELPERS DE RESOLUCIÓN DE CUENTAS
    # ============================================================================

    def _obtener_cuenta_por_codigo(self, empresa_id: int, codigo: str) -> Optional[CuentaContable]:
        """Busca una cuenta por su código exacto."""
        return CuentaContable.objects.filter(empresa_id=empresa_id, codigo=codigo, activa=True).first()

    # ============================================================================
    # VALIDACIONES DE DOMINIO
    # ============================================================================

    def _validar_cuadratura(self, movimientos: List[Dict[str, Any]], estado: str) -> None:
        """Valida que los movimientos cumplan la partida doble si es necesario."""
        if not movimientos:
            if estado != 'BORRADOR':
                raise ValidationError({'movimientos': 'El asiento debe tener al menos un movimiento para este estado.'})
            return

        total_debe = Decimal(str(sum(Decimal(str(m.get('debe', 0))) for m in movimientos)))
        total_haber = Decimal(str(sum(Decimal(str(m.get('haber', 0))) for m in movimientos)))

        if estado in ['APROBADO', 'CERRADO']:
            diferencia = abs(total_debe - total_haber)
            if diferencia >= Decimal('0.01'):
                raise ValidationError({
                    'error': 'asiento_no_cuadrado',
                    'message': f'Desbalance detectado. Debe: {total_debe}, Haber: {total_haber}',
                    'detalles': {
                        'diferencia': str(abs(total_debe - total_haber)),
                        'sugerencia': 'Ajuste los movimientos para que la suma de débitos sea igual a la de créditos.'
                    }
                })

    def _validar_periodo(self, fecha: Any, empresa_id: int) -> None:
        """Valida que la fecha no corresponda a un periodo cerrado."""
        esta_cerrado, periodo = verificar_periodo_cerrado(fecha, empresa_id)
        if esta_cerrado:
            raise ValidationError({'fecha': f'No se pueden realizar movimientos en un periodo cerrado ({periodo}).'})

    def _validar_cuentas_auxiliares(self, movimientos: List[Dict[str, Any]]) -> None:
        """Valida que todas las cuentas sean de nivel 6 (auxiliares)."""
        cuenta_ids = [m['cuenta_id'] for m in movimientos if 'cuenta_id' in m]
        if not cuenta_ids:
            return
            
        cuentas_no_auxiliares = CuentaContable.objects.filter(id__in=cuenta_ids).exclude(nivel=6).only('codigo')
        if cuentas_no_auxiliares.exists():
            codigos = ", ".join([c.codigo for c in cuentas_no_auxiliares])
            raise ValidationError({
                'movimientos': f'Las siguientes cuentas no son auxiliares (nivel 6): {codigos}. '
                               'Solo se permiten registros en cuentas de nivel 6.'
            })

    # ============================================================================
    # ACCIONES DE NEGOCIO
    # ============================================================================

    @transaction.atomic
    def crear_asiento(self, empresa_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Orquesta la creación de un asiento con validaciones de negocio."""
        movimientos = payload.get('movimientos', [])
        estado = payload.get('estado', 'BORRADOR')
        fecha = payload.get('fecha')

        # 1. Validaciones semánticas
        self._validar_periodo(fecha, empresa_id)
        self._validar_cuadratura(movimientos, estado)
        self._validar_cuentas_auxiliares(movimientos)

        # 2. Persistencia vía CRUD
        asiento = self.crud.crear_asiento(empresa_id, payload, movimientos)
        
        return {'id': asiento.id, 'uuid': str(asiento.uuid), 'status': 'success'}

    @transaction.atomic
    def actualizar_asiento(self, asiento_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Orquesta la actualización con validaciones de inmutabilidad."""
        asiento = AsientoContable.objects.get(id=asiento_id)
        
        # 1. Inmutabilidad
        if asiento.estado in ['APROBADO', 'CERRADO']:
            raise ValidationError({'estado': f'No se puede editar un asiento en estado {asiento.estado}.'})

        # 2. Validaciones si se cambia fecha o movimientos
        if 'fecha' in payload:
            self._validar_periodo(payload['fecha'], asiento.empresa_id)
        
        if 'movimientos' in payload:
            self._validar_cuadratura(payload['movimientos'], payload.get('estado', asiento.estado))
            self._validar_cuentas_auxiliares(payload['movimientos'])

        # 3. Persistencia vía CRUD
        asiento = self.crud.actualizar_asiento(asiento_id, payload, payload.get('movimientos'))
        
        return {'id': asiento.id, 'uuid': str(asiento.uuid), 'status': 'updated'}

    @transaction.atomic
    def eliminar_asiento(self, asiento_id: int) -> Dict[str, Any]:
        """Orquesta la eliminación con validaciones de estado."""
        asiento = AsientoContable.objects.get(id=asiento_id)
        
        if asiento.estado in ['APROBADO', 'CERRADO']:
            raise ValidationError({'estado': f'No se puede eliminar un asiento en estado {asiento.estado}.'})

        self.crud.eliminar_asiento(asiento_id)
        return {'status': 'deleted'}

    @transaction.atomic
    def aprobar_asiento(self, asiento_id: int) -> Dict[str, Any]:
        """Cambia el estado de un asiento a APROBADO validando cuadratura."""
        asiento = AsientoContable.objects.prefetch_related('movimientos').get(id=asiento_id)
        
        movimientos_data = [
            {'cuenta_id': m.cuenta_id, 'debe': m.debe, 'haber': m.haber} 
            for m in asiento.movimientos.all()
        ]
        
        self._validar_cuadratura(movimientos_data, 'APROBADO')
        
        asiento.estado = 'APROBADO'
        asiento.save(update_fields=['estado'])
        
        return {'id': asiento.id, 'estado': 'APROBADO'}

    # ============================================================================
    # MATERIALIZACIÓN AUTOMÁTICA
    # ============================================================================

    def listar_documentos_sin_asiento(self, empresa_id: int, tipo: Optional[str] = None) -> Dict[str, Any]:
        """Lista documentos que no tienen asiento contable asociado."""
        from apps.tenant.facturas.models import Factura
        from apps.tenant.gastos.models import Gasto
        import re

        resultado = {'facturas': [], 'gastos': []}

        # Facturas sin asiento
        if not tipo or tipo == 'facturas':
            facturas_con_asiento = AsientoContable.objects.filter(
                empresa_id=empresa_id, factura__isnull=False
            ).values_list('factura_id', flat=True)
            
            facturas_qs = Factura.objects.filter(
                empresa_id=empresa_id,
                estado='ACEPTADA'
            ).exclude(id__in=facturas_con_asiento).order_by('-fecha_emision')[:50]
            
            for f in facturas_qs:
                resultado['facturas'].append({
                    'id': f.id, 'numero': f.numero, 'fecha': str(f.fecha_emision),
                    'total': str(f.total), 'emisor': f.emisor_razon_social
                })

        # Gastos sin asiento
        if not tipo or tipo == 'gastos':
            desc_pattern = 'Asiento automático desde Gasto'
            gastos_con_asiento = AsientoContable.objects.filter(
                empresa_id=empresa_id, descripcion__startswith=desc_pattern
            ).values_list('descripcion', flat=True)
            
            numeros_con_asiento = []
            for d in gastos_con_asiento:
                match = re.search(r'Gasto\s+([A-Z0-9-]+)', d)
                if match:
                    numeros_con_asiento.append(match.group(1))
            
            gastos_qs = Gasto.objects.select_related('documento_soporte').filter(
                empresa_id=empresa_id,
                documento_soporte__activo=True
            ).exclude(documento_soporte__numero_documento__in=numeros_con_asiento).order_by('-documento_soporte__fecha')[:50]
            
            for g in gastos_qs:
                resultado['gastos'].append({
                    'id': g.id, 'numero_documento': g.documento_soporte.numero_documento,
                    'fecha': str(g.documento_soporte.fecha), 'total': str(g.documento_soporte.total),
                    'vendedor': g.documento_soporte.vendedor_nombre
                })

        return resultado

    @transaction.atomic
    def materializar_asiento_desde_factura(self, factura_id: int) -> Dict[str, Any]:
        """Genera el asiento contable automático para una factura aceptada (VENTA/COMPRA)."""
        from apps.tenant.facturas.models import Factura
        factura = Factura.objects.select_related('empresa', 'cliente', 'proveedor').get(id=factura_id)
        
        empresa_id = factura.empresa_id
        asiento_data = {
            'numero': f"AS-FACT-{factura.numero}",
            'fecha': factura.fecha_emision,
            'descripcion': f"Asiento automático desde Factura {factura.numero}",
            'estado': 'APROBADO',
            'factura_id': factura.id,
            'tipo_comprobante': 'FVE' if factura.naturaleza == 'VENTA' else 'FC',
            'numero_comprobante': factura.numero
        }

        # Resolution based on Mapping
        map_key = 'VENTA' if factura.naturaleza == 'VENTA' else 'COMPRA'
        
        c_principal = self._obtener_cuenta_por_codigo(empresa_id, MAPEO_CUENTAS[map_key]['clientes' if map_key == 'VENTA' else 'proveedores'])
        c_contrapartida = self._obtener_cuenta_por_codigo(empresa_id, MAPEO_CUENTAS[map_key]['ingresos' if map_key == 'VENTA' else 'compras'])
        c_iva = self._obtener_cuenta_por_codigo(empresa_id, MAPEO_CUENTAS[map_key]['iva'])

        if not c_principal or not c_contrapartida:
            raise ValidationError(f"Configuración de cuentas para {map_key} incompleta.")

        movimientos = []
        if map_key == 'VENTA':
            # DB: Clientes (Total) / CR: Ingresos (Subtotal), CR: IVA (Impuestos)
            movimientos.append({
                'cuenta_id': c_principal.id, 'debe': factura.total, 'haber': 0,
                'descripcion': f"CXC Factura {factura.numero}",
                'tipo_tercero': 'CLIENTE', 'tercero_id': factura.cliente_id,
                'tercero_nit': factura.cliente.numero_documento, 'tercero_razon_social': factura.cliente.razon_social
            })
            movimientos.append({
                'cuenta_id': c_contrapartida.id, 'debe': 0, 'haber': factura.subtotal,
                'descripcion': f"Ingreso Factura {factura.numero}"
            })
            if factura.impuestos > 0 and c_iva:
                movimientos.append({
                    'cuenta_id': c_iva.id, 'debe': 0, 'haber': factura.impuestos,
                    'descripcion': f"IVA Factura {factura.numero}"
                })
        else: # COMPRA
            # DB: Compras (Subtotal), DB: IVA (Impuestos) / CR: Proveedores (Total)
            movimientos.append({
                'cuenta_id': c_contrapartida.id, 'debe': factura.subtotal, 'haber': 0,
                'descripcion': f"Compra Factura {factura.numero}"
            })
            if factura.impuestos > 0 and c_iva:
                movimientos.append({
                    'cuenta_id': c_iva.id, 'debe': factura.impuestos, 'haber': 0,
                    'descripcion': f"IVA Compra Factura {factura.numero}"
                })
            movimientos.append({
                'cuenta_id': c_principal.id, 'debe': 0, 'haber': factura.total,
                'descripcion': f"CXP Factura {factura.numero}",
                'tipo_tercero': 'PROVEEDOR', 'tercero_id': factura.proveedor_id,
                'tercero_nit': factura.proveedor.numero_documento, 'tercero_razon_social': factura.proveedor.razon_social
            })
        
        asiento = self.crud.crear_asiento(empresa_id, asiento_data, movimientos)
        return {'id': asiento.id, 'numero': asiento.numero, 'status': 'materialized'}

    @transaction.atomic
    def materializar_asiento_desde_gasto(self, gasto_id: int) -> Dict[str, Any]:
        """Genera el asiento contable automático para un gasto con retenciones."""
        from apps.tenant.gastos.models import Gasto
        from apps.tenant.proveedores.models import Proveedor
        
        gasto = Gasto.objects.select_related('documento_soporte', 'empresa').get(id=gasto_id)
        ds = gasto.documento_soporte
        empresa_id = gasto.empresa_id

        # Idempotency check
        asiento_existente = AsientoContable.objects.filter(
            empresa_id=empresa_id,
            tipo_comprobante='CE',
            numero_comprobante=ds.numero_documento
        ).first()

        if asiento_existente:
            return {'id': asiento_existente.id, 'status': 'existing'}

        asiento_data = {
            'numero': f"AS-GASTO-{ds.numero_documento}",
            'fecha': ds.fecha,
            'descripcion': f"Asiento automático desde Gasto {ds.numero_documento}",
            'estado': 'APROBADO',
            'tipo_comprobante': 'CE',
            'numero_comprobante': ds.numero_documento
        }

        # Resolve accounts
        c_gas = self._obtener_cuenta_por_codigo(empresa_id, getattr(gasto, 'codigo_contable', MAPEO_CUENTAS['GASTO']['gastos']))
        c_pro = self._obtener_cuenta_por_codigo(empresa_id, MAPEO_CUENTAS['GASTO']['proveedores'])
        c_rf = self._obtener_cuenta_por_codigo(empresa_id, MAPEO_CUENTAS['GASTO']['retefuente'])
        c_ri = self._obtener_cuenta_por_codigo(empresa_id, MAPEO_CUENTAS['GASTO']['reteica'])

        if not c_gas or not c_pro:
            raise ValidationError("Configuración de cuentas de gasto incompleta.")

        # Tercero resolution
        tercero_data = {}
        if ds.vendedor_nit:
            proveedor = Proveedor.objects.filter(numero_documento=ds.vendedor_nit, empresa_id=empresa_id).first()
            if proveedor:
                tercero_data = {
                    'tipo_tercero': 'PROVEEDOR', 'tercero_id': proveedor.id,
                    'tercero_nit': proveedor.numero_documento, 'tercero_razon_social': proveedor.razon_social
                }

        movimientos = []
        # DB: Gastos (Subtotal)
        movimientos.append({
            'cuenta_id': c_gas.id, 'debe': ds.subtotal, 'haber': 0, 'descripcion': f"Gasto {ds.numero_documento}",
            **tercero_data
        })
        
        # CR: Retefuente / ReteICA if apply
        if ds.retefuente > 0 and c_rf:
            movimientos.append({
                'cuenta_id': c_rf.id, 'debe': 0, 'haber': ds.retefuente, 'descripcion': f"Retefuente Gasto {ds.numero_documento}",
                **tercero_data
            })
        if ds.reteica > 0 and c_ri:
            movimientos.append({
                'cuenta_id': c_ri.id, 'debe': 0, 'haber': ds.reteica, 'descripcion': f"ReteICA Gasto {ds.numero_documento}",
                **tercero_data
            })

        # CR: Proveedores (Total)
        movimientos.append({
            'cuenta_id': c_pro.id, 'debe': 0, 'haber': ds.total, 'descripcion': f"CXP Gasto {ds.numero_documento}",
            **tercero_data
        })

        asiento = self.crud.crear_asiento(empresa_id, asiento_data, movimientos)
        return {'id': asiento.id, 'numero': asiento.numero, 'status': 'materialized'}

    # ============================================================================
    # CRUD CUENTAS (ORQUESTACIÓN)
    # ============================================================================

    @transaction.atomic
    def crear_cuenta(self, empresa_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una cuenta validando unicidad y normativa."""
        codigo = payload.get('codigo', '').strip()
        if CuentaContable.objects.filter(empresa_id=empresa_id, codigo=codigo).exists():
            raise ValidationError({'codigo': f'Ya existe una cuenta con el código {codigo}.'})
            
        cuenta = self.crud.crear_cuenta(empresa_id, payload)
        return {'id': cuenta.id, 'uuid': str(cuenta.uuid), 'status': 'success'}

    @transaction.atomic
    def actualizar_cuenta(self, cuenta_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza una cuenta validando integridad."""
        if 'codigo' in payload:
            cuenta = CuentaContable.objects.get(id=cuenta_id)
            if CuentaContable.objects.filter(empresa_id=cuenta.empresa_id, codigo=payload['codigo']).exclude(id=cuenta_id).exists():
                raise ValidationError({'codigo': 'El código ya está en uso por otra cuenta.'})
                
        cuenta = self.crud.actualizar_cuenta(cuenta_id, payload)
        return {'id': cuenta.id, 'uuid': str(cuenta.uuid), 'status': 'updated'}

    @transaction.atomic
    def eliminar_cuenta(self, cuenta_id: int) -> Dict[str, Any]:
        """Elimina una cuenta si no tiene movimientos ni hijos."""
        cuenta = CuentaContable.objects.get(id=cuenta_id)
        
        if cuenta.cuentas_hijas.exists():
            raise ValidationError({'detail': 'No se puede eliminar una cuenta con subcuentas.'})
            
        if MovimientoContable.objects.filter(cuenta=cuenta).exists():
            raise ValidationError({'detail': 'No se puede eliminar una cuenta con movimientos contables.'})
            
        cuenta.delete()
        return {'status': 'deleted'}

    # ============================================================================
    # CRUD PERIODOS (ORQUESTACIÓN)
    # ============================================================================

    @transaction.atomic
    def crear_periodo(self, empresa_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un periodo validando solapamientos."""
        periodo_val = payload.get('periodo')
        from apps.tenant.contabilidad.models import PeriodoContable
        if PeriodoContable.objects.filter(empresa_id=empresa_id, periodo=periodo_val).exists():
            raise ValidationError({'periodo': f'El periodo {periodo_val} ya existe.'})
            
        periodo = self.crud.crear_periodo(empresa_id, payload)
        return {'id': periodo.id, 'uuid': str(periodo.uuid), 'status': 'success'}

    @transaction.atomic
    def actualizar_periodo(self, periodo_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza un periodo."""
        periodo = self.crud.actualizar_periodo(periodo_id, payload)
        return {'id': periodo.id, 'uuid': str(periodo.uuid), 'status': 'updated'}

    @transaction.atomic
    def eliminar_periodo(self, periodo_id: int) -> Dict[str, Any]:
        """Elimina un periodo si no está cerrado."""
        from apps.tenant.contabilidad.models import PeriodoContable
        periodo = PeriodoContable.objects.get(id=periodo_id)
        if periodo.estado == 'CERRADO':
            raise ValidationError({'detail': 'No se puede eliminar un periodo cerrado.'})
            
        periodo.delete()
        return {'status': 'deleted'}
