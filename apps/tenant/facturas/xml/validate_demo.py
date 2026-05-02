"""
Validacion de facturas demo en la carpeta xml/.

SOLO PARSEO - sin persistencia a BD, sin contexto de tenant requerido.

Ejecutar dentro del contenedor:
    docker exec crm_sintel-web-1 python /app/apps/tenant/facturas/xml/validate_demo.py
"""
import os
import sys

# Asegurar que /app este en el path
sys.path.insert(0, '/app')

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from lxml.etree import QName

from apps.tenant.facturas.utils.ubl_parser import (
    _extraer_invoice_desde_attached_document,
    _limpiar_cdata_eficiente,
    _ns,
    _parse_xml,
    extraer_decimal,
    extraer_texto,
    extraer_texto_xpath,
    parse_ubl_to_dict,
)
from apps.tenant.facturas.utils.ubl_parser import (
    xpath as ubl_xpath,
)

XML_DIR = '/app/apps/tenant/facturas/xml'
XMLS = [
    'TFAv21P11N000000000027476S900298074R901123299D20260214000000.xml',
    'ad09011232990082600000162.xml',
    'ad0901123299008250000005a.xml',
]


def _print_creditnote(cn_root, label='CreditNote'):
    """Imprime campos clave de un CreditNote (NC)."""
    ns = _ns(cn_root)
    numero = extraer_texto(cn_root, './/cbc:ID', ns, '?')
    cude = extraer_texto(cn_root, './/cbc:UUID', ns, '')
    emisor_nit = extraer_texto_xpath(
        cn_root,
        ".//*[local-name()='AccountingSupplierParty']//*[local-name()='CompanyID']/text()",
        ns, '?',
    )
    receptor_nit = extraer_texto_xpath(
        cn_root,
        ".//*[local-name()='AccountingCustomerParty']//*[local-name()='CompanyID']/text()",
        ns, '?',
    )
    total = extraer_decimal(cn_root, './/cbc:PayableAmount', ns)
    print("  numero      : " + str(numero))
    cude_display = (str(cude)[:40] + '...') if len(str(cude)) > 40 else str(cude) or '(ninguno)'
    print("  cude        : " + cude_display)
    print("  emisor NIT  : " + str(emisor_nit))
    print("  receptor NIT: " + str(receptor_nit))
    print("  total       : " + str(total))
    print("  PARSE       : OK (" + label + ")")


def _parse_attached_creditnote(root, xml_bytes):
    """Extrae y parsea CreditNote embebido en AttachedDocument."""
    desc_nodes = ubl_xpath(
        root, "//*[local-name()='Attachment']//*[local-name()='Description']",
        ns=_ns(root),
    )
    for desc in desc_nodes:
        if not desc.text:
            continue
        content = _limpiar_cdata_eficiente(desc.text.strip())
        if '<CreditNote' in content or '<creditnote' in content:
            cn_bytes = content.encode('utf-8', errors='ignore')
            cn_root = _parse_xml(cn_bytes)
            return cn_root
    return None


print("=" * 70)
print("VALIDACION FACTURAS DEMO (solo parseo, sin BD)")
print("=" * 70)

for fname in XMLS:
    path = os.path.join(XML_DIR, fname)
    print("\n[FILE] " + fname)
    if not os.path.exists(path):
        print("  ERROR: archivo no encontrado")
        continue
    try:
        with open(path, 'rb') as f:
            xml_bytes = f.read()

        root = _parse_xml(xml_bytes)
        local = QName(root).localname.lower()
        print("  doc_type    : " + local)

        # CreditNote directo
        if local == 'creditnote':
            _print_creditnote(root, 'CreditNote NC')
            continue

        # AttachedDocument: intentar Invoice primero, luego CreditNote
        if local == 'attacheddocument':
            try:
                invoice_root = _extraer_invoice_desde_attached_document(root, xml_bytes=xml_bytes)
            except ValueError:
                # No habia Invoice embebido — buscar CreditNote
                cn_root = _parse_attached_creditnote(root, xml_bytes)
                if cn_root is not None:
                    _print_creditnote(cn_root, 'AttachedDocument > CreditNote NC134')
                else:
                    print("  PARSE ERROR : AttachedDocument sin Invoice ni CreditNote reconocido")
                continue
            # Se encontro Invoice embebido: usar parse_ubl_to_dict sobre invoice_root
            dto = parse_ubl_to_dict(invoice_root, xml_bytes=xml_bytes)
        else:
            # Invoice directo
            dto = parse_ubl_to_dict(root, xml_bytes=xml_bytes)

        # Mostrar resumen del DTO
        cufe = str(dto.get('cufe', '') or '')
        cufe_display = (cufe[:40] + '...') if len(cufe) > 40 else cufe or '(ninguno)'
        print("  numero      : " + str(dto.get('numero', '?')))
        print("  cufe        : " + cufe_display)
        print("  emisor NIT  : " + str(dto.get('emisor_nit', '?')))
        print("  emisor rs   : " + str(dto.get('emisor_razon_social', '?')))
        print("  receptor NIT: " + str(dto.get('receptor_nit', '?')))
        print("  receptor rs : " + str(dto.get('receptor_razon_social', '?')))
        print("  total       : " + str(dto.get('total', '?')))
        print("  naturaleza  : " + str(dto.get('naturaleza', '?')))
        print("  PARSE       : OK")

    except Exception as e:
        print("  PARSE ERROR : " + str(e))

print("\n" + "=" * 70)
print("FIN VALIDACION PARSE (sin persistencia)")
print("=" * 70)
