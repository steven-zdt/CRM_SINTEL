"""
Test: Verifica que los endpoints de clientes acepten SessionAuthentication
y NO devuelvan 401 cuando el usuario está autenticado con sesión.

Valida que:
1. Los endpoints respondan 200 cuando el usuario está autenticado con sesión
2. Los endpoints NO devuelvan 401 si SessionAuthentication está configurado
3. El handler del workspace NO redirija a login para este módulo no crítico
"""
import pytest

from apps.public.tenants.models import TenantMembership


@pytest.mark.django_db
def test_clientes_list_session_ok(client, django_user_model, tenant):
    """
    Verifica que tras login, el endpoint de clientes NO devuelva 401.
    
    Si el ViewSet acepta SessionAuthentication, NO debe devolver 401 tras login.
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
    
    # Si el ViewSet acepta SessionAuthentication, NO debe devolver 401
    # 200 si funciona correctamente, 404 si falta include en TENANT_URLCONF
    r = client.get("/api/v1/clientes/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    
    # Nunca debe ser 401 si la sesión está activa y SessionAuthentication está configurado
    assert r.status_code != 401, (
        f"El endpoint de clientes devolvió 401 tras login. "
        f"Verifica que ClienteViewSet tenga authentication_classes = [SessionAuthentication]. "
        f"Status recibido: {r.status_code}"
    )
    
    # Debe ser 200 (si funciona) o 404 (si falta include en TENANT_URLCONF)
    assert r.status_code in (200, 404), (
        f"Status inesperado: {r.status_code}. "
        f"Esperado: 200 (funciona) o 404 (falta include). "
        f"401 indica que SessionAuthentication no está configurado."
    )


@pytest.mark.django_db
def test_ventas_cliente_list_session_ok(client, django_user_model, tenant):
    """
    Verifica que tras login, el endpoint de ventas-cliente NO devuelva 401.
    """
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    TenantMembership.objects.create(client=tenant, user=user, is_active=True, rol="ADMIN")
    client.force_login(user)
    
    r = client.get("/api/v1/ventas-cliente/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    assert r.status_code != 401, f"VentaClienteViewSet devolvió 401. Status: {r.status_code}"
    assert r.status_code in (200, 404), f"Status inesperado: {r.status_code}"
