"""
Funciones helper para parsing XML con lxml.

⚠️ v2.36: Migrado desde apps/services/xml_parser/core.py
Funciones utilitarias para trabajar con etree._Element de lxml.
"""
from typing import Optional, List, Any
from lxml import etree


def parse_xml_bytes(xml_bytes: bytes) -> etree._Element:
    """
    Parsea bytes XML a etree._Element.
    
    Args:
        xml_bytes: Contenido XML en bytes
        
    Returns:
        Element raíz del XML
        
    Raises:
        ValueError: Si el XML no es válido
    """
    try:
        parser = etree.XMLParser(recover=True, encoding='utf-8')
        root = etree.fromstring(xml_bytes, parser=parser)
        return root
    except Exception as e:
        raise ValueError(f"Error al parsear XML: {str(e)}")


def local_name(tag: str) -> str:
    """
    Extrae el local name de un tag XML (sin namespace).
    
    Args:
        tag: Tag completo (ej: "{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice")
        
    Returns:
        Local name (ej: "Invoice")
    """
    if not tag:
        return ""
    if "}" in tag:
        return tag.split("}")[-1]
    return tag


def xpath(element: etree._Element, xpath_expr: str) -> List[etree._Element]:
    """
    Ejecuta XPath y retorna lista de elementos.
    
    Args:
        element: Element raíz
        xpath_expr: Expresión XPath
        
    Returns:
        Lista de elementos encontrados
    """
    if element is None:
        return []
    try:
        return element.xpath(xpath_expr)
    except Exception:
        return []


def first(element: etree._Element, xpath_expr: str) -> Optional[etree._Element]:
    """
    Ejecuta XPath y retorna el primer elemento encontrado.
    
    Args:
        element: Element raíz
        xpath_expr: Expresión XPath
        
    Returns:
        Primer elemento encontrado o None
    """
    results = xpath(element, xpath_expr)
    return results[0] if results else None


def text(element: Optional[etree._Element]) -> str:
    """
    Extrae el texto de un elemento.
    
    Args:
        element: Element XML
        
    Returns:
        Texto del elemento o cadena vacía
    """
    if element is None:
        return ""
    return (element.text or "").strip()


def attr(element: Optional[etree._Element], attr_name: str) -> Optional[str]:
    """
    Extrae el valor de un atributo.
    
    Args:
        element: Element XML
        attr_name: Nombre del atributo
        
    Returns:
        Valor del atributo o None
    """
    if element is None:
        return None
    return element.get(attr_name)


def ensure_invoice_root_and_artifacts(root: etree._Element) -> dict:
    """
    Extrae Invoice/CreditNote desde AttachedDocument si es necesario.
    
    ⚠️ v2.36: Migrado desde apps/services/xml_parser/core.py
    
    Args:
        root: Element raíz (puede ser AttachedDocument o Invoice/CreditNote)
        
    Returns:
        Dict con:
        - invoice_root: Element raíz de Invoice/CreditNote
        - invoice_xml: XML del invoice como bytes
        - app_response_xml: XML de ApplicationResponse si existe
        - container: "AttachedDocument" o "Invoice"/"CreditNote"
    """
    container = local_name(root.tag)
    invoice_root = root
    invoice_xml = etree.tostring(root, encoding='utf-8')
    app_response_xml = None
    
    # Si es AttachedDocument, buscar Invoice/CreditNote embebido
    if container == "AttachedDocument":
        # Buscar en elementos hijos
        invoice = first(root, ".//*[local-name()='Invoice']")
        credit_note = first(root, ".//*[local-name()='CreditNote']")
        
        if invoice:
            invoice_root = invoice
            invoice_xml = etree.tostring(invoice, encoding='utf-8')
        elif credit_note:
            invoice_root = credit_note
            invoice_xml = etree.tostring(credit_note, encoding='utf-8')
        else:
            # Buscar en CDATA
            descriptions = xpath(root, ".//*[local-name()='Description']")
            for desc in descriptions:
                if desc.text:
                    try:
                        cdata_text = desc.text.strip()
                        if cdata_text.startswith("<![CDATA["):
                            cdata_text = cdata_text[9:-3]
                        embedded_root = parse_xml_bytes(cdata_text.encode('utf-8'))
                        embedded_tag = local_name(embedded_root.tag)
                        if embedded_tag in ("Invoice", "CreditNote"):
                            invoice_root = embedded_root
                            invoice_xml = etree.tostring(embedded_root, encoding='utf-8')
                            break
                    except Exception:
                        continue
        
        # Buscar ApplicationResponse
        app_response = first(root, ".//*[local-name()='ApplicationResponse']")
        if app_response:
            app_response_xml = etree.tostring(app_response, encoding='utf-8')
    
    return {
        "invoice_root": invoice_root,
        "invoice_xml": invoice_xml,
        "app_response_xml": app_response_xml,
        "container": container,
    }
