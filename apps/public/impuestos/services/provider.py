"""
Servicio Provider para catálogos de normativa DIAN (consumo interno).

⚠️ POLÍTICA SSoT: Este servicio es la ÚNICA fuente de datos de normativa DIAN
para consumo interno entre apps. Otras apps deben usar este servicio en lugar
de consultas ORM directas.

Uso:
    from apps.public.impuestos.services.provider import (
        get_regimen_renta_by_codigo,
        get_responsabilidades_rut,
        get_perfil_tributario,
        clear_impuestos_cache
    )
    
    # Obtener régimen de renta
    regimen = get_regimen_renta_by_codigo('ORDINARIO')
    
    # Obtener responsabilidades RUT
    responsabilidades = get_responsabilidades_rut(['48', '49'])
    
    # Obtener perfil tributario
    perfil = get_perfil_tributario('PJ - Gran Contribuyente - Ordinario')
"""
from functools import lru_cache
from typing import Optional, Iterable, Dict, Any, List
from django.db.models import QuerySet
from apps.public.impuestos.models import (
    ContribuyenteTipo,
    RegimenRenta,
    ResponsabilidadRUT,
    PerfilTributario,
    TipoImpuesto,
    TarifaIVA,
    ActividadEconomica,
)
from apps.public.impuestos.choices.regimen_renta import get_regimen_renta_choices


class ImpuestosNotFoundError(Exception):
    """Se lanza cuando el catálogo requerido no existe o no está activo."""
    pass


# --- Utilidad de caché in-process (invalídala tras cambios de catálogo) ---
def _cache_key(*args) -> str:
    return "|".join(map(str, args))


@lru_cache(maxsize=256)
def get_regimen_renta_by_codigo(codigo: str) -> Dict[str, Any]:
    """
    Obtiene el régimen por código (ORDINARIO|ESPECIAL|SIMPLE) desde public.
    
    ⚠️ POLÍTICA SSoT: Recomendado para composición en TENANT_APPS (contabilidad, facturas).
    
    Args:
        codigo: Código del régimen ('ORDINARIO', 'ESPECIAL', 'SIMPLE')
        
    Returns:
        Dict con datos del régimen
        
    Raises:
        ImpuestosNotFoundError: Si el régimen no existe o no está activo
    """
    obj = RegimenRenta.objects.filter(codigo=codigo, activo=True).first()
    if not obj:
        raise ImpuestosNotFoundError(f"Régimen no encontrado: {codigo}")
    return {
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "requiere_facturacion_electronica": obj.requiere_facturacion_electronica,
        "aplica_retenciones": obj.aplica_retenciones,
        "tarifa_base_pj": float(obj.tarifa_base_pj) if obj.tarifa_base_pj else None,
    }


@lru_cache(maxsize=256)
def get_contribuyentes_tipos_by_clase(clase: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene tipos de contribuyente filtrados por clase (PN/PJ) o todos.
    
    ⚠️ POLÍTICA SSoT: Recomendado para composición en TENANT_APPS.
    
    Args:
        clase: Clase opcional ('PN' o 'PJ') para filtrar
        
    Returns:
        List[Dict] con datos de tipos de contribuyente (clase, segmento_dian, nombre)
    """
    qs = ContribuyenteTipo.objects.filter(activo=True)
    if clase:
        qs = qs.filter(clase=clase)
    
    data = []
    for obj in qs.order_by("clase", "segmento_dian", "nombre"):
        data.append({
            "clase": obj.clase,
            "segmento_dian": obj.segmento_dian,
            "nombre": obj.nombre,
        })
    return data


@lru_cache(maxsize=256)
def get_responsabilidades_rut(codigos: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    """
    Obtiene responsabilidades RUT (todas activas o filtradas por código).
    
    ⚠️ POLÍTICA SSoT: Útil para decidir IVA, retenciones y facturación en TENANT_APPS.
    
    Args:
        codigos: Lista opcional de códigos a filtrar (ej: ['48', '49', '47'])
        
    Returns:
        List[Dict] con datos de responsabilidades
        
    Raises:
        ImpuestosNotFoundError: Si se especifican códigos y ninguno se encuentra
    """
    qs: QuerySet = ResponsabilidadRUT.objects.filter(activo=True)
    if codigos:
        qs = qs.filter(codigo__in=list(codigos))
    data = []
    for r in qs.order_by("codigo"):
        data.append({
            "codigo": r.codigo,
            "nombre": r.nombre,
            "es_responsable_iva": r.es_responsable_iva,
            "es_no_responsable_iva": r.es_no_responsable_iva,
            "es_simple": r.es_simple,
            "es_facturador_electronico": r.es_facturador_electronico,
            "es_gran_contribuyente": r.es_gran_contribuyente,
        })
    if codigos and not data:
        raise ImpuestosNotFoundError(f"Responsabilidades no encontradas: {codigos}")
    return data


@lru_cache(maxsize=256)
def get_perfil_tributario(nombre: str) -> Dict[str, Any]:
    """
    Devuelve un perfil (tipo contribuyente + régimen + set RUT) por nombre.
    
    ⚠️ POLÍTICA SSoT: Útil para onboarding o validaciones coherentes en TENANT_APPS.
    
    Args:
        nombre: Nombre del perfil tributario
        
    Returns:
        Dict con datos del perfil (tipo contribuyente, régimen, responsabilidades)
        
    Raises:
        ImpuestosNotFoundError: Si el perfil no existe o no está activo
    """
    p = (PerfilTributario.objects
         .select_related("tipo_contribuyente", "regimen_renta")
         .prefetch_related("responsabilidades")
         .filter(nombre=nombre, activo=True).first())
    if not p:
        raise ImpuestosNotFoundError(f"Perfil no encontrado: {nombre}")
    return {
        "nombre": p.nombre,
        "tipo_contribuyente": {
            "clase": p.tipo_contribuyente.clase,
            "segmento_dian": p.tipo_contribuyente.segmento_dian,
        },
        "regimen_renta": {
            "codigo": p.regimen_renta.codigo,
            "nombre": p.regimen_renta.nombre,
        },
        "responsabilidades": [r.codigo for r in p.responsabilidades.all()],
    }


@lru_cache(maxsize=128)
def get_tipo_contribuyente_options() -> List[Dict[str, Any]]:
    """
    Obtiene opciones de tipos de contribuyente para selects.
    Usa choices desde apps.public.impuestos.choices.contribuyente_tipo.
    
    Returns:
        List[Dict] con {codigo, nombre} para cada clase (PN, PJ)
    """
    from apps.public.impuestos.choices.contribuyente_tipo import get_clase_choices
    
    return [
        {"codigo": codigo, "nombre": nombre}
        for codigo, nombre in get_clase_choices()
    ]


@lru_cache(maxsize=128)
def get_responsabilidades_rut_options() -> List[Dict[str, Any]]:
    """
    Obtiene opciones de responsabilidades RUT para selects.
    Usa choices desde apps.public.impuestos.choices.responsabilidad_rut.
    
    Returns:
        List[Dict] con {codigo, nombre} para cada responsabilidad del choices
    """
    from apps.public.impuestos.choices.responsabilidad_rut import get_responsabilidad_rut_choices
    
    # Obtener choices estáticos
    choices = get_responsabilidad_rut_choices()
    
    # Enriquecer con datos del modelo si están disponibles (flags booleanos)
    codigos_en_bd = {
        r["codigo"]: {
            "es_responsable_iva": r.get("es_responsable_iva", False),
            "es_no_responsable_iva": r.get("es_no_responsable_iva", False),
        }
        for r in ResponsabilidadRUT.objects.filter(activo=True)
        .values("codigo", "es_responsable_iva", "es_no_responsable_iva")
    }
    
    return [
        {
            "codigo": codigo,
            "nombre": nombre,
            "es_responsable_iva": codigos_en_bd.get(codigo, {}).get("es_responsable_iva", False),
            "es_no_responsable_iva": codigos_en_bd.get(codigo, {}).get("es_no_responsable_iva", False),
        }
        for codigo, nombre in choices
    ]


@lru_cache(maxsize=256)
def search_actividades_economicas(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Búsqueda de actividades económicas (CIIU) por código o nombre.
    Usa choices desde apps.public.impuestos.choices.ciiu.
    
    Args:
        q: Query de búsqueda (código o nombre)
        limit: Límite de resultados (default: 10)
        
    Returns:
        List[Dict] con {codigo, nombre} de actividades que coinciden
    """
    from apps.public.impuestos.choices.ciiu import get_ciiu_choices_search
    
    if not q or len(q) < 1:
        return []
    
    # Usar función de choices que maneja normalización y búsqueda
    choices = get_ciiu_choices_search(q, limit=limit)
    
    # Convertir formato (value, label) a {codigo, nombre}
    return [
        {
            "codigo": codigo,
            "nombre": nombre.split(" — ", 1)[1] if " — " in nombre else nombre
        }
        for codigo, nombre in choices
    ]


@lru_cache(maxsize=128)
def get_tipos_impuesto_options() -> List[Dict[str, Any]]:
    """
    Obtiene opciones de tipos de impuesto para selects.
    
    Returns:
        List[Dict] con {codigo, nombre} para cada tipo activo
    """
    return [
        {"codigo": obj["codigo"], "nombre": obj["nombre"]}
        for obj in TipoImpuesto.objects.filter(activo=True)
        .values("codigo", "nombre")
        .order_by("codigo")
    ]


@lru_cache(maxsize=128)
def get_tarifas_iva_options() -> List[Dict[str, Any]]:
    """
    Obtiene opciones de tarifas IVA para selects.
    
    Returns:
        List[Dict] con {codigo, nombre, porcentaje} para cada tarifa activa
    """
    return [
        {
            "codigo": obj["codigo"],
            "nombre": obj["nombre"],
            "porcentaje": float(obj["porcentaje"]) if obj["porcentaje"] else None,
        }
        for obj in TarifaIVA.objects.filter(activo=True)
        .values("codigo", "nombre", "porcentaje")
        .order_by("codigo")
    ]


def get_empresa_form_metadata() -> Dict[str, Any]:
    """
    Agrupa todos los selects necesarios para el formulario de empresa.
    
    ⚠️ POLÍTICA SSoT: Consume exclusivamente desde catálogos públicos.
    
    Returns:
        Dict con todas las opciones para poblar selects del frontend
    """
    # Obtener tipos de contribuyente por clase
    tipos_pn = get_contribuyentes_tipos_by_clase("PN")
    tipos_pj = get_contribuyentes_tipos_by_clase("PJ")
    
    # Extraer segmentos únicos por clase desde el modelo ContribuyenteTipo
    # Usar el modelo para obtener los nombres correctos desde choices
    segmentos_pn_unicos = {}
    for seg in tipos_pn:
        codigo = seg["segmento_dian"]
        if codigo not in segmentos_pn_unicos:
            # Obtener el nombre del segmento desde el modelo (usar get_FOO_display)
            try:
                obj = ContribuyenteTipo.objects.filter(
                    clase="PN",
                    segmento_dian=codigo,
                    activo=True
                ).first()
                if obj:
                    nombre = obj.get_segmento_dian_display()
                else:
                    # Fallback: usar el código si no se encuentra
                    nombre = codigo
            except Exception:
                nombre = codigo
            segmentos_pn_unicos[codigo] = nombre
    
    segmentos_pj_unicos = {}
    for seg in tipos_pj:
        codigo = seg["segmento_dian"]
        if codigo not in segmentos_pj_unicos:
            try:
                obj = ContribuyenteTipo.objects.filter(
                    clase="PJ",
                    segmento_dian=codigo,
                    activo=True
                ).first()
                if obj:
                    nombre = obj.get_segmento_dian_display()
                else:
                    nombre = codigo
            except Exception:
                nombre = codigo
            segmentos_pj_unicos[codigo] = nombre
    
    # Construir lista plana de segmentos DIAN para el select
    # Usar choices desde apps.public.impuestos.choices.contribuyente_tipo
    from apps.public.impuestos.choices.contribuyente_tipo import get_segmento_dian_choices
    
    segmentos_dian_flat = [
        {"value": codigo, "label": nombre}
        for codigo, nombre in get_segmento_dian_choices()
    ]
    
    return {
        "tipo_contribuyente": {
            "clases": [
                {"codigo": "PN", "nombre": "Persona Natural"},
                {"codigo": "PJ", "nombre": "Persona Jurídica"},
            ],
            "segmentos": {
                "PN": [
                    {"codigo": codigo, "nombre": nombre}
                    for codigo, nombre in sorted(segmentos_pn_unicos.items())
                ],
                "PJ": [
                    {"codigo": codigo, "nombre": nombre}
                    for codigo, nombre in sorted(segmentos_pj_unicos.items())
                ],
            },
        },
        "segmentos_dian": segmentos_dian_flat,  # Lista plana para el select de Segmento DIAN
        "regimenes_renta": [
            {"codigo": codigo, "nombre": nombre}
            for codigo, nombre in get_regimen_renta_choices()
        ],
        "responsabilidades_rut": get_responsabilidades_rut_options(),
        "tipos_impuesto": get_tipos_impuesto_options(),
        "tarifas_iva": get_tarifas_iva_options(),
    }


def clear_impuestos_cache():
    """
    Invalidar caché tras POST/PATCH/DELETE en catálogos.
    
    ⚠️ IMPORTANTE: Llamar desde señales o admin después de modificar catálogos
    para garantizar que el caché refleje los cambios.
    """
    get_regimen_renta_by_codigo.cache_clear()
    get_contribuyentes_tipos_by_clase.cache_clear()
    get_responsabilidades_rut.cache_clear()
    get_perfil_tributario.cache_clear()
    get_tipo_contribuyente_options.cache_clear()
    get_responsabilidades_rut_options.cache_clear()
    search_actividades_economicas.cache_clear()
    get_tipos_impuesto_options.cache_clear()
    get_tarifas_iva_options.cache_clear()