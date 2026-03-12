"""
Service Layer interno para AsientoContable (dominio Contabilidad).

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Contabilidad.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Estados, aprobar con validación de cuadratura (sumas debe/haber)

⚠️ v2.60: Contabilidad Invisible (Event-Driven)
- materializar_asiento_desde_factura(): Crea asiento automático cuando factura se acepta
- materializar_asiento_desde_gasto(): Crea asiento automático cuando gasto se crea activo
- SSoT: Hereda datos inmutables (NIT, fecha, valores) de facturas/gastos
"""
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
import logging
# ⚠️ v2.61: Importación local de verificar_periodo_cerrado para evitar circular import
# Se importa dentro de las funciones que la necesitan

logger = logging.getLogger(__name__)


# ============================================================================
# FUNCIONES HELPER - Normativa NIIF Colombia
# ============================================================================

def _extraer_tercero_desde_asiento(asiento, movimiento_data=None):
    """
    Extrae datos de tercero desde factura o datos del movimiento.
    
    ⚠️ NORMATIVA: Pobla terceros automáticamente cuando es posible.
    
    Args:
        asiento: Instancia de AsientoContable
        movimiento_data: Diccionario con datos del movimiento (opcional)
    
    Returns:
        dict: {
            'tipo_tercero': str,
            'tercero_id': int,
            'tercero_nit': str,
            'tercero_razon_social': str
        }
    """
    # Estrategia 1: Obtener desde factura relacionada
    if asiento.factura:
        factura = asiento.factura
        if hasattr(factura, 'cliente') and factura.cliente:
            return {
                'tipo_tercero': 'CLIENTE',
                'tercero_id': factura.cliente.id,
                'tercero_nit': factura.cliente.numero_documento,
                'tercero_razon_social': factura.cliente.razon_social
            }
        elif hasattr(factura, 'proveedor') and factura.proveedor:
            return {
                'tipo_tercero': 'PROVEEDOR',
                'tercero_id': factura.proveedor.id,
                'tercero_nit': factura.proveedor.numero_documento,
                'tercero_razon_social': factura.proveedor.razon_social
            }
    
    # Estrategia 2: Obtener desde movimiento_data (si viene del frontend)
    if movimiento_data:
        if 'tipo_tercero' in movimiento_data and movimiento_data['tipo_tercero']:
            return {
                'tipo_tercero': movimiento_data['tipo_tercero'],
                'tercero_id': movimiento_data.get('tercero_id'),
                'tercero_nit': movimiento_data.get('tercero_nit', ''),
                'tercero_razon_social': movimiento_data.get('tercero_razon_social', '')
            }
    
    # Estrategia 3: Usar empresa como tercero genérico (fallback)
    empresa = asiento.empresa
    return {
        'tipo_tercero': 'OTRO',
        'tercero_id': empresa.id,
        'tercero_nit': empresa.nit or '000000000',
        'tercero_razon_social': empresa.razon_social or empresa.nombre
    }


def list_asientos(
    filters: Optional[Dict[str, Any]] = None,
    ordering: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Lista asientos contables (paginado).
    
    Args:
        filters: Diccionario con filtros (estado, fecha, search)
        ordering: Campo de ordenamiento (fecha, numero, total_debe, total_haber, created_at)
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.contabilidad.models import AsientoContable
    
    # ⚠️ NORMATIVA: Incluir campos de comprobante en only() para optimización
    qs = AsientoContable.objects.only(
        'id', 'numero', 'fecha', 'descripcion', 'estado',
        'total_debe', 'total_haber', 'tipo_comprobante', 'numero_comprobante', 'created_at'
    )
    
    # Aplicar filtros
    if filters:
        if 'estado' in filters:
            qs = qs.filter(estado=filters['estado'])
        if 'fecha' in filters:
            qs = qs.filter(fecha=filters['fecha'])
        if 'search' in filters:
            search = filters['search']
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(descripcion__icontains=search)
            )
    
    # Aplicar ordenamiento (whitelist)
    ordering_fields = [
        'fecha', 'numero', 'total_debe', 'total_haber', 'created_at',
        '-fecha', '-numero', '-total_debe', '-total_haber', '-created_at'
    ]
    if ordering and ordering in ordering_fields:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('-fecha', '-numero')
    
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    
    results = []
    for asiento in page_obj:
        # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO (alineado con AsientoContableListSerializer)
        results.append({
            'id': asiento.id,
            'numero': asiento.numero,
            'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
            'descripcion': asiento.descripcion,
            'estado': asiento.estado,
            'total_debe': str(asiento.total_debe),
            'total_haber': str(asiento.total_haber),
            'tipo_comprobante': asiento.tipo_comprobante or None,
            'numero_comprobante': asiento.numero_comprobante or None,
            'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        })
    
    return {
        'count': paginator.count,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': results,
    }


@transaction.atomic
def create_asiento(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un asiento contable con sus movimientos.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio completa
    ⚠️ VALIDACIONES: Estados, número único, cuadratura (si estado=APROBADO), periodos cerrados
    ⚠️ VALIDACIÓN DE PERIODOS: Verifica que la fecha no esté en un periodo cerrado
    
    Args:
        data: Diccionario con datos del asiento y movimientos:
            {
                'numero': str,
                'fecha': date,
                'descripcion': str,
                'estado': str,
                'empresa': int (ID),
                'factura': int (ID, opcional),
                'movimientos': [
                    {
                        'cuenta': int (ID),
                        'descripcion': str (opcional),
                        'debe': Decimal,
                        'haber': Decimal
                    },
                    ...
                ]
            }
    
    Returns:
        dict: DTO con datos del asiento creado
    
    Raises:
        rest_framework.exceptions.ValidationError: Si los datos no son válidos (con estructura para error_injector.js)
        ValueError: Si hay errores de negocio
    """
    from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable
    from apps.tenant.empresa.models import Empresa
    from rest_framework.exceptions import ValidationError
    from datetime import datetime
    
    # Extraer movimientos del payload
    movimientos_data = data.pop('movimientos', [])
    
    # Validar que tenga movimientos
    if not movimientos_data:
        raise ValidationError({
            'error': 'asiento_sin_movimientos',
            'message': 'El asiento debe tener al menos un movimiento contable.',
            'missing_fields': ['movimientos'],
            'detalles': {
                'total_movimientos': 0,
                'sugerencia': 'Agregue al menos un movimiento contable (débito o crédito) al asiento.'
            }
        })
    
    # Validar número único
    if 'numero' in data:
        numero = data['numero']
        if not isinstance(numero, str) or len(numero) > 50:
            raise ValidationError({
                'numero': ['El campo "numero" debe ser una cadena de texto de máximo 50 caracteres.']
            })
        if not numero.strip():
            raise ValidationError({
                'numero': ['El campo "numero" no puede estar vacío.']
            })
        if AsientoContable.objects.filter(numero=numero).exists():
            raise ValidationError({
                'numero': [f"Ya existe un asiento con el número '{numero}'."]
            })
    else:
        # Generar número automático si no se proporciona
        from datetime import datetime
        numero = f"AS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data['numero'] = numero
    
    # Validar estado
    estado = data.get('estado', 'BORRADOR')
    estados_validos = ['BORRADOR', 'APROBADO', 'CERRADO']
    if estado not in estados_validos:
        raise ValidationError({
            'estado': [f"El campo 'estado' debe ser uno de: {', '.join(estados_validos)}."]
        })
    
    # ⚠️ v2.60: Validar periodo cerrado
    fecha = data.get('fecha')
    if fecha:
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
                # ⚠️ v2.61: Actualizar data con el objeto date convertido
                data['fecha'] = fecha
            except ValueError:
                raise ValidationError({
                    'fecha': ['Formato de fecha inválido. Use YYYY-MM-DD.']
                })
        
        empresa_id = data.get('empresa')
        if empresa_id:
            # ⚠️ v2.61: Importación local para evitar circular import
            from apps.tenant.contabilidad.services import verificar_periodo_cerrado
            esta_cerrado, periodo = verificar_periodo_cerrado(fecha, empresa_id)
            if esta_cerrado:
                raise ValidationError({
                    'fecha': [f'No se puede crear un asiento en un periodo cerrado ({periodo}).']
                })
    
    # Obtener empresa (SSoT) - Singleton por tenant
    empresa_id = data.get('empresa')
    if not empresa_id:
        # Intentar obtener empresa del tenant actual (singleton)
        try:
            empresa = Empresa.objects.first()
            if not empresa:
                raise ValidationError({
                    'empresa': ['No se encontró una empresa para el tenant actual.']
                })
            data['empresa'] = empresa
        except Exception as e:
            raise ValidationError({
                'empresa': [f'No se pudo determinar la empresa para el asiento: {str(e)}']
            })
    else:
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            data['empresa'] = empresa
        except Empresa.DoesNotExist:
            raise ValidationError({
                'empresa': [f'Empresa con ID {empresa_id} no encontrada.']
            })
    
    # Crear asiento
    asiento = AsientoContable.objects.create(**data)
    
    # Crear movimientos
    total_debe = Decimal('0.00')
    total_haber = Decimal('0.00')
    orden = 1
    
    for mov_data in movimientos_data:
        cuenta_id = mov_data.get('cuenta')
        if not cuenta_id:
            raise ValidationError({
                'movimientos': [f'Movimiento {orden}: El campo "cuenta" es requerido.']
            })
        
        # ⚠️ NORMATIVA: Validar nivel 6 de cuenta
        from apps.tenant.contabilidad.models import CuentaContable
        cuenta = CuentaContable.objects.get(id=cuenta_id)
        if cuenta.nivel != 6:
            raise ValidationError({
                'movimientos': [f'Movimiento {orden}: La cuenta {cuenta.codigo} no es de nivel 6. Solo se permiten registros en cuentas auxiliares (nivel 6).']
            })
        
        debe = Decimal(str(mov_data.get('debe', 0)))
        haber = Decimal(str(mov_data.get('haber', 0)))
        
        # Validar que tenga debe o haber, pero no ambos
        if debe > 0 and haber > 0:
            raise ValidationError({
                'movimientos': [f'Movimiento {orden}: No puede tener débito y crédito simultáneamente.']
            })
        if debe == 0 and haber == 0:
            raise ValidationError({
                'movimientos': [f'Movimiento {orden}: Debe tener débito o crédito mayor a cero.']
            })
        
        # ⚠️ NORMATIVA: Extraer tercero automáticamente
        tercero_data = _extraer_tercero_desde_asiento(asiento, mov_data)
        
        # Crear movimiento con datos de tercero
        MovimientoContable.objects.create(
            asiento=asiento,
            cuenta_id=cuenta_id,
            descripcion=mov_data.get('descripcion', ''),
            debe=debe,
            haber=haber,
            orden=orden,
            # ⚠️ NORMATIVA: Campos de terceros
            tipo_tercero=tercero_data['tipo_tercero'],
            tercero_id=tercero_data['tercero_id'],
            tercero_nit=tercero_data['tercero_nit'],
            tercero_razon_social=tercero_data['tercero_razon_social']
        )
        
        # Los campos tributarios se calculan automáticamente en MovimientoContable.save()
        
        total_debe += debe
        total_haber += haber
        orden += 1
    
    # ⚠️ NORMATIVA: Actualizar totales usando método mejorado del modelo
    asiento.calcular_totales()
    
    # ⚠️ v2.61: Validar cuadratura usando los totales calculados desde la BD (más preciso)
    # Usar Decimal para evitar problemas de precisión de punto flotante
    diferencia = abs(asiento.total_debe - asiento.total_haber)
    
    # ⚠️ v2.60: Validar cuadratura si el estado es APROBADO o CERRADO
    # Para BORRADOR, permitir guardar aunque no cuadre (solo advertir)
    if estado in ['APROBADO', 'CERRADO']:
        if diferencia >= Decimal('0.01'):  # Tolerancia de 0.01 para redondeo
            # Construir error estructurado para error_injector.js
            error_details = {
                'error': 'asiento_no_cuadrado',
                'message': f'El asiento no está cuadrado. Débito: ${asiento.total_debe:,.2f}, Crédito: ${asiento.total_haber:,.2f}. Diferencia: ${diferencia:,.2f}.',
                'missing_fields': ['movimientos'],
                'detalles': {
                    'total_debe': str(asiento.total_debe),
                    'total_haber': str(asiento.total_haber),
                    'diferencia': f'{diferencia:,.2f}',
                    'diferencia_absoluta': f'{diferencia:,.2f}',
                    'tipo_desbalance': 'falta_credito' if asiento.total_debe > asiento.total_haber else 'falta_debito',
                    'valor_faltante': f'{diferencia:,.2f}',
                    'total_movimientos': len(movimientos_data),
                    'sugerencia': f'Agregue un movimiento de {"crédito" if asiento.total_debe > asiento.total_haber else "débito"} por ${diferencia:,.2f} o ajuste los movimientos existentes.'
                }
            }
            raise ValidationError(error_details)
    
    # Guardar asiento con totales actualizados
    asiento.save(update_fields=['total_debe', 'total_haber'])
    
    # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO
    # ⚠️ v2.61: Asegurar que fecha sea un objeto date antes de llamar isoformat()
    # Recargar desde BD para asegurar que tenga el tipo correcto
    asiento.refresh_from_db()
    fecha_str = None
    if asiento.fecha:
        if isinstance(asiento.fecha, str):
            # Si es string, convertir a date primero
            try:
                fecha_obj = datetime.strptime(asiento.fecha, '%Y-%m-%d').date()
                fecha_str = fecha_obj.isoformat()
            except (ValueError, AttributeError):
                fecha_str = str(asiento.fecha)
        else:
            # Si es date, usar isoformat() directamente
            fecha_str = asiento.fecha.isoformat()
    
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': fecha_str,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'tipo_comprobante': asiento.tipo_comprobante or None,
        'numero_comprobante': asiento.numero_comprobante or None,
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        'updated_at': asiento.updated_at.isoformat() if asiento.updated_at else None,
    }


@transaction.atomic
def update_asiento(asiento_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza un asiento contable y sus movimientos.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio completa
    ⚠️ VALIDACIONES: Estados, número único, cuadratura (si estado=APROBADO), periodos cerrados
    ⚠️ VALIDACIÓN DE PERIODOS: Verifica que la fecha no esté en un periodo cerrado
    ⚠️ INMUTABILIDAD: Si el asiento está APROBADO o CERRADO, no se puede editar
    
    Args:
        asiento_id: ID del asiento
        data: Diccionario con campos a actualizar y movimientos (opcional):
            {
                'numero': str (opcional),
                'fecha': date (opcional),
                'descripcion': str (opcional),
                'estado': str (opcional),
                'movimientos': [
                    {
                        'cuenta': int (ID),
                        'descripcion': str (opcional),
                        'debe': Decimal,
                        'haber': Decimal
                    },
                    ...
                ] (opcional - si se proporciona, reemplaza todos los movimientos)
            }
    
    Returns:
        dict: DTO con datos del asiento actualizado
    
    Raises:
        rest_framework.exceptions.ValidationError: Si los datos no son válidos (con estructura para error_injector.js)
        AsientoContable.DoesNotExist: Si el asiento no existe
    """
    from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable
    from rest_framework.exceptions import ValidationError
    from datetime import datetime
    
    asiento = AsientoContable.objects.select_related('empresa').prefetch_related('movimientos').get(id=asiento_id)
    
    # ⚠️ v2.60: Validar inmutabilidad - No se puede editar asientos aprobados o cerrados
    if asiento.estado in ['APROBADO', 'CERRADO']:
        raise ValidationError({
            'estado': [f'No se puede editar un asiento en estado {asiento.estado}. Solo se pueden editar asientos en estado BORRADOR.']
        })
    
    # Extraer movimientos del payload (opcional)
    movimientos_data = data.pop('movimientos', None)
    
    # Validar número único (si se está actualizando)
    if 'numero' in data:
        numero = data['numero']
        if not isinstance(numero, str) or len(numero) > 50:
            raise ValidationError({
                'numero': ['El campo "numero" debe ser una cadena de texto de máximo 50 caracteres.']
            })
        if not numero.strip():
            raise ValidationError({
                'numero': ['El campo "numero" no puede estar vacío.']
            })
        if AsientoContable.objects.filter(numero=numero).exclude(id=asiento_id).exists():
            raise ValidationError({
                'numero': [f"Ya existe otro asiento con el número '{numero}'."]
            })
    
    # Validar estado
    estado = data.get('estado', asiento.estado)
    estados_validos = ['BORRADOR', 'APROBADO', 'CERRADO']
    if estado not in estados_validos:
        raise ValidationError({
            'estado': [f"El campo 'estado' debe ser uno de: {', '.join(estados_validos)}."]
        })
    
    # ⚠️ v2.60: Validar periodo cerrado (si se está actualizando la fecha)
    fecha = data.get('fecha', asiento.fecha)
    if fecha and fecha != asiento.fecha:
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({
                    'fecha': ['Formato de fecha inválido. Use YYYY-MM-DD.']
                })
        
        empresa_id = asiento.empresa.id if asiento.empresa else None
        if empresa_id:
            # ⚠️ v2.61: Importación local para evitar circular import
            from apps.tenant.contabilidad.services import verificar_periodo_cerrado
            esta_cerrado, periodo = verificar_periodo_cerrado(fecha, empresa_id)
            if esta_cerrado:
                raise ValidationError({
                    'fecha': [f'No se puede actualizar un asiento a una fecha en un periodo cerrado ({periodo}).']
                })
    
    # Actualizar campos del asiento
    # ⚠️ NORMATIVA: Incluir campos de comprobante en campos permitidos
    campos_permitidos = ['numero', 'fecha', 'descripcion', 'estado', 'factura', 'tipo_comprobante', 'numero_comprobante']
    update_fields = []
    for campo in campos_permitidos:
        if campo in data:
            setattr(asiento, campo, data[campo])
            update_fields.append(campo)
    
    # Si se proporcionan movimientos, reemplazar todos los existentes
    if movimientos_data is not None:
        # Validar que tenga movimientos
        if not movimientos_data:
            raise ValidationError({
                'error': 'asiento_sin_movimientos',
                'message': 'El asiento debe tener al menos un movimiento contable.',
                'missing_fields': ['movimientos'],
                'detalles': {
                    'total_movimientos': 0,
                    'sugerencia': 'Agregue al menos un movimiento contable (débito o crédito) al asiento.'
                }
            })
        
        # Eliminar movimientos existentes
        asiento.movimientos.all().delete()
        
        # Crear nuevos movimientos
        total_debe = Decimal('0.00')
        total_haber = Decimal('0.00')
        orden = 1
        
        for mov_data in movimientos_data:
            cuenta_id = mov_data.get('cuenta')
            if not cuenta_id:
                raise ValidationError({
                    'movimientos': [f'Movimiento {orden}: El campo "cuenta" es requerido.']
                })
            
            # ⚠️ NORMATIVA: Validar nivel 6 de cuenta
            from apps.tenant.contabilidad.models import CuentaContable
            cuenta = CuentaContable.objects.get(id=cuenta_id)
            if cuenta.nivel != 6:
                raise ValidationError({
                    'movimientos': [f'Movimiento {orden}: La cuenta {cuenta.codigo} no es de nivel 6. Solo se permiten registros en cuentas auxiliares (nivel 6).']
                })
            
            debe = Decimal(str(mov_data.get('debe', 0)))
            haber = Decimal(str(mov_data.get('haber', 0)))
            
            # Validar que tenga debe o haber, pero no ambos
            if debe > 0 and haber > 0:
                raise ValidationError({
                    'movimientos': [f'Movimiento {orden}: No puede tener débito y crédito simultáneamente.']
                })
            if debe == 0 and haber == 0:
                raise ValidationError({
                    'movimientos': [f'Movimiento {orden}: Debe tener débito o crédito mayor a cero.']
                })
            
            # ⚠️ NORMATIVA: Extraer tercero automáticamente
            tercero_data = _extraer_tercero_desde_asiento(asiento, mov_data)
            
            # Crear movimiento con datos de tercero
            MovimientoContable.objects.create(
                asiento=asiento,
                cuenta_id=cuenta_id,
                descripcion=mov_data.get('descripcion', ''),
                debe=debe,
                haber=haber,
                orden=orden,
                # ⚠️ NORMATIVA: Campos de terceros
                tipo_tercero=tercero_data['tipo_tercero'],
                tercero_id=tercero_data['tercero_id'],
                tercero_nit=tercero_data['tercero_nit'],
                tercero_razon_social=tercero_data['tercero_razon_social']
            )
            
            # Los campos tributarios se calculan automáticamente en MovimientoContable.save()
            
            total_debe += debe
            total_haber += haber
            orden += 1
        
        # ⚠️ NORMATIVA: Actualizar totales usando método mejorado del modelo
        asiento.calcular_totales()
        update_fields.extend(['total_debe', 'total_haber'])
    
    # Guardar cambios
    if update_fields:
        asiento.save(update_fields=update_fields)
    
    # ⚠️ NORMATIVA: Recalcular totales si no se actualizaron movimientos (usar método mejorado)
    if movimientos_data is None:
        asiento.calcular_totales()
        asiento.save(update_fields=['total_debe', 'total_haber'])
    
    # ⚠️ v2.60: Validar cuadratura si el estado es APROBADO
    if estado == 'APROBADO':
        diferencia = abs(float(asiento.total_debe) - float(asiento.total_haber))
        if diferencia > 0.01:
            # Construir error estructurado para error_injector.js
            error_details = {
                'error': 'asiento_no_cuadrado',
                'message': f'El asiento no está cuadrado. Débito: ${asiento.total_debe:.2f}, Crédito: ${asiento.total_haber:.2f}. Diferencia: ${diferencia:.2f}.',
                'missing_fields': ['movimientos'],
                'detalles': {
                    'total_debe': str(asiento.total_debe),
                    'total_haber': str(asiento.total_haber),
                    'diferencia': f'{diferencia:.2f}',
                    'diferencia_absoluta': f'{diferencia:.2f}',
                    'tipo_desbalance': 'falta_credito' if asiento.total_debe > asiento.total_haber else 'falta_debito',
                    'valor_faltante': f'{diferencia:.2f}',
                    'total_movimientos': asiento.movimientos.count(),
                    'sugerencia': f'Agregue un movimiento de {"crédito" if asiento.total_debe > asiento.total_haber else "débito"} por ${diferencia:.2f} o ajuste los movimientos existentes.'
                }
            }
            raise ValidationError(error_details)
    
    # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO
    # ⚠️ v2.61: Asegurar que fecha sea un objeto date antes de llamar isoformat()
    # Recargar desde BD para asegurar que tenga el tipo correcto
    asiento.refresh_from_db()
    fecha_str = None
    if asiento.fecha:
        if isinstance(asiento.fecha, str):
            # Si es string, convertir a date primero
            try:
                fecha_obj = datetime.strptime(asiento.fecha, '%Y-%m-%d').date()
                fecha_str = fecha_obj.isoformat()
            except (ValueError, AttributeError):
                fecha_str = str(asiento.fecha)
        else:
            # Si es date, usar isoformat() directamente
            fecha_str = asiento.fecha.isoformat()
    
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': fecha_str,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'tipo_comprobante': asiento.tipo_comprobante or None,
        'numero_comprobante': asiento.numero_comprobante or None,
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        'updated_at': asiento.updated_at.isoformat() if asiento.updated_at else None,
    }


@transaction.atomic
def aprobar_asiento(asiento_id: int) -> Dict[str, Any]:
    """
    Aprueba un asiento contable.
    
    ⚠️ v2.60: Validación detallada de cuadratura con análisis de movimientos.
    ⚠️ VALIDACIÓN: Un asiento solo puede ser aprobado si total_debe == total_haber.
    
    Args:
        asiento_id: ID del asiento
    
    Returns:
        dict: DTO con datos del asiento aprobado o información de error estructurada
    
    Raises:
        AsientoContable.DoesNotExist: Si el asiento no existe
    
    Nota:
        Si el asiento no puede ser aprobado, retorna un dict con 'error' y 'detalles'
        en lugar de lanzar una excepción, para facilitar el manejo en el ViewSet.
    """
    from apps.tenant.contabilidad.models import AsientoContable
    
    asiento = AsientoContable.objects.select_related().prefetch_related('movimientos__cuenta').get(id=asiento_id)
    
    # ⚠️ v2.60: Validar que tenga movimientos
    if not asiento.movimientos.exists():
        return {
            'error': 'asiento_sin_movimientos',
            'message': 'El asiento debe tener al menos un movimiento contable para ser aprobado.',
            'missing_fields': ['movimientos'],
            'detalles': {
                'total_movimientos': 0,
                'sugerencia': 'Agregue al menos un movimiento contable (débito o crédito) al asiento.'
            }
        }
    
    # ⚠️ v2.60: Análisis detallado de cuadratura
    diferencia = float(asiento.total_debe) - float(asiento.total_haber)
    diferencia_abs = abs(diferencia)
    
    if diferencia_abs > 0.01:  # Tolerancia para errores de punto flotante
        # Analizar movimientos para detectar qué cuenta falta o qué valor sobra
        movimientos = asiento.movimientos.select_related('cuenta').all()
        
        # Agrupar por cuenta para detectar desbalances
        cuentas_desbalance = []
        total_debe_movimientos = sum(float(m.debe) for m in movimientos)
        total_haber_movimientos = sum(float(m.haber) for m in movimientos)
        
        for mov in movimientos:
            debe_mov = float(mov.debe)
            haber_mov = float(mov.haber)
            if debe_mov > 0 and haber_mov > 0:
                cuentas_desbalance.append({
                    'cuenta_codigo': mov.cuenta.codigo,
                    'cuenta_nombre': mov.cuenta.nombre,
                    'problema': 'Tiene débito y crédito simultáneamente',
                    'debe': str(debe_mov),
                    'haber': str(haber_mov)
                })
        
        # Construir mensaje detallado
        mensaje_detallado = f'El asiento no está cuadrado. Débito: ${asiento.total_debe:.2f}, Crédito: ${asiento.total_haber:.2f}. Diferencia: ${diferencia_abs:.2f}.'
        
        if diferencia > 0:
            mensaje_detallado += f' Falta ${diferencia_abs:.2f} en crédito.'
            sugerencia = f'Agregue un movimiento de crédito por ${diferencia_abs:.2f} o ajuste los movimientos existentes.'
        else:
            mensaje_detallado += f' Sobra ${diferencia_abs:.2f} en crédito.'
            sugerencia = f'Agregue un movimiento de débito por ${diferencia_abs:.2f} o ajuste los movimientos existentes.'
        
        if cuentas_desbalance:
            mensaje_detallado += ' Además, algunas cuentas tienen débito y crédito simultáneamente.'
        
        return {
            'error': 'asiento_no_cuadrado',
            'message': mensaje_detallado,
            'missing_fields': ['movimientos'],
            'detalles': {
                'total_debe': str(asiento.total_debe),
                'total_haber': str(asiento.total_haber),
                'diferencia': f'{diferencia:.2f}',
                'diferencia_absoluta': f'{diferencia_abs:.2f}',
                'tipo_desbalance': 'falta_credito' if diferencia > 0 else 'falta_debito',
                'valor_faltante': f'{diferencia_abs:.2f}',
                'cuentas_problematicas': cuentas_desbalance,
                'total_movimientos': movimientos.count(),
                'sugerencia': sugerencia
            }
        }
    
    # Si pasa todas las validaciones, aprobar el asiento
    asiento.estado = 'APROBADO'
    asiento.save(update_fields=['estado'])
    
    # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'tipo_comprobante': asiento.tipo_comprobante or None,
        'numero_comprobante': asiento.numero_comprobante or None,
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        'updated_at': asiento.updated_at.isoformat() if asiento.updated_at else None,
    }


@transaction.atomic
@transaction.atomic
def delete_asiento(asiento_id: int) -> None:
    """
    Elimina un asiento contable.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio completa
    ⚠️ VALIDACIONES: Inmutabilidad - No se puede eliminar asientos APROBADOS o CERRADOS
    
    Args:
        asiento_id: ID del asiento
    
    Raises:
        rest_framework.exceptions.ValidationError: Si el asiento no puede ser eliminado
        AsientoContable.DoesNotExist: Si el asiento no existe
    """
    from apps.tenant.contabilidad.models import AsientoContable
    from rest_framework.exceptions import ValidationError
    
    try:
        asiento = AsientoContable.objects.get(id=asiento_id)
    except AsientoContable.DoesNotExist:
        raise ValidationError({
            'detail': [f'Asiento contable con ID {asiento_id} no encontrado.']
        })
    
    # ⚠️ v2.60: Validar inmutabilidad - No se puede eliminar asientos aprobados o cerrados
    if asiento.estado in ['APROBADO', 'CERRADO']:
        raise ValidationError({
            'error': 'validation_error',
            'message': f'No se puede eliminar un asiento en estado {asiento.estado}. Solo se pueden eliminar asientos en estado BORRADOR.',
            'missing_fields': ['estado']
        })
    
    asiento.delete()


def _obtener_cuenta_por_codigo(empresa, codigo: str):
    """
    Helper: Obtiene una cuenta contable por código.
    
    ⚠️ v2.60: SSoT - Busca cuenta por código y empresa.
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        codigo: Código de la cuenta contable
    
    Returns:
        CuentaContable o None
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    try:
        return CuentaContable.objects.get(codigo=codigo, empresa=empresa, activa=True)
    except CuentaContable.DoesNotExist:
        return None


def _obtener_cuenta_por_tipo(empresa, tipo: str):
    """
    Helper: Obtiene una cuenta contable por tipo.
    
    ⚠️ v2.60: SSoT - Busca cuenta por tipo y empresa.
    Usa la primera cuenta activa del tipo especificado.
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        tipo: Tipo de cuenta (ACTIVO, PASIVO, INGRESO, GASTO, PATRIMONIO)
    
    Returns:
        CuentaContable o None
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    try:
        return CuentaContable.objects.filter(
            tipo=tipo, 
            empresa=empresa, 
            activa=True
        ).first()
    except Exception:
        return None


def _obtener_cuenta_por_prefijo(empresa, prefijo: str):
    """
    Helper: Obtiene una cuenta contable por prefijo de código.
    
    ⚠️ v2.60: SSoT - Busca cuenta que comience con el prefijo (ej: "51" para gastos 51xx).
    Útil para buscar cuentas genéricas cuando no hay código exacto.
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        prefijo: Prefijo del código de cuenta (ej: "51", "41")
    
    Returns:
        CuentaContable o None
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    try:
        return CuentaContable.objects.filter(
            codigo__startswith=prefijo,
            empresa=empresa, 
            activa=True
        ).first()
    except Exception:
        return None


# ⚠️ v2.60: Mapeo Automático de Cuentas Contables (Siigo Contador Style)
# Configuración centralizada de códigos de cuenta según tipo de operación
MAPEO_CUENTAS = {
    'VENTA': {
        'clientes': '1305',      # Clientes
        'ingresos': '4135',      # Ingresos
        'iva': '2408',           # IVA por Pagar (si aplica)
    },
    'COMPRA': {
        'compras': '6105',       # Compras
        'proveedores': '2335',   # Costos por Pagar (Proveedores)
        'iva': '2408',           # IVA por Pagar
    },
    'GASTO': {
        'gastos': '5105',        # Gastos (prefijo 51xx)
        'proveedores': '2335',   # Costos por Pagar
        'retefuente': '2365',    # Retefuente
        'reteica': '2368',       # ReteICA
    }
}


@transaction.atomic
def materializar_asiento_desde_factura(factura) -> Dict[str, Any]:
    """
    Materializa automáticamente un asiento contable desde una factura aceptada.
    
    ⚠️ v2.60: Contabilidad Invisible - Event-Driven
    ⚠️ SSoT: Hereda datos inmutables de la factura (NIT, fecha, valores)
    ⚠️ Idempotencia: Si ya existe un asiento para esta factura, no crea otro
    
    Reglas de Negocio:
    - Si naturaleza = VENTA: Debe a Clientes (1305), Haber a Ingresos (41XX)
    - Si naturaleza = COMPRA: Debe a Compras (61XX), Haber a Proveedores (22XX)
    - Incluye IVA si aplica
    
    Args:
        factura: Instancia de Factura (debe estar en estado ACEPTADA)
    
    Returns:
        dict: DTO con datos del asiento creado
    
    Raises:
        ValueError: Si la factura no está en estado ACEPTADA o ya tiene asiento
    """
    from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable
    from apps.tenant.facturas.models import Factura
    
    # Validar estado
    if factura.estado != Factura.Estado.ACEPTADA:
        raise ValueError(f"La factura debe estar en estado ACEPTADA. Estado actual: {factura.estado}")
    
    # ⚠️ Idempotencia: Verificar si ya existe un asiento para esta factura
    if AsientoContable.objects.filter(factura=factura).exists():
        asiento_existente = AsientoContable.objects.get(factura=factura)
        logger.info(f"[asientos.service] Asiento ya existe para factura {factura.numero}: {asiento_existente.numero}")
        # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO
        return {
            'id': asiento_existente.id,
            'numero': asiento_existente.numero,
            'fecha': asiento_existente.fecha.isoformat() if asiento_existente.fecha else None,
            'descripcion': asiento_existente.descripcion,
            'estado': asiento_existente.estado,
            'total_debe': str(asiento_existente.total_debe),
            'total_haber': str(asiento_existente.total_haber),
            'tipo_comprobante': asiento_existente.tipo_comprobante or None,
            'numero_comprobante': asiento_existente.numero_comprobante or None,
            'created_at': asiento_existente.created_at.isoformat() if asiento_existente.created_at else None,
        }
    
    # ⚠️ SSoT: Obtener empresa del tenant
    empresa = factura.empresa
    
    # Generar número de asiento único
    from datetime import datetime
    numero_asiento = f"AS-{factura.numero}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # ⚠️ SSoT: Heredar datos inmutables de la factura
    descripcion = f"Asiento automático desde Factura {factura.numero} - {factura.emisor_razon_social if factura.naturaleza == Factura.Naturaleza.VENTA else factura.receptor_razon_social}"
    
    # ⚠️ NORMATIVA: Crear asiento con comprobante
    asiento = AsientoContable.objects.create(
        numero=numero_asiento,
        fecha=factura.fecha_emision.date() if hasattr(factura.fecha_emision, 'date') else factura.fecha_emision,
        descripcion=descripcion,
        estado='APROBADO',  # ⚠️ Automático: Se crea aprobado porque la factura ya está aceptada
        empresa=empresa,
        factura=factura,
        tipo_comprobante='FVE',  # Factura de Venta Electrónica
        numero_comprobante=factura.numero
    )
    
    # Crear movimientos según naturaleza
    movimientos = []
    orden = 1
    
    if factura.naturaleza == Factura.Naturaleza.VENTA:
        # ⚠️ v2.60: VENTA - Mapeo Siigo Contador Style
        # DB: 1305 (Clientes) / CR: 4135 (Ingresos)
        cuenta_clientes = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['VENTA']['clientes']) or
            _obtener_cuenta_por_tipo(empresa, 'ACTIVO')
        )
        cuenta_ingresos = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['VENTA']['ingresos']) or
            _obtener_cuenta_por_tipo(empresa, 'INGRESO')
        )
        cuenta_iva = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['VENTA']['iva']) or None
        
        if not cuenta_clientes or not cuenta_ingresos:
            raise ValueError(
                f"No se encontraron las cuentas contables necesarias para VENTA. "
                f"Configure: {MAPEO_CUENTAS['VENTA']['clientes']} (Clientes) y "
                f"{MAPEO_CUENTAS['VENTA']['ingresos']} (Ingresos)."
            )
        
        # Movimiento 1: Debe a Clientes (Total factura)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_clientes,
            'debe': factura.total,
            'haber': Decimal('0.00'),
            'descripcion': f"Factura {factura.numero} - {factura.receptor_razon_social}",
            'orden': orden
        })
        orden += 1
        
        # Movimiento 2: Haber a Ingresos (Subtotal)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_ingresos,
            'debe': Decimal('0.00'),
            'haber': factura.subtotal,
            'descripcion': f"Ingresos por venta - Factura {factura.numero}",
            'orden': orden
        })
        orden += 1
        
        # Movimiento 3: Haber a IVA (si aplica)
        if factura.impuestos > 0 and cuenta_iva:
            movimientos.append({
                'asiento': asiento,
                'cuenta': cuenta_iva,
                'debe': Decimal('0.00'),
                'haber': factura.impuestos,
                'descripcion': f"IVA por venta - Factura {factura.numero}",
                'orden': orden
            })
            orden += 1
    
    elif factura.naturaleza == Factura.Naturaleza.COMPRA:
        # ⚠️ v2.60: COMPRA - Mapeo Siigo Contador Style
        # DB: 6105 (Compras) / CR: 2335 (Costos por Pagar)
        cuenta_compras = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['COMPRA']['compras']) or
            _obtener_cuenta_por_tipo(empresa, 'GASTO')
        )
        cuenta_proveedores = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['COMPRA']['proveedores']) or
            _obtener_cuenta_por_tipo(empresa, 'PASIVO')
        )
        cuenta_iva = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['COMPRA']['iva']) or None
        
        if not cuenta_compras or not cuenta_proveedores:
            raise ValueError(
                f"No se encontraron las cuentas contables necesarias para COMPRA. "
                f"Configure: {MAPEO_CUENTAS['COMPRA']['compras']} (Compras) y "
                f"{MAPEO_CUENTAS['COMPRA']['proveedores']} (Costos por Pagar)."
            )
        
        # Movimiento 1: Debe a Compras (Subtotal)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_compras,
            'debe': factura.subtotal,
            'haber': Decimal('0.00'),
            'descripcion': f"Compra - Factura {factura.numero} - {factura.emisor_razon_social}",
            'orden': orden
        })
        orden += 1
        
        # Movimiento 2: Debe a IVA (si aplica)
        if factura.impuestos > 0 and cuenta_iva:
            movimientos.append({
                'asiento': asiento,
                'cuenta': cuenta_iva,
                'debe': factura.impuestos,
                'haber': Decimal('0.00'),
                'descripcion': f"IVA por compra - Factura {factura.numero}",
                'orden': orden
            })
            orden += 1
        
        # Movimiento 3: Haber a Proveedores (Total factura)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_proveedores,
            'debe': Decimal('0.00'),
            'haber': factura.total,
            'descripcion': f"Factura {factura.numero} - {factura.emisor_razon_social}",
            'orden': orden
        })
        orden += 1
    
    # ⚠️ NORMATIVA: Poblar terceros en cada movimiento y crear
    for mov_data in movimientos:
        # Extraer tercero desde factura
        if factura.naturaleza == Factura.Naturaleza.VENTA and hasattr(factura, 'cliente') and factura.cliente:
            tercero_data = {
                'tipo_tercero': 'CLIENTE',
                'tercero_id': factura.cliente.id,
                'tercero_nit': factura.cliente.numero_documento,
                'tercero_razon_social': factura.cliente.razon_social
            }
        elif factura.naturaleza == Factura.Naturaleza.COMPRA and hasattr(factura, 'proveedor') and factura.proveedor:
            tercero_data = {
                'tipo_tercero': 'PROVEEDOR',
                'tercero_id': factura.proveedor.id,
                'tercero_nit': factura.proveedor.numero_documento,
                'tercero_razon_social': factura.proveedor.razon_social
            }
        else:
            tercero_data = {
                'tipo_tercero': 'OTRO',
                'tercero_id': empresa.id,
                'tercero_nit': empresa.nit or '000000000',
                'tercero_razon_social': empresa.razon_social or empresa.nombre
            }
        
        # Agregar terceros al movimiento
        mov_data.update(tercero_data)
        MovimientoContable.objects.create(**mov_data)
    
    # ⚠️ NORMATIVA: Recalcular totales usando método mejorado
    asiento.calcular_totales()
    asiento.save(update_fields=['total_debe', 'total_haber'])
    
    logger.info(f"[asientos.service] Asiento {asiento.numero} materializado desde factura {factura.numero}")
    
    # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'tipo_comprobante': asiento.tipo_comprobante or None,
        'numero_comprobante': asiento.numero_comprobante or None,
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
    }


@transaction.atomic
def materializar_asiento_desde_gasto(gasto) -> Dict[str, Any]:
    """
    Materializa automáticamente un asiento contable desde un gasto activo.
    
    ⚠️ v2.60: Contabilidad Invisible - Event-Driven
    ⚠️ SSoT: Hereda datos inmutables del gasto (NIT, fecha, valores)
    ⚠️ Idempotencia: Si ya existe un asiento para este gasto, no crea otro
    
    Reglas de Negocio:
    - Debe a Gastos (61XX), Haber a Proveedores (22XX)
    - Incluye Retefuente y ReteICA si aplican
    
    Args:
        gasto: Instancia de Gasto (debe estar activo y no anulado)
    
    Returns:
        dict: DTO con datos del asiento creado
    
    Raises:
        ValueError: Si el gasto no está activo o ya tiene asiento
    """
    from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable
    from apps.tenant.gastos.models import Gasto, DocumentoSoporte
    
    # Validar que el gasto esté activo y no anulado
    ds = gasto.documento_soporte
    if not ds.activo:
        raise ValueError(f"El gasto debe estar activo para materializar asiento. Estado: activo={ds.activo}")
    
    if ds.anulado:
        raise ValueError(f"El gasto no puede estar anulado para materializar asiento. Estado: anulado={ds.anulado}")
    
    # ⚠️ Idempotencia: Verificar si ya existe un asiento para este gasto
    # Nota: AsientoContable no tiene FK directa a Gasto, pero podemos usar la descripción
    # Para una mejor implementación, se podría agregar un campo `gasto` al modelo AsientoContable
    # Por ahora, usamos la descripción como identificador
    descripcion_busqueda = f"Asiento automático desde Gasto {ds.numero_documento}"
    if AsientoContable.objects.filter(descripcion__startswith=descripcion_busqueda).exists():
        asiento_existente = AsientoContable.objects.filter(descripcion__startswith=descripcion_busqueda).first()
        logger.info(f"[asientos.service] Asiento ya existe para gasto {ds.numero_documento}: {asiento_existente.numero}")
        # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO
        return {
            'id': asiento_existente.id,
            'numero': asiento_existente.numero,
            'fecha': asiento_existente.fecha.isoformat() if asiento_existente.fecha else None,
            'descripcion': asiento_existente.descripcion,
            'estado': asiento_existente.estado,
            'total_debe': str(asiento_existente.total_debe),
            'total_haber': str(asiento_existente.total_haber),
            'tipo_comprobante': asiento_existente.tipo_comprobante or None,
            'numero_comprobante': asiento_existente.numero_comprobante or None,
            'created_at': asiento_existente.created_at.isoformat() if asiento_existente.created_at else None,
        }
    
    # ⚠️ SSoT: Obtener empresa del tenant
    empresa = ds.empresa
    
    # Generar número de asiento único
    from datetime import datetime
    numero_asiento = f"AS-GASTO-{ds.numero_documento}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # ⚠️ SSoT: Heredar datos inmutables del gasto
    descripcion = f"Asiento automático desde Gasto {ds.numero_documento} - {ds.vendedor_nombre}"
    
    # ⚠️ NORMATIVA: Crear asiento con comprobante
    asiento = AsientoContable.objects.create(
        numero=numero_asiento,
        fecha=ds.fecha,
        descripcion=descripcion,
        estado='APROBADO',  # ⚠️ Automático: Se crea aprobado porque el gasto está activo
        empresa=empresa,
        tipo_comprobante='CE',  # Comprobante de Egreso
        numero_comprobante=ds.numero_documento
    )
    
    # ⚠️ v2.60: GASTO - Mapeo Siigo Contador Style
    # DB: 51xx (Gasto) / CR: 2335 (Costos por Pagar)
    # Retenciones: CR: 2365 (Retefuente) / 2368 (ReteICA)
    movimientos = []
    orden = 1
    
    # Buscar cuentas contables según mapeo Siigo
    cuenta_gastos = (
        _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['gastos']) or
        _obtener_cuenta_por_prefijo(empresa, '51') or
        _obtener_cuenta_por_tipo(empresa, 'GASTO')
    )
    cuenta_proveedores = (
        _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['proveedores']) or
        _obtener_cuenta_por_tipo(empresa, 'PASIVO')
    )
    cuenta_retefuente = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['retefuente']) or None
    cuenta_reteica = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['reteica']) or None
    
    if not cuenta_gastos or not cuenta_proveedores:
        raise ValueError(
            f"No se encontraron las cuentas contables necesarias para GASTO. "
            f"Configure: {MAPEO_CUENTAS['GASTO']['gastos']} (Gastos) y "
            f"{MAPEO_CUENTAS['GASTO']['proveedores']} (Costos por Pagar)."
        )
    
    # Movimiento 1: Debe a Gastos (Subtotal)
    movimientos.append({
        'asiento': asiento,
        'cuenta': cuenta_gastos,
        'debe': ds.subtotal,
        'haber': Decimal('0.00'),
        'descripcion': f"Gasto {ds.numero_documento} - {ds.vendedor_nombre}",
        'orden': orden
    })
    orden += 1
    
    # Movimiento 2: Debe a Retefuente (si aplica)
    if ds.retefuente > 0 and cuenta_retefuente:
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_retefuente,
            'debe': ds.retefuente,
            'haber': Decimal('0.00'),
            'descripcion': f"Retefuente - Gasto {ds.numero_documento}",
            'orden': orden
        })
        orden += 1
    
    # Movimiento 3: Debe a ReteICA (si aplica)
    if ds.reteica > 0 and cuenta_reteica:
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_reteica,
            'debe': ds.reteica,
            'haber': Decimal('0.00'),
            'descripcion': f"ReteICA - Gasto {ds.numero_documento}",
            'orden': orden
        })
        orden += 1
    
    # Movimiento 4: Haber a Proveedores (Total)
    movimientos.append({
        'asiento': asiento,
        'cuenta': cuenta_proveedores,
        'debe': Decimal('0.00'),
        'haber': ds.total,
        'descripcion': f"Gasto {ds.numero_documento} - {ds.vendedor_nombre}",
        'orden': orden
    })
    orden += 1
    
    # ⚠️ NORMATIVA: Poblar terceros en cada movimiento y crear
    for mov_data in movimientos:
        # Extraer tercero desde gasto (vendedor/proveedor)
        if hasattr(ds, 'vendedor_nit') and ds.vendedor_nit:
            # Intentar encontrar proveedor por NIT
            from apps.tenant.proveedores.models import Proveedor
            try:
                proveedor = Proveedor.objects.get(
                    numero_documento=ds.vendedor_nit,
                    empresa=empresa
                )
                tercero_data = {
                    'tipo_tercero': 'PROVEEDOR',
                    'tercero_id': proveedor.id,
                    'tercero_nit': proveedor.numero_documento,
                    'tercero_razon_social': proveedor.razon_social
                }
            except Proveedor.DoesNotExist:
                # Si no existe proveedor, usar datos del documento
                tercero_data = {
                    'tipo_tercero': 'OTRO',
                    'tercero_id': empresa.id,
                    'tercero_nit': ds.vendedor_nit or '000000000',
                    'tercero_razon_social': ds.vendedor_nombre or empresa.razon_social or empresa.nombre
                }
        else:
            # Fallback: usar empresa
            tercero_data = {
                'tipo_tercero': 'OTRO',
                'tercero_id': empresa.id,
                'tercero_nit': empresa.nit or '000000000',
                'tercero_razon_social': empresa.razon_social or empresa.nombre
            }
        
        # Agregar terceros al movimiento
        mov_data.update(tercero_data)
        MovimientoContable.objects.create(**mov_data)
    
    # ⚠️ NORMATIVA: Recalcular totales usando método mejorado
    asiento.calcular_totales()
    asiento.save(update_fields=['total_debe', 'total_haber'])
    
    logger.info(f"[asientos.service] Asiento {asiento.numero} materializado desde gasto {ds.numero_documento}")
    
    # ⚠️ NORMATIVA: Incluir campos de comprobante en DTO
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'tipo_comprobante': asiento.tipo_comprobante or None,
        'numero_comprobante': asiento.numero_comprobante or None,
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
    }


def listar_documentos_sin_asiento(tipo: Optional[str] = None) -> Dict[str, Any]:
    """
    Lista documentos (Facturas y Gastos) que no tienen asiento contable asociado.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio extraída del ViewSet
    ⚠️ Zero Waste: Usa select_related para eficiencia
    
    Args:
        tipo: 'facturas' o 'gastos' (opcional, si no se especifica retorna ambos)
    
    Returns:
        dict: {
            'facturas': [...],
            'gastos': [...]
        }
    """
    from apps.tenant.facturas.models import Factura
    from apps.tenant.gastos.models import Gasto, DocumentoSoporte
    from apps.tenant.contabilidad.models import AsientoContable
    import re
    
    resultado = {
        'facturas': [],
        'gastos': []
    }
    
    # ⚠️ Zero Waste: Obtener IDs de facturas que ya tienen asiento
    facturas_con_asiento = set(
        AsientoContable.objects.filter(factura__isnull=False)
        .values_list('factura_id', flat=True)
    )
    
    # Listar facturas sin asiento
    if not tipo or tipo == 'facturas':
        facturas_qs = Factura.objects.select_related('empresa').filter(
            estado=Factura.Estado.ACEPTADA
        ).exclude(id__in=facturas_con_asiento).order_by('-fecha_emision')[:100]
        
        for factura in facturas_qs:
            resultado['facturas'].append({
                'id': factura.id,
                'numero': factura.numero,
                'fecha': factura.fecha_emision.strftime('%Y-%m-%d') if factura.fecha_emision else '',
                'emisor': factura.emisor_razon_social,
                'receptor': factura.receptor_razon_social,
                'naturaleza': factura.naturaleza,
                'estado': factura.estado,
                'total': str(factura.total),
                'subtotal': str(factura.subtotal),
                'impuestos': str(factura.impuestos),
            })
    
    # ⚠️ Zero Waste: Obtener IDs de gastos que ya tienen asiento (por descripción)
    descripciones_gastos_con_asiento = set(
        AsientoContable.objects.filter(descripcion__startswith='Asiento automático desde Gasto')
        .values_list('descripcion', flat=True)
    )
    
    # Extraer números de documento de las descripciones
    numeros_gastos_con_asiento = set()
    for desc in descripciones_gastos_con_asiento:
        match = re.search(r'Gasto\s+([A-Z0-9-]+)', desc)
        if match:
            numeros_gastos_con_asiento.add(match.group(1))
    
    # Listar gastos sin asiento
    if not tipo or tipo == 'gastos':
        gastos_qs = Gasto.objects.select_related('documento_soporte', 'empresa').filter(
            documento_soporte__activo=True,
            documento_soporte__anulado=False
        ).exclude(documento_soporte__numero_documento__in=numeros_gastos_con_asiento).order_by('-documento_soporte__fecha')[:100]
        
        for gasto in gastos_qs:
            ds = gasto.documento_soporte
            resultado['gastos'].append({
                'id': gasto.id,
                'numero_documento': ds.numero_documento,
                'fecha': ds.fecha.strftime('%Y-%m-%d') if ds.fecha else '',
                'vendedor_nombre': ds.vendedor_nombre,
                'vendedor_nit': ds.vendedor_nit,
                'categoria_contable': gasto.categoria_contable,
                'activo': ds.activo,
                'anulado': ds.anulado,
                'total': str(ds.total),
                'subtotal': str(ds.subtotal),
                'retefuente': str(ds.retefuente),
                'reteica': str(ds.reteica),
            })
    
    return resultado


@transaction.atomic
def crear_asientos_desde_documentos(facturas_ids: List[int], gastos_ids: List[int]) -> Dict[str, Any]:
    """
    Crea asientos contables desde documentos seleccionados.
    
    ⚠️ v2.60: Service Layer Pattern - Lógica de negocio extraída del ViewSet
    ⚠️ Materialización masiva desde documentos
    
    Args:
        facturas_ids: Lista de IDs de facturas
        gastos_ids: Lista de IDs de gastos
    
    Returns:
        dict: {
            'exitosos': [...],
            'errores': [...]
        }
    """
    from apps.tenant.facturas.models import Factura
    from apps.tenant.gastos.models import Gasto
    
    resultado = {
        'exitosos': [],
        'errores': []
    }
    
    # Procesar facturas
    for factura_id in facturas_ids:
        try:
            factura = Factura.objects.get(id=factura_id, estado=Factura.Estado.ACEPTADA)
            asiento = materializar_asiento_desde_factura(factura)
            resultado['exitosos'].append({
                'tipo': 'factura',
                'id': factura_id,
                'numero': factura.numero,
                'asiento_id': asiento['id'],
                'asiento_numero': asiento['numero']
            })
        except Exception as e:
            logger.error(f"Error al crear asiento desde factura {factura_id}: {str(e)}", exc_info=True)
            resultado['errores'].append({
                'tipo': 'factura',
                'id': factura_id,
                'error': str(e)
            })
    
    # Procesar gastos
    for gasto_id in gastos_ids:
        try:
            gasto = Gasto.objects.select_related('documento_soporte').get(id=gasto_id)
            if not gasto.documento_soporte.activo or gasto.documento_soporte.anulado:
                raise ValueError("El gasto debe estar activo y no anulado")
            asiento = materializar_asiento_desde_gasto(gasto)
            resultado['exitosos'].append({
                'tipo': 'gasto',
                'id': gasto_id,
                'numero': gasto.documento_soporte.numero_documento,
                'asiento_id': asiento['id'],
                'asiento_numero': asiento['numero']
            })
        except Exception as e:
            logger.error(f"Error al crear asiento desde gasto {gasto_id}: {str(e)}", exc_info=True)
            resultado['errores'].append({
                'tipo': 'gasto',
                'id': gasto_id,
                'error': str(e)
            })
    
    return resultado