# Mail Digester — Auditoría e Integración Completa

**Fecha:** 2026-08-24. **Estado:** Auditoría (sin cambios de código,
solicitud de solo-lectura). Ámbito: `apps/services/maildigester/`,
`apps/tenant/facturas/services/services_mail_ingestion.py`,
`apps/tenant/facturas/api/views_mail_ingestion.py`,
`apps/tenant/empresa/models.py::MailInboxConfig`,
`apps/tenant/facturas/models.py::MailIngestionRun/MailInboxState`.

**Hallazgo crítico adelantado:** el flujo real y en producción de
"Procesar correo → Facturas" está **actualmente roto** — cualquier
ejecución real fallará al persistir el 100% de las facturas/notas
crédito detectadas, aunque la tarea reporte `status: SUCCESS`. Verificado
empíricamente contra el código real, no es una sospecha (§1).

---

## 1. 🔴 Hallazgo crítico: import roto en el único camino de persistencia real

**`apps/services/maildigester/tasks.py`** (la tarea Celery real, único
disparador de persistencia real) y **`apps/tenant/facturas/services/
services_mail_ingestion.py::process_mail_ingestion_sync()`** (código
muerto, ver §5) intentan:

```python
from apps.tenant.facturas.services import guardar_factura_desde_dto, normalize_document_number
```

**Esa función no existe.** Verificado ejecutando el import real dentro
del contenedor:

```
$ python manage.py shell -c "from apps.tenant.facturas.services import guardar_factura_desde_dto"
ImportError: cannot import name 'guardar_factura_desde_dto' from 'apps.tenant.facturas.services'
```

`apps/tenant/facturas/services/__init__.py` solo expone
`importar_ubl`/`importar_ubl_sync`/`materializar_factura_desde_result`/
`crear_factura` como wrappers de compatibilidad — ninguno se llama
`guardar_factura_desde_dto` ni `guardar_nota_credito_desde_dto`. La
función real que sí existe y hace ese trabajo es
`FacturaBusinessService.guardar_desde_dto()` (auditada extensamente en
`docs/facturas/FACTURAS_HUB_BASELINE.md`) — el nombre correcto nunca se
actualizó en `tasks.py` tras un refactor anterior del Service Layer.

### Por qué esto pasa desapercibido en producción

`tasks.py` hace `from apps.tenant.facturas import services as
facturas_services` (importa el **módulo**, no el símbolo) — eso no
falla. El fallo real ocurre **en tiempo de ejecución**, dentro del loop
por cada XML detectado (`tasks.py:372`,
`facturas_services.guardar_factura_desde_dto(...)`), y está envuelto en
un `except Exception` genérico (`tasks.py:424-434`) que solo incrementa
`counts["errors"]` y sigue con el siguiente correo. **La tarea Celery
completa reporta `status: SUCCESS`** al final (`tasks.py:467`) — el
usuario ve "ejecución exitosa" en el historial (`MailIngestionRun`),
pero con `imported: 0` y `errors: N` para cada correo con factura real.

### Por qué los tests no lo detectaron

`tests/services/maildigester/test_tasks.py` (3 tests) hace `mock.patch`
sobre etapas anteriores del pipeline (conexión, `_should_abort`,
`_update_run`) pero **nunca llega a ejercitar la rama de persistencia
real** — el camino roto está sin cobertura de tests.

### Impacto real

`POST /api/v1/facturas/ingesta-correo/run/`
(`views_mail_ingestion.py::MailIngestionRunCreateAPIView`, con hooks
reales en `facturas_main.js`/`facturas.api.js` — **no es un endpoint
huérfano, está conectado a la UI**) → `enqueue_mail_ingestion()` →
`fetch_and_process_billing_mail.apply_async(...)` — este es el camino
100% real y alcanzable desde la UI de Facturas hoy. **Cualquier tenant
que use "ingesta por correo" hoy no está importando nada**, aunque el
sistema le reporte que la ejecución fue exitosa.

**Corrección mínima** (no aplicada en esta auditoría, solo-lectura):
reemplazar `facturas_services.guardar_factura_desde_dto(dto,
xml_text=...)` por `FacturaBusinessService.guardar_desde_dto(dto,
xml_text=..., file_bytes=..., empresa_id=...)` en `tasks.py` — la firma
real ya soporta exactamente ese uso, es el mismo patrón que
`FacturaUBLMixin.upload_document()` ya usa correctamente.

---

## 2. Arquitectura — dos capas, bien separadas en diseño

```
apps/services/maildigester/          ← genérico, sin conocer "Factura"
    schemas.py       DTOs (MailboxConfigDTO, AttachmentDTO, InvoiceXMLDTO)
    inbox_client.py  Protocol + RealIMAPClient + StubInboxClient (imaplib real)
    extractors.py    extrae adjuntos de un email.message.Message
    archives.py      expande ZIP/RAR/7z (con protección path-traversal)
    detectors.py     heurísticas: ¿es XML? ¿es UBL Invoice? ¿AttachedDocument?
    pipeline.py       orquesta: conectar → mensajes → adjuntos → XML UBL
                       (2 variantes: por límite simple, y por UID incremental)
    connection_test.py  test de conexión IMAP standalone (usado en config UI)
    tasks.py          Celery: fetch_and_process_billing_mail (🔴 roto, §1)
    mail_service.py   🪦 CÓDIGO MUERTO (§5) -- 0 consumidores en todo el repo

apps/tenant/facturas/
    services/services_mail_ingestion.py   puente hacia el dominio Factura
        enqueue_mail_ingestion()   -- encola la tarea Celery (✅ vivo, usado por la API)
        preview_mail_ingestion()  -- preview sin persistir (✅ vivo, usado por la API)
        process_mail_ingestion_sync()  -- 🪦 CÓDIGO MUERTO (§5), mismo bug del §1
        persist_run_result()
    api/views_mail_ingestion.py  -- 3 endpoints DRF (§3)
    inbox_state.py    -- get_or_create_inbox_state/update_inbox_state (UID incremental)
    models.py::MailIngestionRun    -- historial de ejecuciones (estado/counts/task_id)
    models.py::MailInboxState      -- último UID procesado por config (1:1 con MailInboxConfig)

apps/tenant/empresa/
    models.py::MailInboxConfig  -- credenciales IMAP por tenant (🔴 password en texto plano, §6)
    api/, admin.py, tables.py   -- UI de configuración (existe, ver §4)
```

**El diseño de separación es correcto**: `maildigester` no sabe qué es
una `Factura` (solo produce `InvoiceXMLDTO`), y la persistencia real vive
en `facturas`. El bug de §1 es un error de *nombre de función* al
conectar las dos capas, no un problema de arquitectura.

---

## 3. Endpoints API reales (todos con autenticación dual JWT+Session)

| Endpoint | Vista | Estado |
|---|---|---|
| `POST /api/v1/facturas/ingesta-correo/run/` | `MailIngestionRunCreateAPIView` | ✅ vivo, conectado a UI — 🔴 la tarea que dispara está rota (§1) |
| `GET /api/v1/facturas/ingesta-correo/runs/` | `MailIngestionRunsListAPIView` | ✅ vivo — lista `MailIngestionRun`, no afectado por §1 |
| `POST /api/v1/facturas/ingesta-correo/preview/` | `MailIngestionPreviewAPIView` | ✅ vivo — usa `preview_mail_ingestion()`, **no** persiste, no afectado por §1 |

`preview_mail_ingestion()` (línea ~422 de `services_mail_ingestion.py`)
sí funciona correctamente hoy — es la parte que solo muestra al usuario
qué facturas encontró, sin guardarlas. **Esto explica por qué el bug
puede haber pasado desapercibido**: el preview (lo primero que un
usuario probaría) funciona; solo la persistencia real (el paso
"confirmar ejecución") está rota.

---

## 4. Configuración por tenant — `MailInboxConfig` (`apps/tenant/empresa/`)

Modelo completo con UI real: `provider` (Gmail preset / Custom),
`email_address`, host/puerto/SSL, `password`, `is_active`. Expuesto vía
API + admin + tabla de gestión (`apps/tenant/empresa/api/`,
`admin.py`, `tables.py`) — configuración real, no un stub.
`connection_test.py::maildigester_test_connection()` permite probar la
conexión IMAP desde la UI antes de guardar.

**Multi-tenant correcto**: `MailInboxConfig` hereda `SintelTenantBaseModel`
(aislado por schema), y `enqueue_mail_ingestion()` nunca envía
credenciales en el payload de Celery — solo `config_id`; la tarea
resuelve la configuración real dentro de `schema_context()` en el
worker (`tasks.py:193-194`). Correcto para evitar fuga de credenciales
en logs/broker de Celery.

---

## 5. Código muerto confirmado (0 consumidores, verificado por grep)

| Símbolo | Archivo | Evidencia |
|---|---|---|
| Todo `mail_service.py` (7 funciones: `procesar_correo`, `conectar_imap`, `obtener_correos_no_leidos`, etc.) | `apps/services/maildigester/mail_service.py` | Grep de `from apps.services.maildigester.mail_service import` / `from apps.services.maildigester import mail_service`: **0 resultados en todo el repo** (ni producción ni tests) |
| `process_mail_ingestion_sync()` | `apps/tenant/facturas/services/services_mail_ingestion.py:130` | Grep de `process_mail_ingestion_sync`: **1 solo resultado** (su propia definición) |

`mail_service.py` es una implementación completa y paralela (español,
API funcional distinta a `inbox_client.py`+`pipeline.py`) que
aparentemente quedó reemplazada por la arquitectura Protocol/DTO actual
sin eliminarse. `process_mail_ingestion_sync()` es una variante sync del
mismo flujo que `tasks.py` implementa async — nunca se conectó a ningún
endpoint (el único endpoint sync-capable, `MailIngestionRunCreateAPIView`,
siempre encola async vía `enqueue_mail_ingestion()`).

---

## 6. Hallazgo de seguridad — password en texto plano

`MailInboxConfig.password` (`apps/tenant/empresa/models.py`) — el propio
docstring del modelo ya lo documenta como deuda conocida: *"SEGURIDAD: En
fase posterior, cifrar password (TODO: usar django-encrypted-model-fields
o similar)"*. Confirmado: no hay cifrado aplicado hoy — las credenciales
IMAP de cada tenant se almacenan en texto plano en la base de datos.
Riesgo real (acceso a la BD expone credenciales de correo reales), ya
conocido por el propio equipo (no es un hallazgo nuevo, se re-confirma
vigente).

---

## 7. Duplicación de lógica de naturaleza (ya documentado en Facturas Hub)

`services_mail_ingestion.py::preview_mail_ingestion()` reimplementa su
propia versión de "¿es VENTA o COMPRA?" en vez de llamar a
`FacturaBusinessService._resolver_naturaleza()` — ya auditado con detalle
en `docs/facturas/FACTURAS_HUB_BASELINE.md` §2. Se re-menciona aquí
porque es parte directa del flujo de mail digester, no un hallazgo nuevo.

---

## 8. Trazabilidad — qué SÍ funciona bien

- **Idempotencia real:** la persistencia (cuando el bug de §1 se
  corrija) delega en `guardar_desde_dto()`, que ya es idempotente por
  CUFE (mismo mecanismo auditado en Facturas Hub) — el mail digester no
  reinventa deduplicación.
- **Procesamiento incremental por UID IMAP:** `MailInboxState.
  last_seen_uid` evita reprocesar correos ya examinados; primera
  ejecución = histórico completo, siguientes = solo mensajes nuevos.
  Diseño correcto y ya implementado.
- **Cancelación cooperativa:** lee `MailIngestionRun.status ==
  'CANCEL_REQUESTED'` desde BD entre lotes/mensajes/archivos — permite
  cancelar una ingesta larga sin matar el proceso Celery a la fuerza.
- **Protección contra ZIP-bombs/path-traversal:** `archives.py` valida
  antes de expandir (confirmado por `PathTraversalError`/
  `ArchiveExpansionError` en `exceptions.py`, no solo declaradas).
- **Reintentos acotados:** `autoretry_for=(ConnectionError, TimeoutError,
  OSError)` — solo errores transitorios de red, explícitamente NO
  `AttributeError` (irónico dado §1: el bug real produce un
  `AttributeError`/`Exception` genérico que el `except` interno atrapa
  ANTES de que la política de reintentos de Celery pueda actuar sobre
  él — ni siquiera reintenta, solo cuenta como error silencioso).

---

## 9. Resumen ejecutivo

| Área | Estado |
|---|---|
| Arquitectura general (separación maildigester ↔ facturas) | ✅ Correcta |
| Conexión IMAP real (`RealIMAPClient`) | ✅ Implementada, con `StubInboxClient` para tests |
| Detección UBL/AttachedDocument/ZIP | ✅ Implementada, con protecciones reales |
| Procesamiento incremental por UID + cancelación | ✅ Implementado correctamente |
| **Persistencia real (Celery → Factura)** | 🔴 **ROTA** — `ImportError`/`AttributeError` silencioso en cada item, §1 |
| Preview (sin persistir) | ✅ Funciona |
| Configuración por tenant (UI/API/admin) | ✅ Completa |
| Seguridad de credenciales | 🟡 Password en texto plano, deuda ya conocida |
| Código muerto | 🟡 `mail_service.py` completo + `process_mail_ingestion_sync()` |
| Duplicación de reglas de negocio | 🟡 Naturaleza reimplementada en preview (bajo riesgo) |

**Conclusión:** el mail digester está arquitectónicamente bien diseñado
y la mayoría de sus piezas (conexión, detección, incrementalidad,
cancelación, seguridad de credenciales en tránsito) funcionan
correctamente — pero el eslabón final que lo conecta con la persistencia
real de Facturas está roto por un nombre de función desactualizado,
silenciado por un `except Exception` demasiado amplio y sin cobertura de
test en ese punto exacto. Es el tipo de bug que un usuario real
detectaría rápido (facturas que nunca aparecen tras "ejecutar ingesta"),
pero que no deja rastro de error visible sin leer los logs
estructurados (`logger.warning("maildigester.import_exception_invoice",
...)`).
