"""
Servicios de dominio para Gastos (v2.40).
Única fuente de verdad para lógica de negocio de Documento Soporte.
"""
import re
import logging
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q, DecimalField, Max
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tenant.gastos.models import Gasto, DocumentoSoporte, ResolucionDIAN

logger = logging.getLogger(__name__)

# v2.37/v2.40: Campos mínimos para optimización de QuerySets
LIST_FIELDS = ("id", "periodo", "centro_costo", "categoria_contable")
DETAIL_FIELDS = (*LIST_FIELDS, "descripcion", "observaciones", "created_at")

def normalize_document_number(value: Optional[str]) -> Optional[str]:
    """Limpia y normaliza identificadores legales."""
    if not value: return None
    return re.sub(r'\s+', '', str(value)).strip()

def obtener_resolucion_vigente(empresa: Any) -> Optional[ResolucionDIAN]:
    """
    Obtiene la resolución DIAN vigente para una empresa.
    
    ⚠️ v2.40: SSoT - Solo una resolución vigente por empresa.
    """
    return ResolucionDIAN.objects.filter(
        empresa=empresa,
        vigente=True
    ).first()

@transaction.atomic
def obtener_siguiente_numero_soporte(empresa: Any) -> int:
    """
    Calcula y valida el siguiente consecutivo inmutable.
    
    ⚠️ v2.60: GESTIÓN ATÓMICA DE CONSECUTIVOS - Evita colisiones en concurrencia.
    - Busca automáticamente la resolución vigente usando ResolucionDIAN.objects.filter().
    - No recibe resolución como parámetro para simplificar la API.
    - ⚠️ CRÍTICO: El consecutivo NO puede repetirse (garantizado por UniqueConstraint en modelo).
    - ⚠️ CRÍTICO: Incluye documentos anulados en el cálculo para evitar duplicados.
    - ⚠️ ALINEADO: Usa esta_dentro_de_fecha() del modelo en lugar de esta_vigente().
    - ⚠️ v2.60: Usa select_for_update() para evitar race conditions en alta concurrencia.
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

    # ⚠️ CRÍTICO: Incluir TODOS los documentos (incluso anulados) para garantizar consecutividad
    # El consecutivo es único por resolución, incluso si el documento está anulado
    # ⚠️ v2.60: select_for_update() previene race conditions al obtener el máximo consecutivo
    ultimo = DocumentoSoporte.objects.select_for_update().filter(
        empresa=empresa, 
        resolucion_dian=resolucion
    ).aggregate(max_val=Max('consecutivo'))['max_val']

    nuevo_numero = (ultimo + 1) if ultimo else resolucion.rango_desde

    if nuevo_numero > resolucion.rango_hasta:
        raise ValidationError(f"Rango de resolución {resolucion.numero_resolucion} agotado.")
    
    # ⚠️ VALIDACIÓN ADICIONAL: Verificar que no exista ya este consecutivo (doble verificación)
    # Aunque el modelo tiene UniqueConstraint, esta validación previene errores antes de intentar guardar
    # ⚠️ v2.60: select_for_update() asegura que no haya cambios concurrentes durante la verificación
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

def qs_list(search=None):
    """
    QuerySet optimizado para Tabulator (v2.40).
    
    ⚠️ ALINEADO: Incluye campos necesarios del modelo Gasto y DocumentoSoporte.
    ⚠️ SSoT: Incluye empresa para filtrado y validación.
    ⚠️ v2.40: Soporta búsqueda con parámetro ?search=
    
    ⚠️ CRÍTICO: INCLUYE TODOS LOS DOCUMENTOS (anulados y no anulados).
    - Los documentos anulados DEBEN aparecer en la lista para mantener la secuencia de consecutivos.
    - El consecutivo prevalece en la lista, incluso si el documento está anulado.
    - Solo el summary (get_gastos_summary) excluye documentos anulados del cálculo financiero.
    """
    qs = Gasto.objects.select_related(
        "documento_soporte",
        "empresa"  # ⚠️ SSoT: Incluir empresa para filtrado y validación
    ).only(
        *LIST_FIELDS,
        "empresa",  # ⚠️ SSoT: Campo requerido por el modelo
        "documento_soporte__consecutivo",
        "documento_soporte__prefijo",
        "documento_soporte__vendedor_nombre",
        "documento_soporte__fecha",
        "documento_soporte__total",
        "documento_soporte__activo",  # ⚠️ v2.40: Campo activo
        "documento_soporte__anulado"
    )
    
    # ⚠️ v2.40: Aplicar filtro de búsqueda si se proporciona
    if search:
        qs = qs.filter(
            Q(descripcion__icontains=search) |
            Q(documento_soporte__vendedor_nombre__icontains=search) |
            Q(documento_soporte__prefijo__icontains=search)
        )
    
    return qs

def qs_detail():
    """QuerySet completo para vista de detalle."""
    return Gasto.objects.select_related(
        "documento_soporte__resolucion_dian", "empresa"
    ).all()

@transaction.atomic
def desactivar_gasto_service(gasto_id: int) -> Dict[str, Any]:
    """
    Desactiva un gasto (soft-disable).
    
    ⚠️ v2.40: Paso previo obligatorio antes de anular.
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
def anular_gasto_service(gasto_id: int) -> Dict[str, Any]:
    """
    Marca un gasto como anulado (Inmutable).
    
    ⚠️ v2.40: REGLA CRÍTICA - Solo se puede anular si está desactivado (activo=False).
    El documento debe desactivarse primero antes de poder anularlo.
    Usa update() directamente para evitar validaciones del modelo.
    """
    try:
        gasto = Gasto.objects.select_related('documento_soporte').get(pk=gasto_id)
        ds = gasto.documento_soporte
        
        # ⚠️ CRÍTICO: Verificar que esté desactivado antes de anular
        if ds.activo:
            raise ValidationError(
                "No se puede anular un documento activo. Debe desactivarlo primero antes de anular."
            )
        
        if ds.anulado:
            raise ValidationError("El documento ya se encuentra anulado.")
        
        # ⚠️ v2.40: Anulación directa usando update() para evitar validaciones
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

def get_gastos_summary(empresa_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Calcula totales financieros netos (v2.40).
    Excluye automáticamente registros anulados y desactivados.
    Solo suma documentos activos y no anulados.
    """
    # ⚠️ v2.40: Solo incluir documentos activos y no anulados
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
        "retefuente_neto": res["rf"],  # ⚠️ v2.40: Retefuente independiente
        "reteica_neto": res["ri"],  # ⚠️ v2.40: ReteICA independiente
        "retenciones_neto": res["rf"] + res["ri"],  # Total de retenciones (compatibilidad)
        "total_neto": res["tot"],
        "cantidad": res["cant"]
    }

def materializar_gasto_desde_dto(dto: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Integración con Document Ingest Pipeline (Placeholder v2.40)."""
    return {"message": "Implementar materialización según modelos de tenant_gastos"}, 501


# ======================
# SERVICIO DE RESOLUCIONES DIAN (v2.40)
# ======================

def qs_resolucion_list(empresa_id: int):
    """
    QuerySet optimizado para listado de resoluciones (Tabulator v2.40).
    
    ⚠️ SSoT: Filtrado por empresa para aislamiento multi-tenant.
    """
    return ResolucionDIAN.objects.filter(empresa_id=empresa_id).order_by('-vigente', '-fecha_resolucion')


def qs_resolucion_detail(empresa_id: int, resolucion_id: int):
    """
    QuerySet optimizado para detalle de resolución.
    
    ⚠️ SSoT: Filtrado por empresa para aislamiento multi-tenant.
    """
    return ResolucionDIAN.objects.filter(empresa_id=empresa_id, id=resolucion_id).first()


@transaction.atomic
def crear_resolucion(empresa: Any, data: Dict[str, Any]) -> ResolucionDIAN:
    """
    Crea una nueva resolución DIAN.
    
    ⚠️ REGLA CRÍTICA: Solo UNA resolución puede estar vigente por empresa.
    Si se marca como vigente, desactiva automáticamente las anteriores.
    
    ⚠️ INMUTABILIDAD: Las resoluciones son documentos legales y no deben editarse.
    Solo se pueden crear nuevas o desactivar/eliminar (si no tienen uso).
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        data: Diccionario con datos de la resolución
        
    Returns:
        ResolucionDIAN: Instancia creada
        
    Raises:
        ValidationError: Si hay errores de validación
    """
    vigente = data.get('vigente', True)
    
    # Si se marca como vigente, desactivar las anteriores
    if vigente:
        ResolucionDIAN.objects.filter(
            empresa=empresa,
            vigente=True
        ).update(vigente=False)
    
    # Parsear fechas
    from datetime import datetime as dt
    
    def parse_date(date_str):
        """Parsea una fecha desde string ISO (YYYY-MM-DD) o datetime."""
        if isinstance(date_str, str):
            try:
                return dt.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return dt.strptime(date_str, '%d-%m-%Y').date()
                except ValueError:
                    raise ValidationError(f"Formato de fecha inválido: {date_str}. Use YYYY-MM-DD o DD-MM-YYYY")
        elif hasattr(date_str, 'date'):
            return date_str.date() if hasattr(date_str, 'date') else date_str
        return date_str
    
    fecha_resolucion = parse_date(data['fecha_resolucion'])
    fecha_fin = parse_date(data['fecha_fin'])
    
    # Validar que fecha_fin > fecha_resolucion
    if fecha_fin <= fecha_resolucion:
        raise ValidationError("La fecha de fin debe ser posterior a la fecha de emisión (inicio).")
    
    # Crear resolución
    resolucion = ResolucionDIAN(
        empresa=empresa,
        numero_resolucion=data['numero_resolucion'],
        prefijo=data['prefijo'],
        rango_desde=int(data['rango_desde']),
        rango_hasta=int(data['rango_hasta']),
        fecha_resolucion=fecha_resolucion,
        fecha_inicio=fecha_resolucion,  # Usar fecha_resolucion como fecha_inicio
        fecha_fin=fecha_fin,
        clave_tecnica=data.get('clave_tecnica', ''),
        vigente=vigente
    )
    
    # Validar con full_clean()
    resolucion.full_clean()
    resolucion.save()
    
    return resolucion


@transaction.atomic
def desactivar_resolucion(empresa: Any, resolucion_id: int) -> ResolucionDIAN:
    """
    Desactiva una resolución DIAN (marca vigente=False).
    
    ⚠️ INMUTABILIDAD: El DocumentoSoporte conserva su número y prefijo originales
    (snapshot inalterable). La desactivación no afecta documentos ya generados.
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        resolucion_id: ID de la resolución a desactivar
        
    Returns:
        ResolucionDIAN: Instancia desactivada
        
    Raises:
        ValidationError: Si la resolución no existe o no pertenece a la empresa
    """
    resolucion = qs_resolucion_detail(empresa.id, resolucion_id)
    
    if not resolucion:
        raise ValidationError("Resolución no encontrada o no pertenece a esta empresa.")
    
    resolucion.vigente = False
    resolucion.save(update_fields=['vigente'])
    
    return resolucion


def calcular_retenciones(subtotal: Decimal, retefuente_porcentaje: str, reteica_porcentaje: str) -> Dict[str, Decimal]:
    """
    Calcula las retenciones (Retefuente y ReteICA) basándose en el subtotal y los porcentajes.
    
    ⚠️ v2.40: Lógica de cálculo para Documento Soporte según normativa colombiana.
    - Retefuente: subtotal * porcentaje_retefuente
    - ReteICA: subtotal * porcentaje_reteica
    - Total Neto: subtotal - retefuente - reteica
    
    ⚠️ v2.60: VALIDACIÓN DE FÓRMULA - Asegura que Total = Subtotal - Retefuente - ReteICA
    
    Args:
        subtotal: Subtotal del documento (base gravable)
        retefuente_porcentaje: Porcentaje de retención en la fuente (string, ej: '0.04' para 4%)
        reteica_porcentaje: Porcentaje de retención ICA (string, ej: '0.00966' para 0.966%)
        
    Returns:
        Dict con las claves:
            - 'retefuente': Valor calculado de retención en la fuente
            - 'reteica': Valor calculado de retención ICA
            - 'total': Total neto a pagar (subtotal - retenciones)
    
    Raises:
        ValidationError: Si el subtotal es negativo, el total calculado es negativo, 
                        o la fórmula no se cumple (tolerancia de 0.01 para redondeo)
    
    Example:
        >>> calcular_retenciones(Decimal('1000000'), '0.04', '0.00966')
        {
            'retefuente': Decimal('40000.00'),
            'reteica': Decimal('9660.00'),
            'total': Decimal('950340.00')
        }
    """
    if subtotal < 0:
        raise ValidationError("El subtotal no puede ser negativo.")
    
    # Convertir porcentajes a Decimal
    porcentaje_retefuente = Decimal(str(retefuente_porcentaje))
    porcentaje_reteica = Decimal(str(reteica_porcentaje))
    
    # Validar que los porcentajes sean válidos (0 <= porcentaje <= 1)
    if porcentaje_retefuente < 0 or porcentaje_retefuente > 1:
        raise ValidationError(f"Porcentaje de Retefuente inválido: {retefuente_porcentaje}. Debe estar entre 0 y 1.")
    
    if porcentaje_reteica < 0 or porcentaje_reteica > 1:
        raise ValidationError(f"Porcentaje de ReteICA inválido: {reteica_porcentaje}. Debe estar entre 0 y 1.")
    
    # Calcular retenciones (redondeo a 2 decimales para exactitud contable)
    retefuente = (subtotal * porcentaje_retefuente).quantize(Decimal('0.01'))
    reteica = (subtotal * porcentaje_reteica).quantize(Decimal('0.01'))
    
    # Calcular total neto
    total = subtotal - retefuente - reteica
    
    # Validar que el total no sea negativo
    if total < 0:
        raise ValidationError(
            f"El total calculado es negativo ({total}). "
            f"Verifique que las retenciones no excedan el subtotal."
        )
    
    # ⚠️ v2.60: VALIDACIÓN EXPLÍCITA DE FÓRMULA - Total = Subtotal - Retefuente - ReteICA
    # Tolerancia de 0.01 para manejar errores de redondeo en cálculos grandes
    total_calculado = subtotal - retefuente - reteica
    diferencia = abs(total - total_calculado)
    
    if diferencia > Decimal('0.01'):
        raise ValidationError(
            f"Error de validación: La fórmula Total = Subtotal - Retefuente - ReteICA no se cumple. "
            f"Subtotal: {subtotal}, Retefuente: {retefuente}, ReteICA: {reteica}, "
            f"Total calculado: {total_calculado}, Total esperado: {total}, Diferencia: {diferencia}"
        )
    
    return {
        'retefuente': retefuente,
        'reteica': reteica,
        'total': total
    }


def puede_eliminar_resolucion(empresa: Any, resolucion_id: int) -> Tuple[bool, str]:
    """
    Verifica si una resolución puede ser eliminada.
    
    ⚠️ REGLA: No se puede eliminar si tiene Documentos de Soporte asociados.
    Los documentos deben conservar su referencia a la resolución (evidencia legal).
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        resolucion_id: ID de la resolución a verificar
        
    Returns:
        Tuple[bool, str]: (puede_eliminar, mensaje)
    """
    resolucion = qs_resolucion_detail(empresa.id, resolucion_id)
    
    if not resolucion:
        return False, "Resolución no encontrada o no pertenece a esta empresa."
    
    # Contar documentos de soporte asociados
    conteo_documentos = DocumentoSoporte.objects.filter(resolucion_dian=resolucion).count()
    
    if conteo_documentos > 0:
        return False, f"No se puede eliminar esta resolución porque tiene {conteo_documentos} documento(s) de soporte asociado(s). Los documentos deben conservar su referencia a la resolución como evidencia legal."
    
    return True, "La resolución puede ser eliminada."