"""
Heurísticas para detectar XML UBL 2.1 y AttachedDocument.

Filtra archivos que parecen ser facturas UBL antes de enviarlos a los servicios
de apps.tenant.facturas para parsing completo.

WARNING: FASE 1: Solo heurísticas básicas, sin parsing completo.
WARNING: SSoT: El parsing real de UBL está en apps.tenant.facturas.ubl_parser
"""
from typing import Literal


def guess_file_kind(filename: str, content_type: str, content: bytes) -> Literal["xml", "zip", "rar", "7z", "other"]:
    """
    Adivina el tipo de archivo basado en nombre, content-type y contenido.
    
    WARNING: FASE 1: Heurística básica por extensión y magic bytes.
    TODO FASE 2: Detección más robusta con magic bytes completos.
    
    Args:
        filename: Nombre del archivo
        content_type: Content-Type MIME declarado
        content: Primeros bytes del contenido (para magic bytes)
        
    Returns:
        Tipo de archivo detectado
        
    Ejemplo:
        kind = guess_file_kind("factura.xml", "application/xml", b"<?xml...")
        # Retorna: "xml"
    """
    filename_lower = filename.lower()
    
    # Detección por extensión
    if filename_lower.endswith('.xml'):
        return "xml"
    elif filename_lower.endswith('.zip'):
        return "zip"
    elif filename_lower.endswith('.rar'):
        return "rar"
    elif filename_lower.endswith('.7z'):
        return "7z"
    
    # Detección por magic bytes (primeros bytes del archivo)
    if content:
        if content.startswith(b'PK\x03\x04') or content.startswith(b'PK\x05\x06'):
            return "zip"
        elif content.startswith(b'Rar!\x1a\x07'):
            return "rar"
        elif content.startswith(b'7z\xbc\xaf\x27\x1c'):
            return "7z"
        elif content.startswith(b'<?xml') or content.startswith(b'<'):
            return "xml"
    
    # Detección por content-type
    content_type_lower = content_type.lower()
    if 'xml' in content_type_lower:
        return "xml"
    elif 'zip' in content_type_lower:
        return "zip"
    elif 'rar' in content_type_lower:
        return "rar"
    elif '7z' in content_type_lower or 'x-7z' in content_type_lower:
        return "7z"
    
    return "other"


def extract_xml_from_attacheddocument(xml_text: str) -> list[str]:
    """
    Extrae XMLs internos desde un AttachedDocument UBL.
    
    Si el XML es un AttachedDocument que contiene Invoice(s) en base64/CDATA,
    los decodifica y retorna lista de XMLs de Invoice.
    
    WARNING: IMPLEMENTACIÓN: Usa lxml para parsear AttachedDocument UBL.
    WARNING: SSoT: El parsing completo de UBL está en apps.tenant.facturas.ubl_parser
    Esta función solo detecta y extrae XMLs desde AttachedDocument.
    
    Args:
        xml_text: Texto XML que puede ser AttachedDocument
        
    Returns:
        Lista de strings con XMLs de Invoice extraídos (vacía si no es AttachedDocument)
        
    Ejemplo:
        attached_doc_xml = '''<AttachedDocument>
            <cac:Attachment>
                <cbc:EmbeddedDocumentBinaryObject encodingCode="base64">...</cbc:EmbeddedDocumentBinaryObject>
            </cac:Attachment>
        </AttachedDocument>'''
        invoices = extract_xml_from_attacheddocument(attached_doc_xml)
        # Retorna: ["<?xml version='1.0'?><Invoice>...</Invoice>", ...]
    """
    import base64
    
    if not xml_text or not isinstance(xml_text, str):
        return []
    
    xml_lower = xml_text.lower()
    
    # Verificar si es AttachedDocument (buscar namespaces UBL AttachedDocument)
    attached_doc_namespaces = [
        'urn:oasis:names:specification:ubl:schema:xsd:attacheddocument-2',
        'urn:oasis:names:specification:ubl:schema:xsd:attacheddocument',
        'attacheddocument',
    ]
    
    is_attached_doc = any(ns in xml_lower for ns in attached_doc_namespaces)
    if not is_attached_doc:
        # También verificar por elemento raíz
        if not ('<attacheddocument' in xml_lower or '<attached_document' in xml_lower):
            return []
    
    # Intentar parsear con lxml
    try:
        from lxml import etree

        # WARNING: [SEC-A3] resolve_entities=False/load_dtd=False/no_network=True
        # bloquean XXE/expansion de entidades -- este XML viene de un correo entrante,
        # origen no confiable.
        _safe_parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)

        # Parsear XML
        try:
            root = etree.fromstring(xml_text.encode('utf-8'), parser=_safe_parser)
        except etree.XMLSyntaxError:
            # Si falla, intentar con encoding alternativo
            try:
                root = etree.fromstring(xml_text.encode('latin-1'), parser=_safe_parser)
            except Exception:
                return []
        
        # Buscar elementos EmbeddedDocumentBinaryObject
        # Namespace UBL común
        namespaces = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'ubl': 'urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2',
        }
        
        # Buscar sin namespace también (por si no tiene prefijos)
        embedded_objects = root.xpath(
            './/*[local-name()="EmbeddedDocumentBinaryObject"] | '
            './/cbc:EmbeddedDocumentBinaryObject | '
            './/*[contains(local-name(), "EmbeddedDocument")]',
            namespaces=namespaces
        )
        
        extracted_xmls = []
        
        for obj in embedded_objects:
            # Obtener encoding
            encoding = obj.get('encodingCode', '').lower() or obj.get('encoding', '').lower()
            
            # Obtener contenido (texto del elemento)
            content = obj.text
            if not content:
                continue
            
            # Decodificar según encoding
            try:
                if encoding == 'base64':
                    # Decodificar base64
                    decoded_bytes = base64.b64decode(content)
                    decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                elif encoding == 'base64binary':
                    # Variante de base64
                    decoded_bytes = base64.b64decode(content)
                    decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                else:
                    # Asumir que es texto directo o CDATA
                    decoded_text = content
                
                # Validar que el contenido decodificado sea XML válido
                if decoded_text.strip().startswith('<?xml') or decoded_text.strip().startswith('<'):
                    # Verificar que contenga Invoice
                    if '<invoice' in decoded_text.lower() or '<creditnote' in decoded_text.lower():
                        extracted_xmls.append(decoded_text)
            
            except Exception:
                # Continuar con otros objetos si uno falla
                continue
        
        return extracted_xmls
    
    except ImportError:
        # Si lxml no está disponible, usar heurística básica
        # Buscar patrones base64 en el texto
        import re
        
        # Buscar elementos que parezcan EmbeddedDocumentBinaryObject con base64
        base64_pattern = r'<[^>]*EmbeddedDocumentBinaryObject[^>]*>(.*?)</[^>]*EmbeddedDocumentBinaryObject[^>]*>'
        matches = re.findall(base64_pattern, xml_text, re.IGNORECASE | re.DOTALL)
        
        extracted_xmls = []
        for match in matches:
            try:
                # Intentar decodificar base64
                decoded_bytes = base64.b64decode(match.strip())
                decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                
                # Verificar que sea XML válido
                if decoded_text.strip().startswith('<?xml') or decoded_text.strip().startswith('<'):
                    if '<invoice' in decoded_text.lower() or '<creditnote' in decoded_text.lower():
                        extracted_xmls.append(decoded_text)
            except Exception:
                continue
        
        return extracted_xmls
    
    except Exception:
        # Si hay cualquier error, retornar lista vacía
        return []


def is_ubl_invoice(xml_text: str) -> bool:
    """
    Heurística mínima para detectar si un XML es una factura UBL 2.1 o CreditNote.
    
    WARNING: IMPLEMENTACIÓN: Detecta tanto Invoice como CreditNote UBL 2.1.
    WARNING: SSoT: La validación completa de UBL está en apps.tenant.facturas.ubl_parser
    Esta función solo filtra rápidamente antes de enviar al parser completo.
    
    Args:
        xml_text: Texto XML a validar
        
    Returns:
        True si parece ser un Invoice o CreditNote UBL 2.1
        
    Ejemplo:
        xml = '<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">...</Invoice>'
        is_ubl_invoice(xml)  # True
    """
    if not xml_text or not isinstance(xml_text, str):
        return False
    
    xml_lower = xml_text.lower()
    
    # Heurística 1: Debe contener elemento <Invoice> o <CreditNote>
    has_invoice = '<invoice' in xml_lower
    has_creditnote = '<creditnote' in xml_lower or '<credit_note' in xml_lower
    
    if not (has_invoice or has_creditnote):
        return False
    
    # Heurística 2: Debe mencionar namespace UBL 2.1
    ubl_namespaces = [
        'urn:oasis:names:specification:ubl:schema:xsd:invoice-2',
        'urn:oasis:names:specification:ubl:schema:xsd:invoice',
        'urn:oasis:names:specification:ubl:schema:xsd:creditnote-2',
        'urn:oasis:names:specification:ubl:schema:xsd:creditnote',
        'http://www.dian.gov.co/contratos/facturaelectronica/v1',
    ]
    
    if not any(ns in xml_lower for ns in ubl_namespaces):
        return False
    
    return True
