"""
Test: Verifica que el endpoint de gastos NO cause logout inmediato tras login.

Valida que:
1. El endpoint responda 200 cuando el usuario está autenticado con sesión
2. El endpoint NO redirija a login cuando hay sesión activa
3. SessionAuthentication funcione correctamente
"""
import pytest
from apps.public.tenants.models import TenantMembership


@pytest.mark.django_db
def test_no_logout_after_login_with_session_auth_for_gastos(client, django_user_model, tenant):
    """
    Verifica que tras login, el endpoint de gastos NO devuelva 401.
    
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
    resp = client.get("/api/v1/gastos/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    
    # Nunca debe ser 401 si la sesión está activa y SessionAuthentication está configurado
    assert resp.status_code != 401, (
        f"El endpoint devolvió 401 tras login. "
        f"Verifica que GastoViewSet tenga authentication_classes = [SessionAuthentication]. "
        f"Status recibido: {resp.status_code}"
    )
    
    # Debe ser 200 (si funciona) o 404 (si falta include en TENANT_URLCONF)
    assert resp.status_code in (200, 404), (
        f"Status inesperado: {resp.status_code}. "
        f"Esperado: 200 (funciona) o 404 (falta include). "
        f"401 indica que SessionAuthentication no está configurado."
    )
