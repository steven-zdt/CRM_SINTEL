"""
Parser para documentos XML (FASE 2.3).

WARNING: PRINCIPIOS:
- Migra pipeline UBL v2.34
- Soporta Invoice y CreditNote UBL 2.1
- Detecta documentos embebidos en AttachedDocument CDATA
- Retorna DTO JSON unificado según apps/services/document_parser/dto.py
"""
import re
from decimal import Decimal
from typing import Any

from lxml import etree

# WARNING: REFACTOR: Eliminado normalize_encoding - solo se aplica a PDF/Excel en ingest_service.py
# Mantenemos sanitize_text, normalize_nit, normalize_currency porque son
# normalizaciones especificas de datos (no de encoding del archivo).
# normalize_numeric_to_decimal_string ya NO se usa aqui (bug real de
# escala x100, ver _decimal_desde_xml() mas abajo) -- los valores XML
# UBL/DIAN se parsean directo, sin pasar por ese normalizador compartido.
from apps.services.document_parser.normalizers import (
    normalize_currency,
    normalize_nit,
    sanitize_text,
)
from apps.services.document_parser.xml_parser.core import (
    attr,
    first,
    local_name,
    parse_xml_bytes,
    text,
    xpath,
)


def parse_to_dto(file_bytes: bytes, filename: str | None = None) -> dict[str, Any]:
    """
    Parsea un documento XML a DTO JSON unificado.
    
    WARNING: FASE 2.3: Migra pipeline UBL v2.34.
    
    Args:
        file_bytes: Contenido del archivo XML en bytes
        filename: Nombre del archivo (opcional)
        
    Returns:
        Dict con estructura DTO JSON unificado:
        {
            "document_type": "invoice.ubl21" | "creditnote.ubl21",
            "numero": str,
            "identificadores": {"cufe": str, "uuid": str},
            "fecha_emision": str (ISO 8601),
            "emisor": {"nit": str, "razon_social": str, ...},
            "receptor": {"nit": str, "razon_social": str, ...},
            "totales": {"moneda": str, "subtotal": str, "impuestos": str, "total": str},
            "referencia": {...} (solo para CreditNote),
            "motivo": str (solo para CreditNote),
        }
        
    Raises:
        ValueError: Si el XML no es válido o no se puede parsear
    """
    # WARNING: REFACTOR: NO normalizar encoding para XML - lxml maneja encoding automáticamente
    # La normalización solo se aplica a PDF y Excel en ingest_service.py
    # Parsear XML directamente (lxml detecta encoding desde declaración <?xml encoding="...">)
    try:
        xml_root = parse_xml_bytes(file_bytes)
    except Exception as e:
        raise ValueError(f"Error al parsear XML: {str(e)}")
    
    # Detectar tipo de documento (Invoice o CreditNote)
    root_tag = local_name(xml_root.tag)
    
    # Manejar AttachedDocument con documento embebido
    if root_tag == "AttachedDocument":
        # Buscar Invoice o CreditNote embebido directamente en el árbol
        invoice = first(xml_root, ".//*[local-name()='Invoice']")
        credit_note = first(xml_root, ".//*[local-name()='CreditNote']")
        
        if invoice:
            xml_root = invoice
            root_tag = "Invoice"
        elif credit_note:
            xml_root = credit_note
            root_tag = "CreditNote"
        else:
            # Buscar en CDATA dentro de Attachment/ExternalReference/Description
            # WARNING: PATRÓN REAL: Los XMLs de ejemplo tienen el Invoice/CreditNote embebido en CDATA
            # dentro de <cac:Attachment><cac:ExternalReference><cbc:Description><![CDATA[...]]>
            external_refs = xpath(xml_root, ".//*[local-name()='ExternalReference']")
            for ext_ref in external_refs:
                descriptions = xpath(ext_ref, ".//*[local-name()='Description']")
                for desc in descriptions:
                    if desc.text:
                        try:
                            cdata_text = desc.text.strip()
                            # Limpiar CDATA markers si existen
                            if cdata_text.startswith("<![CDATA["):
                                cdata_text = cdata_text[9:-3]
                            elif cdata_text.startswith("<?xml"):
                                # Ya es XML directo sin CDATA markers
                                pass
                            # Intentar parsear
                            embedded_root = parse_xml_bytes(cdata_text.encode('utf-8'))
                            embedded_tag = local_name(embedded_root.tag)
                            if embedded_tag in ("Invoice", "CreditNote"):
                                xml_root = embedded_root
                                root_tag = embedded_tag
                                break
                        except Exception:
                            continue
                    if root_tag in ("Invoice", "CreditNote"):
                        break
                if root_tag in ("Invoice", "CreditNote"):
                    break
            
            # Fallback: buscar en cualquier Description si no se encontró en ExternalReference
            if root_tag == "AttachedDocument":
                descriptions = xpath(xml_root, ".//*[local-name()='Description']")
                for desc in descriptions:
                    if desc.text:
                        try:
                            cdata_text = desc.text.strip()
                            if cdata_text.startswith("<![CDATA["):
                                cdata_text = cdata_text[9:-3]
                            elif cdata_text.startswith("<?xml") or cdata_text.startswith("<Invoice") or cdata_text.startswith("<CreditNote"):
                                embedded_root = parse_xml_bytes(cdata_text.encode('utf-8'))
                                embedded_tag = local_name(embedded_root.tag)
                                if embedded_tag in ("Invoice", "CreditNote"):
                                    xml_root = embedded_root
                                    root_tag = embedded_tag
                                    break
                        except Exception:
                            continue
    
    # Parsear según tipo
    if root_tag == "Invoice":
        return _parse_invoice_ubl21(xml_root)
    elif root_tag == "CreditNote":
        return _parse_credit_note_ubl21(xml_root)
    else:
        raise ValueError(f"Tipo de documento XML no soportado: {root_tag}")


def _decimal_desde_xml(texto: str | None, default: str = "0.00") -> Decimal:
    """
    Parsea un valor numerico crudo de un nodo XML UBL/DIAN a Decimal.

    BUG REAL corregido (2026-09-18, reportado en produccion via "sincronizar
    factura -> Venta": una Factura con InvoicedQuantity=1 y PriceAmount=582992
    en el XML se persistio con cantidad=0.01 y valor_unitario=5829.92 --
    ambos divididos por 100). Causa raiz:
    `normalize_numeric_to_decimal_string()` (normalizers.py, compartida con
    csv/excel/pdf/txt) hace `value.replace('.', '')` y LUEGO comprueba
    `'.' not in value` para decidir si dividir por 100 -- esa comprobacion
    es SIEMPRE True (el punto ya fue eliminado en la linea anterior), asi
    que CUALQUIER valor sin separadores de miles (osea, cualquier numero
    XML valido: "1", "582992", "19.00"...) se divide por 100 sin condicion.
    Los valores con punto decimal ya presente "sobreviven" solo por
    coincidencia (str(Decimal) siempre lo reintroduce), lo cual oculto el
    bug en los totales de cabecera pero no en items con enteros puros.

    Los valores numericos UBL/DIAN son SIEMPRE decimales canonicos (xs:decimal,
    punto como separador decimal, NUNCA separadores de miles) -- no existe
    ninguna ambiguedad de locale que resolver aqui, a diferencia de texto
    extraido de CSV/Excel/PDF (que si puede traer "1.500.000" o "1,500,000").
    Por eso este parser NO debe reutilizar `normalize_numeric_to_decimal_string()`
    (que sigue intacta, sin tocar, para no arriesgar los otros parsers sin
    evidencia de que tambien esten rotos) -- basta un parseo directo.
    """
    if texto is None:
        return Decimal(default)
    texto = texto.strip()
    if not texto:
        return Decimal(default)
    try:
        return Decimal(texto)
    except Exception:
        return Decimal(default)


def _extract_retentions(root: etree._Element) -> dict[str, str]:
    """
    Extrae retenciones (Retefuente, ReteICA, ReteIVA) de un XML UBL.
    
    Args:
        root: Element raíz (Invoice o CreditNote)
        
    Returns:
        Dict con strings normalizados: {"retefuente": "0.00", "reteica": "0.00", "reteiva": "0.00"}
    """
    retentions = {
        "retefuente": Decimal("0.00"),
        "reteica": Decimal("0.00"),
        "reteiva": Decimal("0.00")
    }
    
    # # WARNING: DIAN UBL 2.1: Las retenciones suelen estar en cac:WithholdingTaxTotal
    # local-name() para robustez ante namespaces.
    withholding_tax_totals = xpath(root, ".//*[local-name()='WithholdingTaxTotal']")
    for w_tax in withholding_tax_totals:
        tax_subtotals = xpath(w_tax, ".//*[local-name()='TaxSubtotal']")
        for ts in tax_subtotals:
            tax_scheme_id = text(first(ts, ".//*[local-name()='TaxScheme']//*[local-name()='ID']"))
            tax_amount_str = text(first(ts, ".//*[local-name()='TaxAmount']"))
            
            if not tax_scheme_id or not tax_amount_str:
                continue
                
            amount = _decimal_desde_xml(tax_amount_str)
            
            # # WARNING: SINTEL v2.62: Mantenemos mapeo legacy del proyecto (ubl_parser.py):
            # 05 -> Retefuente (DIAN dice ReteIVA)
            # 06 -> ReteIVA (DIAN dice Retefuente)
            # 07 -> ReteICA
            if tax_scheme_id == "05":
                retentions["retefuente"] += amount
            elif tax_scheme_id == "06":
                retentions["reteiva"] += amount
            elif tax_scheme_id == "07":
                retentions["reteica"] += amount

    return {k: f"{v:.2f}" for k, v in retentions.items()}


def _parse_invoice_ubl21(invoice_root: etree._Element) -> dict[str, Any]:
    """
    Parsea Invoice UBL 2.1 a DTO.
    
    Args:
        invoice_root: Element raíz de Invoice
        
    Returns:
        Dict con DTO JSON unificado
    """
    # Número
    numero = text(first(invoice_root, ".//*[local-name()='ID']"))
    if not numero:
        raise ValueError("Falta campo obligatorio: ID (número de factura)")
    numero = sanitize_text(numero)
    
    # CUFE/UUID
    cufe = text(first(invoice_root, ".//*[local-name()='UUID']")) or ""
    cufe = sanitize_text(cufe)
    
    # Fecha de emisión
    issue_date = text(first(invoice_root, ".//*[local-name()='IssueDate']")) or ""
    issue_time = text(first(invoice_root, ".//*[local-name()='IssueTime']")) or ""
    
    fecha_emision = issue_date
    if issue_time:
        fecha_emision = f"{issue_date}T{issue_time}"
    # WARNING: v2.61.3: Solo agregar timezone si no hay uno ya presente en la cadena
    # El issue_time puede incluir offset como "13:21:00-05:00" → ya tiene zona horaria
    if fecha_emision and "T" in fecha_emision:
        time_part = fecha_emision.split("T", 1)[1]
        # Verificar si ya tiene timezone: ±HH:MM al final, o Z
        has_tz = bool(re.search(r'[+-]\d{2}:\d{2}$', time_part)) or time_part.endswith('Z')
        if not has_tz:
            fecha_emision = f"{fecha_emision}-05:00"  # UTC-5 (Colombia)
    
    # Emisor
    supplier_party = first(invoice_root, ".//*[local-name()='AccountingSupplierParty']//*[local-name()='Party']")
    emisor_nit = ""
    emisor_razon_social = ""
    emisor_direccion = ""
    emisor_email = ""
    emisor_telefono = ""
    emisor_actividad_ciiu = ""
    
    if supplier_party is not None:
        tax_scheme = first(supplier_party, ".//*[local-name()='PartyTaxScheme']")
        if tax_scheme is not None:
            emisor_nit = text(first(tax_scheme, ".//*[local-name()='CompanyID']")) or ""
            # WARNING: FALLBACK: Algunos XMLs tienen RegistrationName directamente en PartyTaxScheme
            # (ej: <cac:PartyTaxScheme><cbc:RegistrationName>...</cbc:RegistrationName>)
            if not emisor_razon_social:
                emisor_razon_social = text(first(tax_scheme, ".//*[local-name()='RegistrationName']")) or ""
        legal_entity = first(supplier_party, ".//*[local-name()='PartyLegalEntity']")
        if legal_entity is not None:
            razon_social_legal = text(first(legal_entity, ".//*[local-name()='RegistrationName']")) or ""
            if razon_social_legal:
                emisor_razon_social = razon_social_legal
        
        # Dirección del emisor
        physical_location = first(supplier_party, ".//*[local-name()='PhysicalLocation']")
        if physical_location is not None:
            address = first(physical_location, ".//*[local-name()='Address']")
            if address is not None:
                address_lines = xpath(address, ".//*[local-name()='AddressLine']//*[local-name()='Line']")
                if address_lines:
                    emisor_direccion = sanitize_text(" ".join([text(line) for line in address_lines if text(line)]))
        
        # Contacto (email, teléfono)
        contact = first(supplier_party, ".//*[local-name()='Contact']")
        if contact is not None:
            emisor_email = text(first(contact, ".//*[local-name()='ElectronicMail']")) or ""
            emisor_telefono = text(first(contact, ".//*[local-name()='Telephone']")) or ""
        
        # CIIU (IndustryClassificationCode)
        emisor_actividad_ciiu = text(first(supplier_party, ".//*[local-name()='IndustryClassificationCode']")) or ""
    
    emisor_nit = normalize_nit(emisor_nit) or ""
    emisor_razon_social = sanitize_text(emisor_razon_social)
    emisor_direccion = sanitize_text(emisor_direccion)
    emisor_email = sanitize_text(emisor_email)
    emisor_telefono = sanitize_text(emisor_telefono)
    emisor_actividad_ciiu = sanitize_text(emisor_actividad_ciiu)
    
    # Receptor
    customer_party = first(invoice_root, ".//*[local-name()='AccountingCustomerParty']//*[local-name()='Party']")
    receptor_nit = ""
    receptor_razon_social = ""
    receptor_direccion = ""
    receptor_email = ""
    receptor_telefono = ""
    
    if customer_party is not None:
        tax_scheme = first(customer_party, ".//*[local-name()='PartyTaxScheme']")
        if tax_scheme is not None:
            receptor_nit = text(first(tax_scheme, ".//*[local-name()='CompanyID']")) or ""
            # WARNING: FALLBACK: Algunos XMLs tienen RegistrationName directamente en PartyTaxScheme
            # (ej: <cac:PartyTaxScheme><cbc:RegistrationName>...</cbc:RegistrationName>)
            if not receptor_razon_social:
                receptor_razon_social = text(first(tax_scheme, ".//*[local-name()='RegistrationName']")) or ""
        legal_entity = first(customer_party, ".//*[local-name()='PartyLegalEntity']")
        if legal_entity is not None:
            razon_social_legal = text(first(legal_entity, ".//*[local-name()='RegistrationName']")) or ""
            if razon_social_legal:
                receptor_razon_social = razon_social_legal
        
        # Dirección del receptor
        physical_location = first(customer_party, ".//*[local-name()='PhysicalLocation']")
        if physical_location is not None:
            address = first(physical_location, ".//*[local-name()='Address']")
            if address is not None:
                address_lines = xpath(address, ".//*[local-name()='AddressLine']//*[local-name()='Line']")
                if address_lines:
                    receptor_direccion = sanitize_text(" ".join([text(line) for line in address_lines if text(line)]))
        
        # Contacto (email, teléfono)
        contact = first(customer_party, ".//*[local-name()='Contact']")
        if contact is not None:
            receptor_email = text(first(contact, ".//*[local-name()='ElectronicMail']")) or ""
            receptor_telefono = text(first(contact, ".//*[local-name()='Telephone']")) or ""
    
    receptor_nit = normalize_nit(receptor_nit) or ""
    receptor_razon_social = sanitize_text(receptor_razon_social)
    receptor_direccion = sanitize_text(receptor_direccion)
    receptor_email = sanitize_text(receptor_email)
    receptor_telefono = sanitize_text(receptor_telefono)
    
    # Metadatos UBL
    ubl_version = text(first(invoice_root, ".//*[local-name()='UBLVersionID']")) or ""
    customization_id = text(first(invoice_root, ".//*[local-name()='CustomizationID']")) or ""
    profile_id = text(first(invoice_root, ".//*[local-name()='ProfileID']")) or ""
    profile_execution_id = text(first(invoice_root, ".//*[local-name()='ProfileExecutionID']")) or ""
    invoice_type_code = text(first(invoice_root, ".//*[local-name()='InvoiceTypeCode']")) or ""
    
    # Extraer prefijo y consecutivo del número (ej: "FST355" → prefijo="FST", consecutivo=355)
    prefijo = ""
    consecutivo = 0
    if numero:
        # Intentar separar prefijo y número
        match = re.match(r'^([A-Za-z]+)(\d+)$', numero.strip())
        if match:
            prefijo = match.group(1)
            try:
                consecutivo = int(match.group(2))
            except ValueError:
                pass
    
    # Autorización DIAN (desde DianExtensions)
    autorizacion_numero = ""
    autorizacion_prefijo = ""
    autorizacion_rango_desde = None
    autorizacion_rango_hasta = None
    autorizacion_vigencia_inicio = None
    autorizacion_vigencia_fin = None
    
    dian_extensions = first(invoice_root, ".//*[local-name()='DianExtensions']")
    if dian_extensions is not None:
        invoice_control = first(dian_extensions, ".//*[local-name()='InvoiceControl']")
        if invoice_control is not None:
            autorizacion_numero = text(first(invoice_control, ".//*[local-name()='InvoiceAuthorization']")) or ""
            authorized_invoices = first(invoice_control, ".//*[local-name()='AuthorizedInvoices']")
            if authorized_invoices is not None:
                autorizacion_prefijo = text(first(authorized_invoices, ".//*[local-name()='Prefix']")) or ""
                desde_str = text(first(authorized_invoices, ".//*[local-name()='From']")) or ""
                hasta_str = text(first(authorized_invoices, ".//*[local-name()='To']")) or ""
                try:
                    autorizacion_rango_desde = int(desde_str) if desde_str else None
                    autorizacion_rango_hasta = int(hasta_str) if hasta_str else None
                except ValueError:
                    pass
            auth_period = first(invoice_control, ".//*[local-name()='AuthorizationPeriod']")
            if auth_period is not None:
                autorizacion_vigencia_inicio = text(first(auth_period, ".//*[local-name()='StartDate']")) or ""
                autorizacion_vigencia_fin = text(first(auth_period, ".//*[local-name()='EndDate']")) or ""
    
    # QR Code y URL
    qr_code = ""
    qr_url = ""
    if dian_extensions is not None:
        qr_code_elem = first(dian_extensions, ".//*[local-name()='QRCode']")
        if qr_code_elem is not None:
            qr_code = text(qr_code_elem) or ""
            # Extraer URL del QR code si está presente
            if qr_code and "https://" in qr_code:
                url_match = re.search(r'https://[^\s]+', qr_code)
                if url_match:
                    qr_url = url_match.group(0)
    
    # Totales
    monetary_total = first(invoice_root, ".//*[local-name()='LegalMonetaryTotal']")
    subtotal_str = "0.00"
    impuestos_str = "0.00"
    total_str = "0.00"
    moneda = "COP"
    
    if monetary_total is not None:
        line_extension_amount = text(first(monetary_total, ".//*[local-name()='LineExtensionAmount']")) or "0.00"
        tax_inclusive_amount = text(first(monetary_total, ".//*[local-name()='TaxInclusiveAmount']")) or "0.00"
        payable_amount = text(first(monetary_total, ".//*[local-name()='PayableAmount']")) or "0.00"
        currency_id = attr(first(monetary_total, ".//*[local-name()='LineExtensionAmount']"), "currencyID") or "COP"
        
        # Normalizar valores (parseo directo -- ver _decimal_desde_xml())
        subtotal_decimal = _decimal_desde_xml(line_extension_amount)
        tax_inclusive_decimal = _decimal_desde_xml(tax_inclusive_amount)
        payable_decimal = _decimal_desde_xml(payable_amount)

        # Calcular impuestos: TaxInclusiveAmount - LineExtensionAmount
        # Esto es más preciso que PayableAmount - LineExtensionAmount porque
        # PayableAmount puede incluir descuentos/cargos adicionales
        impuestos_decimal = tax_inclusive_decimal - subtotal_decimal
        if impuestos_decimal < Decimal("0.00"):
            impuestos_decimal = Decimal("0.00")

        # Usar PayableAmount como total (puede incluir descuentos/cargos)
        # Si PayableAmount no está disponible, usar TaxInclusiveAmount
        if payable_decimal > Decimal("0.00"):
            total_decimal = payable_decimal
        else:
            total_decimal = tax_inclusive_decimal

        # Convertir a strings normalizados
        subtotal_str = f"{subtotal_decimal:.2f}"
        impuestos_str = f"{impuestos_decimal:.2f}"
        total_str = f"{total_decimal:.2f}"
        moneda = normalize_currency(currency_id)

    # Construir DTO (FASE 3: incluir type base para compatibilidad)
    # --- Items (InvoiceLine) ---
    items = []
    invoice_lines = xpath(invoice_root, ".//*[local-name()='InvoiceLine']")
    for line_elem in invoice_lines:
        linea_id = text(first(line_elem, ".//*[local-name()='ID']")) or ""
        descripcion = text(first(line_elem, ".//*[local-name()='Description']")) or ""
        cantidad_str = text(first(line_elem, ".//*[local-name()='InvoicedQuantity']")) or "1"
        qty_elem = first(line_elem, ".//*[local-name()='InvoicedQuantity']")
        unidad_medida = attr(qty_elem, "unitCode") or "UND" if qty_elem is not None else "UND"

        valor_unitario_str = text(first(line_elem, ".//*[local-name()='Price']//*[local-name()='PriceAmount']")) or "0"
        sellers_id = first(line_elem, ".//*[local-name()='SellersItemIdentification']//*[local-name()='ID']")
        codigo = text(sellers_id) or "" if sellers_id is not None else ""

        # IVA del item
        porcentaje_iva = Decimal("0.00")
        tax_subtotals = xpath(line_elem, ".//*[local-name()='TaxTotal']//*[local-name()='TaxSubtotal']")
        for ts in tax_subtotals:
            tax_id = text(first(ts, ".//*[local-name()='TaxCategory']//*[local-name()='TaxScheme']//*[local-name()='ID']")) or ""
            if tax_id == "01":  # IVA
                pct_str = text(first(ts, ".//*[local-name()='Percent']")) or "0"
                porcentaje_iva = _decimal_desde_xml(pct_str)
                break

        cantidad_dec = _decimal_desde_xml(cantidad_str, default="1")
        valor_unitario_dec = _decimal_desde_xml(valor_unitario_str, default="0")

        subtotal_item = cantidad_dec * valor_unitario_dec
        iva_item = subtotal_item * porcentaje_iva / Decimal("100")
        total_item = subtotal_item + iva_item

        items.append({
            "linea_id": sanitize_text(linea_id),
            "codigo": sanitize_text(codigo),
            "descripcion": sanitize_text(descripcion),
            "cantidad": cantidad_dec,
            "unidad_medida": sanitize_text(unidad_medida),
            "valor_unitario": valor_unitario_dec,
            "porcentaje_iva": porcentaje_iva,
            "subtotal": subtotal_item,
            "total": total_item,
        })

    dto = {
        "document_type": "invoice.ubl21",
        "type": "invoice",  # Tipo base para router de validaciones
        "numero": numero,
        "prefijo": prefijo,
        "consecutivo": consecutivo,
        "identificadores": {
            "cufe": cufe,
            "numero": numero,
        },
        "fecha_emision": fecha_emision,
        "emisor": {
            "nit": emisor_nit,
            "razon_social": emisor_razon_social,
            "direccion": emisor_direccion,
            "email": emisor_email,
            "telefono": emisor_telefono,
            "actividad_ciiu": emisor_actividad_ciiu,
        },
        "receptor": {
            "nit": receptor_nit,
            "razon_social": receptor_razon_social,
            "direccion": receptor_direccion,
            "email": receptor_email,
            "telefono": receptor_telefono,
        },
        "totales": {
            "moneda": moneda,
            "subtotal": subtotal_str,
            "impuestos": impuestos_str,
            "total": total_str,
            **_extract_retentions(invoice_root)
        },
        "items": items,
        # Metadatos UBL
        "ubl_version": ubl_version,
        "customization_id": customization_id,
        "profile_id": profile_id,
        "profile_execution_id": profile_execution_id,
        "invoice_type_code": invoice_type_code,
        # Autorización DIAN
        "autorizacion": {
            "numero": autorizacion_numero,
            "prefijo": autorizacion_prefijo,
            "rango_desde": autorizacion_rango_desde,
            "rango_hasta": autorizacion_rango_hasta,
            "vigencia_inicio": autorizacion_vigencia_inicio,
            "vigencia_fin": autorizacion_vigencia_fin,
        },
        # QR Code
        "qr_code": qr_code,
        "qr_url": qr_url,
    }
    
    return dto


def _parse_credit_note_ubl21(credit_note_root: etree._Element) -> dict[str, Any]:
    """
    Parsea CreditNote UBL 2.1 a DTO.
    
    Args:
        credit_note_root: Element raíz de CreditNote
        
    Returns:
        Dict con DTO JSON unificado
    """
    # Número
    numero = text(first(credit_note_root, ".//*[local-name()='ID']"))
    if not numero:
        raise ValueError("Falta campo obligatorio: ID (número de nota crédito)")
    numero = sanitize_text(numero)
    
    # CUDE/UUID
    cude = text(first(credit_note_root, ".//*[local-name()='UUID']")) or ""
    cude = sanitize_text(cude)
    
    # Fecha de emisión
    issue_date = text(first(credit_note_root, ".//*[local-name()='IssueDate']")) or ""
    issue_time = text(first(credit_note_root, ".//*[local-name()='IssueTime']")) or ""
    
    fecha_emision = issue_date
    if issue_time:
        fecha_emision = f"{issue_date}T{issue_time}"
    # WARNING: v2.61.3: Solo agregar timezone si no hay uno ya presente en la cadena
    # El issue_time puede incluir offset como "16:59:00-05:00" → ya tiene zona horaria
    if fecha_emision and "T" in fecha_emision:
        time_part = fecha_emision.split("T", 1)[1]
        has_tz = bool(re.search(r'[+-]\d{2}:\d{2}$', time_part)) or time_part.endswith('Z')
        if not has_tz:
            fecha_emision = f"{fecha_emision}-05:00"
    
    # Emisor
    supplier_party = first(credit_note_root, ".//*[local-name()='AccountingSupplierParty']//*[local-name()='Party']")
    emisor_nit = ""
    emisor_razon_social = ""
    emisor_direccion = ""
    emisor_email = ""
    emisor_telefono = ""
    
    if supplier_party is not None:
        tax_scheme = first(supplier_party, ".//*[local-name()='PartyTaxScheme']")
        if tax_scheme is not None:
            emisor_nit = text(first(tax_scheme, ".//*[local-name()='CompanyID']")) or ""
            # WARNING: FALLBACK: Algunos XMLs tienen RegistrationName directamente en PartyTaxScheme
            # (ej: <cac:PartyTaxScheme><cbc:RegistrationName>...</cbc:RegistrationName>)
            if not emisor_razon_social:
                emisor_razon_social = text(first(tax_scheme, ".//*[local-name()='RegistrationName']")) or ""
        legal_entity = first(supplier_party, ".//*[local-name()='PartyLegalEntity']")
        if legal_entity is not None:
            razon_social_legal = text(first(legal_entity, ".//*[local-name()='RegistrationName']")) or ""
            if razon_social_legal:
                emisor_razon_social = razon_social_legal
        
        # Dirección del emisor
        physical_location = first(supplier_party, ".//*[local-name()='PhysicalLocation']")
        if physical_location is not None:
            address = first(physical_location, ".//*[local-name()='Address']")
            if address is not None:
                address_lines = xpath(address, ".//*[local-name()='AddressLine']//*[local-name()='Line']")
                if address_lines:
                    emisor_direccion = sanitize_text(" ".join([text(line) for line in address_lines if text(line)]))
        
        # Contacto (email, teléfono)
        contact = first(supplier_party, ".//*[local-name()='Contact']")
        if contact is not None:
            emisor_email = text(first(contact, ".//*[local-name()='ElectronicMail']")) or ""
            emisor_telefono = text(first(contact, ".//*[local-name()='Telephone']")) or ""
    
    emisor_nit = normalize_nit(emisor_nit) or ""
    emisor_razon_social = sanitize_text(emisor_razon_social)
    emisor_direccion = sanitize_text(emisor_direccion)
    emisor_email = sanitize_text(emisor_email)
    emisor_telefono = sanitize_text(emisor_telefono)
    
    # Receptor
    customer_party = first(credit_note_root, ".//*[local-name()='AccountingCustomerParty']//*[local-name()='Party']")
    receptor_nit = ""
    receptor_razon_social = ""
    receptor_direccion = ""
    receptor_email = ""
    receptor_telefono = ""
    
    if customer_party is not None:
        tax_scheme = first(customer_party, ".//*[local-name()='PartyTaxScheme']")
        if tax_scheme is not None:
            receptor_nit = text(first(tax_scheme, ".//*[local-name()='CompanyID']")) or ""
            # WARNING: FALLBACK: Algunos XMLs tienen RegistrationName directamente en PartyTaxScheme
            # (ej: <cac:PartyTaxScheme><cbc:RegistrationName>...</cbc:RegistrationName>)
            if not receptor_razon_social:
                receptor_razon_social = text(first(tax_scheme, ".//*[local-name()='RegistrationName']")) or ""
        legal_entity = first(customer_party, ".//*[local-name()='PartyLegalEntity']")
        if legal_entity is not None:
            razon_social_legal = text(first(legal_entity, ".//*[local-name()='RegistrationName']")) or ""
            if razon_social_legal:
                receptor_razon_social = razon_social_legal
        
        # Dirección del receptor
        physical_location = first(customer_party, ".//*[local-name()='PhysicalLocation']")
        if physical_location is not None:
            address = first(physical_location, ".//*[local-name()='Address']")
            if address is not None:
                address_lines = xpath(address, ".//*[local-name()='AddressLine']//*[local-name()='Line']")
                if address_lines:
                    receptor_direccion = sanitize_text(" ".join([text(line) for line in address_lines if text(line)]))
        
        # Contacto (email, teléfono)
        contact = first(customer_party, ".//*[local-name()='Contact']")
        if contact is not None:
            receptor_email = text(first(contact, ".//*[local-name()='ElectronicMail']")) or ""
            receptor_telefono = text(first(contact, ".//*[local-name()='Telephone']")) or ""
    
    receptor_nit = normalize_nit(receptor_nit) or ""
    receptor_razon_social = sanitize_text(receptor_razon_social)
    receptor_direccion = sanitize_text(receptor_direccion)
    receptor_email = sanitize_text(receptor_email)
    receptor_telefono = sanitize_text(receptor_telefono)
    
    # Motivo completo (Note)
    motivo_completo = text(first(credit_note_root, ".//*[local-name()='Note']")) or ""
    motivo_completo = sanitize_text(motivo_completo)
    
    # Totales
    monetary_total = first(credit_note_root, ".//*[local-name()='LegalMonetaryTotal']")
    subtotal_str = "0.00"
    impuestos_str = "0.00"
    total_str = "0.00"
    moneda = "COP"
    
    if monetary_total is not None:
        line_extension_amount = text(first(monetary_total, ".//*[local-name()='LineExtensionAmount']")) or "0.00"
        tax_inclusive_amount = text(first(monetary_total, ".//*[local-name()='TaxInclusiveAmount']")) or "0.00"
        payable_amount = text(first(monetary_total, ".//*[local-name()='PayableAmount']")) or "0.00"
        currency_id = attr(first(monetary_total, ".//*[local-name()='LineExtensionAmount']"), "currencyID") or "COP"
        
        # Normalizar valores (parseo directo -- ver _decimal_desde_xml())
        subtotal_decimal = _decimal_desde_xml(line_extension_amount)
        tax_inclusive_decimal = _decimal_desde_xml(tax_inclusive_amount)
        payable_decimal = _decimal_desde_xml(payable_amount)

        # Calcular impuestos: TaxInclusiveAmount - LineExtensionAmount
        # Esto es más preciso que PayableAmount - LineExtensionAmount porque
        # PayableAmount puede incluir descuentos/cargos adicionales
        impuestos_decimal = tax_inclusive_decimal - subtotal_decimal
        if impuestos_decimal < Decimal("0.00"):
            impuestos_decimal = Decimal("0.00")

        # Usar PayableAmount como total (puede incluir descuentos/cargos)
        # Si PayableAmount no está disponible, usar TaxInclusiveAmount
        if payable_decimal > Decimal("0.00"):
            total_decimal = payable_decimal
        else:
            total_decimal = tax_inclusive_decimal

        # Convertir a strings normalizados
        subtotal_str = f"{subtotal_decimal:.2f}"
        impuestos_str = f"{impuestos_decimal:.2f}"
        total_str = f"{total_decimal:.2f}"
        moneda = normalize_currency(currency_id)

    # Retenciones
    retenciones = _extract_retentions(credit_note_root)

    # --- Items (CreditNoteLine) ---
    items = []
    credit_note_lines = xpath(credit_note_root, ".//*[local-name()='CreditNoteLine']")
    for line_elem in credit_note_lines:
        linea_id = text(first(line_elem, ".//*[local-name()='ID']")) or ""
        descripcion = text(first(line_elem, ".//*[local-name()='Description']")) or ""
        cantidad_str = text(first(line_elem, ".//*[local-name()='CreditedQuantity']")) or "1"
        qty_elem = first(line_elem, ".//*[local-name()='CreditedQuantity']")
        unidad_medida = attr(qty_elem, "unitCode") or "UND" if qty_elem is not None else "UND"

        valor_unitario_str = text(first(line_elem, ".//*[local-name()='Price']//*[local-name()='PriceAmount']")) or "0"
        sellers_id = first(line_elem, ".//*[local-name()='SellersItemIdentification']//*[local-name()='ID']")
        codigo = text(sellers_id) or "" if sellers_id is not None else ""

        # IVA del item
        porcentaje_iva = Decimal("0.00")
        tax_subtotals = xpath(line_elem, ".//*[local-name()='TaxTotal']//*[local-name()='TaxSubtotal']")
        for ts in tax_subtotals:
            tax_id = text(first(ts, ".//*[local-name()='TaxCategory']//*[local-name()='TaxScheme']//*[local-name()='ID']")) or ""
            if tax_id == "01":  # IVA
                pct_str = text(first(ts, ".//*[local-name()='Percent']")) or "0"
                porcentaje_iva = _decimal_desde_xml(pct_str)
                break

        cantidad_dec = _decimal_desde_xml(cantidad_str, default="1")
        valor_unitario_dec = _decimal_desde_xml(valor_unitario_str, default="0")

        subtotal_item = cantidad_dec * valor_unitario_dec
        iva_item = subtotal_item * porcentaje_iva / Decimal("100")
        total_item = subtotal_item + iva_item

        items.append({
            "linea_id": sanitize_text(linea_id),
            "codigo": sanitize_text(codigo),
            "descripcion": sanitize_text(descripcion),
            "cantidad": cantidad_dec,
            "unidad_medida": sanitize_text(unidad_medida),
            "valor_unitario": valor_unitario_dec,
            "porcentaje_iva": porcentaje_iva,
            "subtotal": subtotal_item,
            "total": total_item,
        })

    # Referencia a factura
    ref_factura_numero = ""
    ref_factura_cufe = ""
    motivo_discrepancy = ""
    
    # Buscar DiscrepancyResponse (referencia a factura - método alternativo)
    discrepancy = first(credit_note_root, ".//*[local-name()='DiscrepancyResponse']")
    if discrepancy is not None:
        ref_factura_numero = text(first(discrepancy, ".//*[local-name()='ReferenceID']")) or ""
        motivo_discrepancy = text(first(discrepancy, ".//*[local-name()='Description']")) or ""
    
    # Buscar InvoiceDocumentReference dentro de BillingReference (método principal UBL 2.1)
    # WARNING: PATRÓN: <cac:BillingReference><cac:InvoiceDocumentReference><cbc:ID>...</cbc:ID></cac:InvoiceDocumentReference></cac:BillingReference>
    # Usar xpath() directamente para mayor robustez
    try:
        billing_refs = xpath(credit_note_root, ".//*[local-name()='BillingReference']")
        if billing_refs:
            billing_ref = billing_refs[0]
            invoice_refs = xpath(billing_ref, ".//*[local-name()='InvoiceDocumentReference']")
            if invoice_refs:
                invoice_ref = invoice_refs[0]
                # Buscar ID dentro de InvoiceDocumentReference (hijo directo primero)
                id_elems = xpath(invoice_ref, "*[local-name()='ID']")
                if not id_elems:
                    id_elems = xpath(invoice_ref, ".//*[local-name()='ID']")
                if id_elems:
                    ref_id = text(id_elems[0])
                    if ref_id and ref_id.strip():
                        ref_factura_numero = ref_id.strip()
                # Buscar UUID dentro de InvoiceDocumentReference (hijo directo primero)
                uuid_elems = xpath(invoice_ref, "*[local-name()='UUID']")
                if not uuid_elems:
                    uuid_elems = xpath(invoice_ref, ".//*[local-name()='UUID']")
                if uuid_elems:
                    ref_uuid = text(uuid_elems[0])
                    if ref_uuid and ref_uuid.strip():
                        ref_factura_cufe = ref_uuid.strip()
    except Exception as e:
        import logging
        log_parser = logging.getLogger("document_parser.xml_parser")
        log_parser.warning(f"Error extrayendo referencia desde BillingReference: {e}")
    
    # Fallback: buscar InvoiceDocumentReference directamente (sin BillingReference)
    if not ref_factura_numero and not ref_factura_cufe:
        try:
            invoice_refs = xpath(credit_note_root, ".//*[local-name()='InvoiceDocumentReference']")
            if invoice_refs:
                invoice_ref = invoice_refs[0]
                # Buscar ID (hijo directo primero)
                id_elems = xpath(invoice_ref, "*[local-name()='ID']")
                if not id_elems:
                    id_elems = xpath(invoice_ref, ".//*[local-name()='ID']")
                if id_elems:
                    ref_id = text(id_elems[0])
                    if ref_id and ref_id.strip():
                        ref_factura_numero = ref_id.strip()
                # Buscar UUID (hijo directo primero)
                uuid_elems = xpath(invoice_ref, "*[local-name()='UUID']")
                if not uuid_elems:
                    uuid_elems = xpath(invoice_ref, ".//*[local-name()='UUID']")
                if uuid_elems:
                    ref_uuid = text(uuid_elems[0])
                    if ref_uuid and ref_uuid.strip():
                        ref_factura_cufe = ref_uuid.strip()
        except Exception as e:
            import logging
            log_parser = logging.getLogger("document_parser.xml_parser")
            log_parser.warning(f"Error extrayendo referencia desde InvoiceDocumentReference directo: {e}")
    
    ref_factura_numero = sanitize_text(ref_factura_numero) if ref_factura_numero else ""
    ref_factura_cufe = sanitize_text(ref_factura_cufe) if ref_factura_cufe else ""
    motivo_discrepancy = sanitize_text(motivo_discrepancy) if motivo_discrepancy else ""
    
    # WARNING: DEBUG: Log para diagnóstico de extracción de referencia
    import logging
    log_parser = logging.getLogger("document_parser.xml_parser")
    if ref_factura_numero or ref_factura_cufe:
        log_parser.debug(f"Referencia extraída de CreditNote: numero='{ref_factura_numero}', cufe='{ref_factura_cufe}'")
    else:
        log_parser.warning("No se pudo extraer referencia a factura desde CreditNote XML")
        # WARNING: DEBUG: Intentar extraer manualmente para diagnóstico
        try:
            billing_refs_debug = xpath(credit_note_root, ".//*[local-name()='BillingReference']")
            log_parser.debug(f"BillingReference encontrados: {len(billing_refs_debug)}")
            if billing_refs_debug:
                invoice_refs_debug = xpath(billing_refs_debug[0], ".//*[local-name()='InvoiceDocumentReference']")
                log_parser.debug(f"InvoiceDocumentReference encontrados: {len(invoice_refs_debug)}")
                if invoice_refs_debug:
                    id_elems_debug = xpath(invoice_refs_debug[0], ".//*[local-name()='ID']")
                    uuid_elems_debug = xpath(invoice_refs_debug[0], ".//*[local-name()='UUID']")
                    log_parser.debug(f"ID elements: {len(id_elems_debug)}, UUID elements: {len(uuid_elems_debug)}")
        except Exception as e:
            log_parser.debug(f"Error en diagnóstico: {e}")
    
    # Usar motivo completo (Note) si está disponible, sino usar motivo de DiscrepancyResponse
    motivo_final = motivo_completo if motivo_completo else motivo_discrepancy
    
    # Construir DTO (FASE 3: incluir type base para compatibilidad)
    dto = {
        "document_type": "creditnote.ubl21",
        "type": "creditnote",  # Tipo base para router de validaciones
        "numero": numero,
        "identificadores": {
            "cude": cude,
            "cufe": cude,  # Alias para compatibilidad
            "numero": numero,
        },
        "fecha_emision": fecha_emision,
        "emisor": {
            "nit": emisor_nit,
            "razon_social": emisor_razon_social,
            "direccion": emisor_direccion,
            "email": emisor_email,
            "telefono": emisor_telefono,
        },
        "receptor": {
            "nit": receptor_nit,
            "razon_social": receptor_razon_social,
            "direccion": receptor_direccion,
            "email": receptor_email,
            "telefono": receptor_telefono,
        },
        "totales": {
            "moneda": moneda,
            "subtotal": subtotal_str,
            "impuestos": impuestos_str,
            "total": total_str,
            **retenciones
        },
        "items": items,
        "referencia": {
            "numero": ref_factura_numero,
            "cufe": ref_factura_cufe,
            "tipo": "invoice",
        },
        "motivo": motivo_final,
    }
    
    return dto
