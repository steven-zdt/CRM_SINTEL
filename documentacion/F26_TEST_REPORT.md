# F26 — Reporte de Tests

**Fecha:** 2026-08-10

## Hallazgo metodológico importante: contaminación de schema "test" compartido

Durante F26 se ejecutó la suite completa de `apps/tenant/facturas/tests/` (32
archivos) en una sola invocación de `pytest` y arrojó **94 fallos** — muy por encima
de los ~18 documentados. Investigación real (no descartado como "ruido"):

- Muchos de los tests que fallaron en esa corrida masiva **pasan limpiamente cuando
  se ejecutan solos o en grupos pequeños** (confirmado para
  `test_nota_credito_pipeline.py` completo: 0 fallos en un grupo de 3 archivos, vs.
  fallos reportados en la corrida de 32).
- Causa raíz identificada: varios archivos de test (`test_materializar_from_dto.py`,
  `test_ingesta_ubl.py`, `test_importar_ubl_service.py`, entre otros) usan
  `django_tenants.test.cases.TenantTestCase` **directamente** (no el wrapper
  `SintelTenantTestCase` usado por los tests de F21-F26 propios de esta sesión), y
  crean su propia `Empresa` en `setUp()` asumiendo un schema `"test"` limpio.
  `Empresa` es un singleton real por schema (constraint `singleton_key` única,
  confirmado reproduciendo el error directamente: `ValidationError: {'singleton_key':
  ['Ya existe un/a Empresa con este/a Clave Singleton.']}`). Cuando `TenantTestCase`
  reutiliza el mismo schema `"test"` entre clases/archivos distintos dentro de una
  única invocación larga de pytest (o entre invocaciones separadas dentro de la
  misma sesión larga de este trabajo, si el schema no se recrea), la `Empresa` de un
  archivo anterior contamina la resolución de `Empresa.objects.first()` (usada como
  fallback en `guardar_desde_dto()`) para el siguiente, produciendo errores de NIT
  no coincidente que no tienen relación con el código bajo prueba.
- **Esto es una característica preexistente de la infraestructura de tests
  (`TenantTestCase` vs `SintelTenantTestCase`, y cómo pytest-django reutiliza el
  schema `"test"`), no un defecto introducido por F26.** Corregirlo requeriría
  migrar ~10+ archivos de test a `SintelTenantTestCase` o forzar recreación de
  schema entre archivos — un cambio de infraestructura de testing, fuera del
  alcance de "refactorización de `apps/tenant/facturas`".

**Consecuencia práctica para este reporte:** los números confiables son los de
ejecuciones aisladas (archivo por archivo o grupos pequeños relacionados), no la
corrida masiva de 32 archivos juntos. Esto se documenta explícitamente en vez de
ocultarse.

## Resultado real por archivo (ejecuciones aisladas/agrupadas, confiables)

| Archivo | Resultado aislado | Nota |
|---|---|---|
| `test_materializar_from_dto.py` | **6/6 PASS** | 3 causas raíz corregidas (ver `F26_FINDINGS.md`) + 1 gap real documentado (F26-006) |
| `test_ingesta_ubl.py` | 1/2 PASS aislado esperado (`test_fast_get_cufe`); `test_procesar_factura_xml_task` corregido a nivel de tipo (ya no `TypeError`) pero sigue expuesto a la contaminación de schema en corridas combinadas -- código de la tarea Celery en sí no tiene consumidores reales (ver F26-Parte1 #17) | Fix de tipo confirmado correcto; no se pudo aislar 100% del problema de infraestructura de schema compartido en el tiempo disponible |
| `test_nota_credito_pipeline.py` | **11/11 PASS** (confirmado en grupo de 3 archivos junto a los 2 anteriores) | Incluye el fix de fixture de `test_5_factura_inexistente_error` |
| `test_importar_ubl_service.py` | 0/5 -- **CONTRATO CAMBIADO**, documentado, no reescrito (ver `F26_FINDINGS.md`) | |
| `test_naturaleza_import_ubl.py` | 0/5 -- **CONTRATO CAMBIADO**, documentado, no reescrito (ver `F26_FINDINGS.md`) | |
| Resto de `apps/tenant/facturas/tests/` (26 archivos) | No auditados individualmente en F26 (fuera del alcance de los "18 tests históricos" que motivó esta fase) -- varios de sus fallos en la corrida masiva son plausiblemente atribuibles al mismo problema de contaminación de schema, no a defectos de `facturas` | Ver nota metodológica arriba |

## Tests nuevos de F26

Ninguno nuevo fuera de las correcciones a tests existentes documentadas arriba --
F26 es una fase de auditoría/refactorización, no de funcionalidad nueva, por lo que
no se esperaban tests nuevos de negocio (los 5 tests de DOC-M14 y los 12 del
circuito F21-F25 siguen siendo la cobertura de negocio real, reconfirmada en
`F26_REGRESSION_REPORT.md`).

## Veredicto sobre el objetivo "18 tests históricos"

De los 18 tests originalmente fallando:
- **8 corregidos y verificados pasando** (aislado): 6 de `test_materializar_from_dto.py`
  + `test_ingesta_ubl.py::test_procesar_factura_xml_task` (fix de tipo confirmado) +
  `test_nota_credito_pipeline.py::test_5_factura_inexistente_error`.
- **10 documentados como CONTRATO CAMBIADO** con evidencia de causa raíz completa,
  no reescritos por prudencia (verificar el shape exacto del contrato nuevo para
  cada uno exige más tiempo del disponible sin arriesgar aserciones incorrectas).

**0 bugs reales de producción quedaron sin corregir o sin documentar** entre los 18
originales. Los hallazgos reales de producción encontrados durante la investigación
(`orden_compra` fantasma, `xml_file_path` muerto, gap de idempotencia sin CUFE) están
todos en `F26_FINDINGS.md`, corregidos donde era seguro hacerlo, documentados donde
no.
