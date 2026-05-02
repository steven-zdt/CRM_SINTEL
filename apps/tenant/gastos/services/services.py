"""
Servicios de dominio para Gastos (v2.40).
Única fuente de verdad para lógica de negocio de Documento Soporte.
"""
import logging
import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, DecimalField, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.tenant.gastos.models import DocumentoSoporte, Gasto, ItemGasto, ResolucionDIAN
from apps.tenant.proveedores.services.services import ProveedorBusinessService

logger = logging.getLogger(__name__)

# v2.37/v2.40: Campos mínimos para optimización de QuerySets
LIST_FIELDS = ("id", "periodo", "centro_costo", "categoria_contable")
DETAIL_FIELDS = (*LIST_FIELDS, "descripcion", "observaciones", "created_at")


def _normalizar_porcentaje_choice_retefuente(value: Decimal) -> str:
    """Convierte porcentaje en formato UI (4) o base-1 (0.04) a choices del modelo."""
    valor = Decimal(str(value or 0))
    opciones = {
        '0': '0.00',
        '0.00': '0.00',
        '4': '0.04',
        '4.0': '0.04',
        '4.00': '0.04',
        '0.04': '0.04',
        '6': '0.06',
        '6.0': '0.06',
        '6.00': '0.06',
        '0.06': '0.06',
        '10': '0.10',
        '10.0': '0.10',
        '10.00': '0.10',
        '0.10': '0.10',
        '11': '0.11',
        '11.0': '0.11',
        '11.00': '0.11',
        '0.11': '0.11',
    }
    clave = format(valor.normalize(), 'f')
    return opciones.get(clave, '0.00')


def _normalizar_porcentaje_choice_reteica(value: Decimal) -> str:
    """Convierte porcentaje en formato UI (0.966) o base-1 (0.00966) a choices del modelo."""
    valor = Decimal(str(value or 0))
    opciones = {
        '0': '0.00',
        '0.0': '0.00',
        '0.00': '0.00',
        '0.69': '0.0069',
        '0.690': '0.0069',
        '0.0069': '0.0069',
        '0.966': '0.00966',
        '0.9660': '0.00966',
        '0.00966': '0.00966',
        '1.104': '0.01104',
        '1.1040': '0.01104',
        '0.01104': '0.01104',
    }
    clave = format(valor.normalize(), 'f')
    return opciones.get(clave, '0.00')

def normalize_document_number(value: str | None) -> str | None:
    """Limpia y normaliza identificadores legales."""
    if not value: return None
    return re.sub(r'\s+', '', str(value)).strip()

def obtener_resolucion_vigente(empresa: Any) -> ResolucionDIAN | None:
    """
    Obtiene la resolución DIAN vigente para una empresa.
    
    # WARNING: v2.40: SSoT - Solo una resolución vigente por empresa.
    """
    return ResolucionDIAN.objects.filter(
        empresa=empresa,
        vigente=True
    ).first()


def process_gasto_payload(empresa: Any, data: dict[str, Any]) -> dict[str, Any]:
    from apps.tenant.contabilidad.services.contabilidad_business_service import (
        ContabilidadBusinessService,
    )

    if not empresa:
        raise ValidationError("No hay empresa configurada para este tenant.")

    tipo_documento = str(data.get('tipo_documento') or '').strip().upper()
    proveedor_uuid = str(data.get('proveedor_uuid') or data.get('proveedor_id') or '').strip()

    try:
        proveedor_model = apps.get_model('tenant_proveedores', 'Proveedor', require_ready=False)
        tipos_documento_permitidos = {str(choice[0]).upper() for choice in proveedor_model.TIPO_DOCUMENTO}
    except LookupError:
        tipos_documento_permitidos = {'NIT', 'CC', 'CE', 'PA'}

    if not tipo_documento:
        raise ValidationError({'tipo_documento': ['Este campo es obligatorio.']})

    if tipo_documento not in tipos_documento_permitidos:
        raise ValidationError({'tipo_documento': [f'Tipo de documento invalido: {tipo_documento}.']})

    if not proveedor_uuid:
        raise ValidationError({'proveedor_uuid': ['Debe seleccionar un proveedor del directorio.']})

    proveedor_snapshot = GastoService.obtener_snapshot_proveedor(
        empresa=empresa,
        proveedor_uuid=proveedor_uuid,
        tipo_documento=tipo_documento,
    )

    if proveedor_snapshot.get('tipo_documento') and proveedor_snapshot.get('tipo_documento') != tipo_documento:
        raise ValidationError(
            {'tipo_documento': ['El tipo de documento no coincide con el proveedor seleccionado.']}
        )

    resolucion = ResolucionService.validar_resolucion_para_gasto(
        empresa,
        data.get('resolucion_dian'),
    )

    subtotal = Decimal(str(data.get('subtotal', 0)))
    retefuente_porcentaje = Decimal(str(data.get('retefuente_porcentaje', 0) or 0))
    reteica_porcentaje = Decimal(str(data.get('reteica_porcentaje', 0) or 0))
    retefuente_porcentaje_choice = _normalizar_porcentaje_choice_retefuente(retefuente_porcentaje)
    reteica_porcentaje_choice = _normalizar_porcentaje_choice_reteica(reteica_porcentaje)
    cuenta_contable_uuid = str(data.get('cuenta_contable_uuid') or '').strip()

    if not cuenta_contable_uuid:
        raise ValidationError({'cuenta_contable_uuid': ['Este campo es obligatorio.']})

    try:
        cuenta_contable_uuid_normalizado = str(UUID(cuenta_contable_uuid))
    except (ValueError, TypeError):
        raise ValidationError({'cuenta_contable_uuid': ['UUID invalido.']})

    contabilidad_service = ContabilidadBusinessService()
    cuentas_gasto = contabilidad_service.obtener_cuentas_gasto_disponibles(empresa_id=empresa.id)
    cuenta_match = next(
        (
            cuenta for cuenta in cuentas_gasto
            if str(cuenta.get('uuid') or '').strip() == cuenta_contable_uuid_normalizado
        ),
        None
    )

    if not cuenta_match:
        raise ValidationError({
            'cuenta_contable_uuid': [
                'La categoria contable seleccionada no existe, no pertenece al tenant o no es de tipo GASTO.'
            ]
        })

    cuenta_display = str(cuenta_match.get('display') or '').strip()
    cuenta_codigo = str(data.get('cuenta_contable_codigo') or '').strip()
    cuenta_nombre = str(data.get('cuenta_contable_nombre') or '').strip()
    cuenta_display_payload = f"[{cuenta_codigo}] - {cuenta_nombre}" if cuenta_codigo and cuenta_nombre else cuenta_display

    campos_faltantes = []
    if subtotal <= 0:
        campos_faltantes.append('subtotal')
    if not data.get('fecha'):
        campos_faltantes.append('fecha')
    if not data.get('periodo'):
        campos_faltantes.append('periodo')

    if campos_faltantes:
        raise ValidationError({
            field: ['Este campo es obligatorio.'] for field in campos_faltantes
        })

    retenciones = calcular_retenciones(subtotal, retefuente_porcentaje, reteica_porcentaje)
    total_neto_servidor = retenciones['total']
    total_neto_cliente = Decimal(str(data.get('total_neto', 0) or 0))

    ProveedorBusinessService.validar_contexto_gasto(
        empresa_id=empresa.id,
        proveedor_uuid=proveedor_uuid,
        tipo_documento=tipo_documento,
        subtotal=subtotal,
        retefuente_porcentaje=retefuente_porcentaje,
        reteica_porcentaje=reteica_porcentaje,
        total_neto=total_neto_cliente,
    )

    return {
        'proveedor_snapshot': proveedor_snapshot,
        'resolucion': resolucion,
        'subtotal': subtotal,
        'retefuente_porcentaje': retefuente_porcentaje_choice,
        'reteica_porcentaje': reteica_porcentaje_choice,
        'retenciones': retenciones,
        'total_neto_servidor': total_neto_servidor,
        'total_neto_cliente': total_neto_cliente,
        'numero_factura_proveedor': data.get('numero_factura_proveedor', ''),
        'fecha': data.get('fecha'),
        'periodo': data.get('periodo'),
        'centro_costo': data.get('centro_costo', ''),
        'categoria_contable': data.get('categoria_contable') or cuenta_display_payload,
        'cuenta_contable_uuid': cuenta_contable_uuid_normalizado,
        'cuenta_contable_display': cuenta_display_payload,
        'descripcion': data.get('descripcion', ''),
        'observaciones': data.get('observaciones', ''),
        'adjunto': data.get('adjunto'),
    }

@transaction.atomic
def obtener_siguiente_numero_soporte(empresa: Any) -> int:
    """
    Calcula y valida el siguiente consecutivo inmutable.
    
    # WARNING: v2.60: GESTIÓN ATÓMICA DE CONSECUTIVOS - Evita colisiones en concurrencia.
    - Busca automáticamente la resolución vigente usando ResolucionDIAN.objects.filter().
    - No recibe resolución como parámetro para simplificar la API.
    - # WARNING: CRÍTICO: El consecutivo NO puede repetirse (garantizado por UniqueConstraint en modelo).
    - # WARNING: CRÍTICO: Incluye documentos anulados en el cálculo para evitar duplicados.
    - # WARNING: ALINEADO: Usa esta_dentro_de_fecha() del modelo en lugar de esta_vigente().
    - # WARNING: v2.60: Usa select_for_update() para evitar race conditions en alta concurrencia.
    """
    # Buscar automáticamente la resolución vigente con lock para evitar cambios concurrentes
    resolucion = ResolucionDIAN.objects.select_for_update().filter(
        empresa=empresa,
        vigente=True
    ).first()
    
    if not resolucion:
        raise ValidationError("No hay resolución DIAN activa. Configure una resolución primero.")
    
    if not resolucion.vigente or not resolucion.esta_dentro_de_fecha():
        raise ValidationError(f"Resolución {resolucion.numero_resolucion} no válida o expirada.")

    # # WARNING: CRÍTICO: Incluir TODOS los documentos (incluso anulados) para garantizar consecutividad
    # El consecutivo es único por resolución, incluso si el documento está anulado
    # # WARNING: v2.60: select_for_update() previene race conditions al obtener el máximo consecutivo
    ultimo = DocumentoSoporte.objects.select_for_update().filter(
        empresa=empresa, 
        resolucion_dian=resolucion
    ).aggregate(max_val=Max('consecutivo'))['max_val']

    nuevo_numero = (ultimo + 1) if ultimo else resolucion.rango_desde

    if nuevo_numero > resolucion.rango_hasta:
        raise ValidationError(f"Rango de resolución {resolucion.numero_resolucion} agotado.")
    
    # # WARNING: VALIDACIÓN ADICIONAL: Verificar que no exista ya este consecutivo (doble verificación)
    # Aunque el modelo tiene UniqueConstraint, esta validación previene errores antes de intentar guardar
    # # WARNING: v2.60: select_for_update() asegura que no haya cambios concurrentes durante la verificación
    existe = DocumentoSoporte.objects.select_for_update().filter(
        empresa=empresa,
        resolucion_dian=resolucion,
        consecutivo=nuevo_numero
    ).exists()
    
    if existe:
        # Si existe, buscar el siguiente disponible (puede haber saltos por eliminaciones manuales)
        # Pero esto no debería pasar si la restricción única funciona correctamente
        raise ValidationError(
            f"El consecutivo {nuevo_numero} ya existe para la resolución {resolucion.numero_resolucion}. "
            f"Contacte al administrador del sistema."
        )
    
    return nuevo_numero

def qs_list(empresa_id: int, search=None):
    """
    QuerySet optimizado para Tabulator (v2.40).
    
    # WARNING: ALINEADO: Incluye campos necesarios del modelo Gasto y DocumentoSoporte.
    # WARNING: SSoT: Incluye empresa para filtrado y validación.
    # WARNING: v2.40: Soporta búsqueda con parámetro ?search=
    
    # WARNING: CRÍTICO: INCLUYE TODOS LOS DOCUMENTOS (anulados y no anulados).
    - Los documentos anulados DEBEN aparecer en la lista para mantener la secuencia de consecutivos.
    - El consecutivo prevalece en la lista, incluso si el documento está anulado.
    - Solo el summary (get_gastos_summary) excluye documentos anulados del cálculo financiero.
    """
    qs = Gasto.objects.filter(empresa_id=empresa_id).select_related(
        "documento_soporte",
        "empresa"  # # WARNING: SSoT: Incluir empresa para filtrado y validación
    ).only(
        *LIST_FIELDS,
        "empresa",  # # WARNING: SSoT: Campo requerido por el modelo
        "documento_soporte__consecutivo",
        "documento_soporte__prefijo",
        "documento_soporte__vendedor_nombre",
        "documento_soporte__fecha",
        "documento_soporte__total",
        "documento_soporte__activo",  # # WARNING: v2.40: Campo activo
        "documento_soporte__anulado"
    )
    
    # # WARNING: v2.40: Aplicar filtro de búsqueda si se proporciona
    if search:
        qs = qs.filter(
            Q(descripcion__icontains=search) |
            Q(documento_soporte__vendedor_nombre__icontains=search) |
            Q(documento_soporte__prefijo__icontains=search)
        )
    
    return qs

def qs_detail(empresa_id: int):
    """QuerySet optimizado para detalle de gasto filtrado por empresa."""
    return Gasto.objects.filter(empresa_id=empresa_id).select_related(
        "documento_soporte__resolucion_dian",
        "empresa",
    ).only(
        "id",
        "empresa",
        "documento_soporte",
        "periodo",
        "centro_costo",
        "categoria_contable",
        "codigo_contable",
        "descripcion",
        "observaciones",
        "created_at",
        "updated_at",
        "documento_soporte__id",
        "documento_soporte__empresa",
        "documento_soporte__resolucion_dian",
        "documento_soporte__prefijo",
        "documento_soporte__consecutivo",
        "documento_soporte__fecha",
        "documento_soporte__vendedor_nit",
        "documento_soporte__vendedor_nombre",
        "documento_soporte__vendedor_direccion",
        "documento_soporte__vendedor_telefono",
        "documento_soporte__numero_factura_proveedor",
        "documento_soporte__subtotal",
        "documento_soporte__retefuente_porcentaje",
        "documento_soporte__retefuente",
        "documento_soporte__reteica_porcentaje",
        "documento_soporte__reteica",
        "documento_soporte__total",
        "documento_soporte__adjunto",
        "documento_soporte__activo",
        "documento_soporte__anulado",
        "documento_soporte__fecha_anulacion",
        "documento_soporte__created_at",
        "documento_soporte__updated_at",
        "documento_soporte__resolucion_dian__id",
        "documento_soporte__resolucion_dian__numero_resolucion",
        "documento_soporte__resolucion_dian__prefijo",
        "documento_soporte__resolucion_dian__rango_desde",
        "documento_soporte__resolucion_dian__rango_hasta",
        "documento_soporte__resolucion_dian__fecha_resolucion",
        "documento_soporte__resolucion_dian__fecha_inicio",
        "documento_soporte__resolucion_dian__fecha_fin",
        "documento_soporte__resolucion_dian__clave_tecnica",
        "documento_soporte__resolucion_dian__vigente",
        "documento_soporte__resolucion_dian__created_at",
        "documento_soporte__resolucion_dian__updated_at",
    )

@transaction.atomic
def desactivar_gasto_service(gasto_id: int) -> dict[str, Any]:
    """
    Desactiva un gasto (soft-disable).
    
    # WARNING: v2.40: Paso previo obligatorio antes de anular.
    El documento debe estar desactivado para poder anularlo.
    """
    try:
        gasto = Gasto.objects.select_related('documento_soporte').get(pk=gasto_id)
        ds = gasto.documento_soporte
        
        if not ds.activo:
            raise ValidationError("El documento ya se encuentra desactivado.")
        
        if ds.anulado:
            raise ValidationError("No se puede desactivar un documento anulado.")
        
        # Desactivar usando update() para evitar validaciones
        DocumentoSoporte.objects.filter(pk=ds.pk).update(activo=False)
        ds.refresh_from_db()
        
        return {
            "id": gasto.id,
            "numero_documento": ds.numero_documento,
            "activo": False,
            "mensaje": "Documento desactivado correctamente. Ahora puede anularlo si lo desea."
        }
    except Gasto.DoesNotExist:
        raise ValidationError("Gasto no encontrado.")


@transaction.atomic
def anular_gasto_service(gasto_id: int) -> dict[str, Any]:
    """
    Marca un gasto como anulado (Inmutable).
    
    # WARNING: v2.40: REGLA CRÍTICA - Solo se puede anular si está desactivado (activo=False).
    El documento debe desactivarse primero antes de poder anularlo.
    Usa update() directamente para evitar validaciones del modelo.
    """
    try:
        gasto = Gasto.objects.select_related('documento_soporte').get(pk=gasto_id)
        ds = gasto.documento_soporte
        
        # # WARNING: CRÍTICO: Verificar que esté desactivado antes de anular
        if ds.activo:
            raise ValidationError(
                "No se puede anular un documento activo. Debe desactivarlo primero antes de anular."
            )
        
        if ds.anulado:
            raise ValidationError("El documento ya se encuentra anulado.")
        
        # # WARNING: v2.40: Anulación directa usando update() para evitar validaciones
        # Esto evita que se ejecute clean() y las validaciones de total
        fecha_anulacion_actual = timezone.now()
        DocumentoSoporte.objects.filter(pk=ds.pk).update(
            anulado=True,
            fecha_anulacion=fecha_anulacion_actual
        )
        
        # Refrescar el objeto desde la BD para obtener los valores actualizados
        ds.refresh_from_db()
        
        return {
            "id": gasto.id,
            "numero_documento": ds.numero_documento,
            "anulado": True,
            "fecha_anulacion": ds.fecha_anulacion.isoformat()
        }
    except Gasto.DoesNotExist:
        raise ValidationError("Gasto no encontrado.")

def get_gastos_summary(empresa_id: int | None = None) -> dict[str, Any]:
    """
    Calcula totales financieros netos (v2.40).
    Excluye automáticamente registros anulados y desactivados.
    Solo suma documentos activos y no anulados.
    """
    # # WARNING: v2.40: Solo incluir documentos activos y no anulados
    filtros = Q(documento_soporte__anulado=False, documento_soporte__activo=True)
    if empresa_id:
        filtros &= Q(empresa_id=empresa_id)

    res = Gasto.objects.filter(filtros).aggregate(
        sub=Coalesce(Sum('documento_soporte__subtotal', output_field=DecimalField()), Decimal('0.00')),
        rf=Coalesce(Sum('documento_soporte__retefuente', output_field=DecimalField()), Decimal('0.00')),
        ri=Coalesce(Sum('documento_soporte__reteica', output_field=DecimalField()), Decimal('0.00')),
        tot=Coalesce(Sum('documento_soporte__total', output_field=DecimalField()), Decimal('0.00')),
        cant=Count('id')
    )

    return {
        "subtotal_neto": res["sub"],
        "retefuente_neto": res["rf"],  # # WARNING: v2.40: Retefuente independiente
        "reteica_neto": res["ri"],  # # WARNING: v2.40: ReteICA independiente
        "retenciones_neto": res["rf"] + res["ri"],  # Total de retenciones (compatibilidad)
        "total_neto": res["tot"],
        "cantidad": res["cant"]
    }

def materializar_gasto_desde_dto(dto: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Integración con Document Ingest Pipeline (Placeholder v2.40)."""
    return {"message": "Implementar materialización según modelos de tenant_gastos"}, 501


# ======================
# SERVICIO DE RESOLUCIONES DIAN (v2.40)
# ======================

def qs_resolucion_list(empresa_id: int):
    """
    QuerySet optimizado para listado de resoluciones (Tabulator v2.40).
    
    # WARNING: SSoT: Filtrado por empresa para aislamiento multi-tenant.
    """
    return ResolucionDIAN.objects.filter(empresa_id=empresa_id).order_by('-vigente', '-fecha_resolucion')


def qs_resolucion_detail(empresa_id: int, resolucion_id: int):
    """
    QuerySet optimizado para detalle de resolución.
    
    # WARNING: SSoT: Filtrado por empresa para aislamiento multi-tenant.
    """
    return ResolucionDIAN.objects.filter(empresa_id=empresa_id, id=resolucion_id).first()


class ResolucionService:
    """Servicio de dominio para CRUD y vigencias de ResolucionDIAN."""

    @staticmethod
    def _parse_date(date_str):
        from datetime import datetime as dt

        if isinstance(date_str, str):
            try:
                return dt.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return dt.strptime(date_str, '%d-%m-%Y').date()
                except ValueError as exc:
                    raise ValidationError(
                        f"Formato de fecha inválido: {date_str}. Use YYYY-MM-DD o DD-MM-YYYY"
                    ) from exc
        if hasattr(date_str, 'date'):
            return date_str.date() if hasattr(date_str, 'date') else date_str
        return date_str

    @staticmethod
    def obtener_vigente(empresa: Any) -> ResolucionDIAN | None:
        return obtener_resolucion_vigente(empresa)

    @staticmethod
    @transaction.atomic
    def validar_resolucion_para_gasto(empresa: Any, resolucion_id: Any) -> ResolucionDIAN:
        if not resolucion_id:
            raise ValidationError("No hay resolucion DIAN activa. Configure una resolucion primero.")

        try:
            resolucion_id = int(resolucion_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("El ID de resolucion proporcionado no es valido.") from exc

        resolucion = ResolucionDIAN.objects.select_for_update().filter(
            empresa=empresa,
            id=resolucion_id,
        ).first()

        if not resolucion:
            raise ValidationError(
                f"La resolucion seleccionada (ID: {resolucion_id}) no existe o no pertenece a este tenant."
            )

        if not resolucion.esta_dentro_de_fecha():
            raise ValidationError(
                f"Resolucion no valida o expirada. Fecha fin: {resolucion.fecha_fin}"
            )

        return resolucion

    @staticmethod
    @transaction.atomic
    def crear_resolucion(empresa: Any, data: dict[str, Any]) -> ResolucionDIAN:
        vigente = bool(data.get('vigente', True))
        numero_resolucion = str(data.get('numero_resolucion', '')).strip()
        existe_vigente = ResolucionDIAN.objects.filter(empresa=empresa, vigente=True).exists()

        existe = ResolucionDIAN.objects.filter(
            empresa=empresa,
            numero_resolucion=numero_resolucion,
        ).exists()
        if existe:
            raise ValidationError({'numero_resolucion': ['Ya existe una resolucion registrada con este numero.']})

        if not existe_vigente:
            vigente = True

        if vigente and existe_vigente:
            ResolucionDIAN.objects.filter(empresa=empresa, vigente=True).update(vigente=False)

        fecha_resolucion = ResolucionService._parse_date(data['fecha_resolucion'])
        fecha_fin = ResolucionService._parse_date(data['fecha_fin'])

        if fecha_fin <= fecha_resolucion:
            raise ValidationError("La fecha de fin debe ser posterior a la fecha de emisión (inicio).")

        resolucion = ResolucionDIAN(
            empresa=empresa,
            numero_resolucion=numero_resolucion,
            prefijo=data['prefijo'],
            rango_desde=int(data['rango_desde']),
            rango_hasta=int(data['rango_hasta']),
            fecha_resolucion=fecha_resolucion,
            fecha_inicio=fecha_resolucion,
            fecha_fin=fecha_fin,
            clave_tecnica=data.get('clave_tecnica', ''),
            vigente=vigente,
        )
        resolucion.full_clean()
        resolucion.save()
        return resolucion

    @staticmethod
    @transaction.atomic
    def desactivar_resolucion(empresa: Any, resolucion_id: int) -> ResolucionDIAN:
        resolucion = qs_resolucion_detail(empresa.id, resolucion_id)
        if not resolucion:
            raise ValidationError("Resolución no encontrada o no pertenece a esta empresa.")

        resolucion.vigente = False
        resolucion.save(update_fields=['vigente'])
        return resolucion

    @staticmethod
    def puede_eliminar_resolucion(empresa: Any, resolucion_id: int) -> tuple[bool, str]:
        resolucion = qs_resolucion_detail(empresa.id, resolucion_id)
        if not resolucion:
            return False, "Resolución no encontrada o no pertenece a esta empresa."

        conteo_documentos = DocumentoSoporte.objects.filter(resolucion_dian=resolucion).count()
        if conteo_documentos > 0:
            return False, f"No se puede eliminar esta resolución porque tiene {conteo_documentos} documento(s) de soporte asociado(s). Los documentos deben conservar su referencia a la resolución como evidencia legal."

        return True, "La resolución puede ser eliminada."


def crear_resolucion(empresa: Any, data: dict[str, Any]) -> ResolucionDIAN:
    return ResolucionService.crear_resolucion(empresa, data)


def desactivar_resolucion(empresa: Any, resolucion_id: int) -> ResolucionDIAN:
    return ResolucionService.desactivar_resolucion(empresa, resolucion_id)


def calcular_retenciones(subtotal: Decimal, retefuente_porcentaje: str, reteica_porcentaje: str) -> dict[str, Decimal]:
    """Redirige todos los calculos de gasto al service maestro de proveedores."""
    return ProveedorBusinessService.calcular_componentes_retencion(
        subtotal=subtotal,
        retefuente_porcentaje=retefuente_porcentaje,
        reteica_porcentaje=reteica_porcentaje,
    )


def puede_eliminar_resolucion(empresa: Any, resolucion_id: int) -> tuple[bool, str]:
    return ResolucionService.puede_eliminar_resolucion(empresa, resolucion_id)


class GastoService:
    """Facade de dominio para registro atomico de gasto con detalle generico."""

    @staticmethod
    def obtener_snapshot_proveedor(empresa, proveedor_uuid=None, tipo_documento=''):
        """
        Resuelve datos del proveedor exclusivamente desde el directorio de catalogo.
        """
        proveedor_uuid = str(proveedor_uuid or '').strip()
        tipo_documento_normalizado = str(tipo_documento or '').strip().upper()

        if not proveedor_uuid:
            raise ValidationError({'proveedor_uuid': ['Debe seleccionar un proveedor del directorio.']})

        try:
            proveedor_model = apps.get_model('tenant_proveedores', 'Proveedor', require_ready=False)
        except LookupError:
            raise ValidationError({'proveedor_uuid': ['El directorio de proveedores no esta disponible.']})

        proveedor = proveedor_model.objects.filter(
            empresa_id=empresa.id,
            uuid=proveedor_uuid,
        ).only(
            'uuid',
            'tipo_documento',
            'nit',
            'razon_social',
            'direccion',
            'telefono_contacto',
        ).first()

        if not proveedor:
            raise ValidationError({'proveedor_uuid': ['El proveedor seleccionado no existe o no pertenece a la empresa activa.']})

        proveedor_tipo_documento = str(proveedor.tipo_documento or '').strip().upper()
        if tipo_documento_normalizado and proveedor_tipo_documento != tipo_documento_normalizado:
            raise ValidationError({'tipo_documento': ['El tipo de documento no coincide con el proveedor seleccionado.']})

        return {
            'uuid': proveedor.uuid,
            'tipo_documento': proveedor_tipo_documento,
            'nit': str(proveedor.nit or '').strip(),
            'razon_social': str(proveedor.razon_social or '').strip(),
            'direccion': str(proveedor.direccion or '').strip(),
            'telefono': str(proveedor.telefono_contacto or '').strip(),
            'origen': 'catalogo',
        }

    @staticmethod
    def ejecutar_operacion_gasto(data: dict[str, Any], empresa_id: int | None) -> dict[str, Any]:
        """Valida payload de gasto (Zero Trust) y retorna datos normalizados."""
        from apps.tenant.empresa.models import Empresa

        if not empresa_id:
            raise ValidationError({'empresa': ['No hay empresa configurada para este tenant.']})

        empresa = Empresa.objects.filter(id=empresa_id).only('id').first()
        if not empresa:
            raise ValidationError({'empresa': ['Empresa del tenant no encontrada.']})

        data_original = dict(data or {})
        payload = process_gasto_payload(empresa, data_original)
        payload_unificado = {**data_original, **payload}
        logger.info(
            '[gasto:contabilidad] Sincronizacion de categoria exitosa. empresa_id=%s cuenta_contable_uuid=%s',
            empresa_id,
            payload.get('cuenta_contable_uuid')
        )

        return {
            'payload': payload_unificado,
            'total_neto': payload.get('total_neto_servidor', Decimal('0')),
        }

    @staticmethod
    @transaction.atomic
    def registrar_gasto_total(empresa, data: dict[str, Any]) -> Gasto:
        """
        Registra un gasto completo: ResolucionDIAN + consecutivo + DocumentoSoporte + Gasto + ItemGasto
        dentro de un unico bloque transaction.atomic().

        Args:
            empresa: Instancia de Empresa del tenant actual.
            data: Diccionario con datos del gasto y documento soporte.

        Returns:
            Gasto creado con DocumentoSoporte asociado.

        Raises:
            ValidationError: Campos faltantes, resolucion invalida, formula incorrecta.
            IntegrityError: Consecutivo duplicado (propagada desde la BD).
        """
        payload = process_gasto_payload(empresa, data)
        proveedor = payload['proveedor_snapshot']
        resolucion = payload['resolucion']

        # --- 2. Calcular y validar consecutivo atomico ---
        ultimo = DocumentoSoporte.objects.select_for_update().filter(
            empresa=empresa, resolucion_dian=resolucion
        ).aggregate(max_val=Max('consecutivo'))['max_val']

        consecutivo = (ultimo + 1) if ultimo else resolucion.rango_desde

        if consecutivo > resolucion.rango_hasta:
            raise ValidationError(
                f"El rango de la resolucion {resolucion.numero_resolucion} se ha agotado. "
                f"Rango disponible: {resolucion.rango_desde}-{resolucion.rango_hasta}"
            )

        if DocumentoSoporte.objects.select_for_update().filter(
            empresa=empresa, resolucion_dian=resolucion, consecutivo=consecutivo
        ).exists():
            raise ValidationError(
                f"Consecutivo duplicado: {consecutivo} ya existe para la "
                f"resolucion {resolucion.numero_resolucion}."
            )

        # --- 3. Validar campos obligatorios ---
        subtotal = payload['subtotal']
        retefuente_porcentaje = payload['retefuente_porcentaje']
        reteica_porcentaje = payload['reteica_porcentaje']

        # --- 4. Calcular retenciones matematicas (Zero Trust: no confiar en cliente) ---
        retenciones = payload['retenciones']

        retefuente_monto = retenciones['retefuente']
        reteica_monto = retenciones['reteica']

        # Validar que el total_neto calculado en el servidor coincida con el enviado por el cliente (margen de error 0.01)
        total_neto_servidor = payload.get('total_neto_servidor', Decimal('0'))
        total_neto_cliente = payload.get('total_neto_cliente', Decimal('0'))
        diferencia = abs(total_neto_servidor - total_neto_cliente)
        if diferencia > Decimal('0.01'):
            raise ValidationError(
                f"Error de validacion: El total neto calculado en el servidor ({total_neto_servidor}) "
                f"no coincide con el enviado por el cliente ({total_neto_cliente}). "
                f"Diferencia: {diferencia}. Margen permitido: 0.01"
            )

        # --- 5. Crear DocumentoSoporte ---
        documento_soporte = DocumentoSoporte.objects.create(
            empresa=empresa,
            resolucion_dian=resolucion,
            prefijo=resolucion.prefijo,
            consecutivo=consecutivo,
            fecha=payload['fecha'],
            vendedor_nit=proveedor['nit'],
            vendedor_nombre=proveedor['razon_social'],
            vendedor_direccion=proveedor['direccion'] or '',
            vendedor_telefono=proveedor['telefono'] or '',
            numero_factura_proveedor=payload['numero_factura_proveedor'],
            subtotal=subtotal,
            retefuente_porcentaje=retefuente_porcentaje,
            retefuente=retefuente_monto,
            reteica_porcentaje=reteica_porcentaje,
            reteica=reteica_monto,
            total=total_neto_servidor,
            adjunto=payload['adjunto']
        )
        documento_soporte.refresh_from_db()

        # --- 6. Crear Gasto ---
        gasto = Gasto.objects.create(
            empresa=empresa,
            documento_soporte=documento_soporte,
            proveedor_uuid=proveedor.get('uuid'),
            proveedor_nit_snapshot=proveedor['nit'],
            proveedor_razon_social_snapshot=proveedor['razon_social'],
            proveedor_origen=proveedor['origen'],
            numero_factura_proveedor=payload['numero_factura_proveedor'],
            periodo=payload['periodo'],
            centro_costo=payload['centro_costo'],
            categoria_contable=payload['categoria_contable'],
            cuenta_contable_uuid=payload['cuenta_contable_uuid'],
            descripcion=payload['descripcion'],
            observaciones=payload['observaciones']
        )

        # --- 7. Crear ItemGasto automatico ---
        descripcion_item = str(
            payload.get('descripcion')
            or payload.get('observaciones')
            or payload.get('categoria_contable')
            or f"Gasto - {proveedor.get('razon_social') or 'Proveedor'}"
        ).strip()

        ItemGasto.objects.create(
            gasto=gasto,
            empresa=empresa,
            descripcion=descripcion_item[:255],
            cantidad=Decimal('1.00'),
            valor_unitario=subtotal,
            total_linea=subtotal,
        )

        # --- 8. Hook contable (materializar_asiento_desde_gasto) ---
        if documento_soporte.activo and not documento_soporte.anulado:
            try:
                from apps.tenant.contabilidad.services.asientos_service import (
                    materializar_asiento_desde_gasto,
                )
                materializar_asiento_desde_gasto(gasto)
                logger.info(
                    "[gastos.service] Asiento contable materializado para gasto %s",
                    documento_soporte.numero_documento
                )
            except Exception as e:
                # Aislamiento Gradual: No fallar la creacion si falla la materializacion
                logger.warning(
                    "[gastos.service] Error al materializar asiento desde gasto %s: %s",
                    documento_soporte.numero_documento, str(e)
                )

        return gasto
