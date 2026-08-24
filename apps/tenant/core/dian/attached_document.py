"""
Contenedor AttachedDocument DIAN para transmision de documentos electronicos.

Ref: Anexo Tecnico FE DIAN v1.9 seccion 6 (Envio documentos). La misma
estructura de AttachedDocument (SenderParty/ReceiverParty/Attachment) es el
contenedor generico que usa la DIAN para envolver cualquier documento
electronico firmado (Invoice, NominaIndividual, CreditNote, etc.) -- solo
cambia el `document_type` declarado.

El AttachedDocument envuelve el documento XML firmado en CDATA dentro
de Attachment/ExternalReference/Description, junto con los metadatos
del emisor/receptor necesarios para que la DIAN lo enrute.

Namespaces:
  xmlns  = urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2
  cac    = urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2
  cbc    = urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2
  ext    = urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2

# WARNING: NOMINA-03: movido desde apps.tenant.facturas.services.dian a este
# paquete neutral (apps.tenant.core.dian). Unico cambio de comportamiento:
# `document_type` ahora es parametrizable (antes hardcodeado a "Invoice") --
# default "Invoice" preserva el comportamiento exacto para facturas/ventas.
# Ver docs/nomina/NOMINA_DIAN_AUDIT.md §3.
"""
import base64
import hashlib
import uuid as _uuid
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
_NS = {
    "AD": "urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


class AttachedDocumentService:
    """
    Genera el contenedor AttachedDocument que la DIAN exige recibir.

    Uso:
        ad_bytes = AttachedDocumentService.build(signed_invoice_bytes, dto, cufe)
        ad_bytes = AttachedDocumentService.build(signed_xml_bytes, dto, cune, document_type="NominaIndividual")
    """

    @classmethod
    def build(cls, signed_invoice_bytes: bytes, dto: dict, cufe: str, document_type: str = "Invoice") -> bytes:
        """
        Envuelve el XML firmado en un AttachedDocument DIAN.
        Retorna los bytes UTF-8 del XML AttachedDocument.

        document_type -- tipo de documento declarado en <cbc:DocumentType>.
                          "Invoice" (default, factura electronica) o
                          "NominaIndividual" (nomina electronica), etc.
        """
        ad_uuid = str(_uuid.uuid4())
        ahora = datetime.now(timezone.utc)
        issue_date = ahora.strftime("%Y-%m-%d")
        issue_time = ahora.strftime("%H:%M:%S") + "-05:00"

        emisor = dto.get("emisor", {})
        receptor = dto.get("receptor", {})

        invoice_b64 = base64.b64encode(signed_invoice_bytes).decode("ascii")
        invoice_sha256 = hashlib.sha256(signed_invoice_bytes).hexdigest()

        # Numero del AttachedDocument == numero del documento origen
        num_fac = dto.get("num_fac", ad_uuid)

        # sts namespace no esta en AttachedDocument; usamos cbc/cac directos
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<AttachedDocument',
            f'  xmlns="{_NS["AD"]}"',
            f'  xmlns:cac="{_NS["cac"]}"',
            f'  xmlns:cbc="{_NS["cbc"]}"',
            f'  xmlns:ext="{_NS["ext"]}"',
            f'  xmlns:xsi="{_NS["xsi"]}">',

            # Extensiones vacias (requeridas por schema)
            "  <ext:UBLExtensions>",
            "    <ext:UBLExtension>",
            "      <ext:ExtensionContent/>",
            "    </ext:UBLExtension>",
            "  </ext:UBLExtensions>",

            # Metadatos
            "  <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>",
            "  <cbc:CustomizationID>1</cbc:CustomizationID>",
            f"  <cbc:ID>{num_fac}</cbc:ID>",
            f"  <cbc:UUID schemeName=\"CUFE-SHA384\">{cufe}</cbc:UUID>",
            f"  <cbc:IssueDate>{issue_date}</cbc:IssueDate>",
            f"  <cbc:IssueTime>{issue_time}</cbc:IssueTime>",

            # Descripcion del documento adjunto
            f"  <cbc:DocumentType>{document_type}</cbc:DocumentType>",

            # Sender (emisor)
            "  <cac:SenderParty>",
            "    <cac:PartyTaxScheme>",
            f"      <cbc:CompanyID schemeName=\"31\" schemeID=\"{emisor.get('dv','0')}\"",
            f"        schemeAgencyName=\"CO, DIAN\" schemeAgencyID=\"195\">",
            f"        {emisor.get('nit','')}",
            "      </cbc:CompanyID>",
            "      <cac:TaxScheme>",
            f"        <cbc:ID>01</cbc:ID>",
            f"        <cbc:Name>IVA</cbc:Name>",
            "      </cac:TaxScheme>",
            "    </cac:PartyTaxScheme>",
            "  </cac:SenderParty>",

            # Receiver (receptor)
            "  <cac:ReceiverParty>",
            "    <cac:PartyTaxScheme>",
            f"      <cbc:CompanyID schemeName=\"{receptor.get('tipo_documento','31')}\" schemeID=\"0\"",
            f"        schemeAgencyName=\"CO, DIAN\" schemeAgencyID=\"195\">",
            f"        {receptor.get('nit','')}",
            "      </cbc:CompanyID>",
            "      <cac:TaxScheme>",
            f"        <cbc:ID>ZZ</cbc:ID>",
            f"        <cbc:Name>No aplica</cbc:Name>",
            "      </cac:TaxScheme>",
            "    </cac:PartyTaxScheme>",
            "  </cac:ReceiverParty>",

            # Attachment: documento XML en base64 (se puede enviar en CDATA o b64)
            "  <cac:Attachment>",
            "    <cac:ExternalReference>",
            f"      <cbc:URI>#invoice-{num_fac}</cbc:URI>",
            f"      <cbc:DocumentHash>{invoice_sha256}</cbc:DocumentHash>",
            f"      <cbc:HashAlgorithmMethod>SHA-256</cbc:HashAlgorithmMethod>",
            f"      <cbc:Description><![CDATA[{signed_invoice_bytes.decode('utf-8')}]]></cbc:Description>",
            "    </cac:ExternalReference>",
            "  </cac:Attachment>",

            "</AttachedDocument>",
        ]

        return "\n".join(lines).encode("utf-8")

    @classmethod
    def build_application_response(cls, dto: dict, cufe: str, validation_code: str = "02") -> bytes:
        """
        Genera un ApplicationResponse minimo con el codigo de validacion.

        validation_code:
          "02" -- Documento procesado correctamente
          "04" -- Rechazado

        Normalmente la DIAN retorna este XML, pero se pre-genera para
        almacenarlo junto con el documento en el campo dian_response_xml.
        """
        ahora = datetime.now(timezone.utc)
        issue_date = ahora.strftime("%Y-%m-%d")
        issue_time = ahora.strftime("%H:%M:%S") + "-05:00"
        num_fac = dto.get("num_fac", "")
        emisor = dto.get("emisor", {})

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<ApplicationResponse',
            '  xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"',
            f'  xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"',
            f'  xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">',
            "  <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>",
            "  <cbc:CustomizationID>1</cbc:CustomizationID>",
            f"  <cbc:ID>{num_fac}</cbc:ID>",
            f"  <cbc:IssueDate>{issue_date}</cbc:IssueDate>",
            f"  <cbc:IssueTime>{issue_time}</cbc:IssueTime>",
            "  <cac:SenderParty>",
            "    <cac:PartyTaxScheme>",
            f"      <cbc:CompanyID schemeName=\"31\">800197268</cbc:CompanyID>",
            "      <cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme>",
            "    </cac:PartyTaxScheme>",
            "  </cac:SenderParty>",
            "  <cac:ReceiverParty>",
            "    <cac:PartyTaxScheme>",
            f"      <cbc:CompanyID schemeName=\"31\">{emisor.get('nit','')}</cbc:CompanyID>",
            "      <cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme>",
            "    </cac:PartyTaxScheme>",
            "  </cac:ReceiverParty>",
            "  <cac:DocumentResponse>",
            "    <cac:Response>",
            f"      <cbc:ResponseCode>{validation_code}</cbc:ResponseCode>",
            f"      <cbc:Description>Documento procesado correctamente</cbc:Description>",
            "    </cac:Response>",
            "    <cac:DocumentReference>",
            f"      <cbc:ID>{num_fac}</cbc:ID>",
            f"      <cbc:UUID schemeName=\"CUFE-SHA384\">{cufe}</cbc:UUID>",
            "    </cac:DocumentReference>",
            "  </cac:DocumentResponse>",
            "</ApplicationResponse>",
        ]

        return "\n".join(lines).encode("utf-8")
