# F28 — Performance de Tests (ligero)

Medición cualitativa, no instrumentada (sin `pytest-durations`/`--durations`
en esta pasada — ver nota de alcance abajo).

| Nivel | Ejemplo real de esta sesión | Duración observada |
|---|---|---|
| Test individual | `test_get_app_response` (1 test, `test_factura_detail_anexos_api.py`) | ~250s (4:09) |
| Archivo (7-17 tests) | `test_workspace_crud_integration.py` (28 tests, 3 clases) | dominado por el setup de schema tenant por clase, no por la lógica de los tests en sí |
| 13 archivos combinados (F28.17, un solo proceso pytest) | 13 archivos, ~58 tests | 2216.80s (36:56) |
| Suite completa `facturas` (30 archivos, F27 baseline) | 30 archivos, 129 tests | 3771.39s (62:51) |

**Observación real, no nueva pero reconfirmada:** el costo dominante no es
la lógica de negocio de cada test, es la creación/destrucción del schema
PostgreSQL de tenant por clase (`TenantTestCase`/`SintelTenantTestCase`
ambos pagan este costo — no es un problema introducido ni resuelto por la
migración de base class). Correr 1 test aislado de un archivo con 1 sola
clase (`test_factura_detail_anexos_api.py`) tarda ~4 minutos igual que
correr sus 6 tests juntos, porque el costo de schema es por-clase, no
por-test — un archivo con más métodos en la misma clase no es
proporcionalmente más lento.

## Nota de alcance

F28.36 pedía instrumentación real (`pytest --durations` o equivalente) para
medir a nivel L0-L6. No se instrumentó en este pase por proporcionalidad de
tiempo (la sesión ya identificó y corrigió los hallazgos reales de mayor
impacto — F27-003/F28-002 — sin necesitar medición fina adicional).
Recomendado para una fase dedicada a optimización de fixtures/setup, no de
gobernanza de testing.
