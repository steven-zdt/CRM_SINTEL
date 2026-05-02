"""
Parser para documentos XML usando lxml.etree.

Referencia: https://lxml.de/
"""

from lxml import etree


def parse_xml_catalog(xml_bytes: bytes) -> dict:
    """
    Parsea un XML de catálogo tributario.

    Args:
        xml_bytes: Contenido XML como bytes

    Returns:
        dict con:
        - 'items': lista de elementos parseados
        - 'root_tag': tag raíz del XML
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        # Intentar parsear con recuperación de errores
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(xml_bytes, parser=parser)

    root_tag = root.tag

    # Extraer elementos relevantes por XPath comunes
    # Ajustar según la estructura real de los XMLs DIAN
    items = []

    # Buscar nodos comunes en catálogos tributarios
    xpaths = [
        "//Impuesto",
        "//Retencion",
        "//Tarifa",
        "//Concepto",
        "//Codigo",
        "//Actividad",
        "//Norma",
        "//Articulo",
    ]

    for xpath in xpaths:
        nodes = root.xpath(xpath)
        for node in nodes:
            # Convertir nodo a dict
            item = {
                "tag": node.tag,
                "text": "".join(node.xpath(".//text()")).strip(),
                "attributes": dict(node.attrib),
            }

            # Extraer hijos como campos
            for child in node:
                item[child.tag] = "".join(child.xpath(".//text()")).strip()

            items.append(item)

    # Si no se encontraron elementos específicos, devolver estructura del árbol
    if not items:
        items = [
            {
                "tag": root.tag,
                "text": "".join(root.xpath(".//text()")).strip(),
                "attributes": dict(root.attrib),
            }
        ]

    return {
        "root_tag": root_tag,
        "items": items,
    }
