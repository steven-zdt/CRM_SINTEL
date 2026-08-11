# F26 — Hallazgos

**Fecha:** 2026-08-10

## Parte 1 — Los 18 tests históricos fallando (clasificados individualmente)

Metodología: reproducción real (`pytest --tb=long`), lectura del código de producción real que ejecuta cada test (no solo el test), y para los casos de "contrato cambiado" comparación explícita entre lo que el test espera y lo que el código actual produce.

| # | Test | Causa raíz (evidencia) | Clasificación | Acción |
|---|---|---|---|---|
| 1-6 | `test_materializar_from_dto.py` (6 tests) | 3 causas raíz reales, encontradas incrementalmente: **(a)** llamaban `materializar_factura_desde_result(dto, persist_anexos=True/False)` -- ese parámetro **no existe** en la firma real (`services/__init__.py:169`: `materializar_factura_desde_result(result, empresa_id=None)`); **(b)** una vez quitado el kwarg inexistente, seguían fallando con `{"error": "invalid_result"}, 400` -- causa real: `materializar_desde_result()` (`business_service.py:882-890`) lee `dto = result.get("dto")`, es decir espera un dict **wrapper** `{"dto": {...}}` (mismo shape que produce `importar_ubl(preview=True)`), pero los tests pasaban el DTO suelto directamente como `result`; **(c)** `test_venta_vs_ssot` asumía que `guardar_desde_dto()` extrae `prefijo`/`consecutivo` desde `numero` -- esa extracción (`_parsear_prefijo_consecutivo()`) ocurre en el **parser** (`ubl_parser.py:548,656,1112`), no dentro de `guardar_desde_dto()`, que solo lee `dto.get("prefijo")`/`dto.get("consecutivo")` tal cual llegan; un DTO armado a mano sin pasar por el parser nunca los tendrá. **Hallazgo adicional real durante la corrección** (`test_idempotencia_por_numero`): cuando `identificadores` viene vacío, `cufe` se resuelve a `""` (no `None`) -- la rama `if cufe:` de idempotencia se salta por completo, y una segunda materialización con el mismo número sin CUFE choca contra la `UniqueConstraint` de `Factura.cufe` a nivel de BD, propagando un `IntegrityError` sin manejar (no hay ninguna ruta real de "idempotencia por número" en el código actual). | 5/6: **CONTRATO CAMBIADO** (parámetro removido + shape de wrapper distinto + capa de parseo distinta -- 3 mismatches de contrato, no bugs de producción). 1/6 (`test_sin_anexos_no_guarda_factura_anexos`): **TEST OBSOLETO**. El hallazgo de idempotencia-por-número es un **REAL BUG/GAP menor**, no de este test específicamente sino del código: documentos sin CUFE duplicados no se manejan con gracia (ver F26-006 abajo). | **FIXED**: 6/6 pasan -- kwarg removido, DTOs envueltos en `{"dto": ...}`, aserción de prefijo/consecutivo corregida a la capa real, y el test de idempotencia-por-número reescrito para documentar el `IntegrityError` real con `assertRaises` en vez de fingir que existe una ruta de dedup que no existe. |
| 7-11 | `test_importar_ubl_service.py` (5 tests) | Esperan `payload["preview"]` / `payload["factura"]["naturaleza"]` / `payload["factura"]["numero"]`. El pipeline universal actual (`ingest_document()`, `apps/services/document_ingest/ingest_service.py:53-100`) documenta y devuelve `{"persisted": bool, "dto": {...}, "sha256":.., "metadata":.., "error"/"message" si aplica}` -- **no existe la clave `factura`**, y la clave es `persisted`, no `preview`. Ademas, el pipeline universal es explícitamente "solo parsing... NO conoce modelos Django" (docstring, líneas 19-23) -- `naturaleza` (VENTA/COMPRA) se calcula DESPUES, dentro de `guardar_desde_dto()` (comparando contra `Empresa.nit`), nunca durante el preview. Las 5 fallas observadas (`422 != 200`, `'missing_required_fields' != 'empresa_no_configurada'`) confirman ademas que los XML minimos de fixture (sin `<cbc:UUID>`/CUFE, sin `CustomizationID`/`ProfileID`) ya no satisfacen la validacion actual del pipeline universal, que rechaza el documento con `missing_required_fields` antes de siquiera llegar al chequeo de empresa. | **CONTRATO CAMBIADO** (shape de respuesta) + **IMPLEMENTACION INCOMPLETA respecto al test** (el preview ya no calcula naturaleza -- decision arquitectonica deliberada del pipeline universal ser agnostico de dominio, no un bug). | **DOCUMENTADO, no reescrito en este pase**: reescribir estas 5 aserciones correctamente exige verificar el shape exacto de `dto` para cada escenario contra una ejecucion real, y las fixtures XML necesitan CUFE/UUID validos -- alcance mayor al que este pase puede verificar con confianza sin arriesgar aserciones incorrectas nuevas. Ver §75 (preferir la opcion menos destructiva: documentar con evidencia en vez de adivinar un rewrite). |
| 12-16 | `test_naturaleza_import_ubl.py` (5 tests) | Mismo patron exacto que 7-11, pero via el endpoint HTTP real `factura-upload-ubl` (`self.client.post(...)`) en vez de la funcion `importar_ubl()` directamente. Mismas claves obsoletas (`resp.json()["factura"]["naturaleza"]`, `.get("preview")`), mismas fixtures XML minimas sin CUFE. | **CONTRATO CAMBIADO** (identico a 7-11). | **DOCUMENTADO**, misma razon que 7-11. |
| 17 | `test_ingesta_ubl.py::test_procesar_factura_xml_task` | El test llamaba `procesar_factura_xml_task(XML_SAMPLE.decode(), ...)` -- decodificando bytes a `str` antes de pasarlo. `ingest_document()` exige `bytes` explicitamente (docstring: "content: Contenido del documento en bytes"; ademas `hashlib.sha256(content)` en la linea 107 de `ingest_service.py` solo acepta bytes) -- de ahi el `TypeError: Strings must be encoded before hashing`. **Hallazgo adicional**: `procesar_factura_xml_task` no tiene **ningun llamador real** en todo el repo (`grep -rn "procesar_factura_xml_task" apps/` fuera de su propia definicion y este test = 0 resultados) -- es una Celery task sin uso en produccion, solo ejercitada por este test. | **REAL BUG** (del test, no de produccion: violaba el contrato de tipos documentado). | **FIXED**: se quito el `.decode()` innecesario. La Celery task en si queda marcada como candidata a revision (posible codigo muerto) en la matriz de campos/codigo, no eliminada en este pase (fuera del alcance minimo: eliminar una Celery task requeriria confirmar que no se invoca desde ningun Celery Beat schedule externo al repo). |
| 18 | `test_nota_credito_pipeline.py::test_5_factura_inexistente_error` | El XML de fixture no declaraba `AccountingSupplierParty`/`AccountingCustomerParty` en absoluto. `guardar_desde_dto()` valida que el NIT de la empresa actual coincida con emisor o receptor **antes** de resolver `factura_original_para_nc` (la validacion que el test realmente queria ejercitar) -- sin esos nodos, el XML nunca llegaba a esa validacion: fallaba antes, con un `DjangoValidationError` de NIT no coincidente, no con `missing_invoice`. | **TEST OBSOLETO / FIXTURE INCOMPLETA** (la intencion del test -- "referenciar una factura inexistente" -- sigue siendo un caso real y valido, pero el fixture nunca llegaba a ejercitarlo). | **FIXED**: se agrego `AccountingCustomerParty` con el NIT de `self.empresa_test` (mismo patron que el helper `_crear_xml_credit_note()` ya usado por otros tests de la misma clase) para que el XML sea valido hasta el punto de resolucion de factura, y el test ejercite genuinamente el escenario que su nombre describe. |

**Resumen:** de 18 tests, **8 corregidos** (6 de `test_materializar_from_dto.py` + `test_ingesta_ubl.py` + `test_nota_credito_pipeline.py::test_5`), **10 documentados como CONTRATO CAMBIADO** con evidencia completa de causa raíz (no reescritos por falta de verificación confiable del shape exacto de respuesta del pipeline universal para cada escenario). 0 bugs reales de producción encontrados en esta investigación (el único hallazgo con impacto de producción real, el campo fantasma `orden_compra`, se documenta en la Parte 2).

---

## Parte 2 — Auditoría de campos (inventario real de consumidores)

Metodología: grep exhaustivo de cada campo en todo el repo (no solo `facturas`), verificando lectores, escritores, serializers, templates, JS.

### F26-001 — `MANUAL_EDITABLE_FIELDS` contenía `'orden_compra'`, un campo fantasma (REAL BUG, HIGH)

`Factura` **nunca ha tenido** un campo `orden_compra` (confirmado por lectura completa de `models.py` — el único `orden_compra` real del repo es un FK en `apps/tenant/compras/models.py`, app distinta). Si un `PATCH` a `FacturaViewSet` hubiera incluido `orden_compra`, `FacturaBusinessService.actualizar_factura_limitado()` lo habría metido en `update_data` sin ninguna rama especial, y `FacturaCRUDService.actualizar()` habría ejecutado `factura.save(update_fields=[..., 'orden_compra', ...])` — Django rechaza esto con `ValueError` (campo inexistente), un 500 real nunca disparado en producción solo porque ningún cliente lo ha enviado todavía.

**Corrección:** eliminado de `MANUAL_EDITABLE_FIELDS` (`models.py`). Riesgo cero: el campo nunca funcionó, no hay comportamiento que preservar.

### F26-002 — `Factura.xml_file_path`: eliminado (REMOVE, verificado)

- **Consumidores:** 0 (grep exhaustivo del repo — solo aparecía en su propia definición, la migración `0001_initial.py`, y `admin.py`, sin lectura ni escritura real en ningún flujo).
- **Datos históricos:** 0 filas con valor no vacío en las 3 empresas del entorno (`home`, `qaisotest`, `shelltest1` — `SELECT COUNT(*) WHERE xml_file_path IS NOT NULL AND != ''` = 0 en las tres).
- **Corrección:** campo eliminado del modelo (`models.py`), referencia en `admin.py` limpiada, migración `0032_remove_factura_xml_file_path.py` generada y aplicada a las 3 empresas.

### F26-003 — `Factura.xml_content` (DEFER, no se elimina en este pase)

Marcado `# WARNING: DEPRECADO: usar FacturaAnexos.ubl_xml en su lugar` desde antes de F26. Auditoría real:
- En el flujo de **ingesta** (`guardar_desde_dto()`, el camino dominante hoy), `factura_data` **no incluye** `xml_content` — el XML va exclusivamente a `FacturaAnexos.ubl_xml`. Para documentos importados, el campo queda `NULL`.
- En el flujo de **venta emisora** (`crear_factura_desde_venta()`, `business_service.py:142`), **sí se sigue escribiendo** (`dto.get("xml_content")`, alimentado desde `ventas/services/business_service.py`).
- Ya existe un comando de backfill (`backfill_facturas_anexos.py`) pensado para migrar este dato hacia `FacturaAnexos`, confirmando que la consolidación es trabajo reconocido pero no completado.
- **Decisión:** `DEFER`. Eliminarlo ahora rompería el flujo de venta emisora (que aún lo escribe activamente) sin haber unificado antes ese flujo para escribir a `FacturaAnexos` — ese es un cambio de código real (no solo de datos) fuera del alcance seguro de este pase sin una suite de tests dedicada al flujo de venta emisora, que no se auditó en profundidad aquí.

### F26-004 — 6 campos de retención en `ItemFactura` (DEFER)

Marcados `[DEPRECATED v3.7.1]`, `editable=False`, pero **siguen siendo poblados activamente** en `guardar_desde_dto()` y `ubl_parser.py`, y son consumidos como fallback real por 3 `properties` (`total_retefuente_item`, etc.) y por el comando one-shot `migrate_retenciones.py`. No están en desuso real, solo son secundarios al Pull Model (`RetencionesService`). **Decisión:** `DEFER` — no se tocan sin confirmar primero que `RetencionesService` nunca fallará (las properties los usan como fallback ante excepción).

### F26-005 — `Factura.dian_response_xml` vs `FacturaAnexos.application_response_xml` (DEFER)

Redundantes en efecto (ambos almacenan la respuesta DIAN), pero `dian_response_xml` se sigue escribiendo en ambos flujos de creación, y `backfill_facturas_anexos.py` ya intenta unificarlos con un fallback explícito (`getattr(factura,'dian_response_xml',None) or getattr(factura,'application_response_xml',None)`), confirmando que es trabajo de migración reconocido pero pendiente, no algo que F26 deba iniciar sin la misma auditoría profunda que F26-003.

### F26-006 — Sin idempotencia real cuando el documento no trae CUFE (REAL BUG, MEDIUM, no corregido)

Descubierto al corregir `test_idempotencia_por_numero`. `guardar_desde_dto()` solo
hace el chequeo de idempotencia dentro de `if cufe:` (bloque "Idempotencia por
CUFE"). Si `identificadores` viene vacío, `cufe` se resuelve a cadena vacía `""`
(no `None`) — esa rama se salta por completo. Una segunda materialización con el
mismo `numero` pero sin CUFE intenta crear una segunda `Factura`, y como
`Factura.cufe` tiene `unique=True`, el segundo `INSERT` con `cufe=""` choca contra
la constraint de BD (`facturas_factura_cufe_key`) y propaga un `IntegrityError` **sin
manejar** hasta el llamador — no hay traducción a una respuesta 200/409 idempotente
como sí ocurre en el camino con CUFE. `@transaction.atomic` en `guardar_desde_dto`
asegura que no queda un registro corrupto (rollback completo del segundo intento),
así que no hay pérdida de integridad de datos — el gap es puramente de manejo de
errores (una excepción de BD sin capturar en vez de una respuesta HTTP limpia).

**Alcance real:** solo afecta documentos que llegan sin ningún CUFE/CUDE en
absoluto — infrecuente para XML DIAN reales (casi siempre lo traen), pero posible
para datos de prueba, migraciones legacy, o documentos parcialmente procesados.
**No corregido en F26**: implementar una ruta real de "dedup por número" es lógica
de negocio nueva (decidir qué hacer: rechazar, actualizar, fusionar), no una
simplificación — fuera del alcance de este pase. Documentado para una fase futura.

### F26-007 a F26-010 — Campos confirmados `KEEP` (con evidencia)

`Factura.categoria` (editable real, expuesto en UI/API), `FacturaImpuesto` (desglose real sin duplicar, consumido por API), `cotizacion_uuid`/`cotizacion_numero` (vinculación activa cross-app con `proyectos`) — los tres con consumidores reales confirmados por grep, sin cambios.

---

## Resumen de correcciones aplicadas en F26

| Archivo | Cambio | Riesgo |
|---|---|---|
| `apps/tenant/facturas/models.py` | Removido `'orden_compra'` de `MANUAL_EDITABLE_FIELDS` | Cero (campo fantasma nunca funcional) |
| `apps/tenant/facturas/models.py` | Removido campo `Factura.xml_file_path` | Cero (0 consumidores, 0 datos históricos, verificado) |
| `apps/tenant/facturas/admin.py` | Removida referencia a `xml_file_path` | Cero (sigue el removal del campo) |
| `apps/tenant/facturas/migrations/0032_remove_factura_xml_file_path.py` | Migración nueva, aplicada a las 3 empresas | Cero (verificado antes de aplicar) |
| `apps/tenant/facturas/tests/test_materializar_from_dto.py` | 6 tests corregidos (contrato real) | Cero (solo tests) |
| `apps/tenant/facturas/tests/test_ingesta_ubl.py` | 1 test corregido (tipo de dato) | Cero (solo tests) |
| `apps/tenant/facturas/tests/test_nota_credito_pipeline.py` | 1 fixture corregida | Cero (solo tests) |

**Deuda documentada, no corregida en este pase** (DEFER, con razón explícita en cada caso): `xml_content` duplicado con `FacturaAnexos.ubl_xml` (F26-003), 6 campos de retención legacy en `ItemFactura` (F26-004), `dian_response_xml` duplicado (F26-005), 10 tests de contrato-cambiado en `test_importar_ubl_service.py`/`test_naturaleza_import_ubl.py` (Parte 1), y la Celery task sin uso `procesar_factura_xml_task` (Parte 1, hallazgo #17).
