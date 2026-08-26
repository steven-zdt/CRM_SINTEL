"""
Regresion real (mision REL, hallazgo confirmado en
docs/integration/CROSS_APP_FINDINGS.md): GastoViewSet.render_offcanvas_editar()
llamaba RetencionesService.listar_retenciones_por_documento() sin el
parametro obligatorio empresa_id -- lanzaba TypeError en cada ejecucion,
silenciado por un `except Exception: pass` sin logging. Efecto real:
retenciones_fracciones siempre quedaba {} y el offcanvas de edicion nunca
mostraba los porcentajes de retencion reales.
"""
from decimal import Decimal

from rest_framework import status

from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class RenderOffcanvasEditarRetencionesTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa REL Retenciones", nit="900000942", direccion="Calle REL",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RES-REL-1", prefijo="GREL",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor REL Retenciones", numero_documento="REL-RET-1", tipo_documento="NIT",
        )
        self.documento = DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=1,
            fecha="2026-06-01", proveedor=self.proveedor, subtotal=Decimal("1000000"), total=Decimal("965000"),
            descripcion="Gasto REL", categoria_contable="ARRENDAMIENTOS",
        )
        # 4% -- debe coincidir con una fraccion real de DocumentoSoporte.RETEFUENTE_CHOICES
        # ('0.04', '4% - Servicios (Declarantes)'), no un porcentaje arbitrario.
        RetencionesService.crear_retencion(
            empresa=self.empresa, tipo="RETEFUENTE", porcentaje=Decimal("4.00"),
            base=Decimal("1000000"), documento_origen_app="gastos",
            documento_origen_modelo="DocumentoSoporte", documento_origen_id=self.documento.id,
        )

    def test_offcanvas_editar_no_falla_y_carga_retenciones_reales(self):
        resp = self.api_client.get(f"/api/v1/gastos/render-offcanvas/editar/?uuid={self.documento.uuid}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        retenciones_fracciones = resp.context["retenciones_fracciones"]
        self.assertIn("RETEFUENTE", retenciones_fracciones)
        self.assertEqual(retenciones_fracciones["RETEFUENTE"], "0.04")
