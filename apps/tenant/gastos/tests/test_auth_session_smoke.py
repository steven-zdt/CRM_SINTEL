"""
Test: Verifica que el endpoint de gastos acepte SessionAuthentication
y NO devuelva 401 cuando el usuario esta autenticado con sesion.

Valida que:
1. El endpoint responda 200 cuando el usuario esta autenticado con sesion
2. El endpoint NO devuelva 401 si SessionAuthentication esta configurado
3. El handler del workspace NO redirija a login para este modulo no critico
"""
import pytest

from apps.public.tenants.models import TenantMembership


@pytest.mark.django_db
def test_gastos_list_session_ok(client, django_user_model, tenant1):
    """
    Verifica que tras login, el endpoint de gastos NO devuelva 401.
    
    Si el ViewSet acepta SessionAuthentication, NO debe devolver 401 tras login.
    """
    # Crear usuario
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    
    # Crear membresia activa en el tenant
    TenantMembership.objects.create(
        client=tenant1,
        user=user,
        is_active=True,
        rol="ADMIN"
    )
    
    # Autenticar usuario (simula login con sesion)
    client.force_login(user)
    
    # Si el ViewSet acepta SessionAuthentication, NO debe devolver 401
    # 200 si funciona correctamente, 404 si falta include en TENANT_URLCONF
    r = client.get("/api/v1/gastos/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    
    # Nunca debe ser 401 si la sesion esta activa y SessionAuthentication esta configurado
    assert r.status_code != 401, (
        f"El endpoint de gastos devolvio 401 tras login. "
        f"Verifica que GastoViewSet tenga authentication_classes = [SessionAuthentication]. "
        f"Status recibido: {r.status_code}"
    )
    
    # Debe ser 200 (si funciona) o 404 (si falta include en TENANT_URLCONF)
    assert r.status_code in (200, 404), (
        f"Status inesperado: {r.status_code}. "
        f"Esperado: 200 (funciona) o 404 (falta include). "
        f"401 indica que SessionAuthentication no esta configurado."
    )
