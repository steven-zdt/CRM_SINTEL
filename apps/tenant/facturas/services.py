"""
Service Layer para la app facturas.

⚠️ v2.30: Service Layer Pattern - Toda la lógica de negocio está aquí.
Las vistas/serializers solo orquestan las llamadas a estos servicios.

⚠️ POLÍTICA SSoT: Usa apps.tenant.empresa.services.get_empresa_emisor_data()
para obtener datos del emisor (NO duplica lógica).

⚠️ v2.35: Pipeline XML Canónico (SSoT)
- guardar_factura_desde_dto(): Persiste desde DTO canónico con idempotencia por CUFE
- guardar_nota_credito_desde_dto(): Persiste nota crédito desde DTO canónico (idempotencia por CUDE)

⚠️ v2.36: Import seguro para Document Ingest Pipeline Universal (FASE 0)
- Import condicional de document_ingest para migración gradual
- Permite coexistencia con pipeline XML legacy durante transición
"""
from __future__ import annotations
import re
import logging
import base64
from django.db import transaction, IntegrityError, DataError
from django.db.models import Sum, Count, Q, DecimalField
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.encoding import smart_str
from decimal import Decimal
from typing import Iterable, Optional, Dict, Any, Tuple, Union
from django_tenants.utils import get_tenant
from django.db import connection
from django_tenants.utils import get_public_schema_name
from apps.tenant.facturas.models import Factura, ItemFactura, FacturaAnexos, NotaCredito
from apps.tenant.empresa.models import Empresa  # ⚠️ v2.40: Importación requerida para FK empresa
from .ubl_parser import importar_factura_desde_ubl
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
# ⚠️ Logger: Definir al inicio del módulo (fuera de try/except)
logger = logging.getLogger(__name__)

# ⚠️ v2.36 FASE 0: Import seguro para Document Ingest Pipeline Universal
# Permite coexistencia con pipeline XML legacy durante migración
try:
    from apps.services.document_ingest.ingest_service import ingest_document
    HAS_DOCUMENT_INGEST = True
except (ImportError, Exception) as e:
    # Si document_ingest no está disponible, continuar con pipeline legacy
    ingest_document = None
    HAS_DOCUMENT_INGEST = False
    logger.debug(f"document_ingest no disponible: {e}")

# ⚠️ FASE 4: Límite para mostrar XML inline vs forzar descarga
MAX_INLINE_BYTES = 2_000_000  # 2MB: ver inline; si mayor, forzar descarga


def get_facturacion_summary(empresa_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Calcula resumen de facturación neta excluyendo facturas con Nota de Crédito.
    
    ⚠️ v2.40: REGLA CRÍTICA - Facturas con nota_credito_id IS NOT NULL => Valor 0.
    Solo suma facturas sin NC asociada para mantener integridad fiscal.
    
    Args:
        empresa_id: ID de la empresa (opcional, filtra por empresa si se proporciona)
        
    Returns:
        Dict con desglose por naturaleza (VENTA/COMPRA):
        {
            "ventas": {
                "subtotal_neto": Decimal,
                "impuestos_neto": Decimal,
                "total_neto": Decimal,
                "cantidad": int
            },
            "compras": {
                "subtotal_neto": Decimal,
                "impuestos_neto": Decimal,
                "total_neto": Decimal,
                "cantidad": int
            }
        }
    """
    # Filtro base: solo facturas sin Nota de Crédito asociada
    base_filter = Q(nota_credito__isnull=True)
    
    # Agregar filtro de empresa si se proporciona
    if empresa_id:
        base_filter &= Q(empresa_id=empresa_id)
    
    # Agregaciones para VENTAS (excluyendo facturas con NC)
    ventas_qs = Factura.objects.filter(
        base_filter,
        naturaleza=Factura.Naturaleza.VENTA
    ).aggregate(
        subtotal_neto=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
        impuestos_neto=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
        total_neto=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
        cantidad=Count('id')
    )
    
    # Agregaciones para COMPRAS (excluyendo facturas con NC)
    compras_qs = Factura.objects.filter(
        base_filter,
        naturaleza=Factura.Naturaleza.COMPRA
    ).aggregate(
        subtotal_neto=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
        impuestos_neto=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
        total_neto=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
        cantidad=Count('id')
    )
    
    return {
        "ventas": {
            "subtotal_neto": ventas_qs["subtotal_neto"] or Decimal('0.00'),
            "impuestos_neto": ventas_qs["impuestos_neto"] or Decimal('0.00'),
            "total_neto": ventas_qs["total_neto"] or Decimal('0.00'),
            "cantidad": ventas_qs["cantidad"] or 0
        },
        "compras": {
            "subtotal_neto": compras_qs["subtotal_neto"] or Decimal('0.00'),
            "impuestos_neto": compras_qs["impuestos_neto"] or Decimal('0.00'),
            "total_neto": compras_qs["total_neto"] or Decimal('0.00'),
            "cantidad": compras_qs["cantidad"] or 0
        }
    }

# --- Utilidades de separación de anexos ---
ANEXO_KEYS = {"ubl_xml", "application_response_xml"}

def normalize_document_number(value: Optional[str]) -> str:
    """
    Normaliza números de documento (factura, NIT, etc.) eliminando espacios,
    saltos de línea y caracteres no imprimibles.
    
    ⚠️ v2.40: CRÍTICO - Evita errores de "Factura no encontrada" por formato.
    Basado en estructura real de XML en apps/tenant/facturas/xml/
    
    ⚠️ v2.60: Manejo de NITs con dígito de verificación (ej: "123-4" → "1234")
    - Para comparaciones de NITs, se recomienda usar normalize_nit() del servicio general
    - Esta función mantiene guiones/puntos para números de factura, pero normaliza NITs
    
    Args:
        value: String con número de documento (puede tener espacios/caracteres invisibles)
        
    Returns:
        String normalizado sin espacios iniciales/finales ni caracteres no imprimibles
        Para NITs: elimina guiones y puntos para estandarizar (ej: "123-4" → "1234")
    """
    if not value:
        return ""
    
    if not isinstance(value, str):
        value = str(value)
    
    # Eliminar espacios iniciales/finales y saltos de línea
    normalized = value.strip()
    
    # Eliminar caracteres no imprimibles (excepto guiones y puntos que pueden ser válidos)
    # Mantener: letras, números, guiones, puntos
    import re
    normalized = re.sub(r'[^\w\-\.]', '', normalized)
    
    # ⚠️ v2.60: Para NITs con dígito de verificación (ej: "123-4" o "123.4"), eliminar guiones y puntos
    # Esto asegura que "123-4", "123.4" y "1234" se comparen correctamente
    # Nota: Para números de factura, los guiones pueden ser parte del formato (ej: "FST-0001")
    # Por eso solo normalizamos si parece un NIT (solo números, guiones y puntos, sin letras)
    if re.match(r'^[\d\-\.]+$', normalized) and not re.search(r'[A-Za-z]', normalized):
        # Es un NIT: eliminar guiones y puntos para estandarizar
        # Ejemplos: "123-4" → "1234", "123.4" → "1234", "901123299-1" → "9011232991"
        normalized = normalized.replace('-', '').replace('.', '')
    
    return normalized

def _split_factura_payload(payload: dict) -> tuple[dict, dict]:
    """
    Separa datos de Factura (kwargs válidos para el modelo) vs anexos (blobs).
    
    ⚠️ CRÍTICO: No permite que ANEXO_KEYS entren a Factura.objects.create(**kwargs).
    Esto previene TypeError cuando se intenta crear Factura con campos que no existen.
    
    Args:
        payload: Dict con datos de factura que puede incluir anexos
        
    Returns:
        Tuple (factura_data, anexos_data) donde:
        - factura_data: Solo campos válidos del modelo Factura
        - anexos_data: Solo campos de anexos (ubl_xml, application_response_xml)
    """
    factura_data = dict(payload or {})
    anexos_data = {}
    
    for k in list(factura_data.keys()):
        if k in ANEXO_KEYS:
            anexos_data[k] = factura_data.pop(k)
    
    return factura_data, anexos_data

# ⚠️ IMPORT DIRECTO: Importar desde apps.tenant.empresa.services (archivo, no paquete)
# ✅ CORRECCIÓN DEFINITIVA: El paquete services/ fue renombrado a impl/ para eliminar shadowing
# Ahora podemos importar directamente desde el archivo services.py sin conflictos
from apps.tenant.empresa.services import (
    get_empresa_emisor_data,
    EmpresaNotConfiguredError,
)

# ⚠️ v2.37: LIST_FIELDS y DETAIL_FIELDS para alineación Serializers ↔ Services ↔ UI
# ⚠️ OPTIMIZACIÓN ZERO WASTE: Solo campos necesarios para el listado (evita cargar campos pesados)
LIST_FIELDS = (
    "id",
    "numero",
    "naturaleza",  # ⚠️ CAPA DE API: Campo calculado disponible para el frontend en el listado optimizado
    "estado",
    "fecha_emision",
    "fecha_vencimiento",  # ⚠️ v2.60: Agregado para estado de pago
    "moneda",
    "subtotal",
    "impuestos",
    "total",
    "emisor_nit",
    "emisor_razon_social",
    "receptor_nit",
    "receptor_razon_social",
    "cufe",
    "qr_url",
)

DETAIL_FIELDS = (
    "id",
    "numero",
    "prefijo",
    "consecutivo",
    "tipo",
    "estado",
    "naturaleza",
    "categoria",
    "fecha_emision",
    "fecha_vencimiento",
    "emisor_nit",
    "emisor_razon_social",
    "emisor_direccion",
    "emisor_email",
    "receptor_nit",
    "receptor_razon_social",
    "receptor_direccion",
    "receptor_email",
    "moneda",
    "subtotal",
    "impuestos",
    "total",
    "cufe",
    "qr_url",
    "created_at",
    "updated_at",
)


def qs_list(search=None):
    """
    QuerySet optimizado para listado (Tabulator v2.40).
    
    ⚠️ OPTIMIZACIÓN ZERO WASTE: El servicio qs_list() ya incluye el campo naturaleza dentro de LIST_FIELDS
    para evitar consultas innecesarias a la base de datos.
    
    ⚠️ v2.40: Usa LIST_FIELDS con only() y select_related para nota_credito.
    ⚠️ v2.40: Soporta filtrado por ?search= para Tabulator.
    ✅ Solo carga campos necesarios para la tabla (incluye naturaleza)
    ✅ Escalable (millones de facturas)
    ✅ Zero Waste: No carga campos pesados (XML, anexos, etc.)
    """
    from django.db.models import Q
    
    # ⚠️ Zero Waste: only(*LIST_FIELDS) asegura que solo se carguen los campos necesarios
    # El campo naturaleza está incluido en LIST_FIELDS, por lo que se carga eficientemente
    qs = Factura.objects.select_related("nota_credito").only(*LIST_FIELDS)
    
    # Aplicar filtro de búsqueda si se proporciona
    if search:
        qs = qs.filter(
            Q(numero__icontains=search) |
            Q(cufe__icontains=search) |
            Q(receptor_razon_social__icontains=search) |
            Q(emisor_razon_social__icontains=search)
        )
    
    return qs


def qs_detail():
    """
    QuerySet optimizado para detalle (retrieve).
    
    ⚠️ v2.37: Usa DETAIL_FIELDS con only() y select_related para nota_credito.
    ✅ Solo carga campos necesarios para el detalle
    """
    return Factura.objects.select_related("nota_credito").only(*DETAIL_FIELDS)


# ⚠️ FASE 4: Persistencia por dominio desde DTO canónico (Pipeline XML SSoT)
# Estas funciones se añaden para soportar el nuevo pipeline canónico
# mientras se mantiene compatibilidad con el código existente

def _resolver_naturaleza(emisor_nit: str | None, empresa_nit: str | None) -> str:
    """
    Resuelve naturaleza (VENTA/COMPRA) comparando emisor vs empresa (SSoT).
    
    ⚠️ CAPA DE LÓGICA: Determinación Automática (Service Layer)
    ⚠️ SSoT: Lógica centralizada para determinar el tipo de factura basada en el NIT.
    
    Regla de Negocio:
    - Si NIT Emisor == NIT Tenant → VENTA (el tenant emite la factura)
    - Si NIT Emisor != NIT Tenant → COMPRA (el tenant recibe la factura)
    
    Normalización:
    - Usa normalize_document_number() para estandarizar NITs con dígito de verificación
    - Maneja NITs con formato "123-4" o "1234" correctamente
    - Elimina guiones y puntos para comparación consistente
    - Asegura que caracteres especiales no afecten la comparación
    
    Args:
        emisor_nit: NIT del emisor extraído del documento (XML/PDF)
        empresa_nit: NIT de la empresa del tenant actual (SSoT - Single Source of Truth)
        
    Returns:
        Factura.Naturaleza.VENTA si emisor == empresa (el tenant es quien emite)
        Factura.Naturaleza.COMPRA si emisor != empresa (el tenant es quien recibe)
        
    Ejemplo:
        - Tenant tiene NIT: "901123299" o "901123299-1"
        - Documento tiene emisor NIT: "901123299" o "901123299-1" → VENTA ✅
        - Documento tiene emisor NIT: "800123456" → COMPRA ✅
        
    Implementación:
        1. Normalizar NIT del emisor: normalize_document_number(emisor_nit)
        2. Normalizar NIT del tenant: normalize_document_number(empresa_nit)
        3. Comparar NITs normalizados
        4. Retornar VENTA si coinciden, COMPRA si no
    """
    # Normalizar ambos NITs para evitar errores por espacios, guiones o dígitos de verificación
    # ⚠️ normalize_document_number() ahora maneja NITs con formato "123-4" correctamente
    nit_dto = normalize_document_number(emisor_nit) if emisor_nit else ""
    nit_tenant = normalize_document_number(empresa_nit) if empresa_nit else ""
    
    # Comparación normalizada: si coinciden, es VENTA (el tenant emite)
    if nit_dto and nit_tenant and nit_dto == nit_tenant:
        logger.debug(f"[_resolver_naturaleza] NIT emisor ({nit_dto}) == NIT empresa ({nit_tenant}) → VENTA")
        return Factura.Naturaleza.VENTA
    
    # Si no coinciden o alguno está vacío, es COMPRA (el tenant recibe)
    logger.debug(f"[_resolver_naturaleza] NIT emisor ({nit_dto}) != NIT empresa ({nit_tenant}) → COMPRA")
    return Factura.Naturaleza.COMPRA


# ⚠️ v2.36 FASE 4: Funciones wrapper para router de dominio
def materializar_factura_desde_dto(dto: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Materializa factura desde DTO (wrapper para router de dominio) (FASE 4).
    
    ⚠️ FASE 4: Wrapper que adapta guardar_factura_desde_dto al contrato del router.
    Detecta automáticamente si el archivo es XML o PDF desde el DTO.
    
    Args:
        dto: DTO JSON canónico del pipeline
        
    Returns:
        Tuple (payload, status_code)
    """
    # Detectar tipo de archivo desde metadata o contenido
    metadata = dto.get("metadata", {})
    file_type = metadata.get("file_type", "xml")  # Default: xml
    mime_type = metadata.get("mime_type", "")
    
    # Detectar tipo desde mime_type si está disponible
    if mime_type:
        if "pdf" in mime_type.lower():
            file_type = "pdf"
        elif "xml" in mime_type.lower() or "text/xml" in mime_type.lower():
            file_type = "xml"
    
    # Extraer contenido del archivo (XML o PDF)
    file_bytes = None
    xml_text = None
    
    # ⚠️ v2.60: Intentar obtener bytes del archivo desde metadata (endpoint universal)
    # El endpoint /api/v1/core/documentos/upload/ incluye file_content_bytes en base64
    if metadata and "file_content_bytes" in metadata:
        import base64
        try:
            file_bytes_b64 = metadata.get("file_content_bytes")
            if isinstance(file_bytes_b64, str):
                file_bytes = base64.b64decode(file_bytes_b64)
                # Actualizar file_type desde metadata si está disponible
                file_type_from_meta = metadata.get("file_type")
                if file_type_from_meta:
                    file_type = file_type_from_meta
        except Exception as e:
            logger.warning(f"Error decodificando file_content_bytes desde metadata: {e}")
    
    # Intentar obtener bytes del archivo desde otros lugares (compatibilidad hacia atrás)
    if not file_bytes:
        if "file_bytes" in dto:
            file_bytes = dto.get("file_bytes")
            if isinstance(file_bytes, str):
                file_bytes = file_bytes.encode("utf-8")
        elif "xml_content" in dto:
            content = dto.get("xml_content")
            if isinstance(content, bytes):
                file_bytes = content
            else:
                xml_text = content or ""
        elif "metadata" in dto and "xml_raw" in metadata:
            content = metadata.get("xml_raw")
            if isinstance(content, bytes):
                file_bytes = content
            else:
                xml_text = content or ""
    
    # Si tenemos file_bytes, usarlo; si no, usar xml_text (compatibilidad hacia atrás)
    if file_bytes:
        return guardar_factura_desde_dto(dto, file_bytes=file_bytes, file_type=file_type)
    elif xml_text:
        return guardar_factura_desde_dto(dto, xml_text=xml_text)
    else:
        # Sin archivo, solo persistir datos
        return guardar_factura_desde_dto(dto)


def materializar_nc_desde_dto(dto: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Materializa nota crédito desde DTO (wrapper para router de dominio) (FASE 4).
    
    ⚠️ FASE 4: Wrapper que adapta guardar_nota_credito_desde_dto al contrato del router.
    No requiere xml_text (se extrae del DTO si está disponible).
    
    Args:
        dto: DTO JSON canónico del pipeline
        
    Returns:
        Tuple (payload, status_code)
    """
    # Extraer xml_text del DTO si está disponible
    xml_text = dto.get("xml_content") or dto.get("metadata", {}).get("xml_raw") or ""
    try:
        nota_credito = guardar_nota_credito_desde_dto(dto, xml_text=xml_text)
        return {
            "id": nota_credito.id,
            "numero": nota_credito.numero,
            "cude": nota_credito.cude,
            "created": True,
        }, 201
    except ValidationError as e:
        # Re-lanzar ValidationError para que el router lo maneje
        raise e


@transaction.atomic
def guardar_factura_desde_dto(
    dto: Dict[str, Any], 
    xml_text: str = None,
    file_bytes: bytes = None,
    file_type: str = 'xml'
) -> Tuple[Dict[str, Any], int]:
    """
    Persiste factura desde DTO canónico del pipeline XML (SSoT).
    
    ⚠️ IDEMPOTENCIA: Por CUFE (clave legal) o número (fallback).
    ⚠️ TRANSACCIONAL: Todo o nada (transaction.atomic).
    ⚠️ SSoT: Usa get_empresa_emisor_data() para resolver naturaleza automáticamente.
    ⚠️ DETERMINACIÓN AUTOMÁTICA DE NATURALEZA: Compara NIT del emisor con NIT de la empresa del tenant.
       - Si coinciden → VENTA (el tenant emite la factura)
       - Si difieren → COMPRA (el tenant recibe la factura)
    ⚠️ ZERO WASTE: Manejo de anexos (XML/PDF) - solo actualiza lo necesario.
    ⚠️ FALLBACK SSoT: Si el DTO viene de un PDF y faltan datos del emisor (razón social, dirección, etc.),
       intenta recuperarlos desde la empresa del tenant cuando el NIT del emisor coincide con el NIT de la empresa.
       Esto es especialmente útil cuando los PDFs no contienen toda la información estructurada.
    
    Flujo de Determinación de Naturaleza:
    1. Obtener datos de la empresa del tenant actual (SSoT) → get_empresa_emisor_data()
    2. Normalizar NIT del emisor del DTO → normalize_document_number()
    3. Comparar NITs usando _resolver_naturaleza() → Determina VENTA/COMPRA automáticamente
    4. Asignar naturaleza al objeto Factura → No requiere parámetros externos
    
    Args:
        dto: DTO canónico de factura (formato: apps/services/xml_ingest/dto.InvoiceDTO)
        xml_text: Texto XML original (para anexos) - DEPRECATED: usar file_bytes + file_type
        file_bytes: Bytes del archivo (XML o PDF) - Opcional
        file_type: Tipo de archivo ('xml' o 'pdf') - Default: 'xml'
        
    Returns:
        Tuple (payload, status_code):
        - 201 Created: Si se crea nueva factura
        - 200 OK: Si factura ya existe (idempotente)
        - 409 Conflict: Si hay conflicto de integridad (duplicado)
        - 422 Unprocessable Entity: Si faltan campos obligatorios
    """
    
    # ⚠️ PASO 1: Obtener datos de la empresa del tenant actual (SSoT)
    # Esta es la única fuente de verdad para determinar la naturaleza de la factura
    try:
        empresa_config = get_empresa_emisor_data()
        logger.debug(f"[guardar_factura_desde_dto] Empresa SSoT obtenida: NIT={empresa_config.get('nit')}")
    except EmpresaNotConfiguredError as ex:
        logger.warning(f"Empresa no configurada: {str(ex)}")
        return {"error": "empresa_no_configurada", "message": str(ex)}, 422
    
    # Extraer campos del DTO canónico
    numero_raw = dto.get("numero")
    fecha_emision = dto.get("fecha_emision")
    emisor = dto.get("emisor", {})
    receptor = dto.get("receptor", {})
    totales = dto.get("totales", {})
    identificadores = dto.get("identificadores", {})
    
    # ⚠️ PASO 2: Normalizar números y NITs usando función dedicada (elimina espacios/caracteres invisibles)
    # ⚠️ CRÍTICO: La normalización es esencial para la comparación correcta de NITs en la determinación de naturaleza
    numero = normalize_document_number(numero_raw) if numero_raw else None
    emisor_nit = normalize_document_number(emisor.get("nit")) if emisor.get("nit") else None
    receptor_nit = normalize_document_number(receptor.get("nit")) if receptor.get("nit") else None
    emisor_razon_social = emisor.get("razon_social", "").strip() if emisor.get("razon_social") else ""
    receptor_razon_social = receptor.get("razon_social", "").strip() if receptor.get("razon_social") else ""
    
    # ⚠️ FALLBACK SSoT: Si el DTO viene de un PDF y faltan datos del emisor, intentar recuperarlos desde la empresa del tenant
    # Esto es especialmente útil cuando los PDFs no contienen toda la información estructurada
    if file_type == 'pdf' and emisor_nit and not emisor_razon_social:
        # Normalizar NITs para comparación (sin DV)
        from apps.services.document_parser.normalizers import normalize_nit as norm_nit
        emisor_nit_norm = norm_nit(emisor_nit)
        empresa_nit_norm = norm_nit(empresa_config.get("nit"))
        
        # Si el NIT del emisor coincide con el NIT de la empresa del tenant (SSoT)
        if emisor_nit_norm and empresa_nit_norm and emisor_nit_norm == empresa_nit_norm:
            logger.info(f"[SSoT Fallback] Completando datos del emisor desde empresa del tenant (NIT: {emisor_nit})")
            # Completar datos del emisor desde la empresa del tenant (SSoT)
            emisor_razon_social = empresa_config.get("razon_social", "")
            # Actualizar el DTO para mantener consistencia
            if not emisor.get("razon_social"):
                emisor["razon_social"] = emisor_razon_social
            # Completar otros campos del snapshot si faltan
            if not emisor.get("direccion") and empresa_config.get("direccion"):
                emisor["direccion"] = empresa_config.get("direccion")
            if not emisor.get("telefono") and empresa_config.get("telefono"):
                emisor["telefono"] = empresa_config.get("telefono")
            if not emisor.get("email") and empresa_config.get("email_contacto"):
                emisor["email"] = empresa_config.get("email_contacto")
    
    # ⚠️ Validar campos obligatorios (después de normalización y fallback SSoT)
    # ⚠️ CRÍTICO: Si falta emisor.nit, no se puede determinar la naturaleza automáticamente
    campos_faltantes = []
    if not numero:
        campos_faltantes.append("numero")
    if not emisor_nit:
        campos_faltantes.append("emisor.nit")  # ⚠️ CRÍTICO: Sin NIT del emisor, no se puede determinar naturaleza
    if not emisor_razon_social:
        campos_faltantes.append("emisor.razon_social")
    if not receptor_nit:
        campos_faltantes.append("receptor.nit")
    if not receptor_razon_social:
        campos_faltantes.append("receptor.razon_social")
    
    if campos_faltantes:
        # ⚠️ Error 422: Campos faltantes - error_injector.js mostrará esto en el Offcanvas
        error_message = f"Faltan campos obligatorios: {', '.join(campos_faltantes)}"
        if "emisor.nit" in campos_faltantes:
            error_message += " (⚠️ CRÍTICO: Sin NIT del emisor, no se puede determinar la naturaleza de la factura automáticamente)"
        
        logger.warning(f"[guardar_factura_desde_dto] Error 422 - Campos faltantes: {campos_faltantes}")
        return {
            "error": "missing_required_fields",
            "message": error_message,
            "missing_fields": campos_faltantes
        }, 422
    
    # ⚠️ PASO 3: Determinar Naturaleza Automática (VENTA/COMPRA)
    # ⚠️ CAPA DE LÓGICA: Determinación Automática (Service Layer)
    # 
    # Lógica de Comparación:
    # 1. Obtención de SSoT: empresa_config ya contiene los datos de la empresa del tenant (obtenidos en PASO 1)
    #    - NIT del Tenant (SSoT): empresa_config.get("nit")
    # 2. Normalización: Se normalizan los NITs con normalize_document_number() (ya normalizados en PASO 2)
    #    - NIT del Emisor: emisor_nit (normalizado)
    #    - NIT del Tenant: empresa_config.get("nit") (se normalizará en _resolver_naturaleza)
    #    - normalize_document_number() asegura que caracteres especiales no afecten la comparación
    #      Ejemplos: "123-4" → "1234", "123.4" → "1234", "901123299-1" → "9011232991"
    # 3. Resolución: _resolver_naturaleza() compara nit_emisor vs nit_tenant
    #    - Regla de Negocio:
    #      * Si NIT Emisor == NIT Tenant → VENTA (el tenant emite la factura)
    #      * Si NIT Emisor != NIT Tenant → COMPRA (el tenant recibe la factura)
    # 
    # ⚠️ AUTOMÁTICO: No requiere parámetros externos, se determina dinámicamente desde el SSoT
    # ⚠️ ANTES DE GUARDAR: La naturaleza se asigna antes de persistir en la base de datos
    naturaleza = _resolver_naturaleza(emisor_nit, empresa_config.get("nit"))
    logger.info(f"[guardar_factura_desde_dto] Naturaleza determinada automáticamente: {naturaleza} (Emisor NIT: {emisor_nit}, Empresa NIT: {empresa_config.get('nit')})")
    
    # ⚠️ PASO 3.5: VALIDACIÓN CRÍTICA - Pertenece al Tenant (Cascading Security)
    # ⚠️ REGLA DE SEGURIDAD: Si es COMPRA, el Receptor DEBE ser el Tenant
    # Esta validación asegura que solo se persistan facturas que realmente pertenecen al tenant actual.
    # Si una factura es de tipo COMPRA (el tenant la recibe), el receptor debe ser el tenant.
    # Si el receptor no es el tenant, significa que la factura no pertenece a este tenant y debe rechazarse.
    # 
    # ⚠️ CASCADING SECURITY: Validación en cascada para proteger la contabilidad
    # 1. Identificación Automática: Si NIT Emisor == NIT Tenant → VENTA (automático)
    # 2. Validación de Compra: Si NIT Emisor != NIT Tenant → COMPRA, pero debe validar Receptor
    # 3. Rechazo Silencioso: Si Receptor != Tenant → Error 422 con mensaje claro
    if naturaleza == Factura.Naturaleza.COMPRA:
        # Normalizar NIT del tenant para comparación
        nit_tenant = normalize_document_number(empresa_config.get("nit"))
        
        # Validar que el receptor sea el tenant
        if receptor_nit != nit_tenant:
            # ⚠️ Error 422: Documento no pertenece al tenant - error_injector.js mostrará esto
            # ⚠️ MENSAJE ESPECÍFICO: Claro y específico para contexto de correo
            # ⚠️ CASCADING SECURITY: Rechazo silencioso con alerta clara
            error_message = (
                f"Este correo contiene una factura dirigida a un tercero (NIT receptor: {receptor_nit}), "
                f"no se incluirá en contabilidad. "
                f"La factura pertenece a otra empresa (NIT del tenant: {nit_tenant})."
            )
            logger.warning(
                f"[guardar_factura_desde_dto] Error 422 - Documento rechazado por validación de NIT: "
                f"Receptor NIT ({receptor_nit}) != Tenant NIT ({nit_tenant}). "
                f"Factura de terceros no se incluirá en contabilidad."
            )
            # ⚠️ Detectar contexto automáticamente: Si viene de correo (file_type='xml' desde preview) o es explícito
            # El contexto puede venir del DTO o detectarse por el origen del archivo
            context = dto.get("metadata", {}).get("context") or dto.get("context")
            if not context and file_type == 'xml':
                # Si es XML y viene del flujo de correo, marcar como mail_ingestion
                # (el preview_mail_ingestion pasa el XML con metadata)
                context = "mail_ingestion"
            
            return {
                "error": "document_not_for_tenant",
                "message": error_message,
                "missing_fields": ["receptor.nit"],  # ⚠️ Incluir en missing_fields para que error_injector.js lo muestre
                "context": context or "general",  # ⚠️ Contexto para identificar origen del error (mail_ingestion o general)
                "receptor_nit": receptor_nit,  # ⚠️ NIT del receptor para debugging
                "tenant_nit": nit_tenant,  # ⚠️ NIT del tenant para debugging
            }, 422
    
    # Extraer prefijo y consecutivo
    prefijo = dto.get("prefijo")
    consecutivo = dto.get("consecutivo", 0)
    if not prefijo and numero:
        # Import local para evitar ciclos si es necesario
        from .ubl_parser import _parsear_prefijo_consecutivo
        prefijo, consecutivo = _parsear_prefijo_consecutivo(numero)
    
    # Parsear fecha de forma robusta
    if fecha_emision and isinstance(fecha_emision, str):
        dt = parse_datetime(fecha_emision)
        if dt:
            fecha_emision = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        else:
            d = parse_date(fecha_emision)
            if d:
                fecha_emision = timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.min.time()))
            else:
                fecha_emision = timezone.now()
    elif not fecha_emision:
        fecha_emision = timezone.now()
    
    # CUFE (clave de idempotencia)
    cufe = identificadores.get("cufe") or identificadores.get("uuid")
    
    # ⚠️ v2.40: Obtener instancia de Modelo Empresa (requerido para FK)
    try:
        empresa_instance = Empresa.objects.first()
        if not empresa_instance:
            return {
                "error": "empresa_no_configurada",
                "message": "No existe Empresa en este tenant. Configure una Empresa antes de importar facturas."
            }, 422
    except Exception as e:
        logger.warning(f"Error obteniendo Empresa: {str(e)}")
        return {
            "error": "empresa_error",
            "message": f"Error al obtener Empresa: {str(e)}"
        }, 422
    
    # ⚠️ PASO 4: Construir datos para Factura con naturaleza determinada automáticamente
    # ⚠️ v2.60: Estado puede venir del DTO (ej: desde UBL parser que establece ACEPTADA)
    estado_factura = dto.get("estado") or Factura.Estado.BORRADOR
    
    factura_data = {
        "empresa": empresa_instance,  # FK Real
        "numero": numero,
        "prefijo": prefijo,
        "consecutivo": consecutivo,
        "fecha_emision": fecha_emision,
        "emisor_nit": emisor_nit,
        "emisor_razon_social": emisor_razon_social,
        "receptor_nit": receptor_nit,
        "receptor_razon_social": receptor_razon_social,
        "subtotal": Decimal(str(totales.get("subtotal", "0.00"))),
        "impuestos": Decimal(str(totales.get("impuestos", "0.00"))),
        "total": Decimal(str(totales.get("total", "0.00"))),
        "moneda": totales.get("moneda", "COP"),
        "naturaleza": naturaleza,  # ⚠️ Asignación automática: VENTA o COMPRA según comparación de NITs
        "estado": estado_factura,  # ⚠️ v2.60: Estado del DTO o BORRADOR por defecto
        "cufe": cufe,
    }
    
    # ⚠️ PASO 5: Persistencia con Idempotencia por CUFE (o número como fallback)
    # ⚠️ La naturaleza ya está determinada automáticamente en factura_data
    instance = None
    created = False
    
    try:
        if cufe:
            # Buscar por CUFE (más confiable) - Idempotencia por clave legal
            instance, created = Factura.objects.update_or_create(
                cufe=cufe,
                defaults={k: v for k, v in factura_data.items() if k != "cufe"}
            )
            logger.debug(f"[guardar_factura_desde_dto] Factura {'creada' if created else 'actualizada'} por CUFE: {cufe}")
        else:
            # Buscar por número (fallback) - Idempotencia por número de factura
            instance, created = Factura.objects.update_or_create(
                numero=numero,
                defaults={k: v for k, v in factura_data.items() if k != "numero"}
            )
            logger.debug(f"[guardar_factura_desde_dto] Factura {'creada' if created else 'actualizada'} por número: {numero}")
    except IntegrityError as e:
        logger.warning(f"IntegrityError al guardar factura: {str(e)}")
        return {
            "error": "duplicate",
            "message": "La factura ya existe (conflicto de integridad)."
        }, 409
    
    # Guardar anexos (XML o PDF) - Zero Waste: solo actualiza lo necesario
    if instance:
        anexo, _ = FacturaAnexos.objects.get_or_create(factura=instance)
        
        # Manejo de archivos: XML o PDF
        if file_bytes:
            if file_type == 'xml':
                # XML: guardar como texto
                try:
                    xml_text_from_bytes = file_bytes.decode('utf-8') if isinstance(file_bytes, bytes) else file_bytes
                    anexo.ubl_xml = xml_text_from_bytes
                except (UnicodeDecodeError, AttributeError) as e:
                    logger.warning(f"Error decodificando XML: {str(e)}")
                    # Si no se puede decodificar, intentar guardar como está
                    anexo.ubl_xml = str(file_bytes) if not isinstance(file_bytes, str) else file_bytes
            elif file_type == 'pdf':
                # PDF: guardar como archivo
                from django.core.files.base import ContentFile
                filename = f"{instance.numero or 'factura'}.pdf"
                anexo.pdf_file.save(filename, ContentFile(file_bytes), save=False)
        
        # Compatibilidad hacia atrás: si se pasa xml_text directamente
        elif xml_text:
            anexo.ubl_xml = xml_text
        
        # Solo guardar si hay cambios
        if file_bytes or xml_text:
            anexo.save()
    
    # ⚠️ v2.60: Contabilidad Invisible - Hook para materializar asiento automático
    # Si la factura está en estado ACEPTADA, crear asiento contable automáticamente
    if instance.estado == Factura.Estado.ACEPTADA:
        try:
            from apps.tenant.contabilidad.services.asientos_service import materializar_asiento_desde_factura
            materializar_asiento_desde_factura(instance)
            logger.info(f"[guardar_factura_desde_dto] Asiento contable materializado automáticamente para factura {instance.numero}")
        except Exception as e:
            # ⚠️ Aislamiento Gradual: No fallar la creación de factura si falla la materialización del asiento
            # El asiento se puede crear manualmente después
            logger.warning(f"[guardar_factura_desde_dto] Error al materializar asiento desde factura {instance.numero}: {str(e)}")
            # No propagar el error - la factura ya está guardada
    
    return {
        "id": instance.id,
        "numero": instance.numero,
        "naturaleza": instance.naturaleza,
        "created": created
    }, 201 if created else 200


@transaction.atomic
def guardar_nota_credito_desde_dto(dto: Dict[str, Any], *, xml_text: str) -> NotaCredito:
    """
    Persiste una Nota Crédito. Idempotencia por CUDE.
    
    ⚠️ IDEMPOTENCIA: Por CUDE (clave legal).
    ⚠️ TRANSACCIONAL: Todo o nada (transaction.atomic).
    ⚠️ ONE-TO-ONE: Una factura solo puede tener UNA nota crédito.
    
    Reglas:
    - La factura referenciada debe existir en el tenant actual.
    - Una factura solo puede tener UNA nota crédito (OneToOne).
    - Una nota crédito aplica a UNA factura (OneToOne).
    - Idempotencia por CUDE: si ya existe, lanza ValidationError.
    
    Args:
        dto: DTO canónico de nota crédito (formato: apps/services/xml_ingest/dto.CreditNoteDTO)
        xml_text: Texto XML original (keyword-only)
        
    Returns:
        NotaCredito: Instancia de la nota crédito creada
        
    Raises:
        ValidationError: Si la nota crédito ya existe (CUDE duplicado), 
                       si la factura referenciada no existe,
                       o si la factura ya tiene una nota crédito asociada.
    """
    from apps.tenant.facturas.models import NotaCredito
    
    # Extraer CUDE (clave de idempotencia)
    identificadores = dto.get("identificadores", {})
    cude = identificadores.get("cude") or identificadores.get("uuid")
    
    if not cude:
        raise ValidationError({
            "error": "missing_cude",
            "message": "El CUDE es obligatorio para la nota crédito."
        })
    
    # ⚠️ IDEMPOTENCIA: Verificar si ya existe por CUDE
    if NotaCredito.objects.filter(cude=cude).exists():
        raise ValidationError({
            "error": "duplicate",
            "message": "La nota crédito ya existe (CUDE duplicado)."
        })
    
    # Extraer referencia a factura desde BillingReference/InvoiceDocumentReference
    # ⚠️ v2.40: Basado en estructura real de XML en apps/tenant/facturas/xml/
    referencia = dto.get("referencia", {})
    ref_num = referencia.get("numero") or dto.get("referencia_factura_numero") or dto.get("referencia", {}).get("numero")
    ref_cufe = referencia.get("cufe") or dto.get("referencia_factura_cufe") or dto.get("referencia", {}).get("cufe")
    
    # ⚠️ DEBUG: Log para diagnóstico
    logger.debug(f"Buscando factura referenciada: numero='{ref_num}', cufe='{ref_cufe}'")
    logger.debug(f"DTO referencia completa: {referencia}")
    
    if not ref_num and not ref_cufe:
        raise ValidationError({
            "error": "missing_reference",
            "message": "Se requiere referencia a factura (numero o cufe)."
        })
    
    # ⚠️ v2.40: Normalizar usando función dedicada (elimina espacios, caracteres invisibles)
    ref_num_normalized = normalize_document_number(ref_num) if ref_num else None
    ref_cufe_normalized = normalize_document_number(ref_cufe) if ref_cufe else None
    
    # Buscar factura referenciada usando ID (Número) y UUID (CUFE) con normalización
    # ⚠️ v2.40: Búsqueda robusta - intenta ambos métodos para asegurar match
    factura = None
    try:
        # Prioridad 1: Buscar por CUFE (más preciso, case-sensitive pero normalizado)
        if ref_cufe_normalized:
            try:
                factura = Factura.objects.get(cufe=ref_cufe_normalized)
                logger.debug(f"Factura encontrada por CUFE normalizado: {factura.numero}")
            except Factura.DoesNotExist:
                pass
        
        # Prioridad 2: Buscar por número (case-insensitive, normalizado)
        if not factura and ref_num_normalized:
            try:
                factura = Factura.objects.get(numero__iexact=ref_num_normalized)
                logger.debug(f"Factura encontrada por número normalizado (case-insensitive): {factura.numero}")
            except Factura.DoesNotExist:
                pass
        
        # Si aún no se encontró, intentar búsqueda sin normalizar (fallback)
        if not factura:
            if ref_cufe:
                factura = Factura.objects.get(cufe=ref_cufe)
            elif ref_num:
                factura = Factura.objects.get(numero__iexact=ref_num)
                
    except Factura.DoesNotExist:
        # ⚠️ DEBUG: Listar facturas disponibles para diagnóstico
        facturas_existentes = list(Factura.objects.values_list('numero', flat=True)[:10])
        logger.warning(
            f"Factura no encontrada: numero='{ref_num}' (normalizado: '{ref_num_normalized}'), "
            f"cufe='{ref_cufe[:20]}...' (normalizado: '{ref_cufe_normalized[:20] if ref_cufe_normalized else None}...'). "
            f"Facturas existentes (primeras 10): {facturas_existentes}"
        )
        raise ValidationError({
            "error": "missing_invoice",
            "message": f"Factura referenciada '{ref_num or ref_cufe}' no existe en este tenant. Cargue la factura original primero."
        })
    except Factura.MultipleObjectsReturned:
        # Si hay múltiples facturas con el mismo número (caso raro), tomar la primera
        logger.warning(f"Múltiples facturas encontradas con número '{ref_num}', tomando la primera")
        factura = Factura.objects.filter(numero__iexact=ref_num).first()
    
    # ⚠️ ONE-TO-ONE: Verificar que la factura no tenga ya una nota crédito
    if hasattr(factura, "nota_credito"):
        raise ValidationError({
            "error": "already_has_nc",
            "message": "La factura ya tiene una nota crédito asociada."
        })
    
    # Extraer campos del DTO
    numero = dto.get("numero")
    fecha_emision = dto.get("fecha_emision")
    totales = dto.get("totales", {})
    motivo = dto.get("motivo", "")
    moneda = totales.get("moneda", "COP")
    
    # Parsear fecha
    from django.utils.dateparse import parse_datetime, parse_date
    from django.utils import timezone as tz
    if fecha_emision and isinstance(fecha_emision, str):
        dt = parse_datetime(fecha_emision)
        if dt:
            fecha_emision = tz.make_aware(dt) if tz.is_naive(dt) else dt
        else:
            d = parse_date(fecha_emision)
            if d:
                fecha_emision = tz.make_aware(tz.datetime.combine(d, tz.datetime.min.time()))
            else:
                fecha_emision = tz.now()
    elif not fecha_emision:
        fecha_emision = tz.now()
    
    # Crear nota crédito
    nota = NotaCredito.objects.create(
        factura=factura,
        empresa=factura.empresa,  # ⚠️ v2.40: Asignar empresa desde factura
        numero=numero,
        cude=cude,
        fecha_emision=fecha_emision,
        moneda=moneda,
        subtotal=Decimal(str(totales.get("subtotal", "0.00"))),
        impuestos=Decimal(str(totales.get("impuestos", "0.00"))),
        total=Decimal(str(totales.get("total", "0.00"))),
        motivo=motivo,
        ref_factura_numero=factura.numero,
        ref_factura_cufe=factura.cufe or "",
        xml_content=xml_text if xml_text else "",
    )
    
    return nota


@transaction.atomic
def guardar_nota_credito_desde_pdf(
    pdf_file: Union[bytes, Any],
    xml_file: Optional[Union[bytes, str]] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Persiste Nota de Crédito desde PDF usando el parser de Fase 1.
    
    ⚠️ FASE 2: Lógica de Negocio - Persistencia Nota Crédito desde PDF.
    ⚠️ TRANSACCIONAL: Todo o nada (transaction.atomic).
    ⚠️ ONE-TO-ONE: Una factura solo puede tener UNA nota crédito.
    
    Flujo:
    1. Parsea el PDF usando ingest_document (Fase 1) para extraer DTO
    2. Obtiene la empresa del tenant actual
    3. Busca la factura padre por referencia_factura
    4. Valida que la factura existe y no tiene ya una NC (OneToOne)
    5. Crea la NotaCredito y guarda archivos si aplica
    
    Args:
        pdf_file: Archivo PDF en bytes o objeto file-like
        xml_file: Archivo XML opcional (para almacenar si está disponible)
        
    Returns:
        Tuple (payload, status_code):
        - 201 Created: Si se crea nueva nota crédito
        - 422 Unprocessable Entity: Si faltan campos, factura no existe, o parser falla
        - 409 Conflict: Si la factura ya tiene una nota crédito asociada (OneToOne)
    """
    # Usar el logger global del módulo (ya definido al inicio)
    schema = getattr(connection, "schema_name", "-")
    
    # 1. Convertir pdf_file a bytes si es necesario
    if hasattr(pdf_file, 'read'):
        pdf_bytes = pdf_file.read()
    elif isinstance(pdf_file, bytes):
        pdf_bytes = pdf_file
    else:
        return {
            "error": "invalid_pdf_file",
            "message": "El archivo PDF debe ser bytes o un objeto file-like."
        }, 422
    
    if not pdf_bytes:
        return {
            "error": "empty_pdf_file",
            "message": "El archivo PDF está vacío."
        }, 422
    
    # 2. Parsing: Invocar al parser (Fase 1) para extraer el DTO del PDF
    try:
        if not HAS_DOCUMENT_INGEST or ingest_document is None:
            return {
                "error": "parser_not_available",
                "message": "El parser de documentos no está disponible. Verifique la configuración."
            }, 422
        
        # Usar ingest_document para parsear el PDF
        result, status_code = ingest_document(
            content=pdf_bytes,
            filename="nota_credito.pdf",
            mime_type="application/pdf",
            kind_hint="creditnote",
            preview=True  # Solo parsear, no persistir aún
        )
        
        if status_code != 200 or result.get("error"):
            error_msg = result.get("message", "Error al parsear el PDF")
            logger.warning(f"Error al parsear PDF: {error_msg}")
            return {
                "error": "parsing_failed",
                "message": f"Error al parsear el PDF: {error_msg}"
            }, 422
        
        # Extraer DTO del resultado
        dto = result.get("dto")
        if not dto:
            return {
                "error": "no_dto_extracted",
                "message": "No se pudo extraer datos del PDF."
            }, 422
        
        # Validar que el DTO tiene los campos requeridos
        numero = dto.get("numero")
        referencia_factura = dto.get("referencia_factura") or dto.get("referencia", {}).get("numero")
        fecha_emision = dto.get("fecha_emision")
        total = dto.get("total") or dto.get("totales", {}).get("total")
        nit_emisor = dto.get("nit_emisor") or dto.get("emisor", {}).get("nit")
        
        if not numero:
            return {
                "error": "missing_numero",
                "message": "El PDF no contiene el número de la Nota de Crédito."
            }, 422
        
        if not referencia_factura:
            return {
                "error": "missing_referencia_factura",
                "message": "El PDF no contiene la referencia a la factura."
            }, 422
        
        if not total:
            return {
                "error": "missing_total",
                "message": "El PDF no contiene el total de la Nota de Crédito."
            }, 422
        
    except Exception as e:
        logger.error(f"Error al parsear PDF: {str(e)}", exc_info=True)
        return {
            "error": "parsing_exception",
            "message": f"Error inesperado al parsear el PDF: {str(e)}"
        }, 422
    
    # 3. Contexto del Tenant: Obtener la empresa actual
    try:
        empresa = Empresa.objects.first()
        if not empresa:
            return {
                "error": "empresa_no_configurada",
                "message": "No existe Empresa en este tenant. Configure una Empresa antes de importar Notas de Crédito."
            }, 422
    except Exception as e:
        logger.warning(f"Error obteniendo Empresa: {str(e)}")
        return {
            "error": "empresa_error",
            "message": f"Error al obtener Empresa: {str(e)}"
        }, 422
    
    # 4. Búsqueda de Factura Padre (Vinculación)
    try:
        factura_padre = Factura.objects.filter(
            numero=referencia_factura,
            empresa=empresa
        ).first()
        
        # Validación Crítica 1: Si factura_padre es None, retorna error 422
        if not factura_padre:
            return {
                "error": "factura_no_existe",
                "message": f"La factura referencia [{referencia_factura}] no existe en el sistema."
            }, 422
        
    except Exception as e:
        logger.error(f"Error buscando factura: {str(e)}", exc_info=True)
        return {
            "error": "factura_search_error",
            "message": f"Error al buscar la factura: {str(e)}"
        }, 422
    
    # 5. Validación OneToOne (Integridad)
    # Como la relación es OneToOneField, verificar si la factura ya tiene una nota de crédito asociada
    if hasattr(factura_padre, 'nota_credito'):
        return {
            "error": "factura_ya_tiene_nc",
            "message": f"La factura [{referencia_factura}] ya tiene una Nota de Crédito asociada. Operación rechazada por regla 1:1."
        }, 409
    
    # 6. Persistencia: Crear la instancia de NotaCredito
    try:
        # Extraer campos adicionales del DTO
        totales = dto.get("totales", {})
        motivo = dto.get("motivo", "")
        moneda = totales.get("moneda", "COP") or dto.get("moneda", "COP")
        subtotal = totales.get("subtotal", "0.00")
        impuestos = totales.get("impuestos", "0.00")
        
        # Parsear fecha de emisión
        if fecha_emision and isinstance(fecha_emision, str):
            dt = parse_datetime(fecha_emision)
            if dt:
                fecha_emision = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            else:
                d = parse_date(fecha_emision)
                if d:
                    fecha_emision = timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.min.time()))
                else:
                    fecha_emision = timezone.now()
        elif not fecha_emision:
            fecha_emision = timezone.now()
        
        # Extraer CUDE/CUFE si está disponible
        identificadores = dto.get("identificadores", {})
        cude = identificadores.get("cude") or identificadores.get("uuid") or identificadores.get("cufe")
        
        # Si no hay CUDE, generar uno temporal basado en número y fecha
        if not cude:
            import hashlib
            cude_raw = f"{numero}_{fecha_emision}_{factura_padre.cufe or factura_padre.numero}"
            cude = hashlib.sha256(cude_raw.encode()).hexdigest()[:32].upper()
            logger.warning(f"CUDE no encontrado en PDF, generado temporal: {cude}")
        
        # Verificar idempotencia por CUDE (si ya existe, retornar la existente)
        nota_existente = NotaCredito.objects.filter(cude=cude).first()
        if nota_existente:
            return {
                "id": nota_existente.id,
                "numero": nota_existente.numero,
                "cude": nota_existente.cude,
                "created": False,
                "message": "La Nota de Crédito ya existe (idempotencia por CUDE)."
            }, 200
        
        # Crear la NotaCredito
        nc = NotaCredito.objects.create(
            factura=factura_padre,  # ⚠️ Relación OneToOne
            empresa=factura_padre.empresa,  # ⚠️ v2.40: Asignar empresa desde factura
            numero=numero,
            cude=cude,
            fecha_emision=fecha_emision,
            moneda=moneda,
            subtotal=Decimal(str(subtotal)),
            impuestos=Decimal(str(impuestos)),
            total=Decimal(str(total)),
            motivo=motivo,
            ref_factura_numero=factura_padre.numero,
            ref_factura_cufe=factura_padre.cufe or "",
            xml_content=xml_file if isinstance(xml_file, str) else "",
        )
        
        # 7. Guardado de Archivos (Anexos) - Si hay un modelo para PDFs
        # Por ahora, el PDF se puede almacenar en xml_content si es necesario
        # o en un campo específico si el modelo lo tiene
        
        logger.info(
            f"Nota de Crédito creada: {nc.numero} para factura {factura_padre.numero}",
            extra={"schema_name": schema, "nc_id": nc.id, "factura_id": factura_padre.id}
        )
        
        return {
            "id": nc.id,
            "numero": nc.numero,
            "cude": nc.cude,
            "factura_numero": factura_padre.numero,
            "created": True,
            "message": f"Nota de Crédito {nc.numero} creada exitosamente."
        }, 201
        
    except IntegrityError as e:
        logger.error(f"IntegrityError al crear Nota de Crédito: {str(e)}", exc_info=True)
        return {
            "error": "integrity_error",
            "message": "Error de integridad al crear la Nota de Crédito. Puede que ya exista."
        }, 409
    except ValidationError as e:
        logger.error(f"ValidationError al crear Nota de Crédito: {str(e)}", exc_info=True)
        return {
            "error": "validation_error",
            "message": f"Error de validación: {str(e)}"
        }, 422
    except Exception as e:
        logger.error(f"Error inesperado al crear Nota de Crédito: {str(e)}", exc_info=True)
        return {
            "error": "unexpected_error",
            "message": f"Error inesperado: {str(e)}"
        }, 500


# --- Funciones de importación UBL (sync/async) ---

# ⚠️ v2.36 FASE 2: Función interna para usar pipeline universal
def importar_documento(
    file_bytes: bytes,
    filename: str = "ubl.xml",
    preview: bool = False,
    async_mode: bool = False
) -> Union[Tuple[Dict[str, Any], int], Dict[str, Any]]:
    """
    Importa documento usando el pipeline universal de documentos (FASE 2).
    
    ⚠️ PIPELINE UNIVERSAL: Usa apps.services.document_ingest.ingest_document
    cuando FEATURE_DOCUMENT_PIPELINE=True, mantiene compatibilidad con pipeline legacy.
    
    Args:
        file_bytes: Bytes del documento a importar
        filename: Nombre del archivo (default: "ubl.xml")
        preview: Si True, solo retorna DTO sin persistir
        async_mode: Si True, procesa de forma asíncrona (actualmente no soportado en pipeline universal)
        
    Returns:
        - Si async_mode=False: Tuple (payload, status_code)
        - Si async_mode=True: Dict con task_id (pendiente implementación)
    """
    # Usar el logger global del módulo (ya definido al inicio)
    schema = getattr(connection, "schema_name", "-")
    request_id = getattr(settings, 'REQUEST_ID', '-')
    
    # Verificar si el pipeline universal está disponible y activo
    use_universal = (
        HAS_DOCUMENT_INGEST and
        ingest_document is not None and
        getattr(settings, 'FEATURE_DOCUMENT_PIPELINE', False)
    )
    
    if not use_universal:
        # TODO: Deprecar fallback legacy una vez que document_ingest esté estable
        if async_mode:
            # TODO: Implementar ingest_ubl_async si es necesario para el fallback
            logger.warning("async_mode_not_supported_in_legacy", extra={"request_id": request_id, "schema_name": schema})
            # Por ahora, fallback síncrono
            # TODO: Deprecar fallback legacy - usar pipeline universal siempre
            # Por ahora, retornar error indicando que el pipeline universal es requerido
            logger.error(
                "legacy_fallback_not_supported",
                extra={"request_id": request_id, "schema_name": schema}
            )
            return {
                "error": "pipeline_universal_required",
                "message": "El pipeline universal es requerido. Configure FEATURE_DOCUMENT_PIPELINE=True."
            }, 503
    
    # Usar pipeline universal
    try:
        # Detectar tipo de documento (hint para XML/UBL)
        kind_hint = None
        if filename.endswith('.xml') or file_bytes.startswith(b'<?xml') or b'<Invoice' in file_bytes[:500] or b'<CreditNote' in file_bytes[:500]:
            # Intentar detectar si es Invoice o CreditNote
            if b'<CreditNote' in file_bytes[:500] or b'CreditNote' in file_bytes[:500]:
                kind_hint = "creditnote"
            else:
                kind_hint = "invoice"
        
        # Llamar al pipeline universal
        result, status_code = ingest_document(
            content=file_bytes,
            filename=filename,
            mime_type="application/xml" if filename.endswith('.xml') else None,
            kind_hint=kind_hint,
            preview=preview,
            async_mode=async_mode
        )
        
        # Si es preview, retornar DTO directamente (formato compatible)
        if preview:
            # Formato compatible con preview del pipeline legacy
            return {
                "dto": result.get("dto", {}),
                "document_type": result.get("dto", {}).get("document_type", "unknown"),
                "persisted": False,
            }, status_code
        
        # ⚠️ REVERSIÓN: document_ingest NO persiste automáticamente
        # Si preview=False, materializar manualmente desde el DTO
        if not preview:
            # El pipeline universal NO persiste, solo parsea
            # Retornar DTO para que la app lo consuma y persista
            dto = result.get("dto", {})
            if not dto:
                return {
                    "error": "no_dto",
                    "message": "El pipeline no generó un DTO válido."
                }, 422
            
            # Detectar tipo de archivo desde metadata o filename
            metadata = result.get("metadata", {})
            file_type = "xml"  # Default
            mime_type = metadata.get("mime_type", "")
            
            if mime_type:
                if "pdf" in mime_type.lower():
                    file_type = "pdf"
                elif "xml" in mime_type.lower() or "text/xml" in mime_type.lower():
                    file_type = "xml"
            elif filename.endswith('.pdf'):
                file_type = "pdf"
            elif filename.endswith('.xml'):
                file_type = "xml"
            
            # Extraer contenido del archivo (XML o PDF)
            # Usar el file_bytes original pasado a la función si está disponible
            file_bytes_to_save = file_bytes
            xml_text = None
            
            # Si no tenemos file_bytes, intentar extraerlo del resultado
            if not file_bytes_to_save and "metadata" in result:
                content = result.get("metadata", {}).get("xml_content") or result.get("metadata", {}).get("file_content")
                if content:
                    if isinstance(content, bytes):
                        file_bytes_to_save = content
                    elif isinstance(content, str) and file_type == "xml":
                        xml_text = content
            
            # Materializar usando guardar_factura_desde_dto o guardar_nota_credito_desde_dto
            doc_type = dto.get("type") or dto.get("document_type", "")
            if "creditnote" in doc_type.lower():
                # Es una nota crédito (solo soporta XML por ahora)
                try:
                    xml_text_for_nc = xml_text or (file_bytes_to_save.decode("utf-8") if file_bytes_to_save and file_type == "xml" else "")
                    nota = guardar_nota_credito_desde_dto(dto, xml_text=xml_text_for_nc)
                    return {
                        "id": nota.id,
                        "numero": nota.numero,
                        "cude": nota.cude,
                        "created": True,
                    }, 201
                except ValidationError as e:
                    error_dict = e.message_dict if hasattr(e, 'message_dict') else {}
                    error_code = error_dict.get("error", ["validation_error"])[0] if isinstance(error_dict.get("error"), list) else error_dict.get("error", "validation_error")
                    return {
                        "error": error_code,
                        "message": str(e),
                    }, 422
            else:
                # Es una factura - usar file_bytes si está disponible, si no xml_text
                if file_bytes_to_save:
                    return guardar_factura_desde_dto(dto, file_bytes=file_bytes_to_save, file_type=file_type)
                elif xml_text:
                    return guardar_factura_desde_dto(dto, xml_text=xml_text)
                else:
                    # Sin archivo, solo persistir datos
                    return guardar_factura_desde_dto(dto)
        
        # Si hay error, retornar error del pipeline
        return {
            "error": result.get("error", "unknown_error"),
            "message": result.get("message", "Error desconocido al procesar documento"),
            "missing_fields": result.get("missing_fields", []),
        }, status_code
        
    except Exception as e:
        logger.exception(f"Error en importar_documento (pipeline universal): {e}")
        return {
            "error": "parse_error",
            "message": f"Error al procesar documento: {str(e)}"
        }, 422


def importar_ubl_sync(xml_bytes: bytes) -> Tuple[Dict[str, Any], int]:
    """
    Importa UBL de forma síncrona usando el pipeline universal (FASE 2).
    
    ⚠️ v2.36 FASE 2: Ahora usa pipeline universal cuando FEATURE_DOCUMENT_PIPELINE=True.
    Mantiene compatibilidad retroactiva con pipeline legacy.
    
    Args:
        xml_bytes: XML bytes a importar
        
    Returns:
        Tuple (payload, status_code)
    """
    return importar_documento(
        file_bytes=xml_bytes,
        filename="ubl.xml",
        preview=False,
        async_mode=False
    )


def importar_ubl_async(file_bytes: bytes, schema_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Importa UBL de forma asíncrona usando el pipeline universal (FASE 2).
    
    ⚠️ v2.36 FASE 2: Ahora usa pipeline universal cuando FEATURE_DOCUMENT_PIPELINE=True.
    Mantiene compatibilidad retroactiva con pipeline legacy.
    
    ⚠️ TENANT-AWARE: Descubre schema_name desde connection si no se proporciona.
    
    Args:
        file_bytes: XML bytes a importar
        schema_name: Nombre del esquema del tenant (opcional, se descubre si no se proporciona)
        
    Returns:
        Dict con task_id y status: {"task_id": str, "status": "PENDING"}
        
    Note:
        El pipeline universal actualmente no soporta async_mode=True completamente.
        Si FEATURE_DOCUMENT_PIPELINE=True, se procesa de forma síncrona pero retorna formato compatible.
    """
    # Descubrir schema_name si no se proporciona
    if not schema_name:
        schema_name = connection.schema_name
        if not schema_name or schema_name == get_public_schema_name():
            raise ValueError("No se puede usar el esquema 'public' para importar facturas. Proporcione schema_name explícito.")
    
    # Verificar si usar pipeline universal
    use_universal = (
        HAS_DOCUMENT_INGEST and
        ingest_document is not None and
        getattr(settings, 'FEATURE_DOCUMENT_PIPELINE', False)
    )
    
    if use_universal:
        # Pipeline universal: procesar síncronamente pero retornar formato compatible
        # TODO: Implementar async_mode completo en pipeline universal
        result, status_code = importar_documento(
            file_bytes=file_bytes,
            filename="ubl.xml",
            preview=False,
            async_mode=False
        )
        
        # Retornar formato compatible con async (simulado)
        if status_code in (200, 201):
            return {
                "task_id": f"sync_{result.get('id', 'unknown')}",
                "status": "SUCCESS",
                "result": result
            }
        else:
            return {
                "task_id": "sync_error",
                "status": "FAILURE",
                "error": result.get("error", "unknown_error"),
                "message": result.get("message", "Error al procesar documento")
            }
    else:
        # Pipeline universal con Celery
        from apps.services.document_ingest.tasks import document_ingest_task
        import base64
        task = document_ingest_task.delay(
            schema_name=schema_name or connection.schema_name,
            file_b64=base64.b64encode(file_bytes).decode("utf-8"),
            filename="ubl.xml"
        )
        return {"task_id": task.id, "status": "PENDING"}


def materializar_factura_desde_result(
    xml_result: Dict[str, Any], 
    persist_anexos: bool = True,
    file_bytes: Optional[bytes] = None,
    file_type: Optional[str] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Materializa factura desde resultado del pipeline XML canónico.
    
    ⚠️ COMPATIBILIDAD: Soporta tanto formato enriquecido (dto/anexos/meta) como formato plano.
    ⚠️ v2.60: Soporta file_bytes y file_type explícitos para PDFs desde endpoint create-from-dto.
    
    Args:
        xml_result: Resultado del pipeline XML (puede ser enriched_payload o DTO plano)
        persist_anexos: Si True, guarda anexos en FacturaAnexos
        file_bytes: Bytes del archivo (XML o PDF) - Opcional, si se proporciona se usa directamente
        file_type: Tipo de archivo ('xml' o 'pdf') - Opcional, se detecta automáticamente si no se proporciona
        
    Returns:
        Tuple (payload, status_code)
    """
    # Detectar formato: enriched (dto/anexos/meta) vs plano
    if "dto" in xml_result:
        # Formato enriquecido del pipeline canónico
        dto = xml_result["dto"]
        anexos = xml_result.get("anexos", {})
        ubl_xml = anexos.get("ubl_xml") or anexos.get("xml_raw") or ""
        # ⚠️ v2.60: Intentar obtener file_bytes desde metadata si no se proporcionó explícitamente
        if not file_bytes:
            metadata = xml_result.get("metadata", {})
            if metadata and "file_content_bytes" in metadata:
                try:
                    file_bytes_b64 = metadata.get("file_content_bytes")
                    if isinstance(file_bytes_b64, str):
                        file_bytes = base64.b64decode(file_bytes_b64)
                    # Actualizar file_type desde metadata si está disponible y no se proporcionó
                    if not file_type:
                        file_type = metadata.get("file_type", "xml")
                except Exception as e:
                    logger.warning(f"Error decodificando file_content_bytes desde metadata: {e}")
    else:
        # Formato plano (legacy)
        dto = xml_result
        ubl_xml = dto.get("ubl_xml") or dto.get("xml_content") or ""
        # ⚠️ v2.60: Intentar obtener file_bytes desde metadata si no se proporcionó explícitamente
        if not file_bytes:
            metadata = dto.get("metadata", {})
            if metadata and "file_content_bytes" in metadata:
                try:
                    file_bytes_b64 = metadata.get("file_content_bytes")
                    if isinstance(file_bytes_b64, str):
                        file_bytes = base64.b64decode(file_bytes_b64)
                    # Actualizar file_type desde metadata si está disponible y no se proporcionó
                    if not file_type:
                        file_type = metadata.get("file_type", "xml")
                except Exception as e:
                    logger.warning(f"Error decodificando file_content_bytes desde metadata: {e}")
    
    # Normalizar DTO a formato canónico si es necesario
    if "emisor" not in dto and "emisor_nit" in dto:
        # Convertir formato plano a canónico
        dto = {
            "numero": dto.get("numero"),
            "fecha_emision": dto.get("fecha_emision"),
            "emisor": {
                "nit": dto.get("emisor_nit"),
                "razon_social": dto.get("emisor_razon_social"),
            },
            "receptor": {
                "nit": dto.get("receptor_nit"),
                "razon_social": dto.get("receptor_razon_social"),
            },
            "totales": {
                "subtotal": dto.get("subtotal", 0.0),
                "impuestos": dto.get("impuestos", 0.0),
                "total": dto.get("total", 0.0),
                "moneda": dto.get("moneda", "COP"),
            },
            "identificadores": {
                "uuid": dto.get("cufe") or dto.get("uuid"),
            },
            "prefijo": dto.get("prefijo"),
            "consecutivo": dto.get("consecutivo", 0),
        }
    
    # Usar guardar_factura_desde_dto para persistir
    # ⚠️ v2.60: Priorizar file_bytes y file_type explícitos (desde endpoint create-from-dto)
    if not persist_anexos:
        # No guardar anexos si persist_anexos=False
        return guardar_factura_desde_dto(dto)
    
    # ⚠️ PRIORIDAD 1: Si se proporcionaron file_bytes explícitamente, usarlos directamente
    if file_bytes:
        # Determinar file_type si no se proporcionó
        if not file_type:
            if file_bytes.startswith(b'%PDF'):
                file_type = "pdf"
            else:
                file_type = "xml"
        return guardar_factura_desde_dto(dto, file_bytes=file_bytes, file_type=file_type)
    
    # ⚠️ PRIORIDAD 2: Intentar usar ubl_xml del resultado (compatibilidad hacia atrás)
    if isinstance(ubl_xml, bytes):
        # Es bytes, determinar tipo desde contenido
        detected_file_type = file_type or ("pdf" if ubl_xml.startswith(b'%PDF') else "xml")
        return guardar_factura_desde_dto(dto, file_bytes=ubl_xml, file_type=detected_file_type)
    elif isinstance(ubl_xml, str):
        # Es string, asumir XML
        return guardar_factura_desde_dto(dto, xml_text=ubl_xml)
    else:
        # Sin archivo, solo persistir datos
        return guardar_factura_desde_dto(dto)


def obtener_anexo_xml(factura: Factura, tipo: str) -> Tuple[Union[HttpResponse, Dict[str, Any]], int]:
    """
    Obtiene anexo XML de una factura (UBL o ApplicationResponse).
    
    ⚠️ FASE 6: Endpoint dedicado para artefactos pesados.
    - Retorna XML completo con Content-Type: application/xml
    - Inline si <= 2MB, descarga forzada si mayor
    
    Args:
        factura: Instancia de Factura
        tipo: "ubl" o "app" (ApplicationResponse)
        
    Returns:
        Tuple (payload, status_code):
        - HttpResponse si es XML para descargar
        - Dict con error si hay problema
    """
    try:
        anexos = FacturaAnexos.objects.get(factura=factura)
    except FacturaAnexos.DoesNotExist:
        return {"error": "no_anexos", "message": "No hay anexos disponibles para esta factura."}, 204
    
    if tipo == "ubl":
        xml_content = anexos.ubl_xml
        filename = f"factura_{factura.numero}_ubl.xml"
    elif tipo == "app":
        xml_content = anexos.application_response_xml
        filename = f"factura_{factura.numero}_app_response.xml"
    else:
        return {"error": "invalid_type", "message": f"Tipo inválido: {tipo}. Use 'ubl' o 'app'."}, 400
    
    if not xml_content:
        return {"error": "no_xml", "message": f"No hay XML {tipo} disponible para esta factura."}, 204
    
    # Convertir a bytes si es string
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content
    
    # Decidir si mostrar inline o forzar descarga
    if len(xml_bytes) > MAX_INLINE_BYTES:
        # Forzar descarga
        response = HttpResponse(xml_bytes, content_type="application/xml")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response, 200
    else:
        # Mostrar inline
        response = HttpResponse(xml_bytes, content_type="application/xml")
        response["X-Content-Type-Options"] = "nosniff"
        return response, 200


def get_facturacion_summary(empresa_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Calcula resumen de facturación neta excluyendo facturas con Nota de Crédito.
    
    ⚠️ v2.40: REGLA CRÍTICA - Facturas con nota_credito_id IS NOT NULL => Valor 0.
    Solo suma facturas sin NC asociada para mantener integridad fiscal.
    
    Args:
        empresa_id: ID de la empresa (opcional, filtra por empresa si se proporciona)
        
    Returns:
        Dict con desglose por naturaleza (VENTA/COMPRA):
        {
            "ventas": {
                "subtotal_neto": Decimal,
                "impuestos_neto": Decimal,
                "total_neto": Decimal,
                "cantidad": int
            },
            "compras": {
                "subtotal_neto": Decimal,
                "impuestos_neto": Decimal,
                "total_neto": Decimal,
                "cantidad": int
            }
        }
    """
    # Filtro base: solo facturas sin Nota de Crédito asociada
    base_filter = Q(nota_credito__isnull=True)
    
    # Agregar filtro de empresa si se proporciona
    if empresa_id:
        base_filter &= Q(empresa_id=empresa_id)
    
    # Agregaciones para VENTAS (excluyendo facturas con NC)
    ventas_qs = Factura.objects.filter(
        base_filter,
        naturaleza=Factura.Naturaleza.VENTA
    ).aggregate(
        subtotal_neto=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
        impuestos_neto=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
        total_neto=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
        cantidad=Count('id')
    )
    
    # Agregaciones para COMPRAS (excluyendo facturas con NC)
    compras_qs = Factura.objects.filter(
        base_filter,
        naturaleza=Factura.Naturaleza.COMPRA
    ).aggregate(
        subtotal_neto=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
        impuestos_neto=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
        total_neto=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
        cantidad=Count('id')
    )
    
    return {
        "ventas": {
            "subtotal_neto": ventas_qs["subtotal_neto"] or Decimal('0.00'),
            "impuestos_neto": ventas_qs["impuestos_neto"] or Decimal('0.00'),
            "total_neto": ventas_qs["total_neto"] or Decimal('0.00'),
            "cantidad": ventas_qs["cantidad"] or 0
        },
        "compras": {
            "subtotal_neto": compras_qs["subtotal_neto"] or Decimal('0.00'),
            "impuestos_neto": compras_qs["impuestos_neto"] or Decimal('0.00'),
            "total_neto": compras_qs["total_neto"] or Decimal('0.00'),
            "cantidad": compras_qs["cantidad"] or 0
        }
    }


def eliminar_factura(factura: Factura) -> None:
    """
    Elimina una factura y todos sus registros relacionados.
    
    ⚠️ NUEVA POLÍTICA v2.95:
    - Se permite eliminar facturas sin restricciones de inmutabilidad.
    - La factura puede eliminarse incluso si tiene notas de crédito asociadas.
    - Se eliminan en cascada: anexos, items, y nota de crédito asociada (si existe).
    - No hay validaciones que bloqueen la eliminación por vínculos contables o documentos relacionados.
    
    Args:
        factura: Instancia de Factura a eliminar
    """
    # ⚠️ v2.95: Eliminar nota de crédito asociada primero (si existe)
    # OneToOne con PROTECT puede bloquear, así que la eliminamos explícitamente
    try:
        nota_credito = NotaCredito.objects.get(factura=factura)
        nota_credito.delete()
    except NotaCredito.DoesNotExist:
        pass
    
    # Eliminar anexos (OneToOne, se elimina automáticamente, pero por seguridad)
    try:
        anexos = FacturaAnexos.objects.get(factura=factura)
        anexos.delete()
    except FacturaAnexos.DoesNotExist:
        pass
    
    # ⚠️ v2.95: Los items se eliminan automáticamente por CASCADE
    # Eliminar factura (esto eliminará automáticamente los items por CASCADE)
    factura.delete()


def importar_ubl(xml_content: str, preview: bool = False) -> Factura:
    """
    Función legacy para importar UBL (compatibilidad).
    
    ⚠️ DEPRECADO: Usar importar_ubl_sync o importar_ubl_async en su lugar.
    
    Args:
        xml_content: XML string a importar
        preview: Si True, no persiste (solo parsea)
        
    Returns:
        Instancia de Factura (si preview=False) o None (si preview=True)
    """
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content
    
    if preview:
        # Solo parsear, no persistir usando pipeline universal
        from apps.services.document_ingest.ingest_service import ingest_document
        result, _ = ingest_document(content=xml_bytes, filename="ubl.xml", preview=True)
        return None  # Preview no retorna factura
    
    # Importar y persistir
    payload, status_code = importar_ubl_sync(xml_bytes)
    if status_code in (200, 201) and "id" in payload:
        return Factura.objects.get(id=payload["id"])
    else:
        raise ValueError(f"Error al importar UBL: {payload.get('message', 'Error desconocido')}")


# ⚠️ v2.60: Funciones de negocio para migración a arquitectura estandarizada
@transaction.atomic
def emitir_factura_desde_cotizacion(cotizacion_id: int, empresa_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Emite una factura desde una cotización aceptada.
    
    ⚠️ ZERO TRUST v2.60:
    - Valida que la factura pertenezca al Tenant (empresa_id)
    - Valida que el Cliente esté activo
    - Valida que la cotización esté en estado ACEPTADA
    
    Args:
        cotizacion_id: ID de la cotización a convertir
        empresa_id: ID de la empresa del tenant (Zero Trust)
        
    Returns:
        Tuple (payload, status_code):
        - 201 Created: Si se crea nueva factura
        - 400 Bad Request: Si la cotización no está en estado válido
        - 404 Not Found: Si la cotización no existe o no pertenece al tenant
        - 422 Unprocessable Entity: Si el cliente no está activo o faltan datos
    """
    try:
        # ⚠️ ZERO TRUST: Importación diferida para evitar ciclos
        from apps.tenant.cotizaciones.models import Cotizacion, CotizacionItem
        from apps.tenant.clientes.models import Cliente
        
        # ⚠️ ZERO TRUST: Validar que la cotización pertenece al tenant
        cotizacion = Cotizacion.objects.filter(
            id=cotizacion_id,
            empresa_id=empresa_id
        ).select_related('cliente').first()
        
        if not cotizacion:
            return {
                "error": "cotizacion_not_found",
                "message": "La cotización no existe o no pertenece a este tenant."
            }, 404
        
        # ⚠️ ZERO TRUST: Validar estado de la cotización
        if cotizacion.estado != Cotizacion.Estado.ACEPTADA:
            return {
                "error": "cotizacion_no_aceptada",
                "message": f"La cotización debe estar en estado ACEPTADA. Estado actual: {cotizacion.estado}"
            }, 400
        
        # ⚠️ ZERO TRUST: Validar que el cliente existe y está activo
        if not cotizacion.cliente_id:
            return {
                "error": "cliente_no_asignado",
                "message": "La cotización no tiene un cliente asignado."
            }, 422
        
        cliente = Cliente.objects.filter(
            id=cotizacion.cliente_id,
            empresa_id=empresa_id,
            activo=True
        ).first()
        
        if not cliente:
            return {
                "error": "cliente_inactivo",
                "message": "El cliente asociado a la cotización no existe o no está activo."
            }, 422
        
        # Obtener datos del emisor (SSoT)
        try:
            empresa_config = get_empresa_emisor_data()
        except EmpresaNotConfiguredError as ex:
            return {
                "error": "empresa_no_configurada",
                "message": str(ex)
            }, 422
        
        # Obtener empresa instance
        try:
            empresa_instance = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            return {
                "error": "empresa_not_found",
                "message": "La empresa no existe."
            }, 404
        
        # Generar número de factura (prefijo + consecutivo)
        # TODO: Implementar lógica de numeración según configuración DIAN
        prefijo = empresa_config.get("prefijo_facturacion", "FST")
        consecutivo = Factura.objects.filter(empresa_id=empresa_id).count() + 1
        numero = f"{prefijo}{consecutivo:06d}"
        
        # Obtener items de la cotización
        items_cotizacion = CotizacionItem.objects.filter(cotizacion=cotizacion)
        
        # Calcular totales
        subtotal = cotizacion.total_con_impuestos / (1 + (cotizacion.iva_porcentaje / 100))
        impuestos = cotizacion.total_con_impuestos - subtotal
        total = cotizacion.total_con_impuestos
        
        # Crear factura
        factura = Factura.objects.create(
            empresa=empresa_instance,
            numero=numero,
            prefijo=prefijo,
            consecutivo=consecutivo,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,  # Se emite como borrador, debe ser validada
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.MIXTO,
            fecha_emision=timezone.now(),
            fecha_vencimiento=cotizacion.fecha_vencimiento,
            # Snapshot emisor
            emisor_nit=empresa_config.get("nit", ""),
            emisor_razon_social=empresa_config.get("razon_social", ""),
            emisor_direccion=empresa_config.get("direccion", ""),
            emisor_email=empresa_config.get("email", ""),
            emisor_telefono=empresa_config.get("telefono", ""),
            # Snapshot receptor
            receptor_nit=cliente.numero_documento,
            receptor_razon_social=cliente.razon_social,
            receptor_direccion=cliente.direccion or "",
            receptor_email=cliente.email or "",
            receptor_telefono=cliente.telefono or "",
            # Totales
            moneda="COP",
            subtotal=subtotal,
            impuestos=impuestos,
            total=total,
        )
        
        # Crear items de factura desde items de cotización
        for idx, item_cot in enumerate(items_cotizacion, start=1):
            ItemFactura.objects.create(
                factura=factura,
                empresa=empresa_instance,
                linea_id=str(idx),
                codigo=item_cot.codigo or "",
                descripcion=item_cot.descripcion,
                cantidad=item_cot.cantidad,
                unidad_medida=item_cot.unidad_medida or "UND",
                valor_unitario=item_cot.precio_unitario,
                porcentaje_iva=cotizacion.iva_porcentaje,
                orden=idx,
            )
        
        return {
            "id": factura.id,
            "numero": factura.numero,
            "estado": factura.estado,
            "total": str(factura.total),
            "created": True
        }, 201
        
    except Exception as e:
        logger.exception(f"Error al emitir factura desde cotización: {e}")
        return {
            "error": "internal_error",
            "message": f"Error inesperado: {str(e)}"
        }, 500


def validar_numeracion_dian(empresa_id: int, prefijo: str, consecutivo: int) -> Tuple[bool, Optional[str]]:
    """
    Valida la numeración de factura según reglas DIAN.
    
    ⚠️ ZERO TRUST v2.60:
    - Valida que la empresa pertenezca al tenant
    - Valida formato de prefijo (máximo 4 caracteres alfanuméricos)
    - Valida rango de consecutivo (1-99999999)
    - Valida que no haya duplicados
    
    Args:
        empresa_id: ID de la empresa del tenant (Zero Trust)
        prefijo: Prefijo de la factura (ej: "FST")
        consecutivo: Número consecutivo
        
    Returns:
        Tuple (is_valid, error_message):
        - (True, None): Si la numeración es válida
        - (False, str): Si hay error, retorna mensaje descriptivo
    """
    try:
        # ⚠️ ZERO TRUST: Validar que la empresa pertenece al tenant
        empresa = Empresa.objects.filter(id=empresa_id).first()
        if not empresa:
            return False, "La empresa no existe o no pertenece a este tenant."
        
        # Validar formato de prefijo
        if not prefijo or len(prefijo) > 4:
            return False, "El prefijo debe tener máximo 4 caracteres."
        
        if not prefijo.replace("_", "").replace("-", "").isalnum():
            return False, "El prefijo solo puede contener letras, números, guiones y guiones bajos."
        
        # Validar rango de consecutivo
        if consecutivo < 1 or consecutivo > 99999999:
            return False, "El consecutivo debe estar entre 1 y 99999999."
        
        # Validar que no haya duplicados
        numero = f"{prefijo}{consecutivo:06d}"
        factura_existente = Factura.objects.filter(
            empresa_id=empresa_id,
            numero=numero
        ).exists()
        
        if factura_existente:
            return False, f"Ya existe una factura con el número {numero}."
        
        # Validar autorización DIAN (si está configurada)
        # TODO: Implementar validación contra autorización DIAN si está disponible
        # Por ahora, solo validamos formato y duplicados
        
        return True, None
        
    except Exception as e:
        logger.exception(f"Error al validar numeración DIAN: {e}")
        return False, f"Error inesperado al validar numeración: {str(e)}"
