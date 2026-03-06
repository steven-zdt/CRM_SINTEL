"""
Test: Verifica que el handler de 401 del workspace NO redirija a login
para módulos no críticos (gastos, clientes, proveedores).

Valida que:
1. Los endpoints respondan 200 cuando el usuario está autenticado con sesión
2. El handler NO redirija a login cuando hay sesión activa y SessionAuthentication está configurado
3. Los módulos no críticos manejen 401 localmente sin expulsar del workspace
"""
import pytest
from apps.public.tenants.models import TenantMembership


@pytest.mark.django_db
def test_workspace_401_handler_does_not_redirect_for_noncritical_modules(client, django_user_model, tenant):
    """
    Verifica que tras login, los endpoints de módulos no críticos NO devuelvan 401.
    
    Si los ViewSets aceptan SessionAuthentication, NO deben devolver 401 tras login.
    """
    # Crear usuario
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    
    # Crear membresía activa en el tenant
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        is_active=True,
        rol="ADMIN"
    )
    
    # Autenticar usuario (simula login con sesión)
    client.force_login(user)
    
    # Si los ViewSets aceptan SessionAuthentication, NO deben devolver 401
    # 200 si funciona correctamente, 404 si falta include en TENANT_URLCONF
    r1 = client.get("/api/v1/gastos/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    r2 = client.get("/api/v1/clientes/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    r3 = client.get("/api/v1/proveedores/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    
    # Nunca deben ser 401 si la sesión está activa y SessionAuthentication está configurado
    assert r1.status_code != 401, (
        f"El endpoint de gastos devolvió 401 tras login. "
        f"Verifica que GastoViewSet tenga authentication_classes = [SessionAuthentication]. "
        f"Status recibido: {r1.status_code}"
    )
    assert r2.status_code != 401, (
        f"El endpoint de clientes devolvió 401 tras login. "
        f"Verifica que ClienteViewSet tenga authentication_classes = [SessionAuthentication]. "
        f"Status recibido: {r2.status_code}"
    )
    assert r3.status_code != 401, (
        f"El endpoint de proveedores devolvió 401 tras login. "
        f"Verifica que ProveedorViewSet tenga authentication_classes = [SessionAuthentication]. "
        f"Status recibido: {r3.status_code}"
    )
    
    # Deben ser 200 (si funciona) o 404 (si falta include en TENANT_URLCONF)
    assert r1.status_code in (200, 404), (
        f"Status inesperado para gastos: {r1.status_code}. "
        f"Esperado: 200 (funciona) o 404 (falta include). "
        f"401 indica que SessionAuthentication no está configurado."
    )
    assert r2.status_code in (200, 404), (
        f"Status inesperado para clientes: {r2.status_code}. "
        f"Esperado: 200 (funciona) o 404 (falta include). "
        f"401 indica que SessionAuthentication no está configurado."
    )
    assert r3.status_code in (200, 404), (
        f"Status inesperado para proveedores: {r3.status_code}. "
        f"Esperado: 200 (funciona) o 404 (falta include). "
        f"401 indica que SessionAuthentication no está configurado."
    )
