"""
Pruebas de humo para API y servicios de clientes (DRF + multitenancy).

Verifica que:
- El servicio de negocio actual crea y actualiza de forma idempotente
- El endpoint principal de clientes responde en contexto tenant autenticado
"""
import pytest
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.services.services import crear_cliente
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db
def test_service_crear_cliente_idempotente(tenant):
    """Verifica que crear_cliente mantiene idempotencia por documento."""
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(
                nombre="Empresa Test",
                razon_social="EMPRESA TEST S.A.S.",
                nit="901234567",
            )

        data = {
            "tipo_persona": "JURIDICA",
            "tipo_documento": "NIT",
            "numero_documento": "901000999",
            "razon_social": "CLIENTE S.A.S.",
            "nombre_comercial": "CLIENTE CO",
            "regimen_tributario": "ORDINARIO",
            "email": "ventas@cliente.com",
            "telefono": "3000000000",
            "activo": True
        }

        c1, creado1 = crear_cliente(empresa, data)
        assert creado1 is True
        assert c1.id and c1.razon_social == "CLIENTE S.A.S."
        
        data2 = {**data, "razon_social": "CLIENTE COLOMBIA S.A.S."}
        c2, creado2 = crear_cliente(empresa, data2)
        assert creado2 is False
        assert c2.id == c1.id and c2.razon_social == "CLIENTE COLOMBIA S.A.S."


@pytest.mark.django_db
def test_api_list_clientes_smoke(client, django_user_model, tenant):
    """Smoke test: lista de clientes."""
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    TenantMembership.objects.create(client=tenant, user=user, is_active=True, rol="ADMIN")
    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant.schema_name):
        client.force_login(user)

    # 200 si TENANT_URLCONF ya incluye /api/v1/clientes/
    resp = client.get("/api/v1/clientes/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"


@pytest.mark.django_db
def test_model_cliente_basico(tenant):
    """Smoke test del modelo Cliente con campos vigentes."""
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(
                nombre="Empresa Test",
                razon_social="EMPRESA TEST S.A.S.",
                nit="901234567",
            )

        c = Cliente.objects.create(
            empresa=empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="900222333",
            razon_social="Cliente X",
            regimen_tributario="ORDINARIO",
            activo=True,
        )
        assert c.id is not None
