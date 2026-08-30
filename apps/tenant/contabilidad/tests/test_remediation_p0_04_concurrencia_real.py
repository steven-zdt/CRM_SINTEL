"""
REM P0-04 (docs/remediation/REM-P0-04.md, docs/remediation/P0_04_NUMBERING.md):
prueba de concurrencia REAL con conexiones/threads distintos -- cierra el gap
admitido explicitamente en la pasada anterior (test_remediation_p0_04_
numeracion_comprobante.py solo probaba llamadas secuenciales en el mismo
proceso/conexion, sin harness de concurrencia real).

Usa pytest.mark.django_db(transaction=True) (no TestCase con rollback
implicito) para que los datos de setup esten realmente COMMITEADOS y
visibles desde otras conexiones -- requisito para que select_for_update()
bloquee de verdad entre threads. Mismo patron ya establecido en
apps/tenant/proveedores/tests/test_idempotence_v2614.py (tenant fixture
module-scoped + schema_context + TenantClient), reutilizado aqui en vez de
inventar un harness nuevo.

Cada thread de Python obtiene su propia conexion de BD (django.db.connection
es thread-local) -- schema_context() dentro del thread fija el search_path
de ESA conexion. Se cierra la conexion explicitamente al final de cada
thread para no dejarla abierta tras el test.
"""
import threading

import pytest
from django_tenants.utils import get_public_schema_name, schema_context

from apps.public.tenants.models import Client as TenantModel
from apps.public.tenants.models import Domain
from apps.tenant.contabilidad.models import TipoComprobante
from apps.tenant.empresa.models import Empresa


def _dns_host(schema_name):
    return f"{schema_name.replace('_', '-')}.sintel.net.co"


@pytest.fixture(scope="module")
def tenant(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock(), schema_context(get_public_schema_name()):
        schema_name = "test_p0_04_concurrencia_01"
        tenant = TenantModel.objects.filter(schema_name=schema_name).only('id', 'schema_name').first()
        if not tenant:
            tenant = TenantModel(schema_name=schema_name, nombre='Test P0-04 Concurrencia', is_active=True)
            tenant.save()
        Domain.objects.get_or_create(
            domain=_dns_host(schema_name),
            defaults={'tenant': tenant, 'is_primary': True},
        )
        return TenantModel.objects.only('id', 'schema_name').get(pk=tenant.pk)


def _get_or_create_empresa():
    empresa = Empresa.objects.only('id', 'razon_social', 'nit').first()
    if empresa:
        return empresa
    return Empresa.objects.create(
        razon_social='EMPRESA TEST P0-04 CONCURRENCIA S.A.S.',
        nit='901234599',
        direccion='Calle Falsa 123',
    )


def _crear_tipo_comprobante(tenant, codigo):
    with schema_context(tenant.schema_name):
        empresa = _get_or_create_empresa()
        tc = TipoComprobante.objects.create(
            empresa=empresa, codigo=codigo, nombre=f'Comprobante {codigo}',
            prefijo=f'{codigo[:4]}-', consecutivo_actual=1,
        )
        return tc.pk, empresa.id


def _generar_numero_en_thread(tenant_schema, tc_pk, resultados, errores, lock):
    """Ejecuta obtener_siguiente_numero() en la conexion propia de este thread."""
    from django.db import connection
    try:
        with schema_context(tenant_schema):
            obj = TipoComprobante.objects.get(pk=tc_pk)
            numero = obj.obtener_siguiente_numero()
            with lock:
                resultados.append(numero)
    except Exception as exc:  # noqa: BLE001 -- se reporta, no se silencia
        with lock:
            errores.append(exc)
    finally:
        connection.close()


def _correr_concurrencia(tenant, codigo, n_threads):
    tc_pk, empresa_id = _crear_tipo_comprobante(tenant, codigo)

    resultados = []
    errores = []
    lock = threading.Lock()
    threads = [
        threading.Thread(
            target=_generar_numero_en_thread,
            args=(tenant.schema_name, tc_pk, resultados, errores, lock),
        )
        for _ in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    return tc_pk, resultados, errores


@pytest.mark.django_db(transaction=True)
class TestConcurrenciaRealNumeracionP0_04:
    """
    P0-04-D: simula 2 y 10 usuarios generando comprobantes simultaneos con
    conexiones/threads REALES (no llamadas secuenciales en el mismo
    proceso). Valida: numeros unicos, secuencia sin huecos, ausencia de
    deadlock, ausencia de duplicados -- exactamente lo que pide la mision.
    """

    def test_dos_usuarios_concurrentes_numeros_unicos_sin_deadlock(self, tenant):
        tc_pk, resultados, errores = _correr_concurrencia(tenant, 'DOS01', n_threads=2)

        assert errores == [], f"No debe haber excepciones/deadlocks: {errores}"
        assert len(resultados) == 2, "Los 2 threads deben completar"
        assert len(set(resultados)) == 2, f"Los 2 numeros deben ser unicos: {resultados}"
        assert set(resultados) == {'DOS0-00001', 'DOS0-00002'}, resultados

        with schema_context(tenant.schema_name):
            tc = TipoComprobante.objects.get(pk=tc_pk)
            assert tc.consecutivo_actual == 3, (
                "Consecutivo final debe ser inicial(1) + n_threads(2), sin huecos ni duplicados"
            )

    def test_diez_usuarios_concurrentes_numeros_unicos_sin_deadlock(self, tenant):
        tc_pk, resultados, errores = _correr_concurrencia(tenant, 'DIEZ1', n_threads=10)

        assert errores == [], f"No debe haber excepciones/deadlocks: {errores}"
        assert len(resultados) == 10, "Los 10 threads deben completar"
        assert len(set(resultados)) == 10, f"Los 10 numeros deben ser unicos: {resultados}"
        assert set(resultados) == {f'DIEZ-{i:05d}' for i in range(1, 11)}, resultados

        with schema_context(tenant.schema_name):
            tc = TipoComprobante.objects.get(pk=tc_pk)
            assert tc.consecutivo_actual == 11, (
                "Consecutivo final debe ser inicial(1) + n_threads(10), sin huecos ni duplicados"
            )
