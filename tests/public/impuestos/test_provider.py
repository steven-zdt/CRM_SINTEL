"""
Pruebas de humo para el servicio provider de normativa DIAN.

⚠️ POLÍTICA SSoT: Verifica que el provider funciona correctamente
y que el caché se invalida después de cambios.
"""
from django.test import TestCase
from apps.public.impuestos.models import (
    ContribuyenteTipo,
    RegimenRenta,
    ResponsabilidadRUT,
    PerfilTributario,
)
from apps.public.impuestos.services.provider import (
    get_regimen_renta_by_codigo,
    get_responsabilidades_rut,
    get_perfil_tributario,
    clear_impuestos_cache,
    ImpuestosNotFoundError,
)


class ImpuestosProviderTestCase(TestCase):
    """Pruebas para el servicio provider de normativa DIAN."""

    def setUp(self):
        """Configurar datos de prueba."""
        # Limpiar caché antes de cada prueba
        clear_impuestos_cache()
        
        # Crear tipo de contribuyente
        self.contribuyente_tipo = ContribuyenteTipo.objects.create(
            nombre="Persona Jurídica - Gran Contribuyente",
            clase=ContribuyenteTipo.CLASE_PJ,
            segmento_dian=ContribuyenteTipo.SEG_GRAN,
            activo=True
        )
        
        # Crear régimen de renta
        self.regimen_renta = RegimenRenta.objects.create(
            codigo=RegimenRenta.ORD,
            nombre="Régimen Ordinario",
            tarifa_base_pj=32.00,
            requiere_facturacion_electronica=True,
            aplica_retenciones=True,
            activo=True
        )
        
        # Crear responsabilidades RUT
        self.responsabilidad_48 = ResponsabilidadRUT.objects.create(
            codigo="48",
            nombre="Responsable de IVA",
            es_responsable_iva=True,
            es_facturador_electronico=True,
            activo=True
        )
        
        self.responsabilidad_49 = ResponsabilidadRUT.objects.create(
            codigo="49",
            nombre="No responsable de IVA",
            es_no_responsable_iva=True,
            activo=True
        )
        
        # Crear perfil tributario
        self.perfil_tributario = PerfilTributario.objects.create(
            nombre="PJ - Gran Contribuyente - Ordinario",
            tipo_contribuyente=self.contribuyente_tipo,
            regimen_renta=self.regimen_renta,
            activo=True
        )
        self.perfil_tributario.responsabilidades.add(self.responsabilidad_48)

    def test_get_regimen_renta_by_codigo(self):
        """Verifica que get_regimen_renta_by_codigo retorna datos correctos."""
        regimen = get_regimen_renta_by_codigo(RegimenRenta.ORD)
        
        self.assertEqual(regimen['codigo'], RegimenRenta.ORD)
        self.assertEqual(regimen['nombre'], "Régimen Ordinario")
        self.assertTrue(regimen['requiere_facturacion_electronica'])
        self.assertTrue(regimen['aplica_retenciones'])
        self.assertEqual(regimen['tarifa_base_pj'], 32.00)

    def test_get_regimen_renta_by_codigo_not_found(self):
        """Verifica que lanza ImpuestosNotFoundError si el régimen no existe."""
        with self.assertRaises(ImpuestosNotFoundError):
            get_regimen_renta_by_codigo('INEXISTENTE')

    def test_get_regimen_renta_by_codigo_inactive(self):
        """Verifica que no retorna regímenes inactivos."""
        self.regimen_renta.activo = False
        self.regimen_renta.save()
        clear_impuestos_cache()
        
        with self.assertRaises(ImpuestosNotFoundError):
            get_regimen_renta_by_codigo(RegimenRenta.ORD)

    def test_get_responsabilidades_rut_all(self):
        """Verifica que get_responsabilidades_rut retorna todas las activas."""
        responsabilidades = get_responsabilidades_rut()
        
        self.assertEqual(len(responsabilidades), 2)
        codigos = [r['codigo'] for r in responsabilidades]
        self.assertIn('48', codigos)
        self.assertIn('49', codigos)

    def test_get_responsabilidades_rut_filtered(self):
        """Verifica que get_responsabilidades_rut filtra por códigos."""
        responsabilidades = get_responsabilidades_rut(['48'])
        
        self.assertEqual(len(responsabilidades), 1)
        self.assertEqual(responsabilidades[0]['codigo'], '48')
        self.assertTrue(responsabilidades[0]['es_responsable_iva'])

    def test_get_responsabilidades_rut_not_found(self):
        """Verifica que lanza ImpuestosNotFoundError si no se encuentran códigos."""
        with self.assertRaises(ImpuestosNotFoundError):
            get_responsabilidades_rut(['999'])

    def test_get_perfil_tributario(self):
        """Verifica que get_perfil_tributario retorna datos correctos."""
        perfil = get_perfil_tributario("PJ - Gran Contribuyente - Ordinario")
        
        self.assertEqual(perfil['nombre'], "PJ - Gran Contribuyente - Ordinario")
        self.assertEqual(perfil['tipo_contribuyente']['clase'], ContribuyenteTipo.CLASE_PJ)
        self.assertEqual(perfil['regimen_renta']['codigo'], RegimenRenta.ORD)
        self.assertIn('48', perfil['responsabilidades'])

    def test_get_perfil_tributario_not_found(self):
        """Verifica que lanza ImpuestosNotFoundError si el perfil no existe."""
        with self.assertRaises(ImpuestosNotFoundError):
            get_perfil_tributario('Perfil Inexistente')

    def test_get_perfil_tributario_inactive(self):
        """Verifica que no retorna perfiles inactivos."""
        self.perfil_tributario.activo = False
        self.perfil_tributario.save()
        clear_impuestos_cache()
        
        with self.assertRaises(ImpuestosNotFoundError):
            get_perfil_tributario("PJ - Gran Contribuyente - Ordinario")

    def test_cache_invalidation(self):
        """Verifica que el caché se invalida correctamente."""
        # Primera llamada (popula caché)
        regimen1 = get_regimen_renta_by_codigo(RegimenRenta.ORD)
        
        # Modificar en BD
        self.regimen_renta.nombre = "Régimen Ordinario Modificado"
        self.regimen_renta.save()
        
        # Segunda llamada (debería usar caché, retorna valor antiguo)
        regimen2 = get_regimen_renta_by_codigo(RegimenRenta.ORD)
        self.assertEqual(regimen2['nombre'], "Régimen Ordinario")  # Valor en caché
        
        # Invalidar caché
        clear_impuestos_cache()
        
        # Tercera llamada (debería consultar BD, retorna valor nuevo)
        regimen3 = get_regimen_renta_by_codigo(RegimenRenta.ORD)
        self.assertEqual(regimen3['nombre'], "Régimen Ordinario Modificado")  # Valor actualizado
