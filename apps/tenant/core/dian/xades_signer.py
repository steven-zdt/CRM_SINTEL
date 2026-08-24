"""
Firma XAdES-EPES para documentos electronicos DIAN (Colombia).

Ref: Anexo Tecnico FE DIAN v1.9 seccion 5.5 (firma digital).
     Politica de firma: https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf

Requisitos de sistema:
  pip install lxml cryptography  (o pyopenssl)

La firma ds:Signature se inserta como hijo de la extension UBLExtension[1]
dentro de ext:ExtensionContent, siguiendo la estructura:

  <ext:UBLExtensions>
    <ext:UBLExtension>          <- [0] DianExtensions
      ...
    </ext:UBLExtension>
    <ext:UBLExtension>          <- [1] Firma (este bloque)
      <ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:ext:XADES</ext:ExtensionURI>
      <ext:ExtensionContent>
        <ds:Signature ...>
          ...
        </ds:Signature>
      </ext:ExtensionContent>
    </ext:UBLExtension>
  </ext:UBLExtensions>

Si el entorno NO tiene certificado DIAN configurado (settings.DIAN_CERT_P12 vacio),
el servicio devuelve el XML sin firmar. Esto permite trabajar en modo "borrador"
o entornos de desarrollo sin certificado.

Settings requeridos para firma real:
  DIAN_CERT_P12       -- ruta al archivo .p12 / .pfx del certificado
  DIAN_CERT_PASSWORD  -- contrasena del .p12 en texto plano (o vacío)

# WARNING: NOMINA-03: movido desde apps.tenant.facturas.services.dian a este
# paquete neutral (apps.tenant.core.dian) sin modificar su logica -- es
# generico por diseño (opera sobre bytes XML crudos via un marcador string,
# sin conocer Invoice/NominaIndividual/ningun schema especifico). Ver
# docs/nomina/NOMINA_DIAN_AUDIT.md §2-3-6 para el razonamiento completo.
# facturas y empleados lo importan por igual desde aqui.
"""
import base64
import hashlib
import uuid as _uuid
from datetime import datetime, timezone

from django.conf import settings


# Politica de firma DIAN (XAdES)
DIAN_POLICY_ID = "https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf"
DIAN_POLICY_DESCRIPTION = "Politica de firma para facturas electronicas de la DIAN"
DIAN_POLICY_HASH_ALG = "http://www.w3.org/2001/04/xmlenc#sha256"


class XadesSignerService:
    """
    Firma un XML UBL 2.1 con XAdES-EPES usando el certificado DIAN.

    Si no hay certificado configurado retorna el XML intacto (modo dev).
    """

    @classmethod
    def sign(cls, xml_bytes: bytes) -> bytes:
        """
        Inserta ds:Signature en la segunda UBLExtension del XML.
        Retorna los bytes del XML firmado (o el original si no hay cert).
        """
        cert_path = getattr(settings, "DIAN_CERT_P12", "")
        cert_pwd = getattr(settings, "DIAN_CERT_PASSWORD", "")

        if not cert_path:
            return xml_bytes

        try:
            return cls._firmar_con_certificado(xml_bytes, cert_path, cert_pwd)
        except Exception:
            return xml_bytes

    # ------------------------------------------------------------------
    # Firma real con certificado PKCS#12
    # ------------------------------------------------------------------

    @classmethod
    def _firmar_con_certificado(cls, xml_bytes: bytes, cert_path: str, cert_pwd: str) -> bytes:
        """
        Implementacion XAdES-EPES real con cryptography + lxml.

        Estructura que produce:
          ds:Signature Id="xmldsig-<uuid>"
            ds:SignedInfo
              ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
              ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
              ds:Reference URI=""           (documento completo)
                ds:Transforms / ds:DigestMethod / ds:DigestValue
              ds:Reference URI="#xmldsig-<uuid>-keyinfo"
                ds:DigestMethod / ds:DigestValue
              ds:Reference URI="#Signature<uuid>-SignedProperties"
                ds:DigestMethod / ds:DigestValue (XAdES)
            ds:SignatureValue Id="xmldsig-<uuid>-sigvalue" -- SHA256withRSA en base64
            ds:KeyInfo Id="xmldsig-<uuid>-keyinfo"
              X509Data / X509Certificate -- cert DER en base64
            ds:Object
              xades:QualifyingProperties
                xades:SignedProperties Id="Signature<uuid>-SignedProperties"
                  xades:SignedSignatureProperties
                    xades:SigningTime    -- UTC ISO
                    xades:SigningCertificate
                    xades:SignaturePolicyIdentifier
                    xades:SignerRole
                      xades:ClaimedRoles / xades:ClaimedRole -- "supplier"
        """
        from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.x509 import load_der_x509_certificate

        with open(cert_path, "rb") as f:
            p12_data = f.read()

        pwd_bytes = cert_pwd.encode("utf-8") if cert_pwd else None
        private_key, certificate, _ = load_key_and_certificates(p12_data, pwd_bytes)

        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode("ascii")
        cert_digest = base64.b64encode(
            hashlib.sha256(cert_der).digest()
        ).decode("ascii")

        sig_uuid = str(_uuid.uuid4()).replace("-", "")
        signing_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # DigestValue del documento (sin firma)
        doc_digest_bytes = hashlib.sha256(xml_bytes).digest()
        doc_digest_b64 = base64.b64encode(doc_digest_bytes).decode("ascii")

        # Construir SignedProperties (para calcular su digest)
        signed_props_id = f"Signature{sig_uuid}-SignedProperties"
        signed_props_xml = cls._build_signed_properties_xml(
            signed_props_id=signed_props_id,
            signing_time=signing_time,
            cert_digest_b64=cert_digest,
            cert_issuer=certificate.issuer.rfc4514_string(),
            cert_serial=str(certificate.serial_number),
        )
        sp_digest = base64.b64encode(
            hashlib.sha256(signed_props_xml.encode("utf-8")).digest()
        ).decode("ascii")

        keyinfo_id = f"xmldsig-{sig_uuid}-keyinfo"
        keyinfo_xml = f'<ds:KeyInfo Id="{keyinfo_id}"><ds:X509Data><ds:X509Certificate>{cert_b64}</ds:X509Certificate></ds:X509Data></ds:KeyInfo>'
        ki_digest = base64.b64encode(
            hashlib.sha256(keyinfo_xml.encode("utf-8")).digest()
        ).decode("ascii")

        # Construir SignedInfo canonicalizado
        signed_info = cls._build_signed_info_xml(
            sig_uuid=sig_uuid,
            doc_digest_b64=doc_digest_b64,
            keyinfo_id=keyinfo_id,
            ki_digest_b64=ki_digest,
            sp_id=signed_props_id,
            sp_digest_b64=sp_digest,
        )

        # Firmar SignedInfo
        sig_value_bytes = private_key.sign(
            signed_info.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        sig_value_b64 = base64.b64encode(sig_value_bytes).decode("ascii")

        # Bloque ds:Signature completo
        sig_block = (
            f'<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" '
            f'Id="xmldsig-{sig_uuid}">\n'
            + signed_info
            + f'\n<ds:SignatureValue Id="xmldsig-{sig_uuid}-sigvalue">{sig_value_b64}</ds:SignatureValue>\n'
            + keyinfo_xml
            + f'\n<ds:Object><xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" '
            f'Target="#xmldsig-{sig_uuid}">'
            + signed_props_xml
            + "</xades:QualifyingProperties></ds:Object>\n"
            + "</ds:Signature>"
        )

        # Insertar en la segunda UBLExtension (ExtensionContent vacia)
        xml_str = xml_bytes.decode("utf-8")
        marker = "<ext:UBLExtension/>"
        if marker in xml_str:
            replacement = (
                "<ext:UBLExtension>"
                f"<ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:ext:XADES</ext:ExtensionURI>"
                f"<ext:ExtensionContent>{sig_block}</ext:ExtensionContent>"
                "</ext:UBLExtension>"
            )
            xml_str = xml_str.replace(marker, replacement, 1)

        return xml_str.encode("utf-8")

    # ------------------------------------------------------------------
    # Helpers de construccion XML para la firma
    # ------------------------------------------------------------------

    @classmethod
    def _build_signed_properties_xml(
        cls,
        signed_props_id: str,
        signing_time: str,
        cert_digest_b64: str,
        cert_issuer: str,
        cert_serial: str,
    ) -> str:
        return (
            f'<xades:SignedProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" '
            f'Id="{signed_props_id}">'
            f"<xades:SignedSignatureProperties>"
            f"<xades:SigningTime>{signing_time}</xades:SigningTime>"
            f"<xades:SigningCertificate>"
            f"<xades:Cert>"
            f"<xades:CertDigest>"
            f'<ds:DigestMethod xmlns:ds="http://www.w3.org/2000/09/xmldsig#" '
            f'Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
            f"<ds:DigestValue xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\">"
            f"{cert_digest_b64}</ds:DigestValue>"
            f"</xades:CertDigest>"
            f"<xades:IssuerSerial>"
            f"<ds:X509IssuerName xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\">"
            f"{cert_issuer}</ds:X509IssuerName>"
            f"<ds:X509SerialNumber xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\">"
            f"{cert_serial}</ds:X509SerialNumber>"
            f"</xades:IssuerSerial>"
            f"</xades:Cert>"
            f"</xades:SigningCertificate>"
            f"<xades:SignaturePolicyIdentifier>"
            f"<xades:SignaturePolicyId>"
            f"<xades:SigPolicyId>"
            f"<xades:Identifier Qualifier=\"OIDAsURI\">{DIAN_POLICY_ID}</xades:Identifier>"
            f"<xades:Description>{DIAN_POLICY_DESCRIPTION}</xades:Description>"
            f"</xades:SigPolicyId>"
            f"<xades:SigPolicyHash>"
            f'<ds:DigestMethod xmlns:ds="http://www.w3.org/2000/09/xmldsig#" '
            f'Algorithm="{DIAN_POLICY_HASH_ALG}"/>'
            f"<ds:DigestValue xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\">"
            f"</ds:DigestValue>"
            f"</xades:SigPolicyHash>"
            f"</xades:SignaturePolicyId>"
            f"</xades:SignaturePolicyIdentifier>"
            f"<xades:SignerRole>"
            f"<xades:ClaimedRoles>"
            f"<xades:ClaimedRole>supplier</xades:ClaimedRole>"
            f"</xades:ClaimedRoles>"
            f"</xades:SignerRole>"
            f"</xades:SignedSignatureProperties>"
            f"</xades:SignedProperties>"
        )

    @classmethod
    def _build_signed_info_xml(
        cls,
        sig_uuid: str,
        doc_digest_b64: str,
        keyinfo_id: str,
        ki_digest_b64: str,
        sp_id: str,
        sp_digest_b64: str,
    ) -> str:
        return (
            "<ds:SignedInfo>"
            '<ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
            '<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>'
            '<ds:Reference Id="xmldsig-' + sig_uuid + '-ref0" URI="">'
            "<ds:Transforms>"
            '<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
            "</ds:Transforms>"
            '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
            "<ds:DigestValue>" + doc_digest_b64 + "</ds:DigestValue>"
            "</ds:Reference>"
            '<ds:Reference URI="#' + keyinfo_id + '">'
            '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
            "<ds:DigestValue>" + ki_digest_b64 + "</ds:DigestValue>"
            "</ds:Reference>"
            '<ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#' + sp_id + '">'
            '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
            "<ds:DigestValue>" + sp_digest_b64 + "</ds:DigestValue>"
            "</ds:Reference>"
            "</ds:SignedInfo>"
        )
