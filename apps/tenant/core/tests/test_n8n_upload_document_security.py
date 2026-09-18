"""
N8N-SINTEL-02 (FASE 3): seguridad multi-tenant real del unico camino REST
que n8n usa hoy para escribir en SINTEL -- POST /api/v1/core/_apps/
facturas/upload-document/, autenticado con la identidad tecnica dedicada
(apps/tenant/core/management/commands/crear_identidad_tecnica_n8n.py).

`test_documentos_upload_api.py::test_multitenant_isolation` (FASE 8, 2026)
es un placeholder que su propio docstring marca como "se puede expandir
mas adelante" -- esto es esa expansion, con 2 tenants reales y la
identidad tecnica real, no una simulacion.

Reutiliza exactamente el patron ya probado en
apps/tenant/bancos/tests/test_cross_tenant_isolation.py (Auditoria
Enterprise 2026-08-06, remediacion Fase 1): un JWT valido para el
tenant equivocado NUNCA debe poder operar; a diferencia de ese test, aqui
la identidad es la tecnica de n8n (rol ADMIN, sin is_staff/is_superuser),
no un usuario humano -- y el POST tiene efecto de escritura real
(persistir una Factura), asi que ademas de status_code se verifica que
NO se cree ningun registro en el tenant equivocado.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenant.core.management.commands.crear_identidad_tecnica_n8n import (
    TECHNICAL_EMAIL_TEMPLATE,
)

UPLOAD_URL = "/api/v1/core/_apps/facturas/upload-document/"

# Mismo XML minimo valido que test_documentos_upload_api.py -- probado
# contra el pipeline real (document_ingest_validation_failed lo acepta).
XML_VALIDO = b'''
<Invoice xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>N8N-SEC-001</cbc:ID>
  <cbc:UUID>N8NSEC0001ABCDEFGHIJKLMN</cbc:UUID>
  <cbc:IssueDate>2026-03-25</cbc:IssueDate>
  <cbc:IssueTime>12:00:00</cbc:IssueTime>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>900123456</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Proveedor S.A.S.</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>901999888</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Mi Empresa S.A.S.</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount>119000.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount>119000.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="UND">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount>100000.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>Producto de prueba</cbc:Description>
      <cac:SellersItemIdentification>
        <cbc:ID>PROD001</cbc:ID>
      </cac:SellersItemIdentification>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount>100000.00</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>
</Invoice>
'''


def _crear_identidad_n8n(tenant):
    """Crea la identidad tecnica REAL via el management command (no un
    doble simulado) y devuelve (user, bearer_header)."""
    from django.contrib.auth import get_user_model

    call_command("crear_identidad_tecnica_n8n", schema=tenant.schema_name)

    User = get_user_model()
    email = TECHNICAL_EMAIL_TEMPLATE.format(schema=tenant.schema_name)
    user = User.objects.get(email=email)
    bearer = "Bearer " + str(RefreshToken.for_user(user).access_token)
    return user, bearer


def _post_upload(tenant, bearer, archivo=None):
    client = APIClient(HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    if bearer is not None:
        client.credentials(HTTP_AUTHORIZATION=bearer)
    file = archivo or SimpleUploadedFile("factura.xml", XML_VALIDO, content_type="application/xml")
    with override_settings(FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True):
        return client.post(UPLOAD_URL, {"file": file}, format="multipart")


@pytest.mark.django_db
def test_identidad_n8n_de_tenant_a_no_puede_escribir_en_tenant_b(n8n_tenant_a, n8n_tenant_b):
    """La identidad tecnica creada para tenant A, usada contra el dominio
    de tenant B, debe ser rechazada -- y NO debe crear ninguna Factura en B."""
    _, bearer_a = _crear_identidad_n8n(n8n_tenant_a)

    resp = _post_upload(n8n_tenant_b, bearer_a)

    assert resp.status_code == 403, (
        f"La identidad n8n de tenant A no debe poder escribir en tenant B "
        f"(status={resp.status_code}, body={resp.content[:300]})"
    )
    with schema_context(n8n_tenant_b.schema_name):
        from apps.tenant.facturas.models import Factura

        assert not Factura.objects.filter(numero="N8N-SEC-001").exists()


@pytest.mark.django_db
def test_identidad_n8n_de_tenant_a_si_puede_escribir_en_su_propio_tenant(n8n_tenant_a):
    """Control positivo -- evita que el test anterior sea un falso
    positivo por un problema ajeno (XML invalido, endpoint deshabilitado, etc.)."""
    _, bearer_a = _crear_identidad_n8n(n8n_tenant_a)

    resp = _post_upload(n8n_tenant_a, bearer_a)

    assert resp.status_code in (200, 201), (
        f"La identidad n8n de tenant A debe poder escribir en su propio tenant "
        f"(status={resp.status_code}, body={resp.content[:300]})"
    )


@pytest.mark.django_db
def test_upload_document_sin_identidad_es_rechazado(n8n_tenant_a):
    """Sin ningun header Authorization, el endpoint no debe aceptar la
    escritura (n8n mal configurado, o cualquier cliente sin credenciales)."""
    resp = _post_upload(n8n_tenant_a, bearer=None)

    assert resp.status_code == 401, (
        f"Una request sin credenciales debe ser rechazada antes de tocar el "
        f"pipeline de documentos (status={resp.status_code}, body={resp.content[:300]})"
    )


@pytest.mark.django_db
def test_usuario_no_admin_no_puede_usar_el_endpoint(n8n_tenant_a):
    """`test_documentos_upload_api.py` documenta (sin probarlo) que
    IsTenantAdminOrReadOnly exige TenantProfile.rol='ADMIN' -- un
    perfil OPERADOR real debe ser rechazado, no solo el humano/n8n ADMIN."""
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.tokens import RefreshToken as RT

    from apps.public.tenants.models import TenantMembership
    from apps.tenant.empresa.models import Empresa
    from apps.tenant.perfil.models import TenantProfile

    User = get_user_model()
    with schema_context("public"):
        user = User.objects.create_user(
            username="n8n_sec_operador", email="operador@n8n-sec-test.com", password="x"
        )
        TenantMembership.objects.create(
            client=n8n_tenant_a, user=user, rol="OPERADOR", is_active=True
        )
    with schema_context(n8n_tenant_a.schema_name):
        empresa = Empresa.objects.first()
        TenantProfile.objects.create(user=user, empresa=empresa, rol="OPERADOR")

    bearer = "Bearer " + str(RT.for_user(user).access_token)
    resp = _post_upload(n8n_tenant_a, bearer)

    assert resp.status_code == 403, (
        f"Un perfil OPERADOR (no ADMIN) no debe poder escribir via upload-document "
        f"(status={resp.status_code}, body={resp.content[:300]})"
    )
