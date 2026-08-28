"""
REM P0-04 (docs/remediation/REM-P0-04.md): TipoComprobante.obtener_siguiente_
numero() era el unico generador de numeracion del sistema sin
select_for_update() -- corregido para re-obtener la fila bajo lock dentro
del propio metodo.

Nota de alcance honesta: no existe en todo el repo ningun patron previo de
test con threads reales / conexiones DB concurrentes (grep confirmado, cero
resultados de `threading`/`ThreadPoolExecutor` en apps/tenant/**/tests/).
TenantTestCase (django-tenants) con su manejo de schema-por-tenant hace que
un harness de concurrencia real con multiples conexiones sea un proyecto
aparte, no una correccion quirurgica de 15 minutos. Se verifica aqui la
correccion funcional real (secuencia sin saltos ni duplicados) y que el
metodo efectivamente usa select_for_update() -- la misma barra de evidencia
que el resto de generadores de numeracion de este proyecto (cotizaciones/
compras/ventas/empleados) ya aceptan sin tests de concurrencia real propios.
"""
from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.contabilidad.models import TipoComprobante
from apps.tenant.empresa.models import Empresa


class TipoComprobanteNumeracionP0_04Tests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Empresa P0-04', nit='900000794',
        )
        self.tipo = TipoComprobante.objects.create(
            empresa=self.empresa, codigo='CP4', nombre='Comprobante P0-04', prefijo='CP4',
            consecutivo_actual=1,
        )

    def test_numeros_secuenciales_sin_saltos_ni_duplicados(self):
        numeros = [self.tipo.obtener_siguiente_numero() for _ in range(10)]
        self.assertEqual(len(numeros), len(set(numeros)), "Se generaron numeros duplicados")
        esperados = [f"CP4{str(i).zfill(5)}" for i in range(1, 11)]
        self.assertEqual(numeros, esperados)

    def test_persiste_el_incremento_en_bd_no_solo_en_memoria(self):
        self.tipo.obtener_siguiente_numero()
        self.tipo.obtener_siguiente_numero()
        recargado = TipoComprobante.objects.get(pk=self.tipo.pk)
        self.assertEqual(recargado.consecutivo_actual, 3)

    def test_usa_select_for_update(self):
        """Confirma que la correccion real (select_for_update) esta en el
        codigo, no solo que el resultado final coincide por casualidad."""
        import inspect
        codigo_fuente = inspect.getsource(TipoComprobante.obtener_siguiente_numero)
        self.assertIn('select_for_update', codigo_fuente)
