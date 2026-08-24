"""
FISCAL-02A: persistencia completa de cada intento de transmision
(TransmisionFactura) via MockTransportAdapter -- CERO conexion externa,
decision explicita del usuario para dejar la arquitectura lista y probada
en modo simulado antes de tener credenciales DIAN reales.

Cubre: creacion del registro PENDIENTE en fase 1, cierre con el resultado
real (ACEPTADO/RECHAZADO/AMBIGUO), reconciliar() de un AMBIGUO via
get_status(), e historial de reintentos (multiples filas, no una sola
sobreescrita).
"""
from decimal import Decimal

from apps.tenant.core.dian import MockTransportAdapter
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos, TransmisionFactura
from apps.tenant.facturas.services.electronic_invoice_service import ElectronicInvoiceApplicationService
from tests.tenant.base_test import SintelTenantTestCase


class TransmisionFacturaPersistenciaTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Fiscal-02A", nit="900000904", direccion="Calle Fiscal-02A",
        )

    def _factura(self, estado=Factura.Estado.BORRADOR):
        factura = Factura.objects.create(
            empresa=self.empresa, numero="FE-F02A-1", prefijo="FE", consecutivo=1, tipo="FE",
            naturaleza=Factura.Naturaleza.VENTA, estado=estado, fecha_emision="2026-06-20",
            emisor_nit="900000904", emisor_razon_social="Empresa Fiscal-02A",
            receptor_nit="800000001", receptor_razon_social="Cliente F02A",
            subtotal=Decimal("100000.00"), impuestos=Decimal("19000.00"), total=Decimal("119000.00"),
            cufe="cufe-f02a-test",
        )
        FacturaAnexos.objects.create(factura=factura, ubl_xml="<Invoice>contenido</Invoice>")
        return factura

    def test_transmitir_crea_una_transmisionfactura_pendiente_y_la_cierra_con_aceptado(self):
        factura = self._factura()

        resultado = ElectronicInvoiceApplicationService.transmitir(
            factura, transport=MockTransportAdapter(scenario="TEST_ACCEPTED"),
        )

        transmision = resultado["transmision"]
        self.assertEqual(TransmisionFactura.objects.filter(factura=factura).count(), 1)
        self.assertEqual(transmision.status, TransmisionFactura.Status.ACEPTADO)
        self.assertEqual(transmision.environment, TransmisionFactura.Environment.TEST)
        self.assertIsNotNone(transmision.submitted_at)
        self.assertIsNotNone(transmision.responded_at)
        self.assertIsNotNone(transmision.track_id)

    def test_transmitir_con_rechazo_persiste_el_mensaje_de_error(self):
        factura = self._factura()

        resultado = ElectronicInvoiceApplicationService.transmitir(
            factura, transport=MockTransportAdapter(scenario="TEST_REJECTED"),
        )

        transmision = resultado["transmision"]
        self.assertEqual(transmision.status, TransmisionFactura.Status.RECHAZADO)
        self.assertIn("SIMULADO", transmision.response_message)
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.RECHAZADA)

    def test_timeout_deja_la_transmision_en_ambiguo_y_la_factura_en_enviada(self):
        factura = self._factura()

        resultado = ElectronicInvoiceApplicationService.transmitir(
            factura, transport=MockTransportAdapter(scenario="TEST_TIMEOUT"),
        )

        transmision = resultado["transmision"]
        self.assertEqual(transmision.status, TransmisionFactura.Status.AMBIGUO)
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.ENVIADA)

    def test_reconciliar_resuelve_un_ambiguo_consultando_get_status(self):
        factura = self._factura()
        adapter = MockTransportAdapter(scenario="TEST_ACCEPTED")

        # Semilla directa del "historial" del mock -- equivalente a que un
        # send() real ya hubiera llegado a la DIAN (aunque la respuesta al
        # cliente se haya perdido por timeout). factura sigue BORRADOR aqui,
        # antes de mutarla mas abajo, asi que el documento construido usa el
        # mismo cufe que despues consultara reconciliar().
        documento = ElectronicInvoiceApplicationService._construir_documento(factura)
        adapter.send(documento)

        # Simula el estado real tras un timeout: Factura en ENVIADA, con una
        # transmision AMBIGUA ya registrada (lo que transmitir() habria dejado).
        TransmisionFactura.objects.create(
            empresa=self.empresa, factura=factura, environment=TransmisionFactura.Environment.TEST,
            status=TransmisionFactura.Status.AMBIGUO,
        )
        factura.estado = Factura.Estado.ENVIADA
        factura.save(update_fields=["estado"])

        resultado = ElectronicInvoiceApplicationService.reconciliar(factura, transport=adapter)

        self.assertEqual(resultado["resultado"].status, "ACEPTADO")
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.ACEPTADA)
        resultado["transmision"].refresh_from_db()
        self.assertEqual(resultado["transmision"].status, TransmisionFactura.Status.ACEPTADO)

    def test_reconciliar_sin_intento_previo_lanza_valueerror(self):
        factura = self._factura()

        with self.assertRaises(ValueError):
            ElectronicInvoiceApplicationService.reconciliar(factura, transport=MockTransportAdapter())

    def test_reintento_legitimo_genera_una_segunda_fila_no_sobreescribe_la_primera(self):
        factura = self._factura()

        ElectronicInvoiceApplicationService.transmitir(factura, transport=MockTransportAdapter(scenario="TEST_REJECTED"))
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.RECHAZADA)  # habilita reintentar (TRANSICIONES_VALIDAS)

        ElectronicInvoiceApplicationService.transmitir(factura, transport=MockTransportAdapter(scenario="TEST_ACCEPTED"))

        self.assertEqual(TransmisionFactura.objects.filter(factura=factura).count(), 2)
        estados = list(
            TransmisionFactura.objects.filter(factura=factura).order_by("submitted_at").values_list("status", flat=True)
        )
        self.assertEqual(estados, [TransmisionFactura.Status.RECHAZADO, TransmisionFactura.Status.ACEPTADO])
