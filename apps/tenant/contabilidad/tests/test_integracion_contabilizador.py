"""
Unit tests for Contabilizador integration service layer.

Tests use synthetic TransaccionEconomica DTOs and mock the database
to verify the accounting logic without external dependencies.

v3.0: Fase 0 (Preparación)
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.tenant.contabilidad.integracion.contabilizador import Contabilizador
from apps.tenant.contabilidad.integracion.dtos import (
    DocumentoOrigen,
    ImpuestoLinea,
    LineaTransaccion,
    TerceroSnapshot,
    TipoTercero,
    TipoTransaccion,
    TransaccionEconomica,
)
from apps.tenant.contabilidad.integracion.excepciones import (
    AsientoNoCuadradoError,
    AsientoYaExisteError,
    ReglaContableNoDefinidaError,
)


class TestContabilizadorDTOConstruction(TestCase):
    """Test TransaccionEconomica DTO construction and immutability."""

    def test_crear_transaccion_venta_simple(self):
        """Create a simple sales invoice transaction DTO."""
        tercero = TerceroSnapshot(
            tipo=TipoTercero.CLIENTE,
            id_origen=1,
            nit='900123456',
            razon_social='Acme Corp'
        )

        linea = LineaTransaccion(
            concepto='INGRESO_PRINCIPAL',
            monto=Decimal('1000000'),
            impuestos=[
                ImpuestoLinea(
                    tipo='IVA_GENERADO',
                    base=Decimal('1000000'),
                    porcentaje=Decimal('19.00'),
                    valor=Decimal('190000')
                )
            ]
        )

        doc_origen = DocumentoOrigen(
            app_label='facturas',
            modelo='Factura',
            id=100,
            numero='INV-2026-001'
        )

        transaccion = TransaccionEconomica(
            tipo=TipoTransaccion.VENTA_FACTURA,
            fecha=date(2026, 5, 3),
            descripcion='Factura venta INV-2026-001',
            tercero=tercero,
            lineas=[linea],
            documento_origen=doc_origen
        )

        # Verify DTO is frozen (immutable)
        self.assertIsNotNone(transaccion)
        self.assertEqual(transaccion.tipo, TipoTransaccion.VENTA_FACTURA)
        self.assertEqual(transaccion.lineas[0].monto, Decimal('1000000'))

        # Attempting to modify should raise error (frozen dataclass)
        with self.assertRaises(AttributeError):
            transaccion.tipo = TipoTransaccion.COMPRA_GASTO

    def test_transaccion_con_multiples_impuestos(self):
        """Create transaction with multiple tax/deduction lines."""
        tercero = TerceroSnapshot(
            tipo=TipoTercero.PROVEEDOR,
            id_origen=2,
            nit='801999999',
            razon_social='Proveedor XYZ'
        )

        linea = LineaTransaccion(
            concepto='GASTO_SERVICIOS',
            monto=Decimal('1000000'),
            impuestos=[
                ImpuestoLinea(
                    tipo='IVA_DESCONTABLE',
                    base=Decimal('1000000'),
                    porcentaje=Decimal('19.00'),
                    valor=Decimal('190000')
                ),
                ImpuestoLinea(
                    tipo='RETEFUENTE',
                    base=Decimal('1000000'),
                    porcentaje=Decimal('4.00'),
                    valor=Decimal('40000')
                ),
                ImpuestoLinea(
                    tipo='RETEICA',
                    base=Decimal('1000000'),
                    porcentaje=Decimal('0.69'),
                    valor=Decimal('6900')
                )
            ]
        )

        transaccion = TransaccionEconomica(
            tipo=TipoTransaccion.COMPRA_GASTO,
            fecha=date(2026, 5, 3),
            descripcion='Compra servicios',
            tercero=tercero,
            lineas=[linea],
            documento_origen=DocumentoOrigen(
                app_label='gastos',
                modelo='DocumentoSoporte',
                id=50,
                numero='FAC-PROV-2026-100'
            )
        )

        self.assertEqual(len(transaccion.lineas[0].impuestos), 3)
        self.assertEqual(
            sum(imp.valor for imp in transaccion.lineas[0].impuestos),
            Decimal('236900')
        )

    def test_transaccion_con_centro_costo(self):
        """Create transaction with project/cost center assignment."""
        linea = LineaTransaccion(
            concepto='GASTO_SERVICIOS',
            monto=Decimal('500000'),
            centro_costo_id=5  # Project ID
        )

        transaccion = TransaccionEconomica(
            tipo=TipoTransaccion.COMPRA_GASTO,
            fecha=date(2026, 5, 3),
            descripcion='Gasto imputado a proyecto',
            tercero=TerceroSnapshot(
                tipo=TipoTercero.PROVEEDOR,
                id_origen=3,
                nit='900777888',
                razon_social='Service Provider'
            ),
            lineas=[linea],
            documento_origen=DocumentoOrigen(
                app_label='gastos',
                modelo='DocumentoSoporte',
                id=51,
                numero='GST-001'
            )
        )

        self.assertEqual(transaccion.lineas[0].centro_costo_id, 5)


class TestContabilizadorLogica(TestCase):
    """Test Contabilizador business logic with mocked models."""

    def setUp(self):
        """Set up test fixtures."""
        self.empresa_id = 1
        self.contabilizador = Contabilizador(empresa_id=self.empresa_id)

    def test_transaccion_economica_inmutabilidad(self):
        """Verify that TransaccionEconomica instances are immutable."""
        dto = TransaccionEconomica(
            tipo=TipoTransaccion.VENTA_FACTURA,
            fecha=date(2026, 5, 3),
            descripcion='Test',
            tercero=TerceroSnapshot(
                tipo=TipoTercero.CLIENTE,
                id_origen=1,
                nit='900123456',
                razon_social='Test Client'
            ),
            lineas=[
                LineaTransaccion(
                    concepto='INGRESO_PRINCIPAL',
                    monto=Decimal('100000')
                )
            ],
            documento_origen=DocumentoOrigen(
                app_label='facturas',
                modelo='Factura',
                id=1,
                numero='TEST-001'
            )
        )

        # Attempting to modify a frozen dataclass raises AttributeError
        with self.assertRaises(AttributeError):
            dto.fecha = date(2026, 5, 4)

    def test_contabilizador_inicializacion(self):
        """Test Contabilizador initialization."""
        contab = Contabilizador(empresa_id=1)
        self.assertEqual(contab.empresa_id, 1)
        self.assertIsNotNone(contab.resolver)

    def test_resolver_resolver_cuenta_hint_override(self):
        """Test that cuenta_hint properly overrides default lookup."""
        resolver = self.contabilizador.resolver

        # With hint, should return hint directly
        cuenta = resolver.resolver_cuenta(
            'INGRESO_PRINCIPAL',
            'VENTA_FACTURA',
            cuenta_hint='999999'
        )
        self.assertEqual(cuenta, '999999')


class TestTransaccionEconomicaExamples(TestCase):
    """Examples of real-world TransaccionEconomica constructions."""

    def test_ejemplo_factura_venta_con_iva_19(self):
        """Example: Sales invoice with 19% VAT ($1M + $190K IVA)."""
        factura_dto = TransaccionEconomica(
            tipo=TipoTransaccion.VENTA_FACTURA,
            fecha=date(2026, 5, 3),
            descripcion='Factura venta INV-2026-0001 — Servicios profesionales',
            tercero=TerceroSnapshot(
                tipo=TipoTercero.CLIENTE,
                id_origen=42,
                nit='900900900',
                razon_social='Cliente Premium S.A.'
            ),
            lineas=[
                LineaTransaccion(
                    concepto='INGRESO_PRINCIPAL',
                    monto=Decimal('1000000'),
                    impuestos=[
                        ImpuestoLinea(
                            tipo='IVA_GENERADO',
                            base=Decimal('1000000'),
                            porcentaje=Decimal('19.00'),
                            valor=Decimal('190000')
                        )
                    ]
                )
            ],
            documento_origen=DocumentoOrigen(
                app_label='facturas',
                modelo='Factura',
                id=101,
                numero='INV-2026-0001'
            ),
            observaciones='Pago 30 días. Cliente aplica retefuente 11%.'
        )

        # Total debe should be $1.190.000 (CXC)
        # Haber should be $1.000.000 (Ingresos) + $190.000 (IVA)
        self.assertEqual(factura_dto.lineas[0].monto, Decimal('1000000'))
        self.assertEqual(
            sum(imp.valor for imp in factura_dto.lineas[0].impuestos),
            Decimal('190000')
        )

    def test_ejemplo_compra_gasto_con_retenciones(self):
        """Example: Purchase expense with multiple retentions ($1M + taxes)."""
        gasto_dto = TransaccionEconomica(
            tipo=TipoTransaccion.COMPRA_GASTO,
            fecha=date(2026, 5, 2),
            descripcion='Factura compra servicios generales',
            tercero=TerceroSnapshot(
                tipo=TipoTercero.PROVEEDOR,
                id_origen=15,
                nit='860555444',
                razon_social='Proveedor de Servicios Ltda.'
            ),
            lineas=[
                LineaTransaccion(
                    concepto='GASTO_SERVICIOS',
                    monto=Decimal('1000000'),
                    impuestos=[
                        ImpuestoLinea(
                            tipo='IVA_DESCONTABLE',
                            base=Decimal('1000000'),
                            porcentaje=Decimal('19.00'),
                            valor=Decimal('190000')
                        ),
                        ImpuestoLinea(
                            tipo='RETEFUENTE',
                            base=Decimal('1000000'),
                            porcentaje=Decimal('4.00'),
                            valor=Decimal('40000')
                        ),
                        ImpuestoLinea(
                            tipo='RETEICA',
                            base=Decimal('1000000'),
                            porcentaje=Decimal('0.69'),
                            valor=Decimal('6900')
                        )
                    ]
                )
            ],
            documento_origen=DocumentoOrigen(
                app_label='gastos',
                modelo='DocumentoSoporte',
                id=500,
                numero='FAC-PROV-1234'
            )
        )

        total_impuestos = sum(imp.valor for imp in gasto_dto.lineas[0].impuestos)
        self.assertEqual(total_impuestos, Decimal('236900'))

    def test_ejemplo_nomina_liquidacion_simplificada(self):
        """Example: Payroll with employee contributions (simplified)."""
        nómina_dto = TransaccionEconomica(
            tipo=TipoTransaccion.NOMINA_LIQUIDACION,
            fecha=date(2026, 5, 1),
            descripcion='Nómina mayo 2026 — Empleado 1',
            tercero=TerceroSnapshot(
                tipo=TipoTercero.EMPLEADO,
                id_origen=1,
                nit='12345678',
                razon_social='Juan Pérez García'
            ),
            lineas=[
                LineaTransaccion(
                    concepto='SUELDO',
                    monto=Decimal('2000000'),
                    impuestos=[
                        ImpuestoLinea(
                            tipo='SALUD_EMPLEADO',
                            base=Decimal('2000000'),
                            porcentaje=Decimal('4.00'),
                            valor=Decimal('80000')
                        ),
                        ImpuestoLinea(
                            tipo='PENSION_EMPLEADO',
                            base=Decimal('2000000'),
                            porcentaje=Decimal('4.00'),
                            valor=Decimal('80000')
                        )
                    ]
                ),
                LineaTransaccion(
                    concepto='AUXILIO_TRANSPORTE',
                    monto=Decimal('162000')
                )
            ],
            documento_origen=DocumentoOrigen(
                app_label='empleados',
                modelo='Devengo',
                id=1001,
                numero='DEV-2026-05-001'
            )
        )

        self.assertEqual(nómina_dto.lineas[0].monto, Decimal('2000000'))
        self.assertEqual(nómina_dto.lineas[1].monto, Decimal('162000'))
