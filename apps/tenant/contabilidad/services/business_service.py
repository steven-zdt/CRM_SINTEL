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

from django.db.models import Q
from django.utils import timezone

from apps.tenant.contabilidad.models import AsientoContable, CatalogoMaestroNIIF, CuentaContable, MovimientoContable, PeriodoContable, TipoComprobante
from apps.tenant.contabilidad.services.selectors import verificar_periodo_cerrado
from apps.tenant.contabilidad.services.crud_service import ContabilidadCRUDService

logger = logging.getLogger(__name__)


class ContabilidadBusinessService:
    """Servicio de orquestación y reglas de negocio contable."""

    def __init__(self):
        self.crud = ContabilidadCRUDService()

    # ============================================================================
    # HELPERS DE RESOLUCIÓN DE CUENTAS
    # ============================================================================

    def _obtener_cuenta_por_codigo(self, empresa_id: int, codigo: str) -> Optional[CuentaContable]:
        """Busca una cuenta por su código exacto."""
        return CuentaContable.objects.filter(
            empresa_id=empresa_id,
            codigo=codigo,
            activa=True,
        ).only('id', 'codigo', 'nombre', 'nivel', 'empresa_id').first()

    _DIGITO_TIPO = {
        '1': 'ACTIVO', '2': 'PASIVO', '3': 'PATRIMONIO',
        '4': 'INGRESO', '5': 'GASTO', '6': 'GASTO',
    }

    def _obtener_o_crear_cuenta(self, empresa_id: int, codigo: str) -> CuentaContable:
        """
        Obtiene CuentaContable por codigo; si no existe la crea automaticamente:
        1. Desde CatalogoMaestroNIIF si esta disponible (nombre y nivel correctos)
        2. Infiriendo propiedades desde la estructura del codigo PUC Colombia
        Esto permite usar cualquier codigo PUC valido sin requerir carga previa del plan.
        """
        cuenta = CuentaContable.objects.filter(
            empresa_id=empresa_id, codigo=codigo, activa=True,
        ).only('id', 'codigo', 'nivel').first()
        if cuenta:
            return cuenta

        catalogo = CatalogoMaestroNIIF.objects.filter(codigo=codigo).only(
            'id', 'codigo', 'nombre', 'nivel', 'naturaleza'
        ).first()
        if catalogo:
            nombre = catalogo.nombre
            nivel = catalogo.nivel
        else:
            nombre = f'Cuenta {codigo}'
            nivel = len(codigo)

        tipo = self._DIGITO_TIPO.get(codigo[0] if codigo else '', 'GASTO')

        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.filter(id=empresa_id).only('id').first()
        if not empresa:
            raise ValidationError({'lineas': f'Empresa id={empresa_id} no encontrada.'})

        cuenta, _ = CuentaContable.objects.get_or_create(
            empresa_id=empresa_id,
            codigo=codigo,
            defaults={'empresa': empresa, 'nombre': nombre, 'tipo': tipo, 'nivel': nivel, 'activa': True},
        )
        return cuenta

    def _normalizar_movimientos(self, empresa_id: int, movimientos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normaliza movimientos de UI/API a cuenta_id + cuenta_codigo y aplica DSV.
        Acepta cuenta_id, cuenta o cuenta_codigo como entrada.
        """
        normalizados = []
        for idx, mov in enumerate(movimientos, start=1):
            cuenta_id = mov.get('cuenta_id') or mov.get('cuenta')
            cuenta_codigo = str(mov.get('cuenta_codigo') or '').strip()

            qs = CuentaContable.objects.filter(empresa_id=empresa_id, activa=True)
            if cuenta_id:
                cuenta = qs.filter(id=cuenta_id).only('id', 'codigo', 'nombre', 'nivel', 'empresa_id').first()
            elif cuenta_codigo:
                cuenta = qs.filter(codigo=cuenta_codigo).only('id', 'codigo', 'nombre', 'nivel', 'empresa_id').first()
            else:
                raise ValidationError({'movimientos': f'La linea {idx} no tiene cuenta contable asignada.'})

            if not cuenta:
                raise ValidationError({'movimientos': f'La cuenta de la linea {idx} no existe o no pertenece a la empresa activa.'})
            if cuenta.nivel != 6:
                raise ValidationError({'movimientos': f'La cuenta {cuenta.codigo} no es auxiliar nivel 6.'})

            debe = Decimal(str(mov.get('debe', 0) or 0))
            haber = Decimal(str(mov.get('haber', 0) or 0))
            if debe == Decimal('0') and haber == Decimal('0'):
                raise ValidationError({'movimientos': f'La linea {idx} debe tener debito o credito mayor a cero.'})
            if debe > Decimal('0') and haber > Decimal('0'):
                raise ValidationError({'movimientos': f'La linea {idx} no puede tener debito y credito simultaneamente.'})

            normalizados.append({
                **mov,
                'cuenta_id': cuenta.id,
                'cuenta_codigo': cuenta.codigo,
                'debe': debe,
                'haber': haber,
            })
        return normalizados

    def _generar_numero_asiento(self, prefijo: str = 'ASI') -> str:
        """Genera un número canónico para asientos manuales/API."""
        import uuid as _uuid
        return f"{prefijo}-{timezone.now().strftime('%Y%m%d')}-{str(_uuid.uuid4())[:8].upper()}"

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
        if not payload.get('numero'):
            payload['numero'] = self._generar_numero_asiento()

        # 1. Validaciones semánticas
        movimientos = self._normalizar_movimientos(empresa_id, movimientos)
        self._validar_periodo(fecha, empresa_id)
        self._validar_cuadratura(movimientos, estado)

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
            payload['movimientos'] = self._normalizar_movimientos(asiento.empresa_id, payload['movimientos'])
            self._validar_cuadratura(payload['movimientos'], payload.get('estado', asiento.estado))

        # 3. Persistencia vía CRUD
        asiento = self.crud.actualizar_asiento(asiento_id, payload, payload.get('movimientos'))
        
        return {'id': asiento.id, 'uuid': str(asiento.uuid), 'status': 'updated'}

    @transaction.atomic
    def eliminar_asiento(self, asiento_id: int) -> Dict[str, Any]:
        """Elimina un asiento sin restriccion de estado (movimientos por CASCADE)."""
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
            
        # Validar periodos anteriores abiertos
        periodos_abiertos = PeriodoContable.objects.filter(
            empresa_id=empresa_id,
            periodo__lt=periodo_val,
            estado='ABIERTO'
        ).order_by('periodo')
        if periodos_abiertos.exists():
            primer_abierto = periodos_abiertos.first().periodo
            raise ValidationError({
                'periodo': f'No se puede crear el periodo {periodo_val} porque existe un periodo anterior ({primer_abierto}) abierto. Debe cerrarlo primero.'
            })

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

    @transaction.atomic
    def cerrar_periodo(self, periodo_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Cierra un periodo ABIERTO. Una vez cerrado no se puede reabrir."""
        from apps.tenant.contabilidad.models import PeriodoContable
        periodo = PeriodoContable.objects.get(id=periodo_id)
        if periodo.estado == 'CERRADO':
            raise ValidationError({'detail': 'El periodo ya esta cerrado.'})
        data = {'estado': 'CERRADO'}
        observaciones = payload.get('observaciones', '')
        if observaciones:
            data['observaciones'] = observaciones
        periodo = self.crud.actualizar_periodo(periodo_id, data)
        return {'id': periodo.id, 'uuid': str(periodo.uuid), 'status': 'cerrado'}

    # ============================================================================
    # FLUJO MANUAL ON-DEMAND (contabilizacion desde la UI)
    # ============================================================================

    @transaction.atomic
    def contabilizar_documento_manual(self, empresa_id: int, dto) -> Dict[str, Any]:
        """
        Genera un AsientoContable APROBADO a partir de un documento pendiente
        con las cuentas PUC asignadas manualmente por el usuario.

        No pasa por ReglaContable: cada LineaManual trae cuenta_codigo explicita.
        """
        import uuid as _uuid

        # 1. Idempotencia: el documento no puede tener asiento previo
        if AsientoContable.objects.filter(
            empresa_id=empresa_id,
            documento_origen_app=dto.app_label,
            documento_origen_modelo=dto.modelo,
            documento_origen_id=dto.documento_id,
        ).exists():
            raise ValidationError({
                'documento': f'El documento {dto.documento_numero} ya fue contabilizado.'
            })

        # 2. Periodo abierto y correspondencia de fecha
        periodo = PeriodoContable.objects.filter(
            empresa_id=empresa_id,
            uuid=dto.periodo_uuid
        ).first()

        if not periodo:
            raise ValidationError({
                'periodo': 'El periodo contable seleccionado no existe.'
            })

        if periodo.estado != 'ABIERTO':
            raise ValidationError({
                'periodo': f'El periodo contable {periodo.periodo} no esta abierto.'
            })

        if not (periodo.fecha_inicio <= dto.fecha <= periodo.fecha_fin):
            raise ValidationError({
                'fecha': f'La fecha del documento ({dto.fecha}) no corresponde al periodo contable seleccionado {periodo.periodo} ({periodo.fecha_inicio} a {periodo.fecha_fin}).'
            })

        self._validar_periodo(dto.fecha, empresa_id)

        # 3. Resolver cuenta_codigo -> cuenta_id (auto-crea desde catalogo si no existe)
        movimientos = []
        for linea in dto.lineas:
            cuenta = self._obtener_o_crear_cuenta(empresa_id, linea.cuenta_codigo)
            movimientos.append({
                'cuenta_id': cuenta.id,
                'cuenta_codigo': cuenta.codigo,
                'debe': linea.debe,
                'haber': linea.haber,
                'descripcion': linea.descripcion,
                'tercero_nit': linea.tercero_nit,
                'tercero_razon_social': linea.tercero_razon_social,
                'centro_costo_id': linea.centro_costo_id,
            })

        # 4. Cuadratura obligatoria (partida doble)
        self._validar_cuadratura(movimientos, 'APROBADO')

        # 5. Obtener TipoComprobante y generar numero dinámico
        tipo_comprobante = TipoComprobante.objects.filter(
            empresa_id=empresa_id,
            id=dto.tipo_comprobante_id,
            activa=True
        ).first()

        if not tipo_comprobante:
            raise ValidationError({'tipo_comprobante': 'El tipo de comprobante no existe o esta inactivo.'})

        numero = tipo_comprobante.obtener_siguiente_numero()

        # 6. Persistencia via CRUD
        asiento = self.crud.crear_asiento_manual(
            empresa_id=empresa_id,
            data={
                'numero': numero,
                'tipo_comprobante_id': tipo_comprobante.id,
                'periodo_contable_id': periodo.id,
                'fecha': dto.fecha,
                'descripcion': dto.descripcion,
                'estado': 'APROBADO',
                'documento_origen_app': dto.app_label,
                'documento_origen_modelo': dto.modelo,
                'documento_origen_id': dto.documento_id,
                'documento_origen_numero': dto.documento_numero,
            },
            movimientos=movimientos,
        )
        return {'id': asiento.id, 'uuid': str(asiento.uuid), 'numero': asiento.numero}

    @transaction.atomic
    def sincronizar_cuentas_plan(self, empresa_id: int) -> Dict[str, Any]:
        """
        Crea en CuentaContable todas las entradas del CatalogoMaestroNIIF
        que aun no existen para la empresa. Idempotente — no duplica registros.
        Usado por la accion POST /cuentas-contables/sincronizar/.
        """
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.filter(id=empresa_id).first()
        if not empresa:
            raise ValidationError({'detail': 'Empresa no encontrada.'})

        codigos_existentes = set(
            CuentaContable.objects.filter(empresa_id=empresa_id).values_list('codigo', flat=True)
        )

        catalogo = list(
            CatalogoMaestroNIIF.objects.filter(activa=True)
            .values('codigo', 'nombre', 'nivel')
            .order_by('codigo')
        )

        a_crear = []
        for entry in catalogo:
            if entry['codigo'] in codigos_existentes:
                continue
            tipo = self._DIGITO_TIPO.get(entry['codigo'][0] if entry['codigo'] else '', 'GASTO')
            a_crear.append(CuentaContable(
                empresa=empresa,
                empresa_id=empresa_id,
                codigo=entry['codigo'],
                nombre=entry['nombre'],
                tipo=tipo,
                nivel=entry['nivel'],
                activa=True,
            ))

        if a_crear:
            CuentaContable.objects.bulk_create(a_crear, ignore_conflicts=True)

        return {
            'creadas': len(a_crear),
            'total_catalogo': len(catalogo),
            'total_plan': CuentaContable.objects.filter(empresa_id=empresa_id).count(),
        }

    # ============================================================================
    # CATÁLOGO MAESTRO NIIF
    # ============================================================================

    _TIPO_PREFIJO_MAP = {
        'ACTIVO': '1',
        'PASIVO': '2',
        'PATRIMONIO': '3',
        'INGRESO': '4',
        'GASTO': '5',
        'COSTO': '6',
    }

    def buscar_catalogo_niif_por_tipo(self, tipo: str, search: str = '', nivel: Optional[str] = None) -> List[Dict[str, Any]]:
        prefijo = self._TIPO_PREFIJO_MAP.get((tipo or '').upper())
        if not prefijo:
            raise ValidationError({'tipo': f'Tipo "{tipo}" no valido. Opciones: {list(self._TIPO_PREFIJO_MAP)}'})

        qs = CatalogoMaestroNIIF.objects.filter(
            codigo__startswith=prefijo,
            activa=True,
        ).only('id', 'codigo', 'nombre', 'nivel', 'naturaleza')

        if search:
            qs = qs.filter(Q(codigo__icontains=search) | Q(nombre__icontains=search))

        if nivel:
            try:
                qs = qs.filter(nivel=int(nivel))
            except (ValueError, TypeError):
                pass

        return list(qs.values('id', 'codigo', 'nombre', 'nivel', 'naturaleza').order_by('codigo')[:50])

    def materializar_catalogo_niif(self, codigo: str) -> CatalogoMaestroNIIF:
        from apps.tenant.contabilidad.choices.choices import CATALOGO_NIIF_COLOMBIA
        from apps.tenant.empresa.models import Empresa

        catalogo_map = {c[0]: c for c in CATALOGO_NIIF_COLOMBIA}
        if codigo not in catalogo_map:
            raise ValidationError({'codigo': f'Codigo "{codigo}" no encontrado en el catalogo NIIF Colombia'})

        codigo_niif, nombre, nivel, naturaleza = catalogo_map[codigo]
        empresa = Empresa.objects.first()
        if not empresa:
            raise ValidationError({'empresa': 'No se encontro empresa en este schema'})

        cuenta, _ = CatalogoMaestroNIIF.objects.update_or_create(
            codigo=codigo_niif,
            defaults={'nombre': nombre, 'nivel': nivel, 'naturaleza': naturaleza, 'empresa': empresa, 'activa': True},
        )
        return cuenta

    # ============================================================================
    # ORQUESTACIÓN DE INTEGRACIÓN (ETL PULL MODEL)
    # ============================================================================

    def ejecutar_integracion_completa(self, empresa_id: int) -> Dict[str, Any]:
        """
        Ejecuta todos los extractores registrados para sincronizar datos 
        de aplicaciones externas hacia contabilidad.
        
        [ARCHITECTURE v3.5] - Pull Model
        Este método es el punto de entrada para las tareas programadas (Celery)
        o activaciones manuales de sincronización contable.
        """
        from apps.tenant.contabilidad.integracion.extractores import (
            ExtractorGastos, ExtractorFacturas, ExtractorNomina
        )
        
        extractores = [
            ExtractorGastos(empresa_id),
            ExtractorFacturas(empresa_id),
            ExtractorNomina(empresa_id),
        ]
        
        resumen = {
            "empresa_id": empresa_id,
            "extractores": {}
        }
        
        for ext in extractores:
            nombre = ext.__class__.__name__
            try:
                # AbstractExtractor.contabilizar_pendientes handles the loop and Contabilizador
                stats = ext.contabilizar_pendientes()
                resumen["extractores"][nombre] = stats
                logger.info(f"[INTEGRACION] {nombre} completado para empresa {empresa_id}: {stats}")
            except Exception as e:
                logger.exception(f"[INTEGRACION] Fallo crítico en extractor {nombre} para empresa {empresa_id}")
                resumen["extractores"][nombre] = {"error": str(e)}

        return resumen

    # ============================================================================
    # ASISTENTE IA — SUGERENCIA DE LINEAS DE ASIENTO
    # ============================================================================

    _APP_TIPO_LABEL = {
        'facturas': 'Factura de Venta',
        'gastos': 'Compra/Gasto (Documento Soporte)',
        'empleados': 'Nomina (Devengo de empleado)',
        'inventario': 'Movimiento Reciente de Inventario',
    }

    def sugerir_lineas_asiento_ia(self, empresa_id: int, app_label: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Llama al modelo Claude via Anthropic API para sugerir lineas de asiento en partida doble.

        ctx debe contener: numero, subtotal, impuestos, total, tercero_nit, tercero_nombre.
        Retorna lista de dicts con: cuenta_codigo, cuenta_nombre, debe, haber, descripcion.
        Las cuentas sugeridas son validadas contra CuentaContable nivel=6 del tenant.
        """
        import os
        import json

        try:
            import anthropic
        except ImportError:
            raise ValidationError({'ia': 'Paquete anthropic no instalado. Ejecute: pip install anthropic'})

        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            raise ValidationError({'ia': 'ANTHROPIC_API_KEY no configurada en el entorno del servidor.'})

        from apps.tenant.contabilidad.services.selectors import filtrar_cuentas_por_app_origen

        qs_cuentas = CuentaContable.objects.filter(
            empresa_id=empresa_id, activa=True, nivel=6
        ).only('codigo', 'nombre', 'tipo')
        qs_filtrado = filtrar_cuentas_por_app_origen(qs_cuentas, app_label)
        cuentas_txt = '\n'.join(
            f"- {c.codigo}: {c.nombre} ({c.tipo})" for c in qs_filtrado[:50]
        )
        if not cuentas_txt:
            raise ValidationError({'ia': 'No hay cuentas nivel 6 disponibles para este tipo de documento.'})

        tipo_label = self._APP_TIPO_LABEL.get(app_label, app_label)
        prompt = (
            f"Eres un contador experto en NIIF PYMES Colombia con amplio conocimiento del PUC.\n\n"
            f"Documento a contabilizar:\n"
            f"- Tipo: {tipo_label}\n"
            f"- Numero: {ctx.get('numero', 'N/A')}\n"
            f"- Tercero: {ctx.get('tercero_nombre', 'N/A')} (NIT: {ctx.get('tercero_nit', 'N/A')})\n"
            f"- Subtotal: $ {ctx.get('subtotal', '0')}\n"
            f"- Impuestos/Retenciones: $ {ctx.get('impuestos', '0')}\n"
            f"- Total a pagar/cobrar: $ {ctx.get('total', '0')}\n\n"
            f"Cuentas PUC nivel 6 disponibles para {tipo_label}:\n{cuentas_txt}\n\n"
            f"Genera las lineas del asiento contable en partida doble garantizando que "
            f"la suma del Debe sea exactamente igual a la suma del Haber. "
            f"Responde UNICAMENTE con un JSON valido (sin markdown, sin texto adicional):\n"
            f'{{ "lineas": [{{"cuenta_codigo": "string", "debe": 0.00, "haber": 0.00, "descripcion": "string"}}, ...] }}'
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}],
        )

        raw = message.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error('[contabilidad:asistente_ia] JSON invalido de Claude: %s', raw[:200])
            raise ValidationError({'ia': f'La IA retorno un formato inesperado: {exc}'})

        lineas_raw = data.get('lineas', [])
        if not isinstance(lineas_raw, list) or len(lineas_raw) < 2:
            raise ValidationError({'ia': 'La IA no retorno un asiento valido (minimo 2 lineas).'})

        resultado = []
        for item in lineas_raw:
            codigo = str(item.get('cuenta_codigo', '')).strip()
            if not codigo:
                continue
            cuenta = CuentaContable.objects.filter(
                empresa_id=empresa_id, codigo=codigo, nivel=6, activa=True
            ).only('codigo', 'nombre').first()
            if not cuenta:
                raise ValidationError({'ia': f'La cuenta {codigo} sugerida no existe o no es nivel 6 en este tenant.'})
            resultado.append({
                'cuenta_codigo': cuenta.codigo,
                'cuenta_nombre': cuenta.nombre,
                'debe': float(item.get('debe', 0)),
                'haber': float(item.get('haber', 0)),
                'descripcion': str(item.get('descripcion', '')),
            })

        total_debe = sum(r['debe'] for r in resultado)
        total_haber = sum(r['haber'] for r in resultado)
        if abs(total_debe - total_haber) >= 0.01:
            raise ValidationError({
                'ia': f'El asiento sugerido no cuadra: Debe={total_debe:.2f}, Haber={total_haber:.2f}'
            })

        return resultado
