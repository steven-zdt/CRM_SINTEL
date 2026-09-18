# BANCOS PDF + APLICACIONES MÚLTIPLES — STATUS

Mission: BANCOS_PDF_APLICACIONES_01

Current Phase: PHASE-59 (release gate)
Overall Status: PASS_WITH_DEFERRED

- Fecha: 2026-09-17
- Rama: feat/onboarding-cookie
- Entorno: Docker (web container), Python 3.12.14
- `manage.py check`: 0 issues. `makemigrations --check`: sin cambios pendientes (esta misión NO requirió migraciones nuevas).

## Hallazgo crítico de INSPECT (antes de implementar)

La auditoría de código real (no solo `.agent/AUDITORIA_FLUJO_COMPLETO.md`) confirma que
**la mayor parte del sistema de aplicaciones múltiples (Fases 01-27 del plan) ya estaba
construido en una misión previa ("Fase 5-7, mision Bancos v3.0")**:

- `MovimientoBancarioAplicacion` (modelo completo: `tipo_referencia` con 13 choices
  incluyendo `FACTURA_VENTA`/`ANTICIPO`, `referencia_uuid`, `tercero_tipo`/`tercero_uuid`,
  `monto_aplicado`, `origen_matching`, `confianza`).
- `MovimientoBancarioAplicacionCRUDService` (crear/editar/eliminar, guard de
  sobreaplicación con `select_for_update()`, sincronización ascendente de `conciliado`).
- API completa: `GET/POST /transacciones/{uuid}/aplicaciones/`,
  `GET/PATCH/DELETE /aplicaciones/{uuid}/`.
- `BankTransactionMatchingService` (motor de sugerencias multi-candidato, scoring por
  NIT/monto/fecha/texto).
- UI: "Paso 5: Aplicaciones múltiples" ya en `offcanvas_detalle_extracto.html` (resumen
  aplicado/pendiente, barra de progreso, botón "Sugerir", selector de tipo).
- Tests: `test_aplicaciones.py` (7 casos: completo, parcial, múltiples, sobreaplicación,
  quitar, referencia sin resolver, editar con guard) + cross-tenant isolation.
- Filtro `Factura.objects.filter(naturaleza='VENTA')` (nunca `tipo=`) ya usado en
  `search-facturas` y `BankTransactionMatchingService`.

No se creó un segundo sistema paralelo — toda la implementación de esta pasada extiende
el modelo/servicio ya existente.

## Decisions

1. **`ANTICIPO_CLIENTE` no se agrega como choice nueva.** `TipoReferenciaAplicacion.ANTICIPO`
   ya existe; combinado con `tercero_tipo="CLIENTE"` + `tercero_uuid=<cliente>` representa
   sin ambigüedad un "anticipo de cliente" sin `referencia_uuid` (factura). Agregar una
   choice nueva sería una duplicación semántica (Fase 04 lo permite solo "si no existe
   concepto equivalente" — sí existe).
2. **Gap real encontrado y corregido: `MovimientoBancarioAplicacionCRUDService` NO
   sincronizaba Cartera ni validaba saldo de factura.** La arquitectura v4.0.0 F2 ("Facturas
   = document store") ya había removido `Factura.saldo_pendiente`/`total_pagado_bancos` —
   `Cartera.saldo` (app `clientes`) es la única SSoT real de saldo por factura. El vínculo
   LEGADO 1:1 (`conciliar_transaccion`) ya sincronizaba Cartera vía
   `CarteraBusinessService.registrar_abono_desde_conciliacion_bancaria()`, pero el camino
   NUEVO de aplicaciones múltiples nunca lo llamaba — un pago dividido entre facturas vía
   `MovimientoBancarioAplicacion` quedaba invisible para Cartera. Corregido en
   `crud_service.py`: `crear_aplicacion()`/`editar_aplicacion()` ahora, cuando
   `tipo_referencia=FACTURA_VENTA`, (a) validan `monto <= Cartera.saldo` (lee el campo ya
   calculado, no reimplementa la fórmula) y (b) sincronizan el abono real. Si no existe una
   Cartera para esa `factura_uuid` todavía (soft-reference sin resolver), no bloquea — mismo
   criterio ya usado en todo el proyecto.
   **Detalle de diseño importante, encontrado durante el testing:**
   `registrar_abono_desde_conciliacion_bancaria()` exige resolver una `Factura` real
   (`naturaleza='VENTA'`, `cliente_uuid` no nulo) INCLUSO cuando la Cartera ya existe --
   habría hecho que la sincronización fallara en silencio (best-effort) para cualquier
   Cartera creada sin una Factura real correspondiente en esta misma base de datos (caso
   común en datos de prueba, y potencialmente en datos reales si Cartera se registró por
   otro camino). Corregido: `_sincronizar_cartera()` primero busca la Cartera directamente
   por `factura_uuid`; si ya existe, abona con `CarteraBusinessService.registrar_abono()`
   (que solo necesita la Cartera, no la Factura); solo si la Cartera NO existe todavía cae
   al camino legado que sí requiere la Factura para poder crearla.
3. **Editar una aplicación NO revierte un abono ya sincronizado en Cartera** (Cartera no
   tiene mecanismo de reverso — limitación ya documentada explícitamente para el vínculo
   legado, `crud_service.py::conciliar_transaccion`). Un incremento del monto SÍ sincroniza
   el delta; un decremento se acepta pero no revierte Cartera. Documentado en el docstring
   de `MovimientoBancarioAplicacionCRUDService`.
4. **PDF: se reutiliza `pdfminer.six`** (ya en `requirements.txt`, ya usado en
   `apps/public/impuestos/services/etl/parse_pdf.py` y
   `apps/services/document_parser/normalizers.py`). No se agrega ninguna dependencia nueva.
5. **Parser PDF (Fase 32): layout de una columna "valor" (firmado) + una columna "saldo"
   por línea** — mismo contrato de una sola columna `valor` que ya usan XLSX/CSV (no
   débito/crédito en columnas separadas). Un layout con columnas débito/crédito separadas
   NO está soportado en esta pasada (ver Deferred). No se declara soporte universal de
   bancos colombianos en PDF — es un parser genérico best-effort, probado con fixtures
   sintéticas (no extractos reales de un banco específico, que no estaban disponibles en
   este entorno).
6. **Fixtures de test PDF generadas con `xhtml2pdf`** (ya en `requirements.txt`, usado en
   `apps/tenant/cotizaciones/services/pdf/generator.py`) — sintéticas/representativas, no
   extractos reales de un banco. Verificado empíricamente que el roundtrip
   `xhtml2pdf` → `pdfminer.extract_text()` preserva las líneas de texto para este propósito.
7. **Bug real encontrado y corregido durante el testing** (2 tests fallaron en la primera
   corrida de pytest): `_MONEY_TOKEN_RE` (regex de detección de montos) era demasiado
   permisivo — capturaba números sueltos de 1-3 dígitos sin separador de miles ni parte
   decimal (ej. el "1" de "Movimiento página 1", o el "2" de "Pago 2") como si fueran montos
   válidos, rompiendo el conteo esperado de "2 montos por línea" (valor, saldo) en
   descripciones que casualmente contienen un número corto -- confirmado reproduciendo el
   fallo con `parsear_texto_extracto()` sobre un string plano (no era un artefacto del
   renderizado de PDF). Corregido exigiendo que todo token de monto tenga AL MENOS un
   separador de miles O una parte decimal de exactamente 2 dígitos — un extracto bancario
   real siempre muestra centavos o miles, un número de página/ítem/referencia dentro de la
   descripción nunca los tiene. Aprovechando el diagnóstico, se refactorizó también
   `pdf_importer.py` para separar `parsear_texto_extracto(texto)` (lógica de parseo de
   líneas, pura, testeable con strings) de `importar()` (extracción de bytes PDF vía
   pdfminer) — mejora la testabilidad de casos de borde sin depender del round-trip completo
   de renderizado de PDF.

## Files Changed

- `apps/tenant/bancos/services/importers/pdf_importer.py` (NUEVO) — `PDFBankStatementImporter`.
- `apps/tenant/bancos/services/importers/__init__.py` — registra el importador PDF en `_IMPORTERS`.
- `apps/tenant/bancos/services/crud_service.py` — `_validar_saldo_factura()`,
  `_sincronizar_cartera()`, wiring en `crear_aplicacion()`/`editar_aplicacion()`.
- `apps/tenant/bancos/templates/tenant/bancos/offcanvas_crear_extracto.html` — acepta
  `.csv`/`.pdf` además de `.xls/.xlsx`, muestra tamaño máximo real (20 MB).
- `apps/tenant/bancos/tests/test_import_pdf.py` (NUEVO).
- `apps/tenant/bancos/tests/test_aplicaciones_cartera_sync.py` (NUEVO).

## Migrations

Ninguna. No se modificó ningún modelo (todos los campos necesarios ya existían).

## Tests

Todo ejecutado con `pytest` real (en lotes de 4-6 archivos, coordinado con la misión
GASTOS_PROYECTOS_01 que compartía el mismo `test_sintel`) una vez liberado el turno:

| Suite | Resultado |
|---|---|
| `test_import_pdf.py` + `test_aplicaciones_cartera_sync.py` (nuevos) | 22 passed |
| `test_aplicaciones.py` + `test_conciliacion_dispara_abono_cartera.py` + `test_import_csv.py` + `test_balance_validation.py` + `test_import_xlsx_real_fixture.py` | 23 passed |
| `test_cross_tenant_isolation.py` + `test_organizational_context_adoption.py` + `test_multitenant_isolation.py` + `test_remediation_p1_03_extracto_duplicado.py` + `test_remediation_p1_04_fecha_pago_vs_documento.py` | 10 passed |
| `test_conciliacion_dispara_abono_cartera.py` (re-verificado) + `test_b1_resolucion_empresa_id_fallback.py` + `test_money_parser.py` + `test_matching_service.py` + `test_cuenta_bancaria_crud_workspace.py` | 33 passed |
| Cross-app: `clientes/tests/test_cartera_crud_api.py` + `test_cartera_pull_model_saldo_real.py` (código no modificado, solo consumido) | 4 passed |

**Total: 80 passed en `apps/tenant/bancos/tests/` (58 baseline preexistente + 22 nuevos),
0 failed. 4/4 en el spot-check cross-app de Cartera.** Un archivo (`test_conciliacion_...`)
se corrió dos veces por error de loteo — sin impacto, confirmado verde ambas veces.

Durante la primera corrida de `test_import_pdf.py` aparecieron 2 fallos reales (ver
Decisions #7) — diagnosticados y corregidos antes de la corrida final (todas verdes).

## Last Verification

- 2026-09-18: `manage.py check` (0 issues), `makemigrations --check` (sin cambios),
  `py_compile` de todos los archivos tocados (OK), regresión completa de
  `apps/tenant/bancos/tests/` (80 passed, 0 failed) + cross-app `clientes` Cartera
  (4 passed, 0 failed).

## Deferred (no incluido en esta pasada, documentado explícitamente)

- Adapter XML por banco (Fase 27/28) — sigue siendo un contrato sin implementación real,
  tal como ya estaba (ningún banco con esquema XML confirmado disponible).
- OCR para PDFs escaneados (Fase 34) — explícitamente fuera de alcance ("no introducir un
  sistema OCR pesado sin auditar su impacto primero"); el sistema responde
  `NEEDS_OCR/UNSUPPORTED_FORMAT` de forma controlada.
- Layout PDF con columnas débito/crédito separadas (3 montos por línea) — no soportado en
  esta pasada, solo el layout de una columna `valor` firmada + `saldo`.
- Test de concurrencia real con hilos/procesos sobre `MovimientoBancarioAplicacionCRUDService`
  (Fase 46) — el guard usa `select_for_update()` (mismo patrón validado en otras misiones de
  esta sesión), pero no se ejecutó una prueba de carga concurrente real en esta pasada.
- Fixtures de PDF de bancos reales (Bancolombia/Davivienda/etc.) — no disponibles en este
  entorno; las fixtures usadas son sintéticas.
- Auditoría N+1/performance dedicada (Fase 47/54) — no se detectaron problemas nuevos
  introducidos (los cambios de esta pasada son lecturas puntuales por aplicación, no en
  listados), pero no se hizo un profiling formal.
- "Distribución propuesta" multi-documento (Fase 27, sugerir automáticamente una
  combinación de facturas que sume el valor del movimiento) — `BankTransactionMatchingService`
  ya sugiere múltiples candidatos individuales rankeados, pero no arma combinaciones
  (subset-sum). Es una mejora incremental razonable, no un requisito bloqueante del plan
  ("si el código existente permite...", no "constrúyelo").
- Vínculo par-a-par de `TRANSFERENCIA_INTERNA` entre dos movimientos de cuentas propias
  (ya documentado como deferred en `AUDITORIA_FLUJO_COMPLETO.md` desde la misión v3.0
  anterior) — no revisitado en esta pasada.

---

## FINAL REPORT

Mission: BANCOS_PDF_APLICACIONES_01

Status: PASS_WITH_DEFERRED

### Implemented
- Importador de extractos bancarios en PDF (`PDFBankStatementImporter`), integrado al
  dispatcher `get_importer_for()` junto a XLSX/CSV/XML.
- Sincronización de aplicaciones `FACTURA_VENTA` con `Cartera` (SSoT real de saldo de
  cliente) — gap real encontrado en el sistema de aplicaciones múltiples ya existente
  (Fase 5-7, misión previa), donde el pago dividido entre facturas quedaba invisible para
  Cartera.
- Validación de saldo (`monto_aplicado <= Cartera.saldo`) antes de aplicar o editar una
  aplicación contra una factura de venta.
- Aceptación de `.csv`/`.pdf` en el formulario de carga de extractos (antes solo
  `.xls`/`.xlsx` en el `accept` del input, pese a que CSV ya estaba soportado en backend).

### Models
Ninguno modificado. Todos los campos necesarios (`MovimientoBancarioAplicacion.tipo_referencia`
con `FACTURA_VENTA`/`ANTICIPO`, `tercero_tipo`/`tercero_uuid`, `Cartera.saldo`) ya existían
de una misión previa (Fase 5-7, "mision Bancos v3.0").

### Migrations
Ninguna — no se requirió ningún cambio de esquema.

### Services
- `apps/tenant/bancos/services/importers/pdf_importer.py` (nuevo): `PDFBankStatementImporter`
  + `parsear_texto_extracto()` (lógica de parseo pura, separada de la extracción de bytes).
- `apps/tenant/bancos/services/importers/__init__.py`: PDF registrado en el dispatcher.
- `apps/tenant/bancos/services/crud_service.py`: `MovimientoBancarioAplicacionCRUDService`
  gana `_validar_saldo_factura()` y `_sincronizar_cartera()`, conectados en
  `crear_aplicacion()`/`editar_aplicacion()`.

### APIs
Ninguna nueva — se reutilizan íntegramente los endpoints ya existentes
(`/transacciones/{uuid}/aplicaciones/`, `/aplicaciones/{uuid}/`, `/extractos/{uuid}/procesar/`).

### PDF
`pdfminer.six` (ya en `requirements.txt`, sin dependencia nueva). Parser genérico
best-effort: detecta fecha + 2 montos (valor firmado, saldo) por línea; multipágina soportado
de forma nativa (pdfminer concatena todas las páginas); encabezados repetidos filtrados;
validación de firma binaria `%PDF-`; errores controlados para PDF corrupto, protegido,
vacío o escaneado sin OCR (nunca un 500). No soporta layout de columnas débito/crédito
separadas ni bancos específicos por adapter (ver Deferred). Fixtures de test sintéticas
(generadas con `xhtml2pdf`, ya en `requirements.txt`) — no hay extractos PDF reales de un
banco disponibles en este entorno.

### Multiple Applications
Ya estaban implementadas casi en su totalidad antes de esta misión (modelo, CRUD con guard
de sobreaplicación vía `select_for_update()`, API, UI "Paso 5" en el offcanvas de detalle,
motor de sugerencias). Esta pasada agregó la pieza que faltaba: sincronización real con
Cartera (antes solo el vínculo legado 1:1 lo hacía).

### Partial Payments
Verificado con test dedicado (`test_movimiento_dividido_multiples_facturas`, Escenario B/C
del plan): 3 facturas + anticipo cubren un pago de $2.000.000, cada `Cartera` queda con su
`estado_pago` correcto (`PAGADA`/`PARCIAL` según corresponda) de forma independiente.

### Advances
`ANTICIPO` (choice ya existente) + `tercero_tipo="CLIENTE"` + `referencia_uuid=None`
representa un anticipo sin factura sin crear una Factura ficticia (verificado con test
dedicado). No se agregó `ANTICIPO_CLIENTE` como choice nueva (duplicaría un concepto ya
representable).

### Legacy Compatibility
`conciliar_transaccion()` (vínculo 1:1 legado) permanece intacto y sin cambios. Ambos
caminos (legado y aplicaciones múltiples) ahora sincronizan Cartera de forma consistente.

### Tests
- Bancos: 80/80 passed (58 baseline preexistente + 22 nuevos), 0 failed.
- Cross-App (Cartera/clientes): 4/4 passed.
- 2 fallos reales encontrados y corregidos durante el desarrollo (bug de regex en el
  parser PDF que capturaba números sueltos como montos) — ver Decisions #7.

### Security
DSV (`empresa_id`) respetado en todas las consultas nuevas (`Cartera.objects.filter(empresa_id=...)`).
Ningún endpoint nuevo expuesto. Firma binaria de PDF validada antes de procesar (no confía
solo en la extensión).

### Performance
Sin cambios de patrón de consultas en listados (los cambios son lecturas puntuales de
`Cartera` por `factura_uuid`, ya indexado). No se hizo profiling formal dedicado.

### Deferred
- OCR para PDFs escaneados.
- Layout PDF con columnas débito/crédito separadas.
- Adapter XML por banco (ya deferred desde la misión anterior).
- Test de concurrencia real con hilos sobre aplicaciones múltiples.
- Fixtures de PDF de bancos reales (no disponibles en este entorno).
- "Distribución propuesta" automática multi-factura (subset-sum) en el motor de sugerencias.
- Vínculo par-a-par de `TRANSFERENCIA_INTERNA` (ya deferred desde la misión anterior).
- Verificación visual en navegador real (Capa 1) — no disponible en este entorno; toda la
  verificación fue vía API real (pytest + DRF test client), igual que el resto de esta sesión.

### Blockers
Ninguno activo al cierre.

### Evidence
- `manage.py check` → 0 issues.
- `manage.py makemigrations --check` → sin cambios pendientes.
- `pytest apps/tenant/bancos/tests/` (en 4 lotes) → 80 passed, 0 failed.
- `pytest apps/tenant/clientes/tests/test_cartera_crud_api.py test_cartera_pull_model_saldo_real.py` → 4 passed.
- Verificación manual (`manage.py shell`) del round-trip `xhtml2pdf`→`pdfminer` y de los
  4 escenarios de error del importador PDF, previa a la corrida formal de pytest.

### Files Changed
- `apps/tenant/bancos/services/importers/pdf_importer.py` (nuevo)
- `apps/tenant/bancos/services/importers/__init__.py`
- `apps/tenant/bancos/services/crud_service.py`
- `apps/tenant/bancos/templates/tenant/bancos/offcanvas_crear_extracto.html`
- `apps/tenant/bancos/tests/test_import_pdf.py` (nuevo)
- `apps/tenant/bancos/tests/test_aplicaciones_cartera_sync.py` (nuevo)
- `docs/remediation/BANCOS_PDF_APLICACIONES_MULTIPLES_STATUS.md` (nuevo)

No se creó ningún commit — norma de la sesión (no commitear sin pedido explícito del usuario).
