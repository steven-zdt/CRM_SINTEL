"""
Generador XML UBL 2.1 para Factura Electronica DIAN (Colombia).

Produce un documento Invoice compliant con:
  - Anexo Tecnico FE DIAN v1.9
  - Resolucion 000042 de 2020
  - Estandar UBL 2.1 OASIS

Namespaces usados:
  xmlns     = urn:oasis:names:specification:ubl:schema:xsd:Invoice-2
  cac       = urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2
  cbc       = urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2
  ext       = urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2
  sts       = dian:gov:co:facturaelectronica:Structures-2-1
  ds        = http://www.w3.org/2000/09/xmldsig#
  xades     = http://uri.etsi.org/01903/v1.3.2#
"""
import uuid as _uuid
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
NS = {
    "invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sts": "dian:gov:co:facturaelectronica:Structures-2-1",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# Prefijos registrados para serializar correctamente
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)


def _tag(ns_key: str, local: str) -> str:
    return "{%s}%s" % (NS[ns_key], local)


def _sub(parent, ns_key: str, local: str, text: str = None, attribs: dict = None):
    el = ET.SubElement(parent, _tag(ns_key, local), attrib=attribs or {})
    if text is not None:
        el.text = str(text)
    return el


def _fmt2(val) -> str:
    return str(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Servicio principal
# ---------------------------------------------------------------------------

class UBL21BuilderService:
    """
    Construye el XML Invoice UBL 2.1 DIAN a partir del DTO canonico.

    Uso:
        xml_bytes = UBL21BuilderService.build(dto, cufe, qr_string)
        # Retorna bytes UTF-8 del documento XML sin firmar.
    """

    @classmethod
    def build(cls, dto: dict, cufe: str, qr_string: str) -> bytes:
        """
        Genera el XML de la factura. No incluye firma ds:Signature
        (esa la agrega XadesSignerService a continuacion).
        """
        root = cls._build_invoice(dto, cufe, qr_string)
        ET.indent(root, space="  ")
        return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode").encode("utf-8")

    # ------------------------------------------------------------------
    # Invoice root
    # ------------------------------------------------------------------

    @classmethod
    def _build_invoice(cls, dto: dict, cufe: str, qr_string: str) -> ET.Element:
        root = ET.Element(_tag("invoice", "Invoice"), attrib={
            "xmlns": NS["invoice"],
            _tag("xsi", "schemaLocation"): (
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2 "
                "http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd"
            ),
        })
        for prefix in ("ext", "sts", "cac", "cbc", "ds", "xades", "xsi"):
            root.set("xmlns:" + prefix, NS[prefix])

        # Placeholder para el bloque de extensiones (firma se inserta aqui)
        cls._build_extensions(root, dto, cufe, qr_string)

        # Metadatos del documento
        _sub(root, "cbc", "UBLVersionID", "UBL 2.1")
        _sub(root, "cbc", "CustomizationID", dto.get("customization_id", "10"))
        _sub(root, "cbc", "ProfileID", dto.get("profile_id", "DIAN 2.1"))
        _sub(root, "cbc", "ProfileExecutionID", dto.get("tip_amb", "2"))
        _sub(root, "cbc", "ID", dto["num_fac"])
        _sub(root, "cbc", "UUID", cufe, {
            "schemeID": dto.get("tip_amb", "2"),
            "schemeName": "CUFE-SHA384",
        })
        _sub(root, "cbc", "IssueDate", dto["fec_fac"])
        _sub(root, "cbc", "IssueTime", dto["hor_fac"])
        _sub(root, "cbc", "InvoiceTypeCode", dto.get("invoice_type_code", "01"), {
            "listAgencyID": "195",
            "listAgencyName": "CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)",
            "listID": "UN/ECE 1001 Subset",
            "listName": "Tipo de Comprobante",
            "listSchemeURI": "http://www.dian.gov.co/contratos/facturaelectronica/v1/InvoiceType",
            "listURI": "http://www.dian.gov.co/contratos/facturaelectronica/v1/InvoiceType",
            "listVersionID": "1.0",
            "name": "Tipo de Comprobante",
        })

        # Nota / observacion
        if dto.get("observaciones"):
            _sub(root, "cbc", "Note", dto["observaciones"])

        _sub(root, "cbc", "DocumentCurrencyCode", dto.get("moneda", "COP"))
        _sub(root, "cbc", "LineCountNumeric", str(len(dto.get("lineas", []))))

        # OrderReference (opcional, DIAN lo pide como placeholder)
        order_ref = _sub(root, "cac", "OrderReference")
        _sub(order_ref, "cbc", "ID", dto["num_fac"])

        # Partes del documento
        cls._build_supplier_party(root, dto["emisor"])
        cls._build_customer_party(root, dto["receptor"])

        # Medio de pago
        cls._build_payment_means(root, dto.get("medio_pago", {}), dto["fec_fac"])

        # Impuestos totales
        cls._build_tax_totals(root, dto.get("impuestos_discriminados", []))

        # LegalMonetaryTotal
        cls._build_legal_monetary_total(root, dto["totales"])

        # Lineas
        for linea in dto.get("lineas", []):
            cls._build_invoice_line(root, linea)

        return root

    # ------------------------------------------------------------------
    # sts:DianExtensions
    # ------------------------------------------------------------------

    @classmethod
    def _build_extensions(cls, root: ET.Element, dto: dict, cufe: str, qr_string: str):
        ext_content = _sub(root, "ext", "UBLExtensions")
        ext1 = _sub(ext_content, "ext", "UBLExtension")
        ext_uri = _sub(ext1, "ext", "ExtensionURI")
        ext_uri.text = "urn:oasis:names:specification:ubl:dsig:ext:XADES"
        content = _sub(ext1, "ext", "ExtensionContent")

        # sts:DianExtensions
        dian_ext = _sub(content, "sts", "DianExtensions")

        # InvoiceControl
        inv_ctrl = _sub(dian_ext, "sts", "InvoiceControl")
        dian_sw = dto.get("dian_software", {})
        resol = dto.get("resolucion", {})
        _sub(inv_ctrl, "sts", "InvoiceAuthorization", resol.get("numero_autorizacion", "0"))
        auth_period = _sub(inv_ctrl, "sts", "AuthorizationPeriod")
        _sub(auth_period, "cbc", "StartDate", resol.get("fecha_inicio", dto["fec_fac"]))
        _sub(auth_period, "cbc", "EndDate", resol.get("fecha_fin", dto["fec_fac"]))
        auth_range = _sub(inv_ctrl, "sts", "AuthorizedInvoices")
        _sub(auth_range, "sts", "Prefix", resol.get("prefijo", ""))
        _sub(auth_range, "sts", "From", resol.get("desde", "1"))
        _sub(auth_range, "sts", "To", resol.get("hasta", "1"))

        # InvoiceSource
        inv_source = _sub(dian_ext, "sts", "InvoiceSource")
        _sub(inv_source, "cbc", "IdentificationCode",
             "CO", {"listAgencyID": "6", "listAgencyName": "United Nations Economic and Social Council",
                    "listSchemeURI": "urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1"})

        # SoftwareProvider
        sw_prov = _sub(dian_ext, "sts", "SoftwareProvider")
        _sub(sw_prov, "sts", "ProviderID",
             dian_sw.get("provider_id", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN",
              "schemeID": "4", "schemeName": "31"})
        _sub(sw_prov, "sts", "SoftwareID",
             dian_sw.get("software_id", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN"})

        # SoftwareSecurityCode
        _sub(dian_ext, "sts", "SoftwareSecurityCode",
             dian_sw.get("software_security_code", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN"})

        # AuthorizationProvider (DIAN)
        auth_prov = _sub(dian_ext, "sts", "AuthorizationProvider")
        _sub(auth_prov, "sts", "AuthorizationProviderID",
             dian_sw.get("authorization_id", "800197268"),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN",
              "schemeID": "4", "schemeName": "31"})

        # QRCode
        _sub(dian_ext, "sts", "QRCode", qr_string)

        # Placeholder para ds:Signature (XadesSignerService lo reemplaza)
        _sub(ext_content, "ext", "UBLExtension")

    # ------------------------------------------------------------------
    # AccountingSupplierParty (emisor)
    # ------------------------------------------------------------------

    @classmethod
    def _build_supplier_party(cls, root: ET.Element, emisor: dict):
        supplier = _sub(root, "cac", "AccountingSupplierParty")
        _sub(supplier, "cbc", "AdditionalAccountID",
             emisor.get("additional_account_id", "1"))
        party = _sub(supplier, "cac", "Party")

        # Nombre comercial
        party_name = _sub(party, "cac", "PartyName")
        _sub(party_name, "cbc", "Name", emisor.get("razon_social", ""))

        # Datos fiscales
        phys_loc = _sub(party, "cac", "PhysicalLocation")
        addr = _sub(phys_loc, "cac", "Address")
        _sub(addr, "cbc", "CityName", emisor.get("ciudad", ""))
        _sub(addr, "cbc", "CountrySubentity", emisor.get("departamento", ""))
        addr_line = _sub(addr, "cac", "AddressLine")
        _sub(addr_line, "cbc", "Line", emisor.get("direccion", ""))
        country = _sub(addr, "cac", "Country")
        _sub(country, "cbc", "IdentificationCode",
             "CO", {"listAgencyID": "6", "listAgencyName": "United Nations Economic and Social Council",
                    "listSchemeURI": "urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1"})

        # Identificacion fiscal del emisor
        tax_scheme_info = _sub(party, "cac", "PartyTaxScheme")
        _sub(tax_scheme_info, "cbc", "RegistrationName", emisor.get("razon_social", ""))
        _sub(tax_scheme_info, "cbc", "CompanyID",
             emisor.get("nit", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN",
              "schemeID": emisor.get("dv", "0"), "schemeName": "31"})
        _sub(tax_scheme_info, "cbc", "TaxLevelCode",
             emisor.get("tax_level_code", "O-13"),
             {"listName": emisor.get("tax_level_list_name", "48")})
        ts = _sub(tax_scheme_info, "cac", "TaxScheme")
        _sub(ts, "cbc", "ID", emisor.get("tax_scheme_id", "01"))
        _sub(ts, "cbc", "Name", emisor.get("tax_scheme_name", "IVA"))

        # Razon social legal
        party_legal = _sub(party, "cac", "PartyLegalEntity")
        _sub(party_legal, "cbc", "RegistrationName", emisor.get("razon_social", ""))
        _sub(party_legal, "cbc", "CompanyID",
             emisor.get("nit", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN",
              "schemeID": emisor.get("dv", "0"), "schemeName": "31"})

        # Contacto
        contact = _sub(party, "cac", "Contact")
        _sub(contact, "cbc", "ElectronicMail", emisor.get("email", ""))
        _sub(contact, "cbc", "Telephone", emisor.get("telefono", ""))

    # ------------------------------------------------------------------
    # AccountingCustomerParty (receptor / cliente)
    # ------------------------------------------------------------------

    @classmethod
    def _build_customer_party(cls, root: ET.Element, receptor: dict):
        customer = _sub(root, "cac", "AccountingCustomerParty")
        _sub(customer, "cbc", "AdditionalAccountID",
             receptor.get("additional_account_id", "1"))
        party = _sub(customer, "cac", "Party")

        party_name = _sub(party, "cac", "PartyName")
        _sub(party_name, "cbc", "Name", receptor.get("razon_social", ""))

        phys_loc = _sub(party, "cac", "PhysicalLocation")
        addr = _sub(phys_loc, "cac", "Address")
        _sub(addr, "cbc", "CityName", receptor.get("ciudad", ""))
        addr_line = _sub(addr, "cac", "AddressLine")
        _sub(addr_line, "cbc", "Line", receptor.get("direccion", ""))
        country = _sub(addr, "cac", "Country")
        _sub(country, "cbc", "IdentificationCode",
             "CO", {"listAgencyID": "6", "listAgencyName": "United Nations Economic and Social Council",
                    "listSchemeURI": "urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1"})

        tipo_doc = receptor.get("tipo_documento", "31")
        tax_scheme_info = _sub(party, "cac", "PartyTaxScheme")
        _sub(tax_scheme_info, "cbc", "RegistrationName", receptor.get("razon_social", ""))
        _sub(tax_scheme_info, "cbc", "CompanyID",
             receptor.get("nit", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN",
              "schemeID": "0", "schemeName": tipo_doc})
        _sub(tax_scheme_info, "cbc", "TaxLevelCode",
             receptor.get("tax_level_code", "R-99-PN"),
             {"listName": receptor.get("tax_level_list_name", "49")})
        ts = _sub(tax_scheme_info, "cac", "TaxScheme")
        _sub(ts, "cbc", "ID", receptor.get("tax_scheme_id", "ZZ"))
        _sub(ts, "cbc", "Name", receptor.get("tax_scheme_name", "No aplica"))

        party_legal = _sub(party, "cac", "PartyLegalEntity")
        _sub(party_legal, "cbc", "RegistrationName", receptor.get("razon_social", ""))
        _sub(party_legal, "cbc", "CompanyID",
             receptor.get("nit", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN",
              "schemeID": "0", "schemeName": tipo_doc})

        contact = _sub(party, "cac", "Contact")
        _sub(contact, "cbc", "ElectronicMail", receptor.get("email", ""))
        _sub(contact, "cbc", "Telephone", receptor.get("telefono", ""))

    # ------------------------------------------------------------------
    # PaymentMeans
    # ------------------------------------------------------------------

    @classmethod
    def _build_payment_means(cls, root: ET.Element, medio_pago: dict, fecha_emision: str):
        pm = _sub(root, "cac", "PaymentMeans")
        _sub(pm, "cbc", "ID", "1")
        _sub(pm, "cbc", "PaymentMeansCode", medio_pago.get("codigo", "47"))
        _sub(pm, "cbc", "PaymentDueDate",
             medio_pago.get("fecha_vencimiento", fecha_emision))
        _sub(pm, "cbc", "PaymentID", medio_pago.get("instruccion", "Transferencia"))

    # ------------------------------------------------------------------
    # TaxTotal
    # ------------------------------------------------------------------

    @classmethod
    def _build_tax_totals(cls, root: ET.Element, impuestos: list):
        """
        Un cac:TaxTotal por tasa diferente.
        Estructura DIAN: TaxAmount > TaxSubtotal > TaxableAmount + TaxAmount + TaxCategory.
        """
        total_impuestos = sum(Decimal(str(i.get("valor", "0"))) for i in impuestos)
        tax_total = _sub(root, "cac", "TaxTotal")
        _sub(tax_total, "cbc", "TaxAmount", _fmt2(total_impuestos), {"currencyID": "COP"})

        for imp in impuestos:
            sub_t = _sub(tax_total, "cac", "TaxSubtotal")
            _sub(sub_t, "cbc", "TaxableAmount", _fmt2(imp.get("base", "0")), {"currencyID": "COP"})
            _sub(sub_t, "cbc", "TaxAmount", _fmt2(imp.get("valor", "0")), {"currencyID": "COP"})
            pct = Decimal(str(imp.get("porcentaje", "0")))
            _sub(sub_t, "cbc", "Percent", _fmt2(pct))
            cat = _sub(sub_t, "cac", "TaxCategory")
            ts = _sub(cat, "cac", "TaxScheme")
            _sub(ts, "cbc", "ID", imp.get("tax_scheme_id", "01"))
            _sub(ts, "cbc", "Name", imp.get("tax_scheme_name", "IVA"))

    # ------------------------------------------------------------------
    # LegalMonetaryTotal
    # ------------------------------------------------------------------

    @classmethod
    def _build_legal_monetary_total(cls, root: ET.Element, totales: dict):
        lmt = _sub(root, "cac", "LegalMonetaryTotal")
        _sub(lmt, "cbc", "LineExtensionAmount",
             _fmt2(totales.get("line_extension_amount", totales.get("subtotal", "0"))),
             {"currencyID": "COP"})
        _sub(lmt, "cbc", "TaxExclusiveAmount",
             _fmt2(totales.get("tax_exclusive_amount", totales.get("subtotal", "0"))),
             {"currencyID": "COP"})
        _sub(lmt, "cbc", "TaxInclusiveAmount",
             _fmt2(totales.get("tax_inclusive_amount", totales.get("total", "0"))),
             {"currencyID": "COP"})
        _sub(lmt, "cbc", "AllowanceTotalAmount",
             _fmt2(totales.get("allowance_total", "0.00")),
             {"currencyID": "COP"})
        _sub(lmt, "cbc", "ChargeTotalAmount",
             _fmt2(totales.get("charge_total", "0.00")),
             {"currencyID": "COP"})
        _sub(lmt, "cbc", "PayableAmount",
             _fmt2(totales.get("payable_amount", totales.get("total", "0"))),
             {"currencyID": "COP"})

    # ------------------------------------------------------------------
    # InvoiceLine
    # ------------------------------------------------------------------

    @classmethod
    def _build_invoice_line(cls, root: ET.Element, linea: dict):
        line = _sub(root, "cac", "InvoiceLine")
        _sub(line, "cbc", "ID", linea.get("id", "1"))
        _sub(line, "cbc", "InvoicedQuantity",
             linea.get("cantidad", "1"),
             {"unitCode": linea.get("unidad", "NAL")})
        _sub(line, "cbc", "LineExtensionAmount",
             _fmt2(linea.get("subtotal", "0")), {"currencyID": "COP"})

        # Referencia al pedido (requerida por DIAN aunque sea sin valor)
        doc_ref = _sub(line, "cac", "DocumentReference")
        _sub(doc_ref, "cbc", "ID", linea.get("id", "1"))

        # TaxTotal de la linea
        line_tax_total = _sub(line, "cac", "TaxTotal")
        _sub(line_tax_total, "cbc", "TaxAmount",
             _fmt2(linea.get("iva", "0")), {"currencyID": "COP"})
        sub_t = _sub(line_tax_total, "cac", "TaxSubtotal")
        _sub(sub_t, "cbc", "TaxableAmount",
             _fmt2(linea.get("subtotal", "0")), {"currencyID": "COP"})
        _sub(sub_t, "cbc", "TaxAmount",
             _fmt2(linea.get("iva", "0")), {"currencyID": "COP"})
        _sub(sub_t, "cbc", "Percent", linea.get("porcentaje_iva", "0"))
        cat = _sub(sub_t, "cac", "TaxCategory")
        ts = _sub(cat, "cac", "TaxScheme")
        _sub(ts, "cbc", "ID", linea.get("tax_scheme_id", "01"))
        _sub(ts, "cbc", "Name", linea.get("tax_scheme_name", "IVA"))

        # Item descriptor
        item = _sub(line, "cac", "Item")
        _sub(item, "cbc", "Description", linea.get("descripcion", ""))
        seller_id = _sub(item, "cac", "SellersItemIdentification")
        _sub(seller_id, "cbc", "ID", linea.get("seller_item_id", linea.get("id", "1")))
        std_id = _sub(item, "cac", "StandardItemIdentification")
        _sub(std_id, "cbc", "ID",
             linea.get("std_item_id", linea.get("id", "1")),
             {"schemeAgencyID": "10", "schemeID": "001"})

        # Precio unitario
        price = _sub(line, "cac", "Price")
        _sub(price, "cbc", "PriceAmount",
             _fmt2(linea.get("valor_unitario", "0")), {"currencyID": "COP"})
        _sub(price, "cbc", "BaseQuantity",
             "1", {"unitCode": linea.get("unidad", "NAL")})
