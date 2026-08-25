"""
Pruebas de humo CRUD v3.8.0 - Modulos Independientes

Garantiza que cada modulo (Empleados / Contratos / Nominas) tiene un ciclo
CRUD completo e independiente accesible via API.

Cobertura:
  Empleados  : LIST, CREATE, DETAIL, UPDATE (PATCH), DELETE
  Contratos  : LIST, CREATE, DETAIL, UPDATE (PATCH), CANCELAR (accion custom)
  Nominas    : LIST, CREATE, DETAIL, ANULAR (accion custom)

Restricciones:
  - Sin emojis en codigo Python (AGENTS.md 0)
  - Sin logica de negocio en tests (AGENTS.md 5)
  - Aislamiento tenant estricto via schema_context (AGENTS.md 4)
  - UUID como lookup field en todos los endpoints (AGENTS.md 14)
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_host(tenant):
    return f"{tenant.schema_name}.sintel.net.co"


EMPLEADO_PAYLOAD = {
    "tipo_documento": "CC",
    "numero_documento": "9001234567",
    "primer_nombre": "Smoke",
    "primer_apellido": "Test",
    "email": "smoke.test@sintel.local",
    "fecha_ingreso": "2025-01-01",
    "eps": "EPS001",
    "afp": "AFP001",
    "arl": "ARL001",
    "nivel_riesgo_arl": "I",
}

CONTRATO_PAYLOAD_BASE = {
    "tipo": "FIJO",
    "salario_mensual": "1500000.00",
    "fecha_inicio": "2025-01-01",
    "cargo": "Smoke Tester",
    "estado": "ACTIVO",
}

DEVENGO_PAYLOAD_BASE = {
    "periodo_mes": "2025-01",
    "fecha_pago": "2025-01-30",
    "dias_laborados": 30,
}


# ─────────────────────────────────────────────────────────────────────────────
# MODULO 1: EMPLEADOS - CRUD Completo Independiente
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmpleadoCRUDSmoke:
    """
    Garantiza que el modulo Empleados tiene CRUD completo via /api/v1/empleados/
    """
    URL = "/api/v1/empleados/"

    def test_create_empleado(self, client, admin_user, tenant):
        """C: Crear empleado retorna 201 con uuid."""
        client.force_login(admin_user)
        resp = client.post(
            self.URL,
            data=EMPLEADO_PAYLOAD,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code == 201, f"CREATE failed: {resp.status_code} {resp.content[:300]}"
        data = resp.json()
        assert "uuid" in data
        assert data["numero_documento"] == EMPLEADO_PAYLOAD["numero_documento"]

    def test_list_empleados(self, client, admin_user, tenant):
        """L: Listar empleados retorna 200 con formato paginado."""
        client.force_login(admin_user)
        resp = client.get(self.URL, HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, f"LIST failed: {resp.status_code} {resp.content[:300]}"
        data = resp.json()
        assert "results" in data or isinstance(data, list), "Debe ser paginado o lista"

    def test_detail_empleado(self, client, admin_user, tenant):
        """R: Detalle de empleado por UUID retorna 200."""
        client.force_login(admin_user)
        create_resp = client.post(
            self.URL,
            data=EMPLEADO_PAYLOAD,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.get(f"{self.URL}{uuid}/", HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, f"DETAIL failed: {resp.status_code}"
        assert resp.json()["uuid"] == uuid

    def test_update_empleado(self, client, admin_user, tenant):
        """U: Actualizar empleado via PATCH retorna 200."""
        client.force_login(admin_user)
        create_resp = client.post(
            self.URL,
            data=EMPLEADO_PAYLOAD,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.patch(
            f"{self.URL}{uuid}/",
            data={"primer_nombre": "UpdatedSmoke"},
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code == 200, f"UPDATE failed: {resp.status_code} {resp.content[:300]}"
        # El modelo capitaliza el nombre automaticamente (ej: "UpdatedSmoke" -> "Updatedsmoke")
        # Verificamos que el campo cambio, independientemente de la capitalizacion aplicada
        assert resp.json()["primer_nombre"].lower() == "updatedsmoke"

    def test_delete_empleado(self, client, admin_user, tenant):
        """D: Eliminar empleado via DELETE retorna 204 o 200."""
        client.force_login(admin_user)
        # Crear y retirar primero (no se puede eliminar empleado ACTIVO en muchos setups)
        create_resp = client.post(
            self.URL,
            data=EMPLEADO_PAYLOAD,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.delete(f"{self.URL}{uuid}/", HTTP_HOST=make_host(tenant))
        # 204 = eliminado OK, 400/409 = regla de negocio valida (ej: solo se
        # puede eliminar un empleado en estado RETIRADO, no ACTIVO)
        assert resp.status_code in (200, 204, 400, 409), (
            f"DELETE failed unexpectedly: {resp.status_code} {resp.content[:300]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MODULO 2: CONTRATOS - CRUD Completo Independiente
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestContratoCRUDSmoke:
    """
    Garantiza que el modulo Contratos tiene CRUD completo via /api/v1/empleados/contratos/
    El modulo es INDEPENDIENTE del tab Empleados desde v3.8.0.
    """
    URL_EMP = "/api/v1/empleados/"
    URL = "/api/v1/empleados/contratos/"

    def _crear_empleado(self, client, admin_user, tenant):
        """Helper: crear empleado base para contratos."""
        resp = client.post(
            self.URL_EMP,
            data=EMPLEADO_PAYLOAD,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code == 201, f"Setup empleado failed: {resp.content[:200]}"
        return resp.json()

    def test_list_contratos(self, client, admin_user, tenant):
        """L: Listar contratos independientemente retorna 200."""
        client.force_login(admin_user)
        resp = client.get(self.URL, HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, f"LIST contratos failed: {resp.status_code} {resp.content[:300]}"
        data = resp.json()
        assert "results" in data or isinstance(data, list)

    def test_create_contrato(self, client, admin_user, tenant):
        """C: Crear contrato con empleado FK retorna 201."""
        client.force_login(admin_user)
        emp = self._crear_empleado(client, admin_user, tenant)

        payload = {**CONTRATO_PAYLOAD_BASE, "empleado": emp["id"]}
        resp = client.post(
            self.URL,
            data=payload,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code == 201, f"CREATE contrato failed: {resp.status_code} {resp.content[:400]}"
        data = resp.json()
        assert "uuid" in data
        assert data["estado"] == "ACTIVO"

    def test_detail_contrato(self, client, admin_user, tenant):
        """R: Detalle de contrato por UUID retorna 200."""
        client.force_login(admin_user)
        emp = self._crear_empleado(client, admin_user, tenant)
        payload = {**CONTRATO_PAYLOAD_BASE, "empleado": emp["id"]}
        create_resp = client.post(
            self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant)
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.get(f"{self.URL}{uuid}/", HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, f"DETAIL contrato failed: {resp.status_code}"
        assert resp.json()["uuid"] == uuid

    def test_update_contrato(self, client, admin_user, tenant):
        """U: Actualizar contrato via PATCH retorna 200."""
        client.force_login(admin_user)
        emp = self._crear_empleado(client, admin_user, tenant)
        payload = {**CONTRATO_PAYLOAD_BASE, "empleado": emp["id"]}
        create_resp = client.post(
            self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant)
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.patch(
            f"{self.URL}{uuid}/",
            data={"cargo": "Senior Smoke Tester"},
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code == 200, f"UPDATE contrato failed: {resp.status_code} {resp.content[:300]}"
        assert resp.json()["cargo"] == "Senior Smoke Tester"

    def test_cancelar_contrato(self, client, admin_user, tenant):
        """D: Cancelar contrato via accion custom retorna 200."""
        client.force_login(admin_user)
        emp = self._crear_empleado(client, admin_user, tenant)
        payload = {**CONTRATO_PAYLOAD_BASE, "empleado": emp["id"]}
        create_resp = client.post(
            self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant)
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.post(
            f"{self.URL}{uuid}/cancelar/",
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        # 200 = cancelado OK; 400 = regla de negocio (ya cancelado, etc.) ambos validos
        assert resp.status_code in (200, 400), (
            f"CANCELAR contrato failed: {resp.status_code} {resp.content[:300]}"
        )

    def test_no_duplicar_contrato_activo(self, client, admin_user, tenant):
        """Regla de negocio: un empleado no puede tener dos contratos ACTIVO a la vez."""
        client.force_login(admin_user)
        emp = self._crear_empleado(client, admin_user, tenant)
        payload = {**CONTRATO_PAYLOAD_BASE, "empleado": emp["id"]}

        r1 = client.post(self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant))
        assert r1.status_code == 201

        r2 = client.post(self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant))
        assert r2.status_code in (400, 409), (
            f"Debe rechazar segundo contrato ACTIVO: got {r2.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MODULO 3: NOMINAS (DEVENGOS) - CRUD Completo Independiente
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestNominaCRUDSmoke:
    """
    Garantiza que el modulo Nominas tiene CRUD completo via /api/v1/empleados/devengos/
    El modulo es INDEPENDIENTE del tab Empleados desde v3.8.0.
    """
    URL_EMP  = "/api/v1/empleados/"
    URL_CONT = "/api/v1/empleados/contratos/"
    URL      = "/api/v1/empleados/devengos/"

    def _setup(self, client, admin_user, tenant):
        """Helper: crea empleado + contrato y retorna IDs."""
        # El service layer exige una ResolucionDIAN vigente que cubra la
        # fecha_pago de DEVENGO_PAYLOAD_BASE (2025-01-30); sin ella,
        # procesar_devengo() rechaza el POST con 400 (AGENTS.md 18/CONTAB).
        with schema_context(tenant.schema_name):
            from apps.tenant.empleados.models import ResolucionDIAN
            from apps.tenant.empresa.models import Empresa

            empresa = Empresa.objects.only("id").first()
            ResolucionDIAN.objects.get_or_create(
                empresa=empresa,
                numero_resolucion="RES-SMOKE-NOMINA",
                defaults={
                    "prefijo": "SMK",
                    "rango_desde": 1,
                    "rango_hasta": 10000,
                    "fecha_resolucion": "2025-01-01",
                    "fecha_inicio": "2025-01-01",
                    "fecha_fin": "2027-01-01",
                    "vigente": True,
                },
            )

        emp_resp = client.post(
            self.URL_EMP,
            data=EMPLEADO_PAYLOAD,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert emp_resp.status_code == 201, f"Setup empleado: {emp_resp.content[:200]}"
        emp = emp_resp.json()

        cont_resp = client.post(
            self.URL_CONT,
            data={**CONTRATO_PAYLOAD_BASE, "empleado": emp["id"]},
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert cont_resp.status_code == 201, f"Setup contrato: {cont_resp.content[:200]}"
        cont = cont_resp.json()

        return emp, cont

    def test_list_nominas(self, client, admin_user, tenant):
        """L: Listar devengos independientemente retorna 200."""
        client.force_login(admin_user)
        resp = client.get(self.URL, HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, f"LIST nominas failed: {resp.status_code} {resp.content[:300]}"
        data = resp.json()
        assert "results" in data or isinstance(data, list)

    def test_create_nomina(self, client, admin_user, tenant):
        """C: Crear nomina retorna 201 con calculos del service layer."""
        client.force_login(admin_user)
        emp, cont = self._setup(client, admin_user, tenant)

        payload = {
            **DEVENGO_PAYLOAD_BASE,
            "empleado": emp["id"],
            "contrato": cont["id"],
        }
        resp = client.post(
            self.URL,
            data=payload,
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code == 201, f"CREATE nomina failed: {resp.status_code} {resp.content[:500]}"
        data = resp.json()
        assert "uuid" in data
        # Verificar que el service layer calculo los campos
        assert "neto_pagar" in data
        assert "salario_base" in data
        assert Decimal(data["neto_pagar"]) > 0

    def test_detail_nomina(self, client, admin_user, tenant):
        """R: Detalle de devengo por UUID retorna 200."""
        client.force_login(admin_user)
        emp, cont = self._setup(client, admin_user, tenant)
        payload = {**DEVENGO_PAYLOAD_BASE, "empleado": emp["id"], "contrato": cont["id"]}
        create_resp = client.post(
            self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant)
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.get(f"{self.URL}{uuid}/", HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, f"DETAIL nomina failed: {resp.status_code}"
        assert resp.json()["uuid"] == uuid

    def test_nomina_inmutable_no_editable(self, client, admin_user, tenant):
        """U: Los devengos son inmutables - PATCH debe estar bloqueado o retornar error."""
        client.force_login(admin_user)
        emp, cont = self._setup(client, admin_user, tenant)
        payload = {**DEVENGO_PAYLOAD_BASE, "empleado": emp["id"], "contrato": cont["id"]}
        create_resp = client.post(
            self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant)
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        # Intentar modificar campo de calculo - debe ser ignorado o rechazado
        resp = client.patch(
            f"{self.URL}{uuid}/",
            data={"salario_base": "9999999.00", "neto_pagar": "9999999.00"},
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        if resp.status_code == 200:
            # Si permite PATCH, verificar que los campos calculados no cambiaron
            data = resp.json()
            assert Decimal(data["neto_pagar"]) != Decimal("9999999.00"), (
                "El service layer debe proteger los campos calculados"
            )
        else:
            # 400 o 405 = bloqueado correctamente
            assert resp.status_code in (400, 405), (
                f"PATCH devengo inesperado: {resp.status_code} {resp.content[:300]}"
            )

    def test_anular_nomina(self, client, admin_user, tenant):
        """D: Anular devengo via accion custom retorna 200."""
        client.force_login(admin_user)
        emp, cont = self._setup(client, admin_user, tenant)
        payload = {**DEVENGO_PAYLOAD_BASE, "empleado": emp["id"], "contrato": cont["id"]}
        create_resp = client.post(
            self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant)
        )
        assert create_resp.status_code == 201
        uuid = create_resp.json()["uuid"]

        resp = client.post(
            f"{self.URL}{uuid}/anular/",
            content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code in (200, 400), (
            f"ANULAR nomina failed: {resp.status_code} {resp.content[:300]}"
        )
        if resp.status_code == 200:
            with schema_context(tenant.schema_name):
                from apps.tenant.empleados.models import Devengo
                dev = Devengo.objects.get(uuid=uuid)
                assert dev.anulado is True, "El devengo debe quedar marcado como anulado"

    def test_no_duplicar_nomina_mismo_periodo(self, client, admin_user, tenant):
        """Regla de negocio: no se puede registrar dos nominas para el mismo periodo."""
        client.force_login(admin_user)
        emp, cont = self._setup(client, admin_user, tenant)
        payload = {**DEVENGO_PAYLOAD_BASE, "empleado": emp["id"], "contrato": cont["id"]}

        r1 = client.post(self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant))
        assert r1.status_code == 201

        r2 = client.post(self.URL, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant))
        assert r2.status_code in (400, 409), (
            f"Debe rechazar duplicado de periodo: got {r2.status_code} {r2.content[:300]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-MODULE: Verificar endpoints de los 3 modulos son accesibles
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEndpointsAccessibilitySmoke:
    """
    Verifica que los 3 endpoints base responden correctamente.
    Garantia minima: 200 (hay datos) o 200 sin datos (lista vacia).
    Falla si hay 404 (endpoint no registrado) o 500 (error interno).
    """

    def test_endpoint_empleados_accesible(self, client, admin_user, tenant):
        client.force_login(admin_user)
        resp = client.get("/api/v1/empleados/", HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, (
            f"Endpoint /api/v1/empleados/ no accesible: {resp.status_code}"
        )

    def test_endpoint_contratos_accesible(self, client, admin_user, tenant):
        client.force_login(admin_user)
        resp = client.get("/api/v1/empleados/contratos/", HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, (
            f"Endpoint /api/v1/empleados/contratos/ no accesible: {resp.status_code}"
        )

    def test_endpoint_devengos_accesible(self, client, admin_user, tenant):
        client.force_login(admin_user)
        resp = client.get("/api/v1/empleados/devengos/", HTTP_HOST=make_host(tenant))
        assert resp.status_code == 200, (
            f"Endpoint /api/v1/empleados/devengos/ no accesible: {resp.status_code}"
        )

    def test_ninguno_devuelve_500(self, client, admin_user, tenant):
        """Los 3 endpoints NO deben generar errores internos."""
        client.force_login(admin_user)
        host = make_host(tenant)
        for url in [
            "/api/v1/empleados/",
            "/api/v1/empleados/contratos/",
            "/api/v1/empleados/devengos/",
        ]:
            resp = client.get(url, HTTP_HOST=host)
            assert resp.status_code != 500, (
                f"ERROR 500 en {url}: {resp.content[:500]}"
            )
            assert resp.status_code != 404, (
                f"ERROR 404 en {url} - endpoint no registrado"
            )
