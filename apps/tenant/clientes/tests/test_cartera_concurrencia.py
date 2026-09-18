"""
DEUDA-C06 "Clientes + Cartera" (seccion 51/66 de la mision, 2026-09-11):
test de concurrencia REAL para `CarteraBusinessService.registrar_abono()`
usando `@pytest.mark.django_db(transaction=True)` + threads reales -- un
test envuelto en la transaccion automatica de `TestCase`/`django_db`
normal (sin `transaction=True`) NO detectaria un `select_for_update()` mal
usado, porque todas las "conexiones" verian los mismos datos no
confirmados de la misma transaccion externa (Django docs, "Testing
transactions").

Cada hilo necesita su PROPIA conexion a BD (Django asigna una por hilo) y
debe fijar el schema del tenant explicitamente en ese hilo -- `search_path`
es una propiedad de la conexion, no algo que se herede entre hilos.

Escenario: Cartera con saldo=100.000. Dos hilos intentan abonar 60.000
cada uno simultaneamente. Sin `select_for_update()`, ambos podrian leer
saldo=100.000 y "pasar" la validacion de sobrepago, dejando el sistema en
un estado imposible (pagado > total). Con el lock (ya implementado desde
antes de esta mision), el segundo hilo debe esperar a que el primero
confirme, releer el saldo YA actualizado (40.000) y ser rechazado por
sobrepago (60.000 > 40.000) -- exactamente uno de los dos abonos aplica.
"""
import threading

import pytest
from decimal import Decimal
from django.db import connection
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cartera, Cliente
from apps.tenant.clientes.services.business_service import CarteraBusinessService
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db(transaction=True)
def test_dos_abonos_concurrentes_solo_uno_aplica_sin_sobrepago(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cliente = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900555666", razon_social="Cliente Concurrencia",
            regimen_tributario="ORDINARIO", activo=True,
        )
        cartera = Cartera.objects.create(
            empresa=empresa, cliente=cliente, numero_factura="FE-CONC-1",
            fecha_emision="2026-06-01", fecha_vencimiento="2026-07-01",
            valor_total=Decimal("100000.00"),
        )
        cartera_uuid = cartera.uuid
        empresa_id = empresa.id

    resultados = {}
    barrera = threading.Barrier(2)

    def _abonar(nombre):
        try:
            with schema_context(tenant.schema_name):
                barrera.wait(timeout=5)  # maximiza la probabilidad de solape real
                CarteraBusinessService.registrar_abono(
                    empresa_id=empresa_id, cartera_uuid=cartera_uuid, monto=Decimal("60000.00"),
                )
                resultados[nombre] = "OK"
        except Exception as exc:
            resultados[nombre] = f"RECHAZADO: {exc}"
        finally:
            connection.close()

    hilo_a = threading.Thread(target=_abonar, args=("A",))
    hilo_b = threading.Thread(target=_abonar, args=("B",))
    hilo_a.start()
    hilo_b.start()
    hilo_a.join(timeout=10)
    hilo_b.join(timeout=10)

    # Exactamente uno de los dos abonos debio aplicarse -- el otro debe
    # haber sido rechazado por sobrepago (select_for_update() serializo el
    # acceso; sin el lock, ambos podrian haber "pasado" con datos obsoletos).
    exitosos = [n for n, r in resultados.items() if r == "OK"]
    rechazados = [n for n, r in resultados.items() if r.startswith("RECHAZADO")]
    assert len(exitosos) == 1, f"Se esperaba exactamente 1 abono exitoso, resultados: {resultados}"
    assert len(rechazados) == 1, f"Se esperaba exactamente 1 abono rechazado, resultados: {resultados}"

    with schema_context(tenant.schema_name):
        cartera_final = Cartera.objects.get(uuid=cartera_uuid)
        # Invariante critica: el saldo NUNCA debe quedar negativo ni el
        # pagado exceder el total -- esto es lo que select_for_update()
        # protege realmente.
        assert cartera_final.valor_pagado == Decimal("60000.00")
        assert cartera_final.saldo == Decimal("40000.00")
        assert cartera_final.saldo >= Decimal("0.00")
        assert cartera_final.valor_pagado <= cartera_final.valor_total
