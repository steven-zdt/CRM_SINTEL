# Mail Hub — Baseline (FASE 0)

**Fecha:** 2026-08-24. **Estado:** Auditoría (sin cambios de código).
Complementa `docs/maildigester/MAILDIGESTER_AUDIT.md` (auditoría previa,
misma sesión) — no repite la evidencia ya citada ahí, la referencia y la
organiza para la misión "Document Intake Service".

---

## 1. Arquitectura actual (3 capas)

```
apps/services/maildigester/     -- genérico, no conoce "Factura"
    schemas.py        DTOs: MailboxConfigDTO, AttachmentDTO, ExtractedFileDTO, InvoiceXMLDTO
    inbox_client.py    Protocol InboxClient + RealIMAPClient (imaplib real) + StubInboxClient
    extractors.py      extrae adjuntos de email.message.Message
    archives.py        expande ZIP/RAR/7z, protección path-traversal
    detectors.py       heurísticas: tipo de archivo, ¿es UBL Invoice?, AttachedDocument
    pipeline.py        orquesta: conectar→mensajes→adjuntos→XML (2 variantes: simple y por UID)
    connection_test.py test de conexión IMAP standalone
    tasks.py           Celery: fetch_and_process_billing_mail -- ROTO, ver §5
    mail_service.py    CÓDIGO MUERTO -- 0 consumidores, ver §7

apps/tenant/facturas/           -- puente hacia el dominio Factura
    services/services_mail_ingestion.py
        enqueue_mail_ingestion()        vivo, encola la tarea Celery
        preview_mail_ingestion()        vivo, no persiste -- naturaleza duplicada, ver §6
        process_mail_ingestion_sync()   CÓDIGO MUERTO -- 0 consumidores, ver §7
        persist_run_result()
    api/views_mail_ingestion.py         3 endpoints DRF, ver §3
    inbox_state.py                      get_or_create_inbox_state/update_inbox_state
    models.py::MailIngestionRun         historial de ejecuciones
    models.py::MailInboxState           último UID procesado (1:1 con MailInboxConfig)

apps/tenant/empresa/            -- configuración por tenant
    models.py::MailInboxConfig          credenciales IMAP -- password en texto plano, ver §8
    api/, admin.py, tables.py           UI de configuración completa
```

---

## 2. Consumidores confirmados (grep repo-wide)

| Símbolo | Consumidores reales |
|---|---|
| `pipeline.collect_invoice_xml_from_mailbox_by_uid` | `apps/services/maildigester/tasks.py` |
| `enqueue_mail_ingestion` | `apps/tenant/facturas/api/views_mail_ingestion.py::MailIngestionRunCreateAPIView` |
| `preview_mail_ingestion` | `apps/tenant/facturas/api/views_mail_ingestion.py::MailIngestionPreviewAPIView` |
| `mail_service.py` (7 funciones) | **ninguno** |
| `process_mail_ingestion_sync()` | **ninguno** (ni siquiera un test) |

---

## 3. Endpoints reales

| Endpoint | Vista | Estado |
|---|---|---|
| `POST /api/v1/facturas/ingesta-correo/run/` | `MailIngestionRunCreateAPIView` | conectado a `facturas_main.js`/`facturas.api.js` -- dispara la tarea rota |
| `GET /api/v1/facturas/ingesta-correo/runs/` | `MailIngestionRunsListAPIView` | funciona |
| `POST /api/v1/facturas/ingesta-correo/preview/` | `MailIngestionPreviewAPIView` | funciona, no persiste |

## 4. Jobs / Celery

Única tarea real: `apps.services.maildigester.tasks.fetch_and_process_billing_mail`
(`autoretry_for=(ConnectionError, TimeoutError, OSError)`, `max_retries=5`,
cola `high_priority`). Cancelación cooperativa vía `MailIngestionRun.status
== 'CANCEL_REQUESTED'`, verificada entre lotes/mensajes/archivos.

## 5. Fallo confirmado en producción

`tasks.py` llama `facturas_services.guardar_factura_desde_dto(...)` y
`facturas_services.guardar_nota_credito_desde_dto(...)` — **ninguna de
las dos existe** en `apps.tenant.facturas.services`
(`ImportError` verificado ejecutando el import real, ver
`MAILDIGESTER_AUDIT.md` §1). La función real que ya cubre AMBOS casos
(factura y nota crédito, vía detección `is_credit_note` interna) es
`FacturaBusinessService.guardar_desde_dto()` — un solo punto de entrada,
no dos. Corregido en FASE 1 de esta misión.

## 6. Duplicación de reglas de negocio

`preview_mail_ingestion()` reimplementa la comparación emisor/empresa
para determinar VENTA/COMPRA en vez de delegar a
`FacturaBusinessService._resolver_naturaleza()` (SSoT real, ya auditada
en `docs/facturas/FACTURAS_HUB_BASELINE.md` §2). Corregido en FASE 12 de
esta misión.

## 7. Código muerto confirmado (DEAD_CONFIRMED)

- `apps/services/maildigester/mail_service.py` — archivo completo, 7
  funciones (`procesar_correo`, `conectar_imap`,
  `obtener_correos_no_leidos`, `obtener_mensaje_por_id`,
  `decodificar_header`, `extraer_adjuntos_xml`), 0 consumidores.
- `apps/tenant/facturas/services/services_mail_ingestion.py::process_mail_ingestion_sync()`
  — 0 consumidores, ni siquiera en tests.

Verificado con grep de `from apps.services.maildigester.mail_service
import`, `from apps.services.maildigester import mail_service`, y
`process_mail_ingestion_sync` sobre `*.py` en todo el repo: solo la
propia definición aparece en cada caso.

## 8. Seguridad de credenciales

`MailInboxConfig.password` (`apps/tenant/empresa/models.py`) — texto
plano, ya documentado como deuda conocida en el propio docstring del
modelo (`TODO: usar django-encrypted-model-fields o similar`). Ninguna
dependencia de cifrado está instalada hoy (`requirements.txt` no la
tiene). A resolver en FASE 15.

## 9. Tests existentes

`tests/services/maildigester/test_tasks.py` — 3 tests
(`test_fetch_and_process_billing_mail_eager`,
`_handles_validation_error`, `_handles_empty_mailbox`), todos con `mock.patch`
sobre etapas anteriores del pipeline (conexión/estado), **ninguno llega a
la persistencia real** — la rama rota (§5) está sin cobertura.
`tests/services/maildigester/test_pipeline_contract.py` — contrato del
pipeline (extracción/detección), no toca persistencia.

## 10. Riesgos identificados para esta misión

- **Cambiar la firma de llamada a `guardar_desde_dto()` sin verificar
  `empresa_id`** puede romper el aislamiento multi-tenant si se asume
  incorrectamente — se resuelve explícitamente dentro de
  `schema_context(tenant_schema)`, mismo patrón ya usado en el resto de
  la tarea.
- **Agregar `PARTIAL_SUCCESS` a `MailIngestionRun.STATUS_CHOICES`**
  requiere una migración aditiva (bajo riesgo, mismo patrón que
  `Factura.Estado.ERROR_TRANSMISION` de la misión Ciclo Fiscal).
- **Tests DB-backed en este entorno toman 15-20 minutos** (medido
  repetidamente en sesiones anteriores) — dado el límite operativo de 15
  minutos por acción de esta misión (REGLA #6), la verificación de esta
  misión prioriza scripts de verificación directos (Django test Client +
  rollback, ya establecidos en esta sesión) y tests puros sin DB sobre
  corridas completas de pytest con DB, documentando la estrategia
  alternativa en cada fase donde aplique.

---

## 11. Estado formal de FASE 0

**`MAIL_HUB FASE 0 = COMPLETA`.** Continuando automáticamente a FASE 1
(reparar el camino de producción), sin pausa, según regla de autonomía
de esta misión.

---

## 12. Addendum -- Ejecución FASE 1-4 (2026-08-25)

### FASE 1 -- Reparado

`tasks.py` colapsado a una sola llamada a
`FacturaBusinessService.guardar_desde_dto(dto, xml_text=..., file_bytes=...,
file_type="xml", empresa_id=...)` (cubre factura Y nota crédito
internamente). `empresa_id` se resuelve explícitamente desde
`MailInboxConfig.objects.only("empresa_id").get(id=config_id).empresa_id`
dentro del `schema_context`, nunca se infiere del DTO. Verificado con
persistencia real (savepoint correctamente envuelto en
`transaction.atomic()`, ver §14): creación 201 real, CUFE poblado,
idempotencia 200/`created=False` en el segundo intento.

### FASE 2 -- Reparado

Estado final del run ahora se calcula de los contadores reales:
`errors==0` -> `SUCCESS`; `errors>0 and (imported>0 or duplicates>0)` ->
`PARTIAL_SUCCESS` (valor nuevo, migración `0038_partial_success_status`,
aplicada a los 3 schemas de tenant); `errors>0 and imported==0 and
duplicates==0` -> `FAILED`. Ya no existe el falso `SUCCESS` cuando
`imported=0` y `errors>0`.

### FASE 3 -- Reparado

Nuevo `_clasificar_excepcion()` en `tasks.py`: clasifica cada excepción de
procesamiento por documento en `transient/programming/domain/validation/
security/unknown`. `programming`/`security` se loggean con
`logger.error(exc_info=True)`; el resto con `logger.warning(exc_info=True)`.
Ninguna excepción se descarta bajo un `except Exception` genérico sin
clasificar y sin `exc_info=True`.

### FASE 4 -- Código muerto eliminado (DEAD_CONFIRMED, 3 objetivos)

1. `apps/services/maildigester/mail_service.py` (archivo completo) --
   0 consumidores confirmados.
2. `apps/tenant/facturas/services/services_mail_ingestion.py::process_mail_ingestion_sync()`
   -- 0 consumidores confirmados.
3. **Hallazgo nuevo durante FASE 1** (no estaba en el alcance original de
   esta fase, pero es el mismo patrón): `apps/tenant/core/document_router.py`
   -- archivo completo. Registraba "materializadores" para un dispatcher
   genérico (`materialize_document()`/`materializar()`), pero **cada una**
   de sus 4 rutas de registro (`invoice`, `creditnote`, `gasto`,
   `inventario`) importaba símbolos inexistentes o rutas de módulo
   incorrectas (`guardar_factura_desde_dto`, `guardar_nota_credito_desde_dto`,
   `materializar_factura_desde_dto`, `materializar_nc_desde_dto`,
   `apps/tenant/gastos/services.py` como archivo plano -- no existe, es un
   paquete --, `apps.tenant.inventario.services.services` -- no existe,
   el módulo real es `ingesta_service.py`). Todas envueltas en
   `except ImportError: logger.warning(...)`, exactamente el mismo
   anti-patrón que causó el bug de FASE 1. Su único consumidor real
   (`apps/services/document_ingest/ingest_service.py`) tiene el import
   **comentado explícitamente** desde un refactor previo ("Eliminado
   import de materialize_document - document_ingest SOLO parsea, NO
   persiste"). 0 consumidores reales confirmados por grep repo-wide.
   Eliminado.

Verificación: `manage.py check` limpio, `py_compile` limpio en los 3
archivos tocados, grep repo-wide post-eliminación confirma cero referencias
de código (solo quedan menciones en docs `.agent/` archivadas).

### Hallazgo adicional -- bug real en `inbox_state.py` (no estaba en el radar original)

Al escribir el primer test real de persistencia para `tasks.py` (FASE 28,
adelantado durante esta misma sesión de trabajo porque era la única forma
de probar FASE 1 con rigor), se descubrió que
`apps/tenant/facturas/inbox_state.py::get_or_create_inbox_state()` y
`update_inbox_state()` llaman `MailInboxState.objects.get_or_create(
mailbox_config=config, defaults={...})` **sin incluir `empresa`** en
`defaults`. `SintelTenantBaseModel.save()` rechaza cualquier registro con
`empresa=None` (regla dura del proyecto). Esto significa que **la primera
vez que se procesa un buzón nuevo, la tarea real crashea** con
`ValueError: MailInboxState.empresa no puede ser NULL` -- un segundo bug de
producción independiente del de FASE 1, enmascarado de la misma forma (bajo
el `except Exception` de nivel de tarea, contado como error genérico).
Corregido: ambas llamadas ahora pasan `"empresa_id": config.empresa_id` en
`defaults`. Verificado con un script de verificación real (esta vez
correctamente envuelto en `transaction.atomic()`).

### FASE 5 -- Normalización de arquitectura mail (evaluada, ya cumplida)

Con FASE 1 y FASE 4 cerradas, ya existe **un solo pipeline de mail**:
`inbox_client.py` (Protocol + `RealIMAPClient` + `StubInboxClient`) ->
`extractors.py` -> `archives.py` -> `detectors.py` -> `pipeline.py`
(`collect_invoice_xml_from_mailbox_by_uid`, la única variante que consume
`tasks.py`) -> `tasks.py`. No queda ningún pipeline paralelo/legacy: el
`mail_service.py` legacy y el `process_mail_ingestion_sync()` síncrono
paralelo ya fueron eliminados en FASE 4. `pipeline.py` conserva
`collect_invoice_xml_from_mailbox` (variante no incremental, sin UID) --
NO es código muerto: la usan los tests de contrato
(`test_pipeline_contract.py`) y queda disponible como utilidad de bajo
nivel, pero **no tiene ningún consumidor de producción** fuera de tests;
se deja documentado aquí para revisión en FASE 31 (cleanup), no se elimina
en esta fase por prudencia (podría ser usada por `connection_test.py` u
otra herramienta de diagnóstico -- pendiente de confirmar antes de tocarla).

### FASE 12 -- Duplicación de naturaleza eliminada (y 3 bugs adicionales encontrados)

Al corregir `preview_mail_ingestion()` para consultar el mismo SSoT que
persistencia (`FacturaBusinessService._resolver_naturaleza()` +
`FacturaBusinessService.normalize_document_number()`, en vez de reimplementar
la comparación emisor/receptor==empresa con una fuente de empresa distinta
`get_empresa_emisor_data()`), se descubrió que la función estaba rota en
**otros 3 puntos independientes**, sin relación con la duplicación de
naturaleza -- **`preview_mail_ingestion()` nunca ha funcionado en
producción**, todo call real cae en el `except Exception` genérico:

1. `MailboxConfigDTO(**dict)` -- es un `TypedDict`, llamarlo así solo
   devuelve un `dict` plano; el acceso posterior `mailbox_config.host`
   (atributo) lanzaba `AttributeError` SIEMPRE.
2. `ingest_document(xml_bytes, file_type='xml')` -- el kwarg real es
   `mime_type=`, no `file_type=`; además la función retorna una tupla
   `(result, status_code)`, no un dict suelto. Causaba que la rama
   "moderna" (document_ingest) SIEMPRE fallara y cayera al parser UBL
   legacy... que a su vez fallaba por el bug #3.
3. `from apps.tenant.facturas.services import normalize_document_number` --
   nunca estuvo exportado en `apps/tenant/facturas/services/__init__.py`;
   `ImportError` garantizado. El método real es
   `FacturaBusinessService.normalize_document_number` (staticmethod).

Los 4 problemas (duplicación de naturaleza + 3 bugs) se corrigieron juntos
en `apps/tenant/facturas/services/services_mail_ingestion.py`. Verificado
con el mismo XML fixture y comparación cruzada preview-vs-persistencia real
(properly `transaction.atomic()`-wrapped): `preview_mail_ingestion()` ahora
retorna `pending_invoices` con `belongs_to_tenant=True,
validation_message="VENTA (emitida por esta empresa)"` para el mismo
documento que `guardar_desde_dto()` persiste con `naturaleza=VENTA` --
coinciden.

### FASE 15 -- Seguridad de credenciales (gap de descifrado real, no solo cifrado en reposo)

El cifrado en reposo YA estaba parcialmente implementado antes de esta
misión: `apps/services/security/crypto.py` (Fernet, usa la dependencia
`cryptography` ya existente -- ninguna librería nueva) +
`MailInboxConfigViewSet` (endpoint de test de conexión, con graceful
degradation a texto plano) + el serializer de `empresa` (`encrypt_password()`
al guardar `imap_password`/`smtp_password`, ambos `write_only=True`, nunca
serializados). **Lo que faltaba, y es la causa por la que cualquier
`MailInboxConfig` creada vía la API actual fallaría SIEMPRE la autenticación
IMAP real**: `apps/tenant/empresa/impl/mailbox_provider.py::get_mailbox_config()`
-- el único punto real desde donde `tasks.py`/`pipeline.py` obtienen
credenciales para conectar -- nunca llamaba a `decrypt_password()`; enviaba
el ciphertext directo como password a `RealIMAPClient.connect()`. Corregido
con el mismo patrón de graceful degradation ya usado en el viewset (intenta
descifrar, si falla -- clave rotada o fila legacy en texto plano -- usa el
valor crudo sin loggearlo). Verificado: password cifrado guardado ->
`get_mailbox_config()` devuelve el texto plano correcto.

Adicionalmente, `MailInboxConfigAdmin` (Django admin) renderizaba los 5
campos de password con el widget de texto por defecto (mostrando el valor
guardado: texto plano en el campo legacy `password`, ciphertext en los
nuevos). Corregido con un `ModelForm` que usa `PasswordInput(render_value=False)`
+ cifra cualquier valor nuevo escrito ahí con el mismo helper del serializer
(el admin es otra vía de escritura, no debía ser la excepción que persiste
en texto plano).

**Gap residual documentado, no cerrado en esta fase**: el campo legacy
`password` (distinto de `imap_password`) nunca se cifra en el serializer de
API (solo `imap_password`/`smtp_password` lo hacen) -- de bajo riesgo porque
es un campo marcado deprecado y `get_mailbox_config()` ya lo trata con
graceful degradation, pero queda pendiente para una fase de limpieza futura
si se confirma que algún flujo real todavía escribe ahí.

### Nota operativa -- incidente de verificación (ver `feedback_savepoint_needs_atomic_wrapper` en memoria)

Durante la verificación de estos hallazgos, varios scripts de
`manage.py shell` usaron `transaction.savepoint()`/`savepoint_rollback()`
**sin** envolver en `transaction.atomic()`, lo cual NO protege contra
commits reales en este entorno (autocommit por statement). Esto dejó datos
de prueba reales en el tenant `qaisotest` (NIT de empresa alterado, 2
`MailInboxConfig`, 1 `Factura`, 3 `MailIngestionRun`, 2 `MailInboxState`
de prueba). Detectado y corregido en la misma sesión: datos de prueba
eliminados, NIT original restaurado. Ningún dato de producción real fue
afectado (schema `qaisotest` es un tenant de QA, no de cliente real), pero
se documenta como lección operativa para el resto de esta misión y
misiones futuras.
