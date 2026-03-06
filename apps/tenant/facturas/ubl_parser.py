"""
Parser UBL 2.1 para importación de facturas electrónicas DIAN.

⚠️ v2.30: Service Layer Pattern - Separado de services.py para mantener SRP.
Este módulo solo mapea UBL→DTO; el parsing de bytes se hace en xml_parser.

⚠️ CONSUME: apps/services/xml_parser para helpers genéricos (xpath, text, attr).
⚠️ NO PARSEA BYTES: Acepta root ya parseado (etree._Element).

⚠️ SEGURIDAD: Parser robusto con namespaces dinámicos y local-name() para evitar
fallos por prefijos no declarados (ej. sts:).

⚠️ SOPORTE AttachedDocument: Si el root es AttachedDocument, extrae el Invoice
interno desde CDATA en //cac:Attachment//cbc:Description.
"""
from lxml import etree
import re
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, date, time
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from apps.services.document_parser.xml_parser.core import xpath, text, parse_xml_bytes


# --- Utilidades de parsing seguras (mantenidas para compatibilidad interna) ---

def _parse_xml(xml_input: str | bytes) -> etree._Element:
    """
    Parser robusto: acepta bytes o str, detecta encoding desde declaración XML.
    
    ⚠️ FORÉNSICA: Respeta encoding declarado en XML (<?xml version="1.0" encoding="...">).
    Si es str, lo convierte a bytes asumiendo UTF-8; si es bytes, lxml detecta encoding.
    
    Args:
        xml_input: XML como string o bytes
        
    Returns:
        Elemento raíz del XML parseado
    """
    parser = etree.XMLParser(
        ns_clean=True,
        remove_blank_text=True,
        recover=True,
        huge_tree=True  # Soporta XML grandes
    )
    if isinstance(xml_input, bytes):
        # lxml detecta encoding desde declaración XML automáticamente
        root = etree.fromstring(xml_input, parser=parser)
    else:
        # Si es str, convertir a bytes asumiendo UTF-8 (fallback)
        root = etree.fromstring(xml_input.encode("utf-8", errors="ignore"), parser=parser)
    return root


def _ns(root: etree._Element) -> dict:
    """
    Mapa de namespaces dinámico desde el documento + fallbacks UBL comunes.
    Evita fallos por prefijos no pasados al XPath.
    """
    ns = {k: v for k, v in (root.nsmap or {}).items() if k}  # ignora None (default NS)
    # Fallbacks UBL (no pisan los del documento)
    ns.setdefault("cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")
    ns.setdefault("cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
    ns.setdefault("ext", "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2")
    # No hardcodear 'sts'; si el XML lo aporta, vendrá en root.nsmap; si no, evita usarlo en XPath.
    return ns


def _x(root: etree._Element, expr: str):
    """
    Helper de XPath que siempre inyecta el nsmap del documento.
    
    ⚠️ DEPRECATED: Usar apps.services.xml_parser.xpath() en su lugar.
    Mantenido para compatibilidad con código existente.
    
    Raises:
        ValueError: Si hay error de evaluación XPath (mapeado desde etree.XPathEvalError)
    """
    try:
        return xpath(root, expr, ns=_ns(root))
    except etree.XPathEvalError as e:
        raise ValueError(f"XPath no válido o namespaces inesperados: {e}")


def _aware_issue_datetime(issue_date: str | None, issue_time: str | None) -> Optional[datetime]:
    """
    Parsea fecha/hora de emisión con manejo timezone-aware.
    
    ⚠️ TIMEZONE-AWARE: Retorna datetime con timezone si está disponible.
    ⚠️ VALIDATION: Lanza ValueError genérica si la fecha no es válida (el ViewSet la convertirá a 400 minimal).
    
    Args:
        issue_date: String de fecha (ej: "2024-01-15")
        issue_time: String de hora opcional (ej: "14:30:00")
        
    Returns:
        Objeto datetime timezone-aware
        
    Raises:
        ValueError: Si la fecha/hora no es válida (mensaje genérico)
    """
    if not issue_date and not issue_time:
        return None
    
    s = issue_date or ""
    if issue_time:
        s = f"{s}T{issue_time}" if "T" not in s else s
    
    dt = parse_datetime(s)
    
    # Fallback: formatos manuales si parse_datetime falla
    if dt is None:
        formatos = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        for formato in formatos:
            try:
                dt = datetime.strptime(s, formato)
                break
            except ValueError:
                continue
    
    if dt is None:
        # ValueError genérica; el ViewSet la convertirá a 400 minimal
        raise ValueError("issue_datetime_invalid")
    
    # Asegurar timezone-aware
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    
    return dt


def parsear_fecha_dian(fecha_str: str, hora_str: Optional[str] = None) -> Optional[datetime]:
    """
    Parsea una fecha en formato DIAN con manejo de timezone.
    
    ⚠️ DEPRECATED: Usar _aware_issue_datetime() para mejor manejo de errores.
    Mantenido por compatibilidad.
    
    Args:
        fecha_str: String de fecha en formato DIAN (ej: "2024-01-15")
        hora_str: String de hora opcional (ej: "14:30:00")
        
    Returns:
        Objeto datetime timezone-aware o None si no se puede parsear
    """
    try:
        return _aware_issue_datetime(fecha_str, hora_str)
    except ValueError:
        return None


def parsear_fecha_simple(fecha_str: str) -> Optional[date]:
    """Parsea una fecha simple (sin hora)."""
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def parsear_hora(hora_str: str) -> Optional[time]:
    """Parsea una hora."""
    try:
        return datetime.strptime(hora_str, '%H:%M:%S').time()
    except ValueError:
        return None


def extraer_texto(elemento: etree._Element, ruta: str, namespaces: dict = None, default: str = '') -> str:
    """
    Extrae texto de un elemento XML usando una ruta XPath simple (sin predicados/local-name()).
    
    ⚠️ LIMITACIÓN: .find() no soporta XPath completo. Para rutas con predicados, local-name(), 
    o /text(), usa extraer_texto_xpath().
    
    Args:
        elemento: Elemento raíz o elemento padre
        ruta: Ruta XPath relativa simple (sin predicados)
        namespaces: Diccionario de namespaces (opcional, si no se proporciona usa _ns())
        default: Valor por defecto si no se encuentra
        
    Returns:
        Texto del elemento o default
    """
    if namespaces is None:
        namespaces = _ns(elemento)
    resultado = elemento.find(ruta, namespaces) if namespaces else elemento.find(ruta)
    if resultado is not None and resultado.text:
        return resultado.text.strip()
    return default


def extraer_texto_xpath(elemento: etree._Element, expr: str, namespaces: dict = None, default: str = '') -> str:
    """
    Extrae texto usando XPath completo (soporta local-name(), //, text(), predicados).
    
    ⚠️ FORÉNSICA: Usa .xpath() en lugar de .find() para soportar XPath completo.
    
    Args:
        elemento: Elemento raíz o elemento padre
        expr: Expresión XPath completa (puede incluir local-name(), predicados, /text())
        namespaces: Diccionario de namespaces (opcional, si no se proporciona usa _ns())
        default: Valor por defecto si no se encuentra
        
    Returns:
        Texto del elemento o default
    """
    if namespaces is None:
        namespaces = _ns(elemento)
    try:
        nodos = elemento.xpath(expr, namespaces=namespaces)
        if not nodos:
            return default
        v = nodos[0]
        if isinstance(v, str):
            return v.strip()
        if hasattr(v, 'text') and v.text:
            return v.text.strip()
        return default
    except etree.XPathEvalError:
        return default


def extraer_decimal(elemento: etree._Element, ruta: str, namespaces: dict = None, default: Decimal = Decimal('0.00')) -> Decimal:
    """
    Extrae un valor decimal de un elemento XML usando ruta simple.
    
    ⚠️ LIMITACIÓN: .find() no soporta XPath completo. Para rutas con predicados, usa extraer_decimal_xpath().
    
    Args:
        elemento: Elemento raíz o elemento padre
        ruta: Ruta XPath relativa simple (sin predicados)
        namespaces: Diccionario de namespaces (opcional, si no se proporciona usa _ns())
        default: Valor por defecto si no se encuentra
        
    Returns:
        Decimal o default
    """
    if namespaces is None:
        namespaces = _ns(elemento)
    resultado = elemento.find(ruta, namespaces) if namespaces else elemento.find(ruta)
    if resultado is not None and resultado.text:
        try:
            return Decimal(resultado.text.strip())
        except (ValueError, TypeError):
            pass
    return default


def extraer_decimal_xpath(elemento: etree._Element, expr: str, namespaces: dict = None, default: Decimal = Decimal('0.00')) -> Decimal:
    """
    Extrae un valor decimal usando XPath completo (soporta local-name(), //, predicados).
    
    ⚠️ FORÉNSICA: Usa .xpath() en lugar de .find() para soportar XPath completo.
    
    Args:
        elemento: Elemento raíz o elemento padre
        expr: Expresión XPath completa
        namespaces: Diccionario de namespaces (opcional, si no se proporciona usa _ns())
        default: Valor por defecto si no se encuentra
        
    Returns:
        Decimal o default
    """
    texto = extraer_texto_xpath(elemento, expr, namespaces, '')
    if not texto:
        return default
    try:
        return Decimal(texto)
    except (ValueError, TypeError):
        return default


def extraer_entero(elemento: etree._Element, ruta: str, namespaces: dict = None, default: int = 0) -> int:
    """
    Extrae un valor entero de un elemento XML usando ruta simple.
    
    ⚠️ LIMITACIÓN: .find() no soporta XPath completo. Para rutas con predicados, usa extraer_entero_xpath().
    """
    if namespaces is None:
        namespaces = _ns(elemento)
    resultado = elemento.find(ruta, namespaces) if namespaces else elemento.find(ruta)
    if resultado is not None and resultado.text:
        try:
            return int(resultado.text.strip())
        except (ValueError, TypeError):
            pass
    return default


def extraer_entero_xpath(elemento: etree._Element, expr: str, namespaces: dict = None, default: int = 0) -> int:
    """
    Extrae un valor entero usando XPath completo (soporta local-name(), //, predicados).
    
    ⚠️ FORÉNSICA: Usa .xpath() en lugar de .find() para soportar XPath completo.
    """
    texto = extraer_texto_xpath(elemento, expr, namespaces, '')
    if not texto:
        return default
    try:
        return int(texto)
    except (ValueError, TypeError):
        return default


def _extraer_invoice_desde_attached_document(root: etree._Element) -> Optional[etree._Element]:
    """
    Si root es AttachedDocument, extrae el Invoice interno desde CDATA o ExternalReference.
    
    ⚠️ FORÉNSICA: Busca Invoice en múltiples ubicaciones:
    - //cac:Attachment//cbc:Description (CDATA)
    - //cac:Attachment//cac:ExternalReference//cbc:Description (texto)
    
    Args:
        root: Elemento raíz del XML
        
    Returns:
        Elemento Invoice interno o None si no se encuentra
        
    Raises:
        ValueError: Si es AttachedDocument pero no se encuentra Invoice embebido
    """
    from lxml.etree import QName
    local = QName(root).localname.lower()
    
    if local == "invoice":
        return root
    
    if local == "attacheddocument":
        # Buscar en múltiples ubicaciones
        # 1. //cac:Attachment//cbc:Description (CDATA o texto)
        attachment_nodes = xpath(root, "//*[local-name()='Attachment']", ns=_ns(root))
        for attachment in attachment_nodes:
            # Buscar Description directamente
            description_nodes = xpath(attachment, ".//*[local-name()='Description']", ns=_ns(root))
            for desc in description_nodes:
                if desc.text:
                    invoice_xml = desc.text.strip()
                    # Limpiar CDATA markers si existen
                    invoice_xml = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', invoice_xml, flags=re.DOTALL)
                    if invoice_xml:
                        try:
                            invoice_root = _parse_xml(invoice_xml.encode("utf-8", errors="ignore") if isinstance(invoice_xml, str) else invoice_xml)
                            if QName(invoice_root).localname.lower() == "invoice":
                                return invoice_root
                        except Exception:
                            continue
            
            # 2. //cac:ExternalReference//cbc:Description (alternativa)
            external_ref_nodes = xpath(attachment, ".//*[local-name()='ExternalReference']", ns=_ns(root))
            for ext_ref in external_ref_nodes:
                desc_nodes = xpath(ext_ref, ".//*[local-name()='Description']", ns=_ns(root))
                for desc in desc_nodes:
                    if desc.text:
                        invoice_xml = desc.text.strip()
                        invoice_xml = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', invoice_xml, flags=re.DOTALL)
                        if invoice_xml:
                            try:
                                invoice_root = _parse_xml(invoice_xml.encode("utf-8", errors="ignore") if isinstance(invoice_xml, str) else invoice_xml)
                                if QName(invoice_root).localname.lower() == "invoice":
                                    return invoice_root
                            except Exception:
                                continue
        
        # Si llegamos aquí, es AttachedDocument pero no se encontró Invoice
        raise ValueError("AttachedDocument: no se encontró <Invoice> embebido en cbc:Description")
    
    # Si no es Invoice ni AttachedDocument, retornar None (el caller manejará)
    return None


def _parsear_prefijo_consecutivo(numero: str) -> tuple[str, int]:
    """
    Parsea prefijo y consecutivo desde número de factura.
    
    Ejemplos:
    - "FST354" -> ("FST", 354)
    - "FV-001" -> ("FV", 1)
    - "FE-10020298" -> ("FE", 10020298)
    - "123" -> ("", 123)
    - "ABC" -> ("", 0)
    
    Args:
        numero: Número de factura (ej. "FST354", "FV-001")
        
    Returns:
        Tupla (prefijo, consecutivo)
    """
    if not numero:
        return ('', 0)
    
    numero_clean = numero.strip().upper()
    
    # Regex: ^([A-Z]+)[\s\-]?(\d+)$ - soporta guiones y espacios
    match = re.match(r'^([A-Z]+)[\s\-]?(\d+)$', numero_clean)
    if match:
        prefijo = match.group(1)
        consecutivo = int(match.group(2))
        return (prefijo, consecutivo)
    
    # Si no coincide, intentar extraer número al final
    match = re.search(r'(\d+)$', numero_clean)
    if match:
        consecutivo = int(match.group(1))
        return ('', consecutivo)
    
    # Si no hay número, retornar 0
    return ('', 0)


def importar_factura_desde_ubl(xml_text: str):
    """
    Importa una factura UBL 2.1 desde XML.
    - Soporta AttachedDocument con Invoice interno en CDATA.
    - Sin prefijos hardcodeados que no existan en el documento.
    - Usa nsmap dinámico; para nodos 'opcionales' de vendors usa local-name().
    
    ⚠️ v2.30: Service Layer Pattern - Solo parsea XML; la creación de Factura
    se delega a services.importar_ubl() que llama a este parser.
    
    Args:
        xml_text: Contenido XML UBL 2.1 (string)
        
    Returns:
        Instancia de Factura creada
        
    Raises:
        ValueError: Si el XML no es válido o no se puede parsear
    """
    # Importar aquí para evitar problemas de carga circular
    from apps.tenant.facturas.models import Factura
    from apps.tenant.facturas import services as facturas_services
    
    try:
        # Parsear XML con parser robusto
        root = _parse_xml(xml_text)
        
        # Detectar si es AttachedDocument y extraer Invoice interno
        try:
            invoice_root = _extraer_invoice_desde_attached_document(root)
        except ValueError as e:
            # Re-lanzar ValueError con mensaje claro para logging forense
            raise ValueError(str(e))
        
        if invoice_root is None:
            # Verificar si root es Invoice directamente
            from lxml.etree import QName
            local = QName(root).localname.lower()
            if local == "invoice":
                invoice_root = root
            else:
                raise ValueError(f"Documento no soportado: se espera Invoice o AttachedDocument, se encontró {local}")
        
        # Obtener namespaces dinámicos del documento Invoice
        namespaces = _ns(invoice_root)
        
        # Extraer información básica desde invoice_root
        # Número de factura: invoice_root/*[local-name()='ID']/text()
        numero_nodes = _x(invoice_root, ".//*[local-name()='ID'][parent::*[local-name()='Invoice']]/text()")
        if not numero_nodes:
            # Fallback: buscar cualquier ID en el Invoice
            numero_nodes = _x(invoice_root, ".//*[local-name()='ID']/text()")
        numero_factura = numero_nodes[0].strip() if numero_nodes else None
        if not numero_factura:
            # Fallback: intentar con namespace explícito
            numero_factura = extraer_texto(invoice_root, './/cbc:ID', namespaces, '')
        if not numero_factura:
            raise ValueError("No se encontró número de factura en el XML")
        
        # Parsear prefijo y consecutivo
        prefijo, consecutivo = _parsear_prefijo_consecutivo(numero_factura)
        
        # Alternativa DIAN: sts:AuthorizedInvoices/sts:Prefix cuando exista
        if not prefijo:
            prefix_nodes = _x(invoice_root, "//*[local-name()='AuthorizedInvoices']//*[local-name()='Prefix']/text()")
            if prefix_nodes:
                prefijo = prefix_nodes[0].strip()
        
        fecha_emision_str = extraer_texto(invoice_root, './/cbc:IssueDate', namespaces, '')
        hora_emision_str = extraer_texto(invoice_root, './/cbc:IssueTime', namespaces, '')
        try:
            fecha_emision = _aware_issue_datetime(fecha_emision_str, hora_emision_str) or timezone.now()
        except ValueError:
            raise ValueError("issue_datetime_invalid")
        
        # CUFE (Código Único de Facturación Electrónica): invoice_root/*[local-name()='UUID']/text()
        # NO va en numero, va en cufe
        cufe_nodes = _x(invoice_root, ".//*[local-name()='UUID']/text()")
        cufe = cufe_nodes[0].strip() if cufe_nodes else ''
        if not cufe:
            # Fallback: intentar con namespace explícito
            cufe = extraer_texto(invoice_root, './/cbc:UUID', namespaces, '')
        
        # Esta sección parece duplicada, se elimina ya que fecha_emision ya se procesó arriba
        
        # CUFE (Código Único de Facturación Electrónica)
        cufe = extraer_texto(root, './/cbc:UUID', namespaces, '')
        
        # UBL Version y metadatos
        ubl_version = extraer_texto(invoice_root, './/cbc:UBLVersionID', namespaces, '')
        customization_id = extraer_texto(invoice_root, './/cbc:CustomizationID', namespaces, '')
        profile_id = extraer_texto(invoice_root, './/cbc:ProfileID', namespaces, '')
        profile_execution_id = extraer_texto(invoice_root, './/cbc:ProfileExecutionID', namespaces, '')
        invoice_type_code = extraer_texto(invoice_root, './/cac:InvoiceTypeCode//cbc:ID', namespaces, '')
        
        # Emisor (snapshot SSoT): evita prefijos rígidos, usa local-name()
        # ⚠️ v2.60: CRÍTICO - Extracción correcta del NIT del emisor es esencial para determinar naturaleza
        emisor_nit = None
        emisor_nodes = _x(
            invoice_root,
            ".//*[local-name()='AccountingSupplierParty']//*[local-name()='CompanyID']/text()",
        )
        if emisor_nodes:
            emisor_nit = emisor_nodes[0].strip()
        if not emisor_nit:
            # Fallback: intentar con namespace explícito
            emisor_nit = extraer_texto(invoice_root, './/cac:AccountingSupplierParty//cac:Party//cac:PartyTaxScheme//cbc:CompanyID', namespaces, '')
        
        # ⚠️ v2.60: Validar que el NIT del emisor se extrajo correctamente
        # Si no se puede extraer, la factura no puede determinar su naturaleza automáticamente
        if not emisor_nit or not emisor_nit.strip():
            logger.warning("[ubl_parser] ⚠️ NIT del emisor no encontrado en XML - La naturaleza no se podrá determinar automáticamente")
        emisor_razon_social = extraer_texto(invoice_root, './/cac:AccountingSupplierParty//cac:Party//cac:PartyLegalEntity//cbc:RegistrationName', namespaces, '')
        emisor_direccion = extraer_texto(invoice_root, './/cac:AccountingSupplierParty//cac:Party//cac:PostalAddress//cbc:StreetName', namespaces, '')
        emisor_email = extraer_texto(invoice_root, './/cac:AccountingSupplierParty//cac:Party//cac:Contact//cbc:ElectronicMail', namespaces, '')
        emisor_telefono = extraer_texto(invoice_root, './/cac:AccountingSupplierParty//cac:Party//cac:Contact//cbc:Telephone', namespaces, '')
        emisor_actividad_ciiu = extraer_texto(invoice_root, './/cac:AccountingSupplierParty//cac:Party//cac:PartyLegalEntity//cac:RegistrationAddress//cbc:CityName', namespaces, '')
        
        # Receptor
        receptor_nit = extraer_texto(invoice_root, './/cac:AccountingCustomerParty//cac:Party//cac:PartyTaxScheme//cbc:CompanyID', namespaces, '')
        receptor_razon_social = extraer_texto(invoice_root, './/cac:AccountingCustomerParty//cac:Party//cac:PartyLegalEntity//cbc:RegistrationName', namespaces, '')
        receptor_direccion = extraer_texto(invoice_root, './/cac:AccountingCustomerParty//cac:Party//cac:PostalAddress//cbc:StreetName', namespaces, '')
        receptor_email = extraer_texto(invoice_root, './/cac:AccountingCustomerParty//cac:Party//cac:Contact//cbc:ElectronicMail', namespaces, '')
        receptor_telefono = extraer_texto(invoice_root, './/cac:AccountingCustomerParty//cac:Party//cac:Contact//cbc:Telephone', namespaces, '')
        
        # Totales
        subtotal = extraer_decimal(invoice_root, './/cac:LegalMonetaryTotal//cbc:TaxExclusiveAmount', namespaces)
        total_impuestos = extraer_decimal(invoice_root, './/cac:LegalMonetaryTotal//cbc:TaxInclusiveAmount', namespaces)
        impuestos = total_impuestos - subtotal
        total = extraer_decimal(invoice_root, './/cac:LegalMonetaryTotal//cbc:PayableAmount', namespaces)
        
        # Moneda
        moneda = extraer_texto(invoice_root, './/cbc:DocumentCurrencyCode', namespaces, 'COP')
        
        # Formas de pago
        forma_pago = extraer_texto(invoice_root, './/cac:PaymentMeans//cbc:PaymentMeansCode', namespaces, '')
        medio_pago_codigo = extraer_texto(invoice_root, './/cac:PaymentMeans//cac:PaymentID//cbc:ID', namespaces, '')
        payment_due_date_str = extraer_texto(invoice_root, './/cac:PaymentTerms//cbc:PaymentDueDate', namespaces, '')
        payment_due_date = parsear_fecha_simple(payment_due_date_str) if payment_due_date_str else None
        
        # Fecha de vencimiento
        fecha_vencimiento_str = extraer_texto(invoice_root, './/cbc:DueDate', namespaces, '')
        fecha_vencimiento = parsear_fecha_simple(fecha_vencimiento_str) if fecha_vencimiento_str else None
        
        # Autorización DIAN: usar local-name() para evitar fallos por prefijo sts: no declarado
        # Firma (si existe); NO usar 'sts:' en XPath: algunos proveedores no lo declaran
        hay_firma = bool(_x(invoice_root, ".//*[local-name()='Signature']"))
        
        autorizacion_numero_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='InvoiceControl']//*[local-name()='AuthorizationNumber']/text()")
        autorizacion_numero = autorizacion_numero_nodes[0].strip() if autorizacion_numero_nodes else ''
        if not autorizacion_numero:
            # Fallback: intentar con namespace explícito si sts está disponible
            if 'sts' in namespaces:
                autorizacion_numero = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:InvoiceControl//sts:AuthorizationNumber', namespaces, '')
        
        autorizacion_prefijo_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='InvoiceSource']//*[local-name()='IdentificationCode']/text()")
        autorizacion_prefijo = autorizacion_prefijo_nodes[0].strip() if autorizacion_prefijo_nodes else ''
        if not autorizacion_prefijo and 'sts' in namespaces:
            autorizacion_prefijo = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:InvoiceSource//sts:IdentificationCode', namespaces, '')
        
        autorizacion_rango_desde_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='InvoiceSource']//*[local-name()='NumericalRange']//*[local-name()='From']/text()")
        autorizacion_rango_desde = int(autorizacion_rango_desde_nodes[0].strip()) if autorizacion_rango_desde_nodes else 0
        if autorizacion_rango_desde == 0 and 'sts' in namespaces:
            autorizacion_rango_desde = extraer_entero(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:InvoiceSource//sts:NumericalRange//sts:From', namespaces, 0)
        
        autorizacion_rango_hasta_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='InvoiceSource']//*[local-name()='NumericalRange']//*[local-name()='To']/text()")
        autorizacion_rango_hasta = int(autorizacion_rango_hasta_nodes[0].strip()) if autorizacion_rango_hasta_nodes else 0
        if autorizacion_rango_hasta == 0 and 'sts' in namespaces:
            autorizacion_rango_hasta = extraer_entero(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:InvoiceSource//sts:NumericalRange//sts:To', namespaces, 0)
        
        autorizacion_vigencia_inicio_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='InvoiceSource']//*[local-name()='ValidityPeriod']//*[local-name()='StartDate']/text()")
        autorizacion_vigencia_inicio_str = autorizacion_vigencia_inicio_nodes[0].strip() if autorizacion_vigencia_inicio_nodes else ''
        if not autorizacion_vigencia_inicio_str and 'sts' in namespaces:
            autorizacion_vigencia_inicio_str = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:InvoiceSource//sts:ValidityPeriod//cbc:StartDate', namespaces, '')
        
        autorizacion_vigencia_fin_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='InvoiceSource']//*[local-name()='ValidityPeriod']//*[local-name()='EndDate']/text()")
        autorizacion_vigencia_fin_str = autorizacion_vigencia_fin_nodes[0].strip() if autorizacion_vigencia_fin_nodes else ''
        if not autorizacion_vigencia_fin_str and 'sts' in namespaces:
            autorizacion_vigencia_fin_str = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:InvoiceSource//sts:ValidityPeriod//cbc:EndDate', namespaces, '')
        autorizacion_vigencia_inicio = parsear_fecha_simple(autorizacion_vigencia_inicio_str) if autorizacion_vigencia_inicio_str else None
        autorizacion_vigencia_fin = parsear_fecha_simple(autorizacion_vigencia_fin_str) if autorizacion_vigencia_fin_str else None
        
        # QR Code (texto multilínea): sts:QRCode/text() — recomendado TextField
        qr_code_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='QRCode']/text()")
        qr_code = qr_code_nodes[0].strip() if qr_code_nodes else ''
        if not qr_code and 'sts' in namespaces:
            qr_code = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:QRCode', namespaces, '')
        
        # QR URL: última línea del QRCode si es URL válida (puede superar 200 caracteres)
        qr_url = ''
        if qr_code:
            # Buscar URL en las líneas del QRCode
            lines = qr_code.split('\n')
            for line in reversed(lines):  # Empezar desde el final
                line = line.strip()
                if line and (line.startswith('http://') or line.startswith('https://')):
                    qr_url = line
                    break
        
        # Si no se encontró en QRCode, buscar en QRCodeURL
        if not qr_url:
            qr_url_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='QRCodeURL']/text()")
            qr_url = qr_url_nodes[0].strip() if qr_url_nodes else ''
            if not qr_url and 'sts' in namespaces:
                qr_url = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:QRCodeURL', namespaces, '')
        
        # Validación DIAN: usar local-name() para robustez
        dian_validation_code_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='Validation']//*[local-name()='ValidationCode']/text()")
        dian_validation_code = dian_validation_code_nodes[0].strip() if dian_validation_code_nodes else ''
        if not dian_validation_code and 'sts' in namespaces:
            dian_validation_code = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:Validation//sts:ValidationCode', namespaces, '')
        
        dian_validation_desc_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='Validation']//*[local-name()='ValidationDescription']/text()")
        dian_validation_desc = dian_validation_desc_nodes[0].strip() if dian_validation_desc_nodes else ''
        if not dian_validation_desc and 'sts' in namespaces:
            dian_validation_desc = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:Validation//sts:ValidationDescription', namespaces, '')
        
        dian_validation_fecha_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='Validation']//*[local-name()='ValidationDate']/text()")
        dian_validation_fecha_str = dian_validation_fecha_nodes[0].strip() if dian_validation_fecha_nodes else ''
        if not dian_validation_fecha_str and 'sts' in namespaces:
            dian_validation_fecha_str = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:Validation//sts:ValidationDate', namespaces, '')
        
        dian_validation_hora_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='Validation']//*[local-name()='ValidationTime']/text()")
        dian_validation_hora_str = dian_validation_hora_nodes[0].strip() if dian_validation_hora_nodes else ''
        if not dian_validation_hora_str and 'sts' in namespaces:
            dian_validation_hora_str = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:Validation//sts:ValidationTime', namespaces, '')
        
        dian_validation_fecha = parsear_fecha_simple(dian_validation_fecha_str) if dian_validation_fecha_str else None
        dian_validation_hora = parsear_hora(dian_validation_hora_str) if dian_validation_hora_str else None
        
        # ApplicationResponse XML (si está presente): usar local-name()
        dian_response_xml_nodes = _x(invoice_root, ".//*[local-name()='UBLExtensions']//*[local-name()='DianExtensions']//*[local-name()='ApplicationResponse']/text()")
        dian_response_xml = dian_response_xml_nodes[0].strip() if dian_response_xml_nodes else ''
        if not dian_response_xml and 'sts' in namespaces:
            dian_response_xml = extraer_texto(invoice_root, './/ext:UBLExtensions//ext:UBLExtension//ext:ExtensionContent//sts:DianExtensions//sts:ApplicationResponse', namespaces, '')
        
        # Items: usar findall con namespaces dinámicos
        items_data = []
        # Usar xpath para InvoiceLine (soporta local-name() y namespaces dinámicos)
        invoice_lines = _x(invoice_root, ".//*[local-name()='InvoiceLine']")
        for item_elem in invoice_lines:
            linea_id = extraer_texto(item_elem, './/cbc:ID', namespaces)
            codigo = extraer_texto(item_elem, './/cac:Item//cbc:SellersItemIdentification//cbc:ID', namespaces)
            descripcion = extraer_texto(item_elem, './/cbc:Description', namespaces)
            cantidad = extraer_decimal(item_elem, './/cbc:InvoicedQuantity', namespaces)
            # Unidad de medida (usar xpath para mayor robustez)
            unidad_medida_nodes = _x(item_elem, ".//*[local-name()='InvoicedQuantity']")
            if unidad_medida_nodes:
                unidad_medida = unidad_medida_nodes[0].get('unitCode', 'UND')
            else:
                unidad_medida = 'UND'
            valor_unitario = extraer_decimal(item_elem, './/cac:Price//cbc:PriceAmount', namespaces)
            
            # IVA del ítem
            porcentaje_iva = Decimal('0.00')
            # Usar xpath para TaxSubtotal (soporta local-name())
            tax_subtotal_nodes = _x(item_elem, ".//*[local-name()='TaxTotal']//*[local-name()='TaxSubtotal']")
            for tax_elem in tax_subtotal_nodes:
                tax_category_nodes = _x(tax_elem, ".//*[local-name()='TaxCategory']//*[local-name()='ID']")
                tax_category = tax_category_nodes[0].text.strip() if tax_category_nodes and tax_category_nodes[0].text else None
                if tax_category == '01':  # IVA
                    porcentaje_iva = extraer_decimal(tax_elem, './/cbc:Percent', namespaces, Decimal('0.00'))
                    break
            # Si no se encuentra en TaxTotal del item, buscar en el nivel de factura
            if porcentaje_iva == Decimal('0.00'):
                # Usar xpath para TaxSubtotal a nivel de factura
                tax_subtotal_nodes = _x(invoice_root, ".//*[local-name()='TaxTotal']//*[local-name()='TaxSubtotal']")
                for tax_elem in tax_subtotal_nodes:
                    tax_category_nodes = _x(tax_elem, ".//*[local-name()='TaxCategory']//*[local-name()='ID']")
                    tax_category = tax_category_nodes[0].text.strip() if tax_category_nodes and tax_category_nodes[0].text else None
                    if tax_category == '01':  # IVA
                        porcentaje_iva = extraer_decimal(tax_elem, './/cbc:Percent', namespaces, Decimal('0.00'))
                        break
            
            items_data.append({
                'linea_id': linea_id,
                'codigo': codigo,
                'descripcion': descripcion,
                'cantidad': cantidad,
                'unidad_medida': unidad_medida,
                'valor_unitario': valor_unitario,
                'porcentaje_iva': porcentaje_iva,
            })
        
        # Determinar naturaleza (VENTA si el tenant es emisor, COMPRA si es receptor)
        # Esto se hace comparando el NIT del tenant con el emisor/receptor
        from apps.tenant.facturas.models import Factura
        # ⚠️ RESILIENCIA: Import lazy para evitar ImportError en import-time
        try:
            from apps.tenant.empresa.services import get_empresa_emisor_data
            empresa_data = get_empresa_emisor_data()
        except ImportError:
            # Si no está disponible, usar None (naturaleza por defecto: VENTA)
            empresa_data = None
        naturaleza = Factura.Naturaleza.VENTA  # Default
        if empresa_data:
            tenant_nit = empresa_data.get('nit', '')
            # Si el tenant es el receptor, es COMPRA
            if receptor_nit == tenant_nit:
                naturaleza = Factura.Naturaleza.COMPRA
            # Si el tenant es el emisor, es VENTA (ya es el default)
        
        # Determinar categoría (PRODUCTO/SERVICIO/MIXTO) basado en items
        es_servicio_count = sum(1 for item in items_data if item.get('unidad_medida', '').upper() in {'ZZ', 'SERVICIO'})
        if es_servicio_count == 0:
            categoria = Factura.Categoria.PRODUCTO
        elif es_servicio_count == len(items_data):
            categoria = Factura.Categoria.SERVICIO
        else:
            categoria = Factura.Categoria.MIXTO
        
        # Construir datos para crear factura
        factura_data = {
            'numero': numero_factura,
            'prefijo': prefijo,
            'consecutivo': consecutivo,
            'tipo': Factura.TipoFactura.FE,  # Factura Electrónica
            'estado': Factura.Estado.ACEPTADA,  # Asumir aceptada si viene de UBL
            'naturaleza': naturaleza,
            'categoria': categoria,
            'ubl_version': ubl_version,
            'customization_id': customization_id,
            'profile_id': profile_id,
            'profile_execution_id': profile_execution_id,
            'invoice_type_code': invoice_type_code,
            'fecha_emision': fecha_emision,
            'fecha_vencimiento': fecha_vencimiento,
            'emisor_nit': emisor_nit,
            'emisor_razon_social': emisor_razon_social,
            'emisor_direccion': emisor_direccion,
            'emisor_email': emisor_email,
            'emisor_telefono': emisor_telefono,
            'emisor_actividad_ciiu': emisor_actividad_ciiu,
            'receptor_nit': receptor_nit,
            'receptor_razon_social': receptor_razon_social,
            'receptor_direccion': receptor_direccion,
            'receptor_email': receptor_email,
            'receptor_telefono': receptor_telefono,
            'moneda': moneda,
            'subtotal': subtotal,
            'impuestos': impuestos,
            'total': total,
            'forma_pago': forma_pago,
            'medio_pago_codigo': medio_pago_codigo,
            'payment_due_date': payment_due_date,
            'cufe': cufe,
            'qr_code': qr_code,
            'qr_url': qr_url,
            'autorizacion_numero': autorizacion_numero,
            'autorizacion_prefijo': autorizacion_prefijo,
            'autorizacion_rango_desde': autorizacion_rango_desde,
            'autorizacion_rango_hasta': autorizacion_rango_hasta,
            'autorizacion_vigencia_inicio': autorizacion_vigencia_inicio,
            'autorizacion_vigencia_fin': autorizacion_vigencia_fin,
            'dian_validation_code': dian_validation_code,
            'dian_validation_desc': dian_validation_desc,
            'dian_validation_fecha': dian_validation_fecha,
            'dian_validation_hora': dian_validation_hora,
            'dian_response_xml': dian_response_xml,
            'xml_content': xml_text,
        }
        
        # Crear factura usando el servicio (que recalcula totales desde items)
        factura = facturas_services.crear_factura(factura_data, items_data)
        
        return factura
        
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Error al parsear XML UBL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error al importar factura desde UBL: {str(e)}")


def parse_ubl_to_dict(root: etree._Element, xml_bytes: Optional[bytes] = None, naturaleza: Optional[str] = None) -> Dict[str, Any]:
    """
    Mapea UBL 2.1 (root ya parseado) a DTO (dict) sin crear Factura.
    
    ⚠️ CONSUME: apps/services/xml_parser para helpers genéricos.
    ⚠️ NO PARSEA BYTES: Acepta root ya parseado (etree._Element).
    ⚠️ TIMEZONE-AWARE: Retorna fecha_emision como datetime timezone-aware.
    
    Args:
        root: Elemento raíz del XML ya parseado (etree._Element)
        xml_bytes: Bytes originales del XML (opcional, para incluir en DTO)
        naturaleza: "VENTA" | "COMPRA" (opcional, se determina automáticamente si no se proporciona)
        
    Returns:
        Dict con datos de la factura (DTO) sin persistir
        - fecha_emision: datetime timezone-aware (ISO 8601 string en JSON)
        
    Raises:
        ValueError: Si el XML no es válido o no se puede parsear
    """
    try:
        
        # Detectar si es AttachedDocument y extraer Invoice interno
        try:
            invoice_root = _extraer_invoice_desde_attached_document(root)
        except ValueError as e:
            # Re-lanzar ValueError con mensaje claro para logging forense
            raise ValueError(str(e))
        
        if invoice_root is None:
            # Verificar si root es Invoice directamente
            from lxml.etree import QName
            local = QName(root).localname.lower()
            if local == "invoice":
                invoice_root = root
            else:
                raise ValueError(f"Documento no soportado: se espera Invoice o AttachedDocument, se encontró {local}")
        
        # Obtener namespaces dinámicos
        namespaces = _ns(invoice_root)
        
        # Extraer información (mismo proceso que importar_factura_desde_ubl pero sin crear Factura)
        numero_nodes = _x(invoice_root, ".//*[local-name()='ID'][parent::*[local-name()='Invoice']]/text()")
        if not numero_nodes:
            numero_nodes = _x(invoice_root, ".//*[local-name()='ID']/text()")
        numero_factura = numero_nodes[0].strip() if numero_nodes else None
        if not numero_factura:
            numero_factura = extraer_texto(invoice_root, './/cbc:ID', namespaces, '')
        if not numero_factura:
            raise ValueError("No se encontró número de factura en el XML")
        
        prefijo, consecutivo = _parsear_prefijo_consecutivo(numero_factura)
        
        if not prefijo:
            prefix_nodes = xpath(invoice_root, "//*[local-name()='AuthorizedInvoices']//*[local-name()='Prefix']/text()", ns=namespaces)
            if prefix_nodes:
                prefijo = prefix_nodes[0].strip()
        
        # Fecha emisión con timezone-aware
        fecha_emision_str = extraer_texto(invoice_root, './/cbc:IssueDate', namespaces, '')
        hora_emision_str = extraer_texto(invoice_root, './/cbc:IssueTime', namespaces, '')
        try:
            fecha_emision = _aware_issue_datetime(fecha_emision_str, hora_emision_str) or timezone.now()
        except ValueError:
            raise ValueError("issue_datetime_invalid")
        
        # CUFE
        cufe_nodes = xpath(invoice_root, ".//*[local-name()='UUID']/text()", ns=namespaces)
        cufe = cufe_nodes[0].strip() if cufe_nodes else ''
        if not cufe:
            cufe = extraer_texto(invoice_root, './/cbc:UUID', namespaces, '')
        
        # Emisor y Receptor (usar extraer_texto_xpath para rutas con local-name() y /text())
        emisor_nit = extraer_texto_xpath(invoice_root, ".//*[local-name()='AccountingSupplierParty']//*[local-name()='CompanyID']/text()", namespaces, '')
        emisor_razon_social = extraer_texto_xpath(invoice_root, ".//*[local-name()='AccountingSupplierParty']//*[local-name()='RegistrationName']/text()", namespaces, '')
        
        receptor_nit = extraer_texto_xpath(invoice_root, ".//*[local-name()='AccountingCustomerParty']//*[local-name()='CompanyID']/text()", namespaces, '')
        receptor_razon_social = extraer_texto_xpath(invoice_root, ".//*[local-name()='AccountingCustomerParty']//*[local-name()='RegistrationName']/text()", namespaces, '')
        
        # Totales
        subtotal = extraer_decimal(invoice_root, './/cbc:TaxExclusiveAmount', namespaces, Decimal('0.00'))
        impuestos = extraer_decimal(invoice_root, './/cbc:TaxInclusiveAmount', namespaces, Decimal('0.00')) - subtotal
        total = extraer_decimal(invoice_root, './/cbc:PayableAmount', namespaces, Decimal('0.00'))
        
        # Moneda
        moneda = extraer_texto(invoice_root, './/cbc:DocumentCurrencyCode', namespaces, 'COP')
        
        # ⚠️ IMPORTANTE: La naturaleza se calcula en Service Layer, no aquí
        # Este parser solo extrae datos del XML; la lógica de negocio está en services.py
        # Si se pasa naturaleza, se usa (pero normalmente se ignora y se calcula en services)
        if naturaleza:
            naturaleza = naturaleza.upper()
        else:
            # Default temporal (será sobrescrito en Service Layer)
            from apps.tenant.facturas.models import Factura
            naturaleza = Factura.Naturaleza.VENTA
        
        # Construir DTO
        dto = {
            'numero': numero_factura,
            'prefijo': prefijo,
            'consecutivo': consecutivo,
            'fecha_emision': fecha_emision,  # timezone-aware
            'emisor_nit': emisor_nit,
            'emisor_razon_social': emisor_razon_social,
            'receptor_nit': receptor_nit,
            'receptor_razon_social': receptor_razon_social,
            'moneda': moneda,
            'subtotal': subtotal,
            'impuestos': impuestos,
            'total': total,
            'cufe': cufe,
            'naturaleza': naturaleza,
            'items': [],  # Items se pueden agregar si es necesario para preview
        }
        
        # ⚠️ XMLs pesados: incluir en DTO para guardar en FacturaAnexos (no en fila principal)
        # Convertir bytes a string si es necesario
        if xml_bytes:
            dto['ubl_xml'] = xml_bytes.decode("utf-8", errors="ignore")
        else:
            # Fallback: serializar root a string (menos eficiente)
            dto['ubl_xml'] = etree.tostring(root, encoding="utf-8", pretty_print=False).decode("utf-8", errors="ignore")
        
        # Si hay ApplicationResponse/AttachedDocument, extraerlo
        # (por ahora, se puede agregar lógica para extraer ApplicationResponse si existe)
        dto['application_response_xml'] = None  # Se puede poblar si se detecta en el XML
        
        return dto
        
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Error al parsear XML UBL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error al parsear UBL a DTO: {str(e)}")
