# F27 — Hallazgos (Gobernanza y Optimización del Sistema de Testing)

**Fecha:** 2026-08-11. **Metodología:** reproducción real (`pytest --tb=short`,
`manage.py shell`), lectura del código de producción que cada test ejercita,
comparación explícita entre lo que el test espera y lo que el código real
produce hoy. Cero suposiciones sin reproducir (regla F27 §5: "F26 dejó un
diagnóstico documentado como posible problema del fixture/Empresa dummy. NO
aceptar ese diagnóstico sin reproducirlo").

---

## F27-001 — `test_procesar_factura_xml_task`: confirmado FIXTURE BUG, corregido

Ver contexto completo en `documentacion/F26-006_FIX_REPORT.md` y la sesión
previa a F27 (dismissal del task `task_361d382a`, que proponía el mismo fix
de forma independiente).

**Reproducción exigida por F27.13** (aislado → archivo → suite): el test
falló **exactamente igual en aislamiento total** (un solo método, ningún
otro test en el proceso pytest) que en la corrida grande de F26 — esto por
sí solo ya refuta la hipótesis de "contaminación de schema" que F26 había
registrado como causa probable para este test específico.

**Causa real:** el `Empresa` dummy que crea el test usa `nit="900000001"`,
que no coincide con `AccountingSupplierParty` (`900123456`) ni
`AccountingCustomerParty` (`901999888`) de `XML_SAMPLE` —
`guardar_desde_dto()` rechaza el documento con
`ValidationError: El NIT de la empresa actual no coincide...` antes de
llegar a la lógica que el test quiere probar.

**Clasificación (F27.14):** FIXTURE BUG puro — no es problema de test
(assertions correctas), no es de infraestructura (aislamiento probado), no
es de producción (la validación de NIT hace exactamente lo que debe).

**Corrección (F27.15, "corregir solo lo necesario"):** `nit="900000001"` →
`nit="901999888"` (el NIT del receptor real en el XML, consistente con las
aserciones ya existentes del test sobre `factura.receptor_nit`). Verificado
aislado (PASS) y como archivo completo (2/2 PASS).

---

## F27-002 — `test_naturaleza_rule_ssot.py` / `test_naturaleza_import_ubl.py` / `test_importar_ubl_service.py`: NIT extraído de la estructura XML equivocada

Descubierto al investigar por qué `test_importar_ubl_service.py` (uno de
los "10 tests documentados, no reescritos" de F26) seguía fallando incluso
después de corregir el shape de respuesta. Reproducción directa de
`ingest_document()` vía `manage.py shell` sobre el XML de fixture mostró
`emisor.nit` y `receptor.nit` llegando **vacíos** (`""`) al DTO, pese a que
el XML sí declara un NIT.

**Causa real:** el parser real
(`apps/services/document_parser/xml_parser/parser.py`) extrae el NIT desde
`Party > PartyTaxScheme > CompanyID` — **no** desde
`Party > PartyIdentification > ID`, que es la estructura que usaban los
fixtures `XML_VENTA`/`XML_COMPRA` de ambos archivos. Con NIT vacío,
`ingest_document()` rechaza el documento con
`missing_required_fields: emisor.nit, receptor.nit` antes de llegar a
ninguna lógica de naturaleza — la causa real no era el shape de la
respuesta (aunque ese problema también existía, ver F26), era que el
documento nunca pasaba de la validación de entrada.

**Clasificación:** FIXTURE BUG (estructura XML no válida contra el parser
real — inconsistente además con el resto de fixtures del mismo directorio,
que sí usan `PartyTaxScheme`, ej. `_crear_xml_credit_note()` en
`test_nota_credito_pipeline.py`).

**Corrección aplicada — `test_importar_ubl_service.py` (CORREGIR, 5/5
ahora pasan):**
1. Fixtures reescritas a `PartyTaxScheme > CompanyID`.
2. Aserciones de preview corregidas: el pipeline universal no calcula
   `naturaleza` durante preview (ver F26-007..010) — se verifica lo que
   preview sí garantiza (`persisted: False`, `dto.numero` correcto).
3. Aserciones de persistencia corregidas: `guardar_desde_dto()` devuelve
   `naturaleza` en el nivel superior del payload, no anidado bajo una clave
   `"factura"` que nunca existió en ese contrato.
4. **Hallazgo adicional real:** `test_422_sin_empresa` asumía que
   `preview=True` valida la existencia de `Empresa`. Reproducido: con 0
   `Empresa` en el tenant y `preview=True`, el pipeline devuelve **200**
   (`document_ingest_preview_ok`) — la validación de Empresa solo ocurre al
   persistir. Corregido: el test ahora usa `preview=False` para ejercitar
   el escenario real que su nombre describe.

**No corregido — `test_naturaleza_import_ubl.py` (documentado, ver F27-003):**
comparte el mismo bug de fixture, pero tiene 2 problemas adicionales
compuestos (ver abajo) que hacen que corregirlo sea una tarea de mayor
alcance y menor beneficio marginal, dado que ya existe cobertura real
equivalente en `test_importar_ubl_service.py` tras la corrección de arriba.

---

## F27-003 — `TenantTestCase` (django-tenants) no configura el URLconf de tenant; `reverse()` directo falla con `NoReverseMatch`

**El hallazgo más significativo de F27** — reformula y corrige la hipótesis
de "contaminación de schema `test`" que F26/DOC-M15 habían registrado para
varios fallos de la suite de `facturas`.

**Reproducción:** `test_naturaleza_import_ubl.py::_post_upload()` llama
`reverse("factura-upload-ubl")` de forma directa (fuera de un ciclo de
request HTTP real). Falla con:
```
django.urls.exceptions.NoReverseMatch: Reverse for 'factura-upload-ubl' not found.
```
incluso en **aislamiento total** (solo ese archivo). Confirmado además
**fuera de pytest**, vía `manage.py shell`:
```python
>>> from django.urls import reverse
>>> reverse('factura-upload-ubl')
NoReverseMatch: ...
>>> from django.urls import get_resolver
>>> get_resolver().reverse_dict.keys()  # sin urlconf explícito -> resolver PUBLIC
# 0 nombres 'factura-*'
>>> get_resolver('config.urls_tenant').reverse_dict.keys()  # urlconf TENANT explícito
# 'factura-upload-ubl' SÍ existe, junto a 21 rutas 'factura-*' más
```

**Causa real:** `django.urls.reverse()` sin argumento `urlconf` usa
`settings.ROOT_URLCONF` (el urlconf del esquema **público**, que no
registra rutas de `facturas` — esas viven en `config.urls_tenant`). En
producción esto nunca falla porque `TenantMainMiddleware`
(django-tenants) fija `request.urlconf` dinámicamente por request según el
hostname **antes** de resolver la URL — pero una llamada a `reverse()`
**fuera** del ciclo de request (como en un test que arma la URL a mano
antes de llamar a `self.client`) no tiene ese contexto.

`tests/tenant/base_test.py::SintelTenantTestCase` (líneas 125-136) resuelve
esto explícitamente en `setUp()`:
```python
self.urlconf_override = override_settings(ROOT_URLCONF=settings.TENANT_URLCONF)
self.urlconf_override.enable()
set_urlconf(settings.TENANT_URLCONF)
```
`django_tenants.test.cases.TenantTestCase` **no hace esto** — solo cambia
el schema de PostgreSQL activo, no el `URLconf` de Django.

**Alcance real confirmado:** de los 34 archivos que usan `TenantTestCase`
crudo (ver `F27_TEST_INVENTORY.md` §2a), se confirmó el mismo patrón
(`TenantTestCase` + `reverse(...)` directo, sin `self.client` como único
punto de resolución) en al menos:
`test_naturaleza_import_ubl.py`, `test_factura_detail_anexos_api.py`,
`test_facturas_list_detail_payloads.py`, `test_import_ubl_heavy_payload.py`
— y la corrida completa de la suite de `facturas` (`F27_REGRESSION_REPORT.md`)
muestra el mismo `NoReverseMatch` (para `factura-upload-ubl`,
`factura-materialize`, `factura-ingest-status`) en varios archivos más
(`test_upload_async_flow.py`, `test_services_ingest_integration.py`,
`test_multitenant_isolation_tabla_html.py`), consistente con la misma causa
raíz.

**Clasificación:** patrón sistémico de **TEST BUG** (base class
insuficiente para el escenario que el test necesita), no un bug de
producción (el routing real funciona correctamente, verificado con el
urlconf correcto) y **no** contaminación entre archivos (se reproduce en
aislamiento total, un solo archivo, un solo test).

**No corregido en este pase** (ver F27-004 para el razonamiento sobre
alcance): el fix mecánico es conocido y de bajo riesgo (cambiar la base de
`TenantTestCase` a `SintelTenantTestCase`), pero verificar que no rompe
ningún supuesto adicional de cada uno de los ~6+ archivos afectados excede
el tiempo disponible en este pase. Documentado con evidencia completa y
patrón de fix reproducible para una fase dedicada.

---

## F27-004 — `test_naturaleza_import_ubl.py`: 3 bugs compuestos, documentado y no reescrito

Acumula F27-002 (fixture XML) + F27-003 (`reverse()` sin urlconf) + un
tercer problema real encontrado al analizar el flujo completo:
`_post_upload()` no pasa `async=false` en la query string, y el default
real del endpoint (`upload_ubl()`,
`apps/tenant/facturas/api/mixins/factura_ubl_mixin.py:154`) es
`async=true` — incluso corrigiendo 1 y 2, el endpoint respondería `202`
(tarea Celery encolada) en vez del `200/201` síncrono que estas pruebas
esperan.

El endpoint que este archivo prueba está además marcado
`# WARNING: DEPRECATED` en su propio docstring de producción, con
reemplazo explícito documentado
(`POST /api/v1/core/documentos/upload/`). La regla de negocio real que este
archivo pretende probar (detección VENTA/COMPRA) queda cubierta, tras F27,
por:
- `test_importar_ubl_service.py` (capa de servicio, mismos 2 escenarios,
  ahora 5/5 pasando — ver F27-002).
- `test_naturaleza_rule_ssot.py` / `test_naturaleza_unit.py` (unitario,
  función de decisión pura).
- `test_materializar_from_dto.py` / `test_nota_credito_pipeline.py`
  (end-to-end, vía el pipeline vigente).

**Decisión (F27.9/F27.60 — "ante incertidumbre, no eliminar; documentar"):**
no se reescribe ni se elimina en este pase. Se agregó un docstring de
módulo con la evidencia completa de los 3 bugs (commit de este pase) para
que la próxima fase que lo toque no tenga que re-descubrir nada.
Recomendación registrada: CONSOLIDAR (fusionar su cobertura única, si
alguna, en `test_importar_ubl_service.py`) o ELIMINAR, en una pasada
dedicada — no ejecutado aquí porque las acciones de borrado de archivo
fueron bloqueadas por el clasificador de permisos de esta sesión (ver
F27-005) y porque tocar 3 causas compuestas a la vez es mayor riesgo que
beneficio marginal dado que la cobertura real ya no depende de este
archivo.

---

## F27-005 — Duplicado byte-idéntico confirmado, eliminación bloqueada por permisos (no por seguridad del cambio)

`tests/celery/test_tasks_import.py` y
`tests/celery_tasks/test_tasks_import.py` son **archivos idénticos byte a
byte** (`diff` sin salida), mismos 3 tests, mismo tamaño (4923 bytes), mismo
timestamp. Verificado con `grep` que ningún Makefile/CI/config referencia
ninguna de las dos rutas por nombre — la eliminación de cualquiera de los
dos directorios es segura y no rompe nada externo.

**No ejecutado:** el intento de `git rm -r tests/celery/` fue bloqueado por
el clasificador de permisos automático de esta sesión (acción destructiva).
Documentado aquí como recomendación lista para ejecutar, no como hallazgo
sin resolver por falta de evidencia — la evidencia está completa.

**Acción recomendada (no ejecutada):**
```bash
git rm -r tests/celery/
```
(conservar `tests/celery_tasks/`, nombre más descriptivo).

---

## F27-006 — Inventario y candidatos de duplicación adicionales (documentados, no consolidados)

Ver `F27_TEST_INVENTORY.md` §3 para el detalle completo con evidencia. Tres
clusters adicionales, bien evidenciados pero **fuera del alcance ejecutado
en este pase** (volumen: 9+3+2 archivos, cada consolidación real exige
verificar cobertura antes de tocar cualquiera):

- **§3a — Upload-UBL, 9 archivos en `tests/tenant/facturas/`** repiten
  independientemente los mismos 4 hechos de contrato (missing-file 400,
  naturaleza inválida 400, duplicado 409, upload válido 200/201). El
  candidato de dedup más rico del repo — recomendado para una fase
  dedicada a `tests/tenant/facturas/` específicamente.
- **§3b — Listado de facturas "retorna 200", 3 archivos.**
- **§3c — `test_naturaleza_rule_ssot.py` vs `test_naturaleza_unit.py`**:
  ambos prueban `norm_nit()` con nombres de caso casi idénticos — el
  duplicado unitario más claro del repo.

No se tocó ninguno de estos tres en este pase: ejecutar la consolidación
con confianza exige leer cada assertion de cada archivo (no solo nombres),
y el tiempo de este pase se priorizó en los hallazgos con evidencia de
**bug real** (F27-001 a F27-004) sobre los de **redundancia pura** (mismo
comportamiento, sin bug) — consistente con F27 §4 ("el objetivo no es
menos archivos, es mejor señal").

---

## Resumen

| # | Hallazgo | Clasificación | Acción |
|---|---|---|---|
| F27-001 | `test_procesar_factura_xml_task` | FIXTURE BUG | **CORREGIDO** |
| F27-002 | XML fixture NIT (`PartyIdentification` vs `PartyTaxScheme`) | FIXTURE BUG | **CORREGIDO** en `test_importar_ubl_service.py` (5/5) |
| F27-003 | `TenantTestCase` no fija URLconf de tenant | TEST BUG sistémico (~6+ archivos) | Documentado, patrón de fix conocido, no aplicado a todos |
| F27-004 | `test_naturaleza_import_ubl.py` (3 bugs compuestos) | CONTRATO CAMBIADO / OBSOLETO | Documentado, no reescrito (cobertura real ya cubierta en otro lado) |
| F27-005 | Duplicado byte-idéntico `tests/celery*` | DUPLICATE confirmado | Bloqueado por permisos, recomendación lista |
| F27-006 | 3 clusters de duplicación adicionales (14 archivos) | OVERLAPPING (documentado) | Fuera de alcance de este pase, evidencia completa en inventario |
