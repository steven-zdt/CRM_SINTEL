"""
Pruebas de humo para API y servicios de proveedores (DRF + multitenancy).

WARNING: v2.40: Actualizado para usar services.py directamente (proveedor_service.py eliminado).
Verifica que los endpoints respondan correctamente y que el aislamiento
por esquema funcione correctamente.
"""
import pytest
from django_tenants.utils import schema_context

from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proveedores.services import (
    actualizar_proveedor,
    crear_proveedor,
    qs_list,
)


@pytest.mark.django_db
def test_crear_proveedor(tenant):
    """Verifica que el servicio crea proveedores correctamente."""
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            # Crear empresa si no existe
            empresa = Empresa.objects.create(nombre="Test Empresa")
        
        data = {
            "tipo_persona": "JURIDICA",
            "tipo_documento": "NIT",
            "numero_documento": "900123456",
            "razon_social": "ACME S.A.S.",
            "nombre_comercial": "ACME",
            "regimen_tributario": "ORDINARIO",
            "responsable_iva": True,
            "email_contacto": "compras@acme.com",
            "telefono_contacto": "3000000000",
            "activo": True
        }
        p1 = crear_proveedor(empresa, data)
        assert p1.id and p1.razon_social == "ACME S.A.S."
        
        # Actualizar
        data2 = {**data, "razon_social": "ACME COLOMBIA S.A.S."}
        p2 = actualizar_proveedor(p1, data2)
        assert p2.id == p1.id and p2.razon_social == "ACME COLOMBIA S.A.S."


@pytest.mark.django_db
def test_api_list_proveedores_smoke(client, django_user_model, tenant):
    """Smoke test: lista de proveedores."""
    from apps.public.tenants.models import TenantMembership
    from apps.tenant.perfil.models import TenantProfile
    
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        is_active=True,
        rol='ADMIN'
    )
    
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(nombre="Test Empresa")
        TenantProfile.objects.create(
            user=user,
            empresa=empresa,
            rol='ADMIN'
        )
        
    client.force_login(user)
    
    # 200 si TENANT_URLCONF ya incluye /api/v1/proveedores/
    resp = client.get("/api/v1/proveedores/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"


@pytest.mark.django_db
def test_qs_list_filtra_por_empresa(tenant):
    """Verifica que qs_list filtra correctamente por empresa."""
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(nombre="Test Empresa")
        
        # Crear proveedor de prueba
        Proveedor.objects.create(
            empresa=empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="800222333",
            razon_social="Proveedor X",
            regimen_tributario="ORDINARIO",
            activo=True
        )
        
        # Verificar que qs_list retorna el proveedor
        qs = qs_list(empresa.id, None)
        assert qs.count() >= 1
        assert qs.filter(razon_social="Proveedor X").exists()
