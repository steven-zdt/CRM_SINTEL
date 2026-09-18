# [PORTAL] Auditoría: Módulo Clientes

**Versión:** v3.16.0
**Estado:** ⚠️ PRODUCTION READY CON DEUDAS DOCUMENTADAS — ver §Deudas Técnicas. Fase 1 de remediación (2026-09-12) cerró 2 hallazgos CRÍTICO de la auditoría `docs/remediation/AUDIT_BASELINE_20260912.md` (C-1, C-2), ver sección nueva abajo.
**Ubicación:** `apps/tenant/clientes/`
**Última Auditoría:** 2026-09-12 (v3.16.0) — auditoría previa 2026-09-11 (v3.15.0)
**Auditor:** Claude Sonnet 5 (Anthropic) — v3.12.0 a v3.16.0. v3.11.0 y anteriores: Claude Sonnet 4.6 (Anthropic)

---

## v3.16.0 — Fase 1 de remediación (2026-09-12): C-1, C-2 (docs/remediation/AUDIT_BASELINE_20260912.md)

Auditoría transversal "Clientes + Cartera" (8 agentes en paralelo, ver
`docs/remediation/AUDIT_BASELINE_20260912.md`) encontró y esta fase corrigió
2 hallazgos CRÍTICO reales en Cartera, ambos con test de regresión nuevo:

**C-1 — Filtros/KPIs de Cartera leían `Factura.estado_pago`, no el estado
real de `Cartera`.** `registrar_abono()` (única vía de pago autorizada)
solo escribe `Cartera.valor_pagado/saldo/estado_pago`, nunca
`Factura.estado_pago` (ese campo solo lo toca la conciliación bancaria).
`CarteraSelector.qs_list_facturas_venta(estado_pago=...)` y
`get_cartera_kpis_facturas_venta()` (`services/selectors.py`) filtraban y
contaban sobre `Factura.estado_pago` — una factura pagada 100% solo vía
abono manual nunca aparecía bajo `?estado_pago=PAGADA`, seguía contando en
`pendiente_count`/`vencidas_count`, y su monto nunca entraba a
`pagado_monto`. **Fix**: ambos métodos ahora anotan `cartera_estado` (mismo
patrón que ya usaban `sin_pago_count`/`parcial_count`) y lo prefieren sobre
`Factura.estado_pago`, con fallback solo si no existe fila `Cartera`.
Test: `tests/test_cartera_filtros_kpis_reflejan_abono_real.py` — crea la
Factura en su default real (`NO_PAGADA`, sin forzarlo a mano como hacía
`test_cartera_pull_model_saldo_real.py`, que por eso no detectó este bug).

**C-2 — El formulario manual "Nueva Obligación" podía sobrescribir un abono
ya registrado, bypaseando `registrar_abono()`.**
`CarteraBusinessService.registrar_cartera()` es un `get_or_create()`
idempotente pensado para sincronización ETL (único invocador real hoy es
el propio endpoint manual, ver `docs/integration/CROSS_APP_FINDINGS.md`);
si el `(cliente, numero_factura)` ya existía, la rama "not created"
sobrescribía `valor_pagado` sin locking, sin guarda de "ya PAGADA" y sin
`CarteraNota`. **Fix**: `CarteraViewSet.create()` (`api/viewsets.py`) ahora
rechaza con 409 si ya existe una obligación para esa combinación, sin
tocar la semántica de upsert de `registrar_cartera()` en sí (sigue cubierta
por `tests/test_cartera_crud_api.py` para el uso ETL). **Bug lateral
encontrado al verificar C-2**: el mismo `create()` nunca pasaba
`cliente_id` a `registrar_cartera()` (pasaba `cliente`, la instancia ya
resuelta por el `ModelSerializer`) — la creación de CUALQUIER obligación
nueva vía este endpoint fallaba con "cliente no pertenece a esta empresa".
Corregido en el mismo commit. Test:
`tests/test_cartera_no_sobrescribe_obligacion_existente.py`.

**Resultado de test (2026-09-12):** `pytest apps/tenant/clientes/tests/`
completo → `51 passed, 1 error` (26 min). El `1 error` es
`test_cartera_concurrencia.py::test_dos_abonos_concurrentes_solo_uno_aplica_sin_sobrepago`
— **diagnosticado esta sesión** (ver nota "Estado real al cierre" de
2026-09-11 abajo, que dejó esto pendiente): reproducido en aislamiento
completo, **la aserción del test en sí PASA** ("1 passed" en la corrida
aislada) — el error es un `CommandError` de pytest-django al hacer
`flush` de la base de datos de test DESPUÉS de que el test ya terminó
(`transaction=True` + threads reales + schema-switching de django-tenants
es una combinación conocida por ser frágil en el teardown). No es una
regresión de C-1/C-2 (ese test no toca los selectors que se tocaron) ni
del código de producción — es un artefacto de infraestructura de test
reproducible independientemente del resto de la suite.

---

## Resultado real de pytest (2026-09-11) — INCOMPLETO, no asumir en verde

Se corrió `pytest apps/tenant/clientes/tests` dos veces esta sesión (la
primera vez que se logró ejecutar realmente en todo el día, tras el
incidente de memoria de la regresión de 4 apps documentado en `MEMORY.md`).

**Corrida 1** (~24 min, terminó completa): `5 failed, 44 passed, 1 error`.
Causa raíz de los 5 `failed`, confirmada y corregida en el código:
- `test_clientes_crud_workspace.py::test_clientes_crud_completo` y
  `::test_clientes_create_validaciones` — creaban un `Cliente` JURIDICA
  vía `ClienteViewSet` (que desde v3.12.0 exige representante legal) sin
  ningún contacto. **Corregido**: se agregó un contacto
  `es_representante_legal=True` al payload de ambos tests (esto es
  actualizar el fixture a la regla de negocio nueva, no debilitar la regla).
- `test_idempotence_v2614.py::test_api_create_cliente_http_201_first_post`
  y `::test_api_create_cliente_http_400_second_post_duplicado` — mismo
  causa raíz (API JURIDICA sin representante). **Corregido** igual.
- `test_representante_legal.py::test_actualizar_cliente_juridica_quitando_representante_falla`
  — bug en el test propio, no en el código de producción: el PATCH
  reenviaba el contacto sin su `id`, así que `sincronizar_contactos()` lo
  trataba como un contacto NUEVO con el mismo email → violaba
  `uniq_contacto_cliente_email` (error distinto al esperado). **Corregido**:
  el test ahora consulta el `id` real del contacto creado y lo incluye en
  el PATCH para que se trate como UPDATE.

**El `1 error`** fue en
`test_cartera_concurrencia.py::test_dos_abonos_concurrentes_solo_uno_aplica_sin_sobrepago`
— **la traceback real nunca se vio**: el comando original truncó la salida
guardada con `| tail -150` y el error quedó fuera de las últimas 150
líneas. Sigue sin diagnosticar.

**Corrida 2** (con las 4 correcciones ya aplicadas): el sistema mató el
proceso de pytest por memoria baja del host a los ~16 minutos, sin llegar
a completarse (segundo incidente de este tipo en la sesión, esta vez con
una suite mucho más chica que la de 4 apps del incidente anterior — parece
un problema de memoria disponible en la máquina en ese momento, no del
tamaño de la corrida). El contenedor `web` quedó reiniciado y sano. **Por
decisión explícita del usuario, no se reintentó de nuevo esta sesión.**

**Estado real al cierre de la sesión — pendiente para la próxima:**
1. Confirmar que las 4 correcciones de test realmente lo dejan en verde
   (nunca se vio una corrida completa con los fixes aplicados).
2. Diagnosticar el `ERROR` (no `FAILED`) de `test_cartera_concurrencia.py`
   — podría ser un problema real del test (fixture, threading, schema
   multi-conexión) o del entorno; no se debe asumir que el test de
   concurrencia (DEUDA-C06) está realmente cerrado hasta ver esa traceback.
3. Correr también `apps/tenant/bancos/tests/test_conciliacion_dispara_abono_cartera.py`
   (nunca se corrió esta sesión).

---

---

## v3.15.0 — DEUDA-C04: Cartera como Centro de Control (parcial, alcance de visualización) (2026-09-11)

La misión (secciones 36-48, 68-70) pedía que "Períodos... digo, Cartera"
evolucione a un centro de control operativo. Auditando lo ya construido
(sección 5 de la misión: "no empezar por frontend, primero la verdad del
backend"), se separó en dos alcances muy distintos:

**A) Visualización/KPIs (implementado en v3.15.0)** — encaja directo sobre
el modelo `Cartera` ya existente, sin inventar estados nuevos:
- `get_cartera_kpis_facturas_venta()` ahora desglosa `sin_pago_count`,
  `parcial_count`, `vencidas_count` (antes solo `pendiente`/`pagado`
  agregados) — sección 70.
- `qs_list_facturas_venta(solo_vencidas=True)` + filtro `?vencidas=1` en
  `GET /cartera/` — nuevo botón "Vencidas" en la barra de filtros
  (sección 40).
- Grid: columna "Emisión" agregada (antes faltaba, sección 37); "Fecha
  Vence" ahora muestra un badge "N días vencida" cuando aplica (nunca para
  facturas ya `PAGADA`, sección 39/CLI-02).
- Tests: `tests/test_cartera_kpis_y_filtro_vencidas.py` (2 casos).

**B) Workflow de aprobación/pago en lote (NO implementado, ver DEUDA-C07)**
— secciones 20-35 de la misión piden selección múltiple + "Aprobar
seleccionados" + "Autorizar pago seleccionados" + estados `EN_REVISION`/
`APROBADO` por factura antes del pago. **Esto no existe en el dominio
actual de `Cartera`**: hoy un abono se aplica directamente (sin un paso de
aprobación previo, `SIN_PAGO → PARCIAL → PAGADA` es la única máquina de
estados). Implementarlo requeriría diseñar una máquina de estados nueva
sobre `Cartera` (o sobre las facturas VENTA) sin evidencia en el código
actual de que ese flujo de aprobación exista o se necesite — mismo criterio
ya aplicado en `apps/tenant/empleados/` para el workflow de aprobación
individual por período (DEUDA-31 de ese módulo): no se inventa un paso de
negocio nuevo sin evidencia ni decisión explícita. Ver DEUDA-C07.

---

---

## v3.14.0 — DEUDA-C03 (Bancos dispara abono en Cartera) + DEUDA-C06 (test de concurrencia) (2026-09-11)

**Decisión del usuario para DEUDA-C03** (la misión pedía explícitamente no
inventar este flujo sin decisión de negocio): *"Bancos dispara un abono en
Cartera"* — al conciliar una `TransaccionBancaria` contra una `Factura`,
si esa factura es de naturaleza VENTA, se registra automáticamente un
abono en la `Cartera` asociada (creándola si no existía). `Cartera` queda
como la única fuente de verdad real de pagos.

**Implementado:**
- `CarteraBusinessService.registrar_abono_desde_conciliacion_bancaria()`
  (nuevo, `apps/tenant/clientes/`) — resuelve o crea la `Cartera` (mismo
  patrón `get_or_create` ya usado en `render_offcanvas_abono_factura()`),
  acota el monto al saldo disponible (nunca sobrepago por una discrepancia
  de céntimos entre el monto bancario y el saldo), y reutiliza
  `registrar_abono()` tal cual (sin duplicar sus guards).
- Hook en `apps/tenant/bancos/services/crud_service.py::
  conciliar_transaccion()` — se dispara solo en la transición real
  no-conciliada → conciliada (evita doble abono si se re-guarda la misma
  conciliación sin cambiar el flag); nunca propaga una excepción hacia el
  caller (mismo patrón defensivo ya usado ahí para
  `recalcular_estado_pago_automatico()`) — una discrepancia en Cartera no
  debe bloquear una conciliación bancaria ya válida en su propio dominio.
- **Limitación conocida, documentada, no resuelta:** des-conciliar una
  transacción (`conciliado: True → False`) NO revierte el abono ya
  aplicado — `Cartera` no tiene hoy un mecanismo de reverso de abonos (la
  misión, sección 74, pide explícitamente no improvisar un `DELETE`; un
  reverso real es una misión aparte).
- Tests: `apps/tenant/bancos/tests/test_conciliacion_dispara_abono_cartera.py`
  (4 casos: conciliar crea la Cartera y aplica el abono; re-guardar sin
  cambiar `conciliado` no duplica el abono; una Factura de COMPRA nunca
  genera Cartera — CxC ≠ CxP; un monto bancario mayor al saldo se acota en
  vez de fallar).

**DEUDA-C06 (test de concurrencia, sección 51/66 de la misión):**
- `apps/tenant/clientes/tests/test_cartera_concurrencia.py` — test real
  con `@pytest.mark.django_db(transaction=True)` + 2 threads +
  `threading.Barrier` (necesario: un test envuelto en la transacción
  automática de `TestCase`/`django_db` normal no detectaría un
  `select_for_update()` mal usado, porque las "conexiones" verían los
  mismos datos no confirmados). Cada hilo fija su propio `schema_context()`
  (el `search_path` es una propiedad de la conexión, no se hereda entre
  hilos) y cierra su conexión al terminar. Escenario: Cartera con saldo
  100.000, dos hilos abonan 60.000 cada uno simultáneamente — se verifica
  que exactamente uno aplica y el otro es rechazado por sobrepago, y que
  el saldo final nunca queda negativo ni el pagado excede el total.

**Nota de entorno, aplica a v3.12.0/v3.13.0/v3.14.0 completas:** ningún
test de esta sesión pudo ejecutarse con pytest real (intento de regresión
en otros 4 apps tardó >2.5h y fue terminado por el sistema por memoria
baja del host; no reintentado por decisión del usuario). Todo se verificó
con `manage.py check`, `makemigrations --check --dry-run`, `py_compile` y
`ruff` (limpios), y con revisión manual línea por línea del código de
concurrencia/threading (sin poder ejecutarlo). **No asumir en verde sin
correr la suite real en la próxima sesión.**

---

---

## v3.13.0 — CarteraNota: Historial de Notas de Seguimiento (2026-09-11)

**Contexto:** continuación de la misión "Clientes + Cartera" sobre DEUDA-C05
(secciones 29-30: `Cartera.observaciones` es un único campo que se
sobrescribe, sin historial de múltiples interacciones).

**Implementado:**
- `CarteraNota` (nuevo modelo, migración `0010`) — `empresa`, `cartera` (FK
  CASCADE), `usuario` (FK `perfil.TenantProfile`, SET_NULL), `tipo`
  (SEGUIMIENTO/PROMESA_PAGO/DISPUTA/OTRO), `texto`. Append-only: sin
  update/delete en el Service Layer, mismo criterio de inmutabilidad que
  otras entidades de historial en este proyecto. **No reemplaza**
  `Cartera.observaciones`, que sigue existiendo sin cambios.
- `CarteraBusinessService.agregar_nota()` + `CarteraSelector.get_notas()`.
- `CarteraViewSet.notas` (nuevo, `GET`/`POST`
  `/api/v1/clientes/cartera/{uuid}/notas/`) — el `POST` retorna el
  historial completo actualizado (para refresco inmediato en el frontend).
- `offcanvas_abono_cartera.html` ahora muestra días de vencimiento (badge
  cuando aplica) y el historial de notas + un mini-formulario para agregar
  una nueva, independiente del abono (mismo offcanvas, sección separada) —
  sección 26-29 de la misión: "mostrar contexto del cobro para que el
  administrador pueda decidir el abono".
- Frontend: `clientes.api.js` (`getNotas`/`agregarNota`), `clientes.
  cartera.js` (`initNotaForm`, sin `location.reload()` — re-renderiza la
  lista con la respuesta del POST).
- Tests: `tests/test_cartera_notas.py` (4 casos: agregar nota via service,
  texto vacío rechazado, GET/POST via API con historial actualizado, 400
  si el texto viene vacío vía API).

**Actualización v3.14.0:** DEUDA-C06 (test de concurrencia) sí se
implementó — ver sección v3.14.0 más arriba en este archivo.

**Nota de entorno (aplica a todo lo de esta sesión, no solo a v3.13.0):**
esta sesión no pudo correr pytest sobre `clientes` — un intento de
regresión sobre otros 4 apps tardó >2.5h sin terminar y el sistema mató el
proceso por memoria baja del host; por decisión del usuario no se
reintentó pytest el resto de la sesión. Todo lo de v3.12.0/v3.13.0 está
verificado con `manage.py check`, `makemigrations --check --dry-run`,
`py_compile`, `ruff` y `node --check` (todos limpios), pero **no con la
suite de tests real** — no asumir en verde sin correrla.

---

## v3.12.0 — Auditoría "Clientes + Cartera": Representante Legal + Fix de Doble Fuente de Verdad en Pagos (2026-09-11)

**Contexto:** mision "PLAN MAESTRO DE EJECUCIÓN — Clientes + Cartera/CxC"
(auditar, no reconstruir). Se auditó el código real contra la documentación
existente (este archivo) y se encontraron dos contradicciones reales.

### Hallazgo 1 — Representante Legal (secciones 7-10 de la misión)

**Encontrado:** `Cliente.tipo_persona=JURIDICA` no exigía ningún
representante legal. `ContactoCliente` no tenía ningún campo/rol que
distinguiera un contacto cualquiera de un representante legal (Caso C del
mission brief: "no existe representación legal real").

**Corregido:**
- `ContactoCliente.es_representante_legal` (nuevo, migración `0009`).
- `ClienteBusinessService.validar_representante_legal(cliente, empresa_id)`
  — JURIDICA exige ≥1 `ContactoCliente` activo con
  `es_representante_legal=True`; NATURAL no lo requiere.
- Se invoca desde `registrar_cliente_completo()` **solo si el caller pasa
  `validar_representante=True`** (opt-in explícito, default `False`) — y
  solo al crear o cuando la petición toca `contactos` explícitamente. Esto
  evita romper dos flujos reales que crean `Cliente` JURIDICA sin datos de
  representante disponibles en ese momento: `resolver_o_crear_desde_
  factura_venta()` (snapshot desde XML de factura de venta — el XML no
  trae esa información) y el wrapper legacy `services.crear_cliente()`
  (usado solo por `test_service_crear_cliente_idempotente`, que crea un
  cliente JURIDICA sin contactos). `ClienteViewSet.create/update/
  partial_update` (el formulario real de captura manual) sí pasa
  `validar_representante=True` — es el único punto donde la misión pedía
  esta regla.
- Frontend: checkbox "Representante Legal" agregado junto a "Principal" en
  `clientes.utils.js` (fila dinámica) y `offcanvas_editar_cliente.html`
  (filas precargadas del servidor); `clientes.editor.js` lo incluye en el
  payload. Badge "Representante Legal" en `offcanvas_detalle_cliente.html`.
- Tests: `tests/test_representante_legal.py` (5 casos: NATURAL sin
  representante funciona, JURIDICA sin representante falla con 400 y no
  crea el cliente, JURIDICA con representante funciona, PATCH que quita el
  representante falla, PATCH que no toca `contactos` NO falla aunque el
  cliente histórico nunca haya tenido representante).

### Hallazgo 2 — Doble Fuente de Verdad en Pagos (secciones 12-16, 34-35)

**Encontrado (bug real, no solo teórico):** `CarteraSelector.
qs_list_facturas_venta()` / `get_cartera_kpis_facturas_venta()` (Pull
Model, leen `Factura.naturaleza='VENTA'`) inferían `valor_pagado`/`saldo`
desde el enum `Factura.estado_pago` de 3 valores
(`FacturaCxCListSerializer.get_valor_pagado()`: `total` si `PAGADA`, si no
`'0.00'` — **sin importar el estado real**). Mientras tanto, el monto REAL
de los abonos vive en `Cartera.valor_pagado`/`saldo`
(`CarteraBusinessService.registrar_abono()`, con `select_for_update()`,
correcto). Resultado: una factura con un abono parcial de $300.000 sobre
$1.000.000 se mostraba en la pestaña Cartera como **"Sin Pago, saldo
$1.000.000"** — el abono ya registrado desaparecía visualmente. Esta línea
de este mismo archivo (v3.11.0, ahora corregida abajo) documentaba este
comportamiento como diseño intencional ("Calcula saldo desde estado_pago
DIAN"), sin detectar el conflicto con `Cartera.registrar_abono()`.

**Nota de higiene documental:** v3.11.0 también afirmaba que
`FacturaCxCListSerializer` exponía `total_pagado_bancos`/`saldo_pendiente`
vía `BancosBridge` — verificado contra el código real: **eso no existe en
el serializer actual** (esos campos sí existen en los serializers propios
de `apps/tenant/facturas/api/serializers.py`, no en este). Corregido en
§Puntos de Integración abajo — la doc había divergido del código.

**Corregido:**
- `CarteraSelector.get_cartera_map_by_factura_uuids(empresa_id,
  factura_uuids)` (nuevo) — bulk lookup (sin N+1) de `Cartera` por
  `factura_uuid`.
- `CarteraViewSet.list()` arma ese mapa y lo pasa como `context` al
  serializer; `FacturaCxCListSerializer` ahora usa
  `valor_pagado`/`saldo`/`estado_pago` REALES de `Cartera` cuando existe
  una obligación vinculada a la factura, y solo cae al fallback anterior
  (basado en el enum) cuando la factura nunca fue tocada por Cartera
  (comportamiento previo intacto para ese caso, sin regresión).
- `get_cartera_kpis_facturas_venta()` — mismo fix vía `Subquery` sobre
  `Cartera.saldo` (sin N+1, sin cargar filas en Python) para
  `pendiente_monto`.
- Tests: `tests/test_cartera_pull_model_saldo_real.py` (2 casos: abono
  parcial real se refleja en `list()` y `kpis()`; factura sin Cartera
  asociada mantiene el fallback anterior sin regresión).

### Explícitamente NO implementado en esta pasada (ver §Deudas Técnicas)

La misión completa (85 secciones) pide además un "centro de control"
operativo de Cartera: selección múltiple, notas de seguimiento
(`CarteraNota`), y sobre todo la **unificación real Bancos↔Cartera**
(hoy dos mecanismos de pago totalmente independientes — ver DEUDA-C02).
Cada uno es una misión de tamaño comparable a lo ya corregido aquí; no se
improvisaron a medias. Ver DEUDA-C01/C02/C03 abajo.

---

## Documentación Especializada (SSoT)

| Documento | Descripción | Estado |
| :--- | :--- | :--- |
| [Este archivo](AUDITORIA_FLUJO_CLIENTES.md) | Portal SSoT + Resultados de Auditoría | ACTUALIZADO 2026-06-04 |
| [Garantía DSV](GARANTIA_SEGURIDAD_DSV.md) | IDOR Prevention | ✅ |
| [Arquitectura](docs/clientes_microtasks_architecture.md) | Microtareas FSD | ✅ |
| [Mapas de Flujo](docs/clientes_flow_map.md) | Diagramas Mermaid | ✅ |
| [Lógica de Negocio](docs/clientes_business_logic.md) | Reglas de negocio | ✅ |

---

## Responsabilidades Core (v3.11.0)

1. **Gestión de identidad legal**: SSoT por empresa — unicidad `(empresa, tipo_documento, numero_documento)`
2. **Normativa tributaria colombiana**: retenciones (Retefuente, ReteICA, ReteIVA) por cliente
3. **Contactos**: modelo `ContactoCliente` con is_principal, unicidad `(cliente, email)`
4. **Cartera / Cuentas por Cobrar**: Pull Model desde `Factura.naturaleza='VENTA'` (ADR-001, §18)
5. **Registro de abonos**: `registrar_abono()` con `select_for_update()` anti race-condition
6. **Importación idempotente**: `resolver_o_crear_desde_factura_venta()` — upsert sin duplicados
7. **UUID lookup** (AGENTS.md §14) — nunca PK entero en URLs
8. **DSV Zero-Trust** (AGENTS.md §13) — `get_object()` valida UUID + empresa_id

---

## Changelog Versiones

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| **v3.5.0** | 2026-04 | UUID lookup, DSV, Service Layer, Retenciones, offcanvas 800px |
| **v3.8.0** | 2026-05 | Modelo Cartera + CarteraViewSet + Pull Model desde Facturas |
| **v3.10.4** | 2026-05-28 | FIX-001 MRO ContactoSelector / FIX-002 UUID en contactos frontend / FIX-003 ProtectedError |
| **v3.11.0** | 2026-06-04 | Integración Bancos↔Facturas — campos `total_pagado_bancos`, `saldo_pendiente` expuestos en CarteraListSerializer via Pull Model |

---

## Modelos (`models.py`) — 4 modelos, 10 migraciones (mig `0009`: `ContactoCliente.es_representante_legal` v3.12.0; mig `0010`: `CarteraNota` v3.13.0)

### Cliente

```python
class Cliente(SintelTenantBaseModel):
    uuid             = UUIDField(unique=True, db_index=True, editable=False)
    empresa          = FK(Empresa, PROTECT)                    # SSoT multi-tenant
    tipo_persona     = CharField  # NATURAL | JURIDICA
    tipo_documento   = CharField  # CC | CE | NIT | PA
    numero_documento = CharField(db_index=True)                # normalizado sin espacios/guiones
    razon_social     = CharField(max_length=180)
    nombre_comercial = CharField(blank=True)
    regimen_tributario = CharField  # SIMPLE | ORDINARIO | NO_RESP
    # Retenciones colombianas (v3.5.0):
    es_retenedor          = BooleanField
    aplica_retefuente     = BooleanField; retefuente_porcentaje = DecimalField
    aplica_reteica        = BooleanField; reteica_porcentaje    = DecimalField
    aplica_reteiva        = BooleanField; reteiva_porcentaje    = DecimalField
    # Contacto básico:
    email = EmailField; telefono = CharField; direccion = CharField; ciudad = CharField
    activo        = BooleanField(default=True)
    observaciones = TextField

    class Meta:
        constraints = [UniqueConstraint(fields=['empresa','tipo_documento','numero_documento'])]
        indexes     = [Index(['empresa','activo']), Index(['numero_documento'])]
        ordering    = ['razon_social']
```

### ContactoCliente

```python
class ContactoCliente(SintelTenantBaseModel):
    uuid           = UUIDField(unique=True, db_index=True, editable=False)
    cliente        = FK(Cliente, CASCADE, related_name='contactos')
    nombre_completo = CharField(max_length=180)
    cargo          = CharField(blank=True)
    email          = EmailField
    telefono       = CharField(blank=True)
    activo         = BooleanField(default=True)
    is_principal   = BooleanField(default=False)              # contacto principal
    es_representante_legal = BooleanField(default=False)      # mig 0009, v3.12.0 — rol legal

    class Meta:
        constraints = [UniqueConstraint(fields=['cliente','email'])]
        indexes     = [Index(['cliente','activo']), Index(['cliente','is_principal'])]
        ordering    = ['-is_principal', 'nombre_completo']
```

### Cartera (Cuentas por Cobrar) — mig 0008

```python
class Cartera(SintelTenantBaseModel):
    uuid            = UUIDField(unique=True, db_index=True, editable=False)
    empresa         = FK(Empresa, PROTECT)
    cliente         = FK(Cliente, CASCADE)
    numero_factura  = CharField(max_length=50)
    factura_uuid    = UUIDField(null=True, blank=True, db_index=True)  # soft-ref §18
    fecha_emision   = DateField
    fecha_vencimiento = DateField
    valor_total     = DecimalField(18,2)
    valor_pagado    = DecimalField(18,2, default=0)
    saldo           = DecimalField(18,2, editable=False)  # auto en save()
    estado_pago     = CharField  # SIN_PAGO | PARCIAL | PAGADA (auto en save())
    observaciones   = TextField

    def save(...):
        self.valor_pagado = max(0, self.valor_pagado or 0)
        self.saldo        = self.valor_total - self.valor_pagado
        if self.saldo <= 0:        estado_pago = 'PAGADA'
        elif self.valor_pagado > 0: estado_pago = 'PARCIAL'
        else:                       estado_pago = 'SIN_PAGO'

    class Meta:
        constraints = [UniqueConstraint(fields=['empresa','cliente','numero_factura'])]
        indexes     = [Index(['empresa','estado_pago']), Index(['empresa','cliente','estado_pago']),
                       Index(['numero_factura']), Index(['fecha_vencimiento']), Index(['factura_uuid'])]
        ordering    = ['fecha_vencimiento', 'numero_factura']
```

**Nota:** `factura_uuid` es soft-reference (UUIDField nullable, no FK) siguiendo Bounded Context §18. El CRUD de Cartera es independiente del módulo Facturas.

### Migraciones

| # | Contenido |
|---|---|
| 0001 | Crea `Cliente`, `ContactoCliente` base |
| 0002 | Agrega `uuid` fields (UUID lookup §14) |
| 0003 | Agrega 6 campos de retención (es_retenedor, aplica_*, porcentajes) |
| 0004 | Agrega `cuenta_contable_uuid` (deprecated) |
| 0005 | Altera constraints de retención |
| 0006 | Ajustes de retención adicionales |
| 0007 | **Elimina** `cuenta_contable_uuid` (Desacoplamiento Contable v3.7.2) |
| 0008 | Crea modelo `Cartera` (CxC, v3.8+) |

---

## Service Layer

### `selectors.py` — Consultas Zero Waste

**Constantes SSoT (`.only()` garantizado):**

| Constante | Uso | # Campos |
|---|---|---|
| `LIST_FIELDS` | Tabulator list | 26 |
| `DETAIL_FIELDS` | Detail/edit | 50 |
| `CONTACT_FIELDS` | Contactos list | 9 |
| `CARTERA_FIELDS` | Cartera list | 12 |
| `_CLIENTE_TRAVERSALS` | Traversals FK via select_related | — |
| `_CARTERA_CLIENTE_TRAVERSALS` | Cartera→Cliente traversals | — |

#### ClienteSelector

| Método | Descripción |
|--------|-------------|
| `get_cliente_list(empresa_id, search, filters)` | `.only(LIST_FIELDS).order_by('razon_social')`. Soporta search (icontains en 4 campos) y filters (tipo_persona, es_retenedor, activo) |
| `get_cliente_detail(empresa_id, pk)` | `.only(DETAIL_FIELDS)` + prefetch contacts |
| `get_kpis(empresa_id)` | Una sola query de agregación: total, activos, inactivos, jurídicas, naturales, retenedores |
| `get_cartera_resumen(empresa_id, cliente_uuids)` | Bulk aggregation para N clientes en una query. Retorna dict `{uuid: {pendiente_count, pendiente_monto, cobrada_count, total_count}}` — usado en list() para evitar N+1 |
| `existe_documento(empresa_id, tipo, numero, exclude_uuid)` | `.only('id').exists()` — DSV pre-insert |
| `get_cliente_by_documento(empresa_id, tipo, numero)` | Resolución por documento legal (ETL XML) |

#### ContactoSelector

| Método | Descripción |
|--------|-------------|
| `get_contacto_list(empresa_id, cliente_id=None)` | `select_related('cliente').only(CONTACT_FIELDS + _CLIENTE_TRAVERSALS)`. Ordenado por `-is_principal, nombre_completo` |

#### CarteraSelector

| Método | Descripción |
|--------|-------------|
| `get_cartera_list(empresa_id, cliente_id, estado_pago, search)` | `select_related('cliente').only(CARTERA_FIELDS + _CARTERA_CLIENTE_TRAVERSALS)` |
| `get_cartera_detail(empresa_id, uuid)` | Detalle con traversal cliente |
| **`qs_list_facturas_venta(empresa_id, cliente_uuid, estado_pago, search)`** | **Pull Model §18**: lee de `Factura.naturaleza='VENTA'` (no de Cartera). Mapea estados DIAN → estados Cartera |
| `get_cartera_kpis_facturas_venta(empresa_id)` | KPIs desde Facturas VENTA (SSoT) |
| `get_cartera_kpis(empresa_id)` | KPIs desde Cartera legacy |

### `crud_service.py` — Persistencia @atomic

| Servicio | Métodos | Guards |
|---|---|---|
| `ClienteCRUDService` | `create_cliente`, `update_cliente`, `delete_cliente` | IntegrityError → ValidationError; delete solo si `activo=False`; ProtectedError → ValidationError con lista de modelos |
| `ContactoCRUDService` | `create_contacto`, `update_contacto`, `delete_contacto` | IntegrityError `uniq_contacto_cliente_email` |
| `CarteraCRUDService` | `create_cartera`, `update_cartera`, `delete_cartera` | IntegrityError `uniq_cartera_factura_cliente`; ProtectedError |

### `business_service.py` — Reglas de Negocio

#### ClienteBusinessService

| Método | Descripción |
|--------|-------------|
| `normalize_document_number(value)` | Strip, quita espacios/puntos/guiones, uppercase |
| `registrar_cliente_completo(empresa_id, data, contactos_raw, cliente_instance)` | Upsert por documento. Llama `_sanitize_retenciones()` + `sincronizar_contactos()`. Retorna `(cliente, was_created)` |
| `resolver_o_crear_desde_factura_venta(...)` | @atomic. Idempotente para ETL XML. Busca por NIT normalizado, crea si no existe con nombre auto-generado. Crea contacto principal si tiene email. |
| `sincronizar_contactos(empresa_id, cliente_id, contactos_raw)` | Full sync Create/Update/Delete. Valida nombre_completo y email obligatorios. |
| `_sanitize_retenciones(payload)` | Zero Trust: si `es_retenedor=False` → cero todos los flags/porcentajes. Si `es_retenedor=True` → cero porcentajes donde el flag individual es False. |

#### CarteraBusinessService

| Método | Descripción |
|--------|-------------|
| `registrar_cartera(empresa_id, data)` | @atomic. `get_or_create()` por `(empresa, cliente, numero_factura)`. Idempotente para ETL. |
| `registrar_abono(empresa_id, cartera_uuid, monto)` | @atomic. `select_for_update()` anti-race. Valida: monto > 0, no doble pago, monto ≤ saldo. Incrementa valor_pagado. |

### `api_mixins.py` — Bridges ViewSet → Service

Todos heredan `BaseServiceMixin` (canonical, v3.10.1):

| Mixin | selector_class | crud_service_class | Métodos bridge |
|---|---|---|---|
| `ClienteServiceMixin` | ClienteSelector | ClienteCRUDService | `get_qs_list()`, `get_qs_detail()`, `service_registrar_cliente()` |
| `ContactoClienteServiceMixin` | ContactoSelector | ContactoCRUDService | `get_qs_contactos(cliente_id)` |
| `CarteraServiceMixin` | CarteraSelector | CarteraCRUDService | `get_qs_list()` → qs_list_facturas_venta (Pull Model) |

**FIX-001 (v3.10.4):** `contacto_selector` usa instancia directa `ContactoSelector()` en vez de `self.selector_class()` para evitar colisión MRO cuando `ClienteViewSet` hereda ambos mixins.

---

## API Layer

### Serializers (`api/serializers.py`) — 8 serializadores

| Serializer | Uso | Notas |
|---|---|---|
| `ClienteMiniSerializer` | Nested read-only en Cotizaciones/Proyectos | 7 campos mínimos |
| `ClienteListSerializer` | GET `/` — Tabulator | `get_encargado()` lee de `contactos_prefetched[0]`; `get_cartera_resumen()` lee del context `cartera_map` (cero N+1) |
| `ClienteDetailSerializer` | POST/PATCH — CRU | NormalizationMixin + Zero Trust: normaliza doc, valida unicidad en create y update (exclude self) |
| `ContactoClienteSerializer` | CRUD contactos | DSV: valida `cliente.empresa_id == empresa_id`; normaliza email lowercase |
| `CarteraListSerializer` | GET cartera list | Traversals cliente; mapea estado_pago display |
| `CarteraDetailSerializer` | POST/PATCH cartera | Validaciones: valor_total > 0; valor_pagado ≤ valor_total; fechas coherentes |
| `FacturaCxCListSerializer` | **Pull Model §18** | Read-only. Mapea Factura.VENTA → display Cartera. Sin FK a Factura. Calcula saldo desde estado_pago DIAN. |
| `CarteraAbonoSerializer` | POST abono | Input-only: `monto` (DecimalField, min_value=0.01) |

### ViewSets (`api/viewsets.py`) — 3 ViewSets, ~1003 líneas

#### ClienteViewSet

```
Herencia : ClienteServiceMixin + ContactoClienteServiceMixin + CarteraServiceMixin
           + SintelDSVMixin + BaseTenantViewSet
Lookup   : uuid
Permisos : IsTenantMember + IsTenantAdminOrReadOnly
Parsers  : JSONParser + FormParser + MultiPartParser
```

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/clientes/` | GET | list() — paginated + cartera_map sin N+1 |
| `/api/v1/clientes/kpis/` | GET | Aggregation única: total, activos, retendores |
| `/api/v1/clientes/` | POST | create() — upsert via registrar_cliente_completo |
| `/api/v1/clientes/{uuid}/` | GET | retrieve() — DSV |
| `/api/v1/clientes/{uuid}/` | PATCH/PUT | update() — upsert + sync contactos |
| `/api/v1/clientes/{uuid}/` | DELETE | destroy() — solo si activo=False |
| `/api/v1/clientes/render-offcanvas/crear/` | GET | HTML offcanvas crear |
| `/api/v1/clientes/{uuid}/render-offcanvas/editar/` | GET | HTML offcanvas editar + contactos |
| `/api/v1/clientes/{uuid}/render-offcanvas/detalle/` | GET | HTML offcanvas read-only |
| `/api/v1/clientes/offcanvas/` | GET | Alias legacy |

**list() — Zero N+1:**
```python
# 1 query para clientes + 1 query bulk para cartera de todos los clientes en la página
cartera_map = ClienteSelector.get_cartera_resumen(empresa_id, [c.uuid for c in page])
serializer = ClienteListSerializer(page, context={'cartera_map': cartera_map}, many=True)
```

#### ContactoClienteViewSet

```
Herencia : ContactoClienteServiceMixin + SintelDSVMixin + BaseTenantViewSet
Lookup   : uuid
Permisos : IsTenantMember + IsTenantAdminOrReadOnly
```

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/clientes/contactos/` | GET | list — filtrar por ?cliente_id= |
| `/api/v1/clientes/contactos/` | POST | create |
| `/api/v1/clientes/contactos/{uuid}/` | PATCH | partial_update |
| `/api/v1/clientes/contactos/{uuid}/` | DELETE | destroy |
| `/api/v1/clientes/contactos/gestor-offcanvas/` | GET | HTML manager de contactos |
| `/api/v1/clientes/contactos/render-offcanvas/crear/` | GET | HTML crear contacto |
| `/api/v1/clientes/contactos/{uuid}/render-offcanvas/editar/` | GET | HTML editar contacto |
| `/api/v1/clientes/contactos/{uuid}/render-offcanvas/detalle/` | GET | HTML read-only |

#### CarteraViewSet

```
Herencia : CarteraServiceMixin + SintelDSVMixin + BaseTenantViewSet
Lookup   : uuid
Permisos : IsTenantMember
```

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/clientes/cartera/` | GET | list() — **Pull Model**: lee Factura.VENTA; filtros ?cliente_uuid, ?estado_pago |
| `/api/v1/clientes/cartera/kpis/` | GET | KPIs desde Facturas VENTA |
| `/api/v1/clientes/cartera/` | POST | create() — registrar_cartera (idempotente) |
| `/api/v1/clientes/cartera/{uuid}/` | PATCH | partial_update — solo fecha_vencimiento, observaciones, numero_factura, factura_uuid |
| `/api/v1/clientes/cartera/{uuid}/` | DELETE | destroy() — solo si estado_pago == SIN_PAGO |
| `/api/v1/clientes/cartera/{uuid}/registrar-abono/` | POST | Abono con select_for_update |
| `/api/v1/clientes/cartera/render-offcanvas/crear/` | GET | HTML crear cartera |
| `/api/v1/clientes/cartera/render-offcanvas/abono-factura/` | GET | HTML abono por factura_uuid (smart resolution) |
| `/api/v1/clientes/cartera/{uuid}/render-offcanvas/abono/` | GET | HTML abono por cartera uuid |

**`render_offcanvas_abono_factura()` — Smart Resolution:**
```
1. Busca Cartera por factura_uuid
2. Si no existe y Factura tiene cliente_uuid → crea Cartera automáticamente
3. Si sin cliente → renderiza form crear-cartera con prefill de factura
4. Si encontrada → renderiza form de abono
```

### URLs (`api/urls.py`)

```python
# ORDEN CRÍTICO: rutas específicas antes del comodín
router.register(r"contactos", ContactoClienteViewSet, basename="contacto")
router.register(r"cartera",   CarteraViewSet,          basename="cartera")
router.register(r"",          ClienteViewSet,           basename="cliente")  # wildcard último
```

---

## Frontend

### Templates (`templates/tenant/clientes/`) — 10 archivos

| Template | Descripción |
|---|---|
| `clientes_list.html` | Grid principal + KPI cards |
| `offcanvas_crear_cliente.html` | Form crear cliente |
| `offcanvas_editar_cliente.html` | Form editar + contactos anidados |
| `offcanvas_detalle_cliente.html` | Read-only detail |
| `contactos_list.html` | Grid de contactos |
| `contactos_offcanvas.html` | Manager de contactos (modal) |
| `offcanvas_crear_cartera.html` | Registrar CxC |
| `offcanvas_abono_cartera.html` | Registrar abono |
| `assets_clientes.html` | Carga de assets JS/CSS |
| `list.html` | Stub de entrada |

### JavaScript (`static/clientes/js/`) — 8 módulos, ~125 KB

| Archivo | Namespace | Responsabilidad |
|---|---|---|
| `clientes.api.js` | `window.Sintel.Clientes.API` | SSoT endpoints. Objetos frozen immutables. `window.http()` para todas las llamadas |
| `clientes.list.js` | `...CuentaList` / `...List` | Tabulator grid + KPI cards + filtros + row events |
| `clientes.editor.js` | `...Editor` | Form builder crear/editar. Contactos anidados. Toggle retenciones |
| `clientes.cartera.js` | `...Cartera` | Cartera grid + KPIs + abono flow + due-date highlighting |
| `clientes.contactos.js` | `...Contactos` | CRUD contactos + offcanvas management |
| `clientes.detalle.js` | `...Detalle` | Detail view read-only |
| `clientes.utils.js` | `...Utils` | Normalización teléfono/documento, validadores |
| `clientes.module.js` | `...Module` | Inicialización namespace global |

---

## Patrones Arquitecturales Clave

### 1. Zero Waste Queries (AGENTS.md §4.5)

```python
# Todo queryset usa .only() con constantes explícitas
qs = Cliente.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS)

# Aggregation para KPIs en una sola query
Cliente.objects.filter(empresa_id=empresa_id).aggregate(
    total=Count('id'), activos=Count('id', filter=Q(activo=True)), ...
)
```

### 2. Zero N+1 en list()

```python
# ViewSet list(): 2 queries para toda la página, nunca N+1
# Query 1: clientes de la página (paginado)
# Query 2: bulk cartera summary para todos los clientes de la página
cartera_map = ClienteSelector.get_cartera_resumen(empresa_id, [c.uuid for c in page])
# Los serializers leen del contexto, no ejecutan queries
```

### 3. Pull Model Cartera (ADR-001, §18)

```python
# CarteraViewSet.list() lee de Facturas, NO de Cartera
# Bounded Context: sin FK directa entre apps
qs = CarteraSelector.qs_list_facturas_venta(empresa_id)
# → Factura.objects.filter(empresa_id=empresa_id, naturaleza='VENTA')
```

### 4. Double Semantic Verification (DSV)

```python
# get_object() valida AMBAS condiciones
def get_object(self):
    obj = super().get_object()
    if obj.empresa_id != self.get_empresa_id():
        # Log intento IDOR
        raise PermissionDenied()
    return obj
```

### 5. Importación Idempotente

```python
# Seguro para re-ejecución de ETL
cliente, created = ClienteBusinessService.resolver_o_crear_desde_factura_venta(
    empresa_id=empresa_id,
    receptor_nit=nit,
    receptor_razon_social=nombre,
    receptor_email=email,
)
```

### 6. Abono con select_for_update()

```python
# Anti race-condition en pagos concurrentes
cartera = Cartera.objects.select_for_update().get(uuid=uuid, empresa_id=empresa_id)
# Nadie más puede modificar esta fila hasta commit
cartera.valor_pagado += monto
cartera.save()  # → auto-recalcula saldo y estado_pago
```

---

## Conformidad AGENTS.md

| Regla | Sección | Estado |
|---|---|---|
| `SintelTenantBaseModel` en todos los modelos | §14 | ✅ |
| `empresa_id` en todas las queries | §4 | ✅ |
| `.only()` en todos los selectores | §4.5 | ✅ |
| `select_related()` donde hay FK traversals | §4.5 | ✅ |
| `uuid` como lookup_field | §14, §25 | ✅ |
| `BaseTenantViewSet` en herencia | §15 | ✅ |
| `IsTenantMember + IsTenantAdminOrReadOnly` | §15 | ✅ |
| `SintelDSVMixin` + DSV en get_object() | §13 | ✅ |
| `@transaction.atomic` en CRUD | §5 | ✅ |
| `select_for_update()` en abonos | §5 | ✅ |
| Service Layer separado (CRUD + Business) | §5 | ✅ |
| Pull Model — Cartera lee de Facturas | §18 | ✅ |
| Soft reference UUIDs (no FK cross-app) | §18 | ✅ |
| `window.http()` para mutaciones JS | §31 | ✅ |
| SSoT endpoints en `clientes.api.js` | §31 | ✅ |
| `window.Sintel.Clientes.*` namespace FSD | §23 | ✅ |
| Retenciones Pull Model → RetencionesService | ADR-001 | ✅ |
| `cuenta_contable_uuid` eliminado | v3.7.2 | ✅ |

**16/16 ✅ COMPLIANCE**

---

## Fixes Históricos

### FIX-001 — ContactoSelector MRO (v3.10.4)

**Error:** `AttributeError: 'ClienteSelector' object has no attribute 'get_contacto_list'`
**Causa:** MRO Python: `ClienteViewSet` hereda `(ClienteServiceMixin, ContactoClienteServiceMixin)`. `selector_class = ClienteSelector` de `ClienteServiceMixin` sobreescribía `selector_class = ContactoSelector` de `ContactoClienteServiceMixin`. La property `contacto_selector` devolvía `ClienteSelector()` en lugar de `ContactoSelector()`.
**Fix:** `contacto_selector` usa instancia directa `ContactoSelector()` — inmune a MRO.

### FIX-002 — Contacto UUID en frontend (v3.10.4)

**Error:** `ValidationError: "41" no es un UUID válido` en PATCH /contactos/41/
**Causa:** JS y template usaban `data.id` (PK entero). ViewSet tiene `lookup_field = 'uuid'`.
**Fix:** `data-contacto-id="${data.uuid}"` en JS y `{{ contacto.uuid }}` en template.

### FIX-003 — ProtectedError al eliminar cliente (v3.10.4)

**Error:** `ProtectedError: TareaCorta.cliente` FK con `on_delete=PROTECT`
**Fix:** `TareaCorta.cliente → SET_NULL` + captura `ProtectedError` en `delete_cliente()` con mensaje legible.

---

## Puntos de Integración

| Módulo | Tipo | Contrato |
|---|---|---|
| **Facturas** | Pull Model (lectura) | `CarteraSelector.qs_list_facturas_venta()` lee `Factura.naturaleza='VENTA'`. Sin FK directa. |
| **Contabilidad** | Pull Model (delegación) | Retenciones se delegan a `RetencionesService` (ADR-001). Clientes solo guarda config (porcentajes). |
| **Cotizaciones** | Soft reference | Cotizaciones usa `ClienteMiniSerializer` para info básica. |
| **Proyectos** | FK SET_NULL | `TareaCorta.cliente` → SET_NULL al eliminar cliente. Snapshot `cliente_nombre` persiste. |
| **Bancos** | Independiente (ver DEUDA-C02) | `Factura.total_pagado_bancos`/`saldo_pendiente` (via `BancosBridge`, en `apps/tenant/facturas/`) es un mecanismo de conciliación bancaria **separado** de `Cartera.registrar_abono()` — corrección v3.12.0: la afirmación anterior de que `FacturaCxCListSerializer` exponía estos campos era incorrecta, verificado contra código real. Los dos mecanismos pueden marcar la misma factura con estados de pago distintos entre sí sin sincronizarse (ver DEUDA-C02). |

---

## Deudas Técnicas

| ID | Archivo | Prioridad | Descripción | Estado |
|---|---|---|---|---|
| DEUDA-C01-CERRADO | `models.py`, `business_service.py`, frontend | ~~ALTA~~ | JURIDICA sin representante legal obligatorio. Corregido v3.12.0: `es_representante_legal` + `validar_representante_legal()`. Ver sección v3.12.0 arriba. | CERRADO |
| DEUDA-C02-CERRADO | `services/selectors.py`, `api/serializers.py`, `api/viewsets.py` | ~~CRÍTICA~~ | Doble fuente de verdad: `FacturaCxCListSerializer` ignoraba abonos parciales reales de `Cartera`. Corregido v3.12.0: `get_cartera_map_by_factura_uuids()` + Subquery en KPIs. Ver sección v3.12.0 arriba. | CERRADO |
| DEUDA-C03-CERRADO | `apps/tenant/bancos/services/crud_service.py`, `apps/tenant/clientes/services/business_service.py` | ~~ALTA~~ | Decisión del usuario (2026-09-11): "Bancos dispara un abono en Cartera". Corregido v3.14.0: `registrar_abono_desde_conciliacion_bancaria()` + hook en `conciliar_transaccion()`. Limitación conocida y documentada: des-conciliar no revierte el abono (ver sección v3.14.0). | CERRADO |
| DEUDA-C04-CERRADO (parcial) | `services/selectors.py`, `api/viewsets.py`, frontend | ~~MEDIA~~ | Alcance de visualización/KPIs de la misión (secciones 36-40, 68-70): desglose sin_pago/parcial/vencidas en KPIs, filtro "Vencidas", columna "Emisión", badge de días vencida. Corregido v3.15.0. El alcance de workflow de aprobación/pago en lote (secciones 20-35) se separó a DEUDA-C07 (requiere una máquina de estados nueva, no existe evidencia de que se necesite hoy). | CERRADO (alcance de visualización) |
| DEUDA-C07 | `models.py` (`Cartera`), frontend | MEDIA-ALTA (requiere decisión de negocio, no se inventó) | Workflow de aprobación/pago en lote por factura (secciones 20-35 de la misión): selección múltiple, "Aprobar seleccionados", "Autorizar pago seleccionados"/"del período completo" con confirmación mostrando impacto económico, estados `EN_REVISION`/`APROBADO` antes del pago. Hoy `Cartera` no tiene ningún paso de aprobación — un abono se aplica directo. Implementarlo exige diseñar una máquina de estados nueva sin evidencia en el dominio actual de que se necesite (mismo criterio que DEUDA-31 de `empleados`, no se inventa un paso de negocio sin decisión explícita del usuario). | **ABIERTO (requiere decisión de negocio + diseño de estados nuevo)** |
| DEUDA-C05-CERRADO | `models.py`, `business_service.py`, `api/viewsets.py`, frontend | ~~BAJA~~ | Entidad `CarteraNota` (histórico de anotaciones usuario/fecha/texto/tipo), append-only. Corregido v3.13.0. Ver sección v3.13.0 arriba. | CERRADO |
| DEUDA-C06 | `tests/test_cartera_concurrencia.py` | MEDIA | Test de concurrencia real (`django_db(transaction=True)` + threads + `Barrier`) para `registrar_abono()`, escrito en v3.14.0. **Corrección honesta:** la única corrida real de la suite lo marcó como `ERROR` (no `FAILED`) y la traceback real nunca se vio (salida truncada por error del operador). `select_for_update()` en `registrar_abono()` sigue correctamente implementado desde antes — lo que NO está confirmado es que este test específico funcione como está escrito. | **ABIERTO — reabierto, diagnóstico pendiente (ver "Resultado real de pytest")** |

---

## Tests (`tests/`) — 11 archivos

| Archivo | Cobertura |
|---|---|
| `conftest.py` | Fixtures: tenants, empresas, users |
| `test_auth_session_smoke.py` | JWT + Session auth |
| `test_clientes_api_and_service.py` | API endpoints + service layer |
| `test_clientes_crud_workspace.py` | CRUD desde workspace |
| `test_contacto_cliente_crud.py` | ContactoCliente CRUD + UUID lookup |
| `test_cartera_crud_api.py` | Cartera + abonos + Pull Model |
| `test_idempotence_v2614.py` | Idempotencia upsert ETL |
| `test_representante_legal.py` (nuevo v3.12.0) | Regla de representante legal JURIDICA (DEUDA-C01) |
| `test_cartera_pull_model_saldo_real.py` (nuevo v3.12.0) | Fix de doble fuente de verdad en pagos (DEUDA-C02) |
| `test_cartera_notas.py` (nuevo v3.13.0) | CarteraNota: service + API GET/POST (DEUDA-C05) |
| `test_cartera_concurrencia.py` (nuevo v3.14.0) | Concurrencia real (threads) para `registrar_abono()` (DEUDA-C06) |
| `test_cartera_kpis_y_filtro_vencidas.py` (nuevo v3.15.0) | Desglose de KPIs + filtro `?vencidas=1` (DEUDA-C04) |

`apps/tenant/bancos/tests/test_conciliacion_dispara_abono_cartera.py` (nuevo v3.14.0, vive en `bancos` por ser el punto de disparo) también cubre DEUDA-C03.

---

## Próximos Pasos Recomendados

| ID | Prioridad | Descripción |
|---|---|---|
| CLI-03 | BAJA | Agregar paginación server-side a `get_cartera_resumen()` para clientes con > 500 facturas |
| CLI-05 | MEDIA | Mecanismo de reverso de abono cuando se des-concilia una `TransaccionBancaria` (limitación conocida documentada en DEUDA-C03/v3.14.0) |

CLI-01/CLI-02 (columna días vencida + resaltado de filas vencidas) implementados en v3.15.0 — ver sección v3.15.0 y DEUDA-C04-CERRADO arriba.

---

**Última Actualización:** 2026-09-11 (v3.15.0)
**Auditor:** Claude Sonnet 5 (Anthropic)
**Status:** ⚠️ PRODUCTION READY CON DEUDAS DOCUMENTADAS — ver §Deudas Técnicas (DEUDA-C06 y C07 abiertas — ver "Resultado real de pytest" arriba para C06; C07 requiere decisión de negocio + diseño de estados nuevo; DEUDA-C01/C02/C03/C05 cerradas y confirmadas por código, C04 cerrada en su alcance) — 16/16 AGENTS.md COMPLIANCE
**Cambios v3.15.0:** Cartera como centro de control — alcance de visualización (DEUDA-C04): KPIs desglosados (sin pago/parcial/vencidas), filtro "Vencidas", columna "Emisión", badge de días vencida. El workflow de aprobación en lote se separó a DEUDA-C07 (no implementado, requiere decisión de negocio). Ver sección v3.15.0 arriba.
**Cambios v3.14.0:** Bancos dispara abono en Cartera al conciliar (DEUDA-C03, decisión del usuario) + test de concurrencia real para `registrar_abono()` (DEUDA-C06). Ver sección v3.14.0 arriba.
**Cambios v3.13.0:** `CarteraNota` — historial de notas de seguimiento (DEUDA-C05). Ver sección v3.13.0 arriba.
**Cambios v3.12.0:** Representante legal obligatorio para JURIDICA (DEUDA-C01) + fix de doble fuente de verdad en pagos Cartera/Factura (DEUDA-C02). Ver sección v3.12.0 arriba para el detalle completo. Migraciones 0001-0010.
**Tests:** 17 casos nuevos en total entre v3.12.0-v3.15.0 (`test_representante_legal.py`, `test_cartera_pull_model_saldo_real.py`, `test_cartera_notas.py`, `test_cartera_concurrencia.py`, `test_cartera_kpis_y_filtro_vencidas.py`, `bancos/test_conciliacion_dispara_abono_cartera.py`) — **ninguno ejecutado con pytest real en esta sesión** (intento de regresión en otros 4 apps tardó >2.5h y fue terminado por el sistema por memoria baja; no reintentado por decisión del usuario). `manage.py check` y `makemigrations --check --dry-run` sí se verificaron limpios en cada paso. **Correr la suite real es la prioridad #1 de la próxima sesión antes de commitear nada de esto.**
