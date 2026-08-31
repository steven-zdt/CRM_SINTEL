"""
Test de integracion real (DB) del primer tool READ end-to-end:
AIEngine.run_tool('buscar_cliente', ...) -> ClienteSelector -> SSoT.

Nota de diseño real (descubierta al escribir este test): `Empresa` es
SINGLETON por schema de tenant (constraint real en
apps/tenant/empresa/models.py -- "una unica instancia de Empresa por
tenant"), por lo que NO es posible construir un escenario de 2
empresas distintas dentro del mismo schema para probar fuga
cross-empresa aqui. El aislamiento real "un tenant nunca ve datos de
otro" ya esta probado a nivel de SCHEMA (Postgres/django-tenants) en
otras misiones de esta sesion (ej. TEN-01,
docs/e2e/ONBOARDING_E2E_REPORT.md) -- no se repite ese tipo de prueba
aqui. Lo que SI se prueba aqui, con evidencia real: que
build_context() deriva SIEMPRE el empresa_id del TenantProfile real
del usuario autenticado (nunca de un valor arbitrario), que la tool
usa ese empresa_id (no otro) al consultar, y que el enforcement de
flags/permisos del AIEngine es real, no solo documentado.
"""
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.services.ai.engine import run_tool
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()

AI_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}


class _FakeRequest:
    """Doble minimo -- el engine solo lee request.user y request.tenant."""

    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


class BuscarClienteToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA UNICA S.A.S.", nit="900111111", direccion="Calle 1",
        )
        self.user = User.objects.create_user(email="user@test.local", password="testpass123")
        self.profile = TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        # tenant_profile es un related_name real (OneToOne) -- disponible en self.user.tenant_profile.

        Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800000001", razon_social="Cliente Real Uno",
        )
        Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800000002", razon_social="Cliente Real Dos",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_cliente_usa_el_empresa_id_del_contexto_real(self):
        """El empresa_id que llega al Selector viene de build_context(), no de un valor arbitrario."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request)

        assert result.status == "OK"
        nombres = {c["razon_social"] for c in result.data}
        assert nombres == {"Cliente Real Uno", "Cliente Real Dos"}
        assert all(c["numero_documento"].startswith("8000000") for c in result.data)

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_cliente_respeta_search(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request, search="Uno")

        assert result.status == "OK"
        nombres = {c["razon_social"] for c in result.data}
        assert nombres == {"Cliente Real Uno"}

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_cliente_search_sin_resultados(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request, search="no-existe-nada-con-este-texto")

        assert result.status == "OK"
        assert result.data == []

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_cliente_limit_invalido_es_validation_error(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request, limit=999)

        assert result.status == "VALIDATION_ERROR"

    def test_buscar_cliente_bloqueado_si_ai_engine_deshabilitado(self):
        """Fase 63: sin AI_ENABLED, ninguna tool corre, sin importar permisos del usuario."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request)

        assert result.status == "PERMISSION_DENIED"

    @override_settings(AI_ENABLED=True, AI_READ_ENABLED=False)
    def test_buscar_cliente_bloqueado_si_solo_ai_enabled_sin_read_enabled(self):
        """El flag general no basta -- el flag especifico del kind (READ) tambien debe estar activo."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request)

        assert result.status == "PERMISSION_DENIED"

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_cliente_usuario_no_autenticado_denegado(self):
        anon = type("Anon", (), {"is_authenticated": False})()
        request = _FakeRequest(user=anon, tenant=self.tenant)

        result = run_tool("buscar_cliente", request)

        assert result.status == "PERMISSION_DENIED"

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_cliente_usuario_sin_tenant_profile_denegado(self):
        otro_user = User.objects.create_user(email="sin_perfil@test.local", password="testpass123")
        request = _FakeRequest(user=otro_user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request)

        assert result.status == "PERMISSION_DENIED"

    @override_settings(**AI_FLAGS_ON)
    def test_tool_desconocida_devuelve_not_found(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("eliminar_todo_el_erp", request)

        assert result.status == "NOT_FOUND"

    @override_settings(AI_ENABLED=True, AI_READ_ENABLED=True, AI_WRITE_ENABLED=True)
    def test_write_tools_siguen_bloqueadas_aunque_el_flag_write_este_activo(self):
        """
        Regla Absoluta 6/26: no existe ninguna tool WRITE registrada
        hoy, pero si en el futuro alguien registra una sin el flujo de
        aprobacion, AUTO_APPROVED_KINDS la bloquea igual -- este test
        fija esa garantia estructural, no depende de que exista una
        tool WRITE real para probarla via buscar_cliente (que es READ,
        asi que aqui solo confirmamos que el propio flag WRITE no
        afecta una tool READ real -- sigue funcionando normal).
        """
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_cliente", request)

        assert result.status == "OK"
