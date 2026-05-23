"""
Fase 5 — Tests alineados con la refactorización:
  - cuenta_contable_uuid movido de Empleado → Devengo
  - ExtractorNomina solo extrae devengos con cuenta asignada y anulado=False

Estilo: TenantAPITestCase (igual que test_empleados_crud.py)
"""
import uuid
from decimal import Decimal

from django.test import override_settings
from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empleados.models import Contrato, Devengo, Empleado
from apps.tenant.empresa.models import Empresa


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_empleado(empresa, doc="5555555555"):
    return Empleado.objects.create(
        empresa=empresa,
        tipo_documento="CC",
        numero_documento=doc,
        primer_nombre="Test",
        primer_apellido="Fase5",
        email=f"{doc}@test.com",
        fecha_ingreso="2024-01-01",
        eps="EPS004",
        afp="AFP001",
        arl="ARL002",
    )


def _make_contrato(empresa, empleado):
    return Contrato.objects.create(
        empresa=empresa,
        empleado=empleado,
        tipo="INDEF",
        fecha_inicio="2024-01-01",
        salario_mensual=Decimal("2000000.00"),
        cargo="Técnico",
    )


def _make_devengo(empresa, empleado, contrato, cuenta_uuid=None, anulado=False, periodo="2026-05"):
    return Devengo.objects.create(
        empresa=empresa,
        empleado=empleado,
        contrato=contrato,
        periodo_mes=periodo,
        fecha_pago="2026-05-30",
        salario_base=Decimal("2000000.00"),
        auxilio_transporte=Decimal("140000.00"),
        salud_empleado=Decimal("80000.00"),
        pension_empleado=Decimal("80000.00"),
        neto_pagar=Decimal("1980000.00"),
        anulado=anulado,
        cuenta_contable_uuid=cuenta_uuid,
    )


# ── Tests de Serializer ────────────────────────────────────────────────────────

@override_settings(ALLOWED_HOSTS=["*"])
class TestDevengoSerializerCuentaContable(TenantAPITestCase):
    """
    Verifica que cuenta_contable_uuid viaja en el payload de Devengo (no en Empleado).
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()
        self.empleado = _make_empleado(self.empresa, "5001000001")
        self.contrato = _make_contrato(self.empresa, self.empleado)
        self.url_devengos = "/api/v1/empleados/devengos/"

    # ── 1. GET lista incluye cuenta_contable_uuid ──────────────────────────────

    def test_devengo_lista_incluye_cuenta_contable_uuid(self):
        """El listado de devengos expone cuenta_contable_uuid (puede ser null)."""
        _make_devengo(self.empresa, self.empleado, self.contrato, periodo="2026-05")
        resp = self.tget(self.url_devengos)
        self.assertJSONResponse(resp, status.HTTP_200_OK)
        items = resp.data.get("results", resp.data)
        self.assertGreater(len(items), 0)
        self.assertIn("cuenta_contable_uuid", items[0])

    # ── 2. GET detalle incluye los nuevos campos de presentación ──────────────

    def test_devengo_detalle_incluye_campos_presentacion(self):
        """El detalle de un devengo expone empleado_documento y contrato_tipo_display."""
        d = _make_devengo(self.empresa, self.empleado, self.contrato, periodo="2026-06")
        resp = self.tget(f"{self.url_devengos}{d.uuid}/")
        self.assertJSONResponse(resp, status.HTTP_200_OK)
        self.assertIn("empleado_documento",     resp.data)
        self.assertIn("contrato_tipo",          resp.data)
        self.assertIn("contrato_tipo_display",  resp.data)
        self.assertIn("cuenta_contable_uuid",   resp.data)
        self.assertEqual(resp.data["empleado_documento"], self.empleado.numero_documento)

    # ── 3. PATCH asigna cuenta_contable_uuid via /asignar-cuenta/ ────────────

    def test_asignar_cuenta_contable_persiste(self):
        """PATCH /devengos/{uuid}/asignar-cuenta/ asigna y persiste la cuenta."""
        d = _make_devengo(self.empresa, self.empleado, self.contrato, periodo="2026-07")
        self.assertIsNone(d.cuenta_contable_uuid)

        cuenta_uuid = str(uuid.uuid4())
        url = f"{self.url_devengos}{d.uuid}/asignar-cuenta/"
        resp = self.tpatch(url, data={"cuenta_contable_uuid": cuenta_uuid})
        self.assertJSONResponse(resp, status.HTTP_200_OK)
        self.assertEqual(str(resp.data["cuenta_contable_uuid"]), cuenta_uuid)

        d.refresh_from_db()
        self.assertEqual(str(d.cuenta_contable_uuid), cuenta_uuid)

    # ── 4. PATCH puede limpiar cuenta_contable_uuid ───────────────────────────

    def test_asignar_cuenta_contable_limpia_con_null(self):
        """PATCH /asignar-cuenta/ con null limpia el campo."""
        cuenta_uuid = uuid.uuid4()
        d = _make_devengo(self.empresa, self.empleado, self.contrato,
                          cuenta_uuid=cuenta_uuid, periodo="2026-08")

        url = f"{self.url_devengos}{d.uuid}/asignar-cuenta/"
        resp = self.tpatch(url, data={"cuenta_contable_uuid": None})
        self.assertJSONResponse(resp, status.HTTP_200_OK)
        self.assertIsNone(resp.data["cuenta_contable_uuid"])

        d.refresh_from_db()
        self.assertIsNone(d.cuenta_contable_uuid)

    # ── 5. PATCH directo sobre /devengos/{uuid}/ sigue bloqueado ─────────────

    def test_patch_directo_devengo_sigue_bloqueado(self):
        """PATCH directo al recurso /devengos/{uuid}/ retorna 405 (inmutabilidad)."""
        d = _make_devengo(self.empresa, self.empleado, self.contrato, periodo="2026-09")
        resp = self.tpatch(
            f"{self.url_devengos}{d.uuid}/",
            data={"cuenta_contable_uuid": str(uuid.uuid4())},
        )
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ── Tests del Serializer de Empleado ──────────────────────────────────────────

@override_settings(ALLOWED_HOSTS=["*"])
class TestEmpleadoSinCuentaContable(TenantAPITestCase):
    """
    Verifica que cuenta_contable_uuid ya NO aparece en el serializer de Empleado.
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()
        self.url_empleados = "/api/v1/empleados/"

    def test_empleado_create_ignora_cuenta_contable_uuid(self):
        """POST empleado con cuenta_contable_uuid en payload no falla y no lo persiste."""
        payload = {
            "tipo_documento": "CC",
            "numero_documento": "6001000001",
            "primer_nombre": "Sin",
            "primer_apellido": "Cuenta",
            "email": "sin.cuenta@test.com",
            "fecha_ingreso": "2024-01-01",
            "eps": "EPS001",
            "afp": "AFP001",
            "arl": "ARL001",
            "cuenta_contable_uuid": str(uuid.uuid4()),  # campo eliminado de Empleado
        }
        resp = self.tpost(self.url_empleados, data=payload)
        self.assertJSONResponse(resp, status.HTTP_201_CREATED)
        # El campo no debe aparecer en la respuesta de Empleado
        self.assertNotIn("cuenta_contable_uuid", resp.data)

    def test_empleado_detalle_sin_cuenta_contable(self):
        """GET detalle de empleado no expone cuenta_contable_uuid."""
        payload = {
            "tipo_documento": "CC",
            "numero_documento": "6001000002",
            "primer_nombre": "Check",
            "primer_apellido": "Fields",
            "email": "check@test.com",
            "fecha_ingreso": "2024-01-01",
            "eps": "EPS001",
            "afp": "AFP001",
            "arl": "ARL001",
        }
        post_resp = self.tpost(self.url_empleados, data=payload)
        self.assertJSONResponse(post_resp, status.HTTP_201_CREATED)

        emp_uuid = post_resp.data["uuid"]
        resp = self.tget(f"{self.url_empleados}{emp_uuid}/")
        self.assertJSONResponse(resp, status.HTTP_200_OK)
        self.assertNotIn("cuenta_contable_uuid", resp.data)
        self.assertNotIn("cuenta_contable_label", resp.data)


# ── Tests del ExtractorNomina ──────────────────────────────────────────────────

@override_settings(ALLOWED_HOSTS=["*"])
class TestExtractorNominaGuardCuenta(TenantAPITestCase):
    """
    Verifica que ExtractorNomina.extraer_pendientes() respeta los guards:
      - anulado=False  (ya existía antes)
      - cuenta_contable_uuid IS NOT NULL  (nuevo — Fase 4)
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()
        self.empleado = _make_empleado(self.empresa, "7001000001")
        self.contrato = _make_contrato(self.empresa, self.empleado)

    def _get_extractor(self):
        from apps.tenant.contabilidad.integracion.extractores.nomina import ExtractorNomina
        return ExtractorNomina(empresa_id=self.empresa.id)

    def test_extractor_excluye_devengo_sin_cuenta(self):
        """
        Un Devengo sin cuenta_contable_uuid NO debe aparecer en extraer_pendientes().
        """
        _make_devengo(self.empresa, self.empleado, self.contrato,
                      cuenta_uuid=None, periodo="2026-05")
        resultado = self._get_extractor().extraer_pendientes()
        # Ningún devengo sin cuenta debe estar en el resultado
        ids_extraidos = [t.documento_origen.id for t in resultado]
        devengos_sin_cuenta = list(
            Devengo.objects.filter(
                empresa_id=self.empresa.id,
                cuenta_contable_uuid__isnull=True,
            ).values_list("id", flat=True)
        )
        for d_id in devengos_sin_cuenta:
            self.assertNotIn(d_id, ids_extraidos,
                             "Devengo sin cuenta contable no debe ser extraído")

    def test_extractor_excluye_devengo_anulado(self):
        """
        Un Devengo anulado=True NO debe aparecer en extraer_pendientes()
        aunque tenga cuenta_contable_uuid.
        """
        cuenta_uuid = uuid.uuid4()
        d_anulado = _make_devengo(self.empresa, self.empleado, self.contrato,
                                  cuenta_uuid=cuenta_uuid, anulado=True, periodo="2026-05")
        resultado = self._get_extractor().extraer_pendientes()
        ids_extraidos = [t.documento_origen.id for t in resultado]
        self.assertNotIn(d_anulado.id, ids_extraidos,
                         "Devengo anulado no debe ser extraído")

    def test_extractor_incluye_devengo_con_cuenta_y_activo(self):
        """
        Un Devengo con cuenta_contable_uuid y anulado=False SÍ debe aparecer.
        """
        cuenta_uuid = uuid.uuid4()
        d_ok = _make_devengo(self.empresa, self.empleado, self.contrato,
                             cuenta_uuid=cuenta_uuid, anulado=False, periodo="2026-05")
        resultado = self._get_extractor().extraer_pendientes()
        ids_extraidos = [t.documento_origen.id for t in resultado]
        self.assertIn(d_ok.id, ids_extraidos,
                      "Devengo con cuenta y activo debe ser extraído")

    def test_extractor_discrimina_correctamente_tres_casos(self):
        """
        Con 3 devengos (ok / sin cuenta / anulado) solo extrae el primero.
        """
        cuenta_uuid = uuid.uuid4()
        d_ok     = _make_devengo(self.empresa, self.empleado, self.contrato,
                                 cuenta_uuid=cuenta_uuid, anulado=False, periodo="2026-09")
        d_sin    = _make_devengo(self.empresa, self.empleado, self.contrato,
                                 cuenta_uuid=None,        anulado=False, periodo="2026-10")
        d_anul   = _make_devengo(self.empresa, self.empleado, self.contrato,
                                 cuenta_uuid=cuenta_uuid, anulado=True,  periodo="2026-11")

        resultado = self._get_extractor().extraer_pendientes()
        ids_extraidos = {t.documento_origen.id for t in resultado}

        self.assertIn(d_ok.id,    ids_extraidos, "d_ok debe extraerse")
        self.assertNotIn(d_sin.id,  ids_extraidos, "d_sin no debe extraerse")
        self.assertNotIn(d_anul.id, ids_extraidos, "d_anulado no debe extraerse")

    def test_extractor_dto_usa_cuenta_del_devengo(self):
        """
        El DTO producido usa nomina.cuenta_contable_uuid (Devengo) como hint,
        no empleado.cuenta_contable_uuid (eliminado en Fase 1).
        """
        cuenta_uuid = uuid.uuid4()
        d = _make_devengo(self.empresa, self.empleado, self.contrato,
                          cuenta_uuid=cuenta_uuid, periodo="2026-05")

        resultado = self._get_extractor().extraer_pendientes()
        dtos_del_devengo = [t for t in resultado if t.documento_origen.id == d.id]
        self.assertEqual(len(dtos_del_devengo), 1)

        dto = dtos_del_devengo[0]
        # La línea PASIVO_NOMINA_POR_PAGAR debe llevar el hint correcto
        lineas_pasivo = [l for l in dto.lineas if l.concepto == "PASIVO_NOMINA_POR_PAGAR"]
        self.assertEqual(len(lineas_pasivo), 1)
        self.assertEqual(lineas_pasivo[0].cuenta_hint, str(cuenta_uuid))
