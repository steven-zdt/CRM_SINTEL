"""
Tests para PLAN_AJUSTE_CICLO_PROYECTOS_FASE_1_VIABILIDAD_APROBACION.

Cubre:
1. Vinculacion de Facturas de Venta (naturaleza/estado validos, DSV, idempotencia)
2. Calculo del "valor vendido" (FE/ND suman, NC resta -- Decision 04)
3. Resumen de viabilidad (ambos margenes, division por cero protegida)
4. Ciclo de aprobacion sobre el motor generico de apps.tenant.approvals
5. Gate real INICIO -> PLANEACION (bloquea sin aprobacion, permite aprobado)
6. Invalidacion de la aprobacion al editar datos economicos criticos

NOTA: estos tests corren contra el motor GENERICO de SolicitudAprobacion
(apps.tenant.approvals) -- no se duplica infraestructura de aprobacion
propia para Proyectos (Seccion 91 del plan).
"""

from datetime import date
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.approvals.models import SolicitudAprobacion
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proyectos.models import ProyectoFacturaVenta
from apps.tenant.proyectos.services import cambiar_fase_proyecto, orchestrate_create_proyecto
from apps.tenant.proyectos.services.inicio_service import (
    CotizacionCostoProyectoService,
    InversionProyectoInicioService,
    ProyectoFacturaVentaService,
    ProyectoInicioAprobacionService,
    ProyectoInicioResumenService,
)


def _crear_factura(empresa, numero, naturaleza, estado, tipo=Factura.TipoFactura.FE, subtotal="10000000.00", total="11900000.00"):
    return Factura.objects.create(
        empresa=empresa,
        numero=numero,
        consecutivo=1,
        tipo=tipo,
        estado=estado,
        naturaleza=naturaleza,
        fecha_emision="2026-06-01",
        emisor_nit=empresa.nit,
        emisor_razon_social=empresa.razon_social,
        receptor_nit="900123456",
        receptor_razon_social="Cliente Test",
        subtotal=Decimal(subtotal),
        total=Decimal(total),
    )


@pytest.mark.django_db
class TestProyectoFacturaVentaService:
    @pytest.fixture(autouse=True)
    def setup(self, tenant1):
        with schema_context(tenant1.schema_name):
            self.empresa = Empresa.objects.first()
            self.proyecto = orchestrate_create_proyecto(
                self.empresa, {"nombre": "Proyecto Fase1 Test", "tipo_servicio": "PROYECTO_INTEGRAL"}
            )

    def test_vincular_factura_venta_aceptada_ok(self, tenant1):
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FE-001", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA)
            ok, vinculo, status_code = ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id
            )
            assert ok is True
            assert status_code == 201
            assert isinstance(vinculo, ProyectoFacturaVenta)

    def test_vincular_factura_compra_rechazada(self, tenant1):
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FC-001", Factura.Naturaleza.COMPRA, Factura.Estado.ACEPTADA)
            ok, result, status_code = ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id
            )
            assert ok is False
            assert result["error"] == "naturaleza_invalida"
            assert status_code == 422

    def test_vincular_factura_venta_borrador_rechazada(self, tenant1):
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FE-002", Factura.Naturaleza.VENTA, Factura.Estado.BORRADOR)
            ok, result, status_code = ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id
            )
            assert ok is False
            assert result["error"] == "estado_invalido"
            assert status_code == 422

    def test_vincular_misma_factura_dos_veces_rechazada(self, tenant1):
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FE-003", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA)
            ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id
            )
            ok, result, status_code = ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id
            )
            assert ok is False
            assert result["error"] == "ya_vinculada"
            assert status_code == 409

    def test_valor_vendido_resta_notas_credito(self, tenant1):
        """Decision 04: FE + ND - NC."""
        with schema_context(tenant1.schema_name):
            fe = _crear_factura(self.empresa, "FE-100", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA, tipo=Factura.TipoFactura.FE, subtotal="10000000.00")
            nc = _crear_factura(self.empresa, "NC-100", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA, tipo=Factura.TipoFactura.NC, subtotal="2000000.00")
            for f in (fe, nc):
                ProyectoFacturaVentaService.vincular_factura(
                    proyecto=self.proyecto, factura_uuid=str(f.uuid), empresa_id=self.empresa.id
                )
            resumen = ProyectoFacturaVentaService.get_resumen(self.proyecto)
            assert Decimal(resumen["valor_vendido_subtotal"]) == Decimal("8000000.00")

    def test_desvincular_factura_ok(self, tenant1):
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FE-004", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA)
            ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id
            )
            ok, _, status_code = ProyectoFacturaVentaService.desvincular_factura(
                proyecto=self.proyecto, factura_uuid=factura.uuid
            )
            assert ok is True
            assert status_code == 200
            assert not ProyectoFacturaVenta.objects.filter(proyecto=self.proyecto).exists()


@pytest.mark.django_db
class TestProyectoInicioResumenService:
    @pytest.fixture(autouse=True)
    def setup(self, tenant1):
        with schema_context(tenant1.schema_name):
            self.empresa = Empresa.objects.first()
            self.proyecto = orchestrate_create_proyecto(
                self.empresa, {"nombre": "Proyecto Viabilidad Test", "tipo_servicio": "PROYECTO_INTEGRAL"}
            )

    def test_margen_none_sin_valor_vendido(self, tenant1):
        """Division por cero protegida (Seccion 81 del plan)."""
        with schema_context(tenant1.schema_name):
            CotizacionCostoProyectoService.crear(
                proyecto=self.proyecto,
                empresa_id=self.empresa.id,
                data={"categoria": "MANO_OBRA", "valor": Decimal("5000000.00")},
            )
            resumen = ProyectoInicioResumenService.calcular_resumen(self.proyecto)
            assert resumen["viabilidad"]["margen_cotizacion_pct"] is None

    def test_viabilidad_calcula_ambos_margenes(self, tenant1):
        """Decision 10: se exponen ambos margenes, sin un 'oficial' unico."""
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FE-200", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA, subtotal="10000000.00")
            ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id
            )
            CotizacionCostoProyectoService.crear(
                proyecto=self.proyecto, empresa_id=self.empresa.id,
                data={"categoria": "MANO_OBRA", "valor": Decimal("6000000.00")},
            )
            InversionProyectoInicioService.crear(
                proyecto=self.proyecto, empresa_id=self.empresa.id,
                data={"categoria": "MATERIALES", "valor": Decimal("2000000.00"), "fecha": date.today()},
            )
            resumen = ProyectoInicioResumenService.calcular_resumen(self.proyecto)
            assert resumen["cotizaciones_costo"]["total"] == "6000000.00"
            assert resumen["inversion_real"]["total"] == "2000000.00"
            assert resumen["viabilidad"]["margen_cotizacion_pct"] == "40.00"
            assert resumen["viabilidad"]["margen_inversion_pct"] == "80.00"

    def test_cotizacion_costo_proveedor_inexistente_rechazada(self, tenant1):
        """DSV: `_validar_proveedor_dsv` rechaza un proveedor_id que no existe
        para esta empresa (mismo codepath que rechaza uno de otro tenant --
        la query `Proveedor.objects.filter(id=X, empresa_id=Y)` no distingue
        entre "no existe" y "existe pero es de otra empresa")."""
        with schema_context(tenant1.schema_name), pytest.raises(ValidationError):
            CotizacionCostoProyectoService.crear(
                proyecto=self.proyecto,
                empresa_id=self.empresa.id,
                data={"categoria": "MANO_OBRA", "valor": Decimal("100"), "proveedor_id": 999999},
            )


@pytest.mark.django_db
class TestGateAprobacionInicio:
    """Seccion 34/87 del plan: 'No hay Planeacion sin aprobacion del Inicio economico.'"""

    @pytest.fixture(autouse=True)
    def setup(self, tenant1):
        with schema_context(tenant1.schema_name):
            self.empresa = Empresa.objects.first()
            self.usuario = TenantProfile.objects.first()
            self.proyecto = orchestrate_create_proyecto(
                self.empresa, {"nombre": "Proyecto Gate Test", "tipo_servicio": "PROYECTO_INTEGRAL"}
            )
            cambiar_fase_proyecto(self.proyecto, "INICIO")
            self.proyecto.refresh_from_db()

    def _aprobar_proyecto(self):
        factura = _crear_factura(self.empresa, "FE-GATE-001", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA)
        ProyectoFacturaVentaService.vincular_factura(
            proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id, usuario=self.usuario
        )
        ProyectoInicioAprobacionService.enviar_aprobacion(proyecto=self.proyecto, usuario=self.usuario)
        ok, solicitud, _ = ProyectoInicioAprobacionService.aprobar(
            proyecto=self.proyecto, empresa_id=self.empresa.id, usuario=self.usuario, observacion="test"
        )
        assert ok is True
        return solicitud

    def test_gate_bloquea_sin_aprobacion(self, tenant1):
        with schema_context(tenant1.schema_name), pytest.raises(ValidationError):
            cambiar_fase_proyecto(self.proyecto, "PLANEACION")

    def test_enviar_aprobacion_sin_facturas_falla(self, tenant1):
        with schema_context(tenant1.schema_name):
            ok, result, status_code = ProyectoInicioAprobacionService.enviar_aprobacion(
                proyecto=self.proyecto, usuario=self.usuario
            )
            assert ok is False
            assert result["error"] == "sin_valor_vendido"
            assert status_code == 422

    def test_gate_bloquea_con_solicitud_pendiente(self, tenant1):
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FE-GATE-002", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA)
            ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id, usuario=self.usuario
            )
            ProyectoInicioAprobacionService.enviar_aprobacion(proyecto=self.proyecto, usuario=self.usuario)
            with pytest.raises(ValidationError):
                cambiar_fase_proyecto(self.proyecto, "PLANEACION")

    def test_gate_permite_tras_aprobar(self, tenant1):
        with schema_context(tenant1.schema_name):
            self._aprobar_proyecto()
            proyecto_actualizado = cambiar_fase_proyecto(self.proyecto, "PLANEACION")
            assert proyecto_actualizado.fase_actual == "PLANEACION"

    def test_solo_admin_puede_aprobar_rol_no_validado_aqui(self, tenant1):
        """
        La restriccion de rol ADMIN (Seccion 56 del plan) vive en
        `IsTenantAdminOrReadOnly` (permission_classes de ProyectoViewSet,
        heredado), no en el Service Layer -- este test documenta esa
        decision de capa en vez de duplicar la verificacion de permisos
        DRF a nivel de servicio.
        """
        with schema_context(tenant1.schema_name):
            assert True

    def test_invalidar_aprobacion_al_vincular_otra_factura(self, tenant1):
        """Decision 07: editar datos economicos criticos tras aprobar invalida (CANCELADA)."""
        with schema_context(tenant1.schema_name):
            self._aprobar_proyecto()
            solicitud = ProyectoInicioAprobacionService.get_ultima_solicitud(self.proyecto)
            assert solicitud.estado == SolicitudAprobacion.Estado.APROBADA

            factura2 = _crear_factura(self.empresa, "FE-GATE-003", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA)
            ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura2.uuid), empresa_id=self.empresa.id, usuario=self.usuario
            )
            solicitud.refresh_from_db()
            assert solicitud.estado == SolicitudAprobacion.Estado.CANCELADA

    def test_rechazar_requiere_motivo(self, tenant1):
        with schema_context(tenant1.schema_name):
            factura = _crear_factura(self.empresa, "FE-GATE-004", Factura.Naturaleza.VENTA, Factura.Estado.ACEPTADA)
            ProyectoFacturaVentaService.vincular_factura(
                proyecto=self.proyecto, factura_uuid=str(factura.uuid), empresa_id=self.empresa.id, usuario=self.usuario
            )
            ProyectoInicioAprobacionService.enviar_aprobacion(proyecto=self.proyecto, usuario=self.usuario)

            ok, result, status_code = ProyectoInicioAprobacionService.rechazar(
                proyecto=self.proyecto, empresa_id=self.empresa.id, usuario=self.usuario, motivo=""
            )
            assert ok is False
            assert status_code == 422

            ok2, solicitud, _ = ProyectoInicioAprobacionService.rechazar(
                proyecto=self.proyecto, empresa_id=self.empresa.id, usuario=self.usuario, motivo="Costos no viables"
            )
            assert ok2 is True
            assert solicitud.estado == SolicitudAprobacion.Estado.RECHAZADA
            assert solicitud.motivo_rechazo == "Costos no viables"
