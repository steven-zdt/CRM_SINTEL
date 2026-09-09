# PROVEEDORES_AUDIT — Auditoría integral (PROVEEDORES-01)

Fecha: 2026-09-08. Rama: `feat/onboarding-cookie`. Metodología: `INSPECT → MAP →
VERIFY → IDENTIFY GAPS` (lectura de código real + contraste contra la
documentación `.agent/` existente, que en varios puntos está desactualizada).
No se modificó código en esta fase.

Fuentes: código real (`apps/tenant/proveedores/`, `apps/tenant/compras/`,
`apps/tenant/facturas/`, `apps/tenant/contabilidad/`, `apps/tenant/bancos/`,
`apps/tenant/api/permissions.py`), documentación `.agent/` de proveedores (8
docs), `documentacion/arquitectura_general.md`, `documentacion/audits/apps/
F34_proveedores_AUDIT.md`, `docs/ADR-001-retention-pull-model.md`.

---

## 1. Veredicto de la documentación `.agent/` existente

La documentación de proveedores (8 archivos en `.agent/`) está **parcialmente
desactualizada**, en algunos casos de forma significativa:

| Documento | Fecha/versión | Estado |
|---|---|---|
| `RESUMEN_EJECUTIVO.md` | v3.5.0, 2026-05-09 | Obsoleto — los 3 blockers que reporta ya están resueltos |
| `README.md` | v3.6.0, 2026-05-11 | Parcialmente obsoleto — enlaza a 5 archivos que no existen; describe frontend Tabulator que ya no es el real |
| `AUDITORIA_CODIGO_COMPLETA.md` | v3.16.1, 2026-06-03 | Mayormente vigente, con 2 gaps de test aún abiertos |
| `AUDITORIA_FLUJO_PROVEEDORES.md` | v3.17.1, 2026-06-10 (+ adenda 2026-08-26) | El más reciente y completo, pero **no documenta** la migración de Tabulator → server-rendered (django-tables2+HTMX) ni el bridge Compras→CxP con su limitación conocida |
| `docs/proveedores_flow_map.md` | v3.5.0 | Obsoleto (nombres de archivo JS ya no existen) |
| `docs/proveedores_business_logic.md` | v3.5.0 | Obsoleto (documenta `codigo_contable`, eliminado del modelo) |
| `docs/proveedores_microtasks_architecture.md` | v3.5.0 | Obsoleto (mismo motivo) |
| `PLAN_CARTERA_UI.md` | 2026-06-03 | Histórico — el modelo `Cartera` fue renombrado a `CuentasPagar` el mismo día |

**Los 3 "blockers" del `RESUMEN_EJECUTIVO.md` (2026-05-09), verificados contra
el código real hoy:**

| Blocker | Estado real |
|---|---|
| `lookup_field='pk'` | **RESUELTO.** `uuid` en los 3 ViewSets (`Proveedor`, `Representante`, `CuentasPagar` hereda de `BaseTenantViewSet`). |
| Namespace JS inconsistente | **NO resuelto, sigue dual.** Ver hallazgo H1 abajo. |
| Duplicidad de mixins | **Nunca existió tal cual se describió** — no hay `api/mixins.py`, solo `services/api_mixins.py`. Sin duplicidad real. |

---

## 2. Mapa de modelos (SSoT real, verificado en código)

### `Proveedor` (`models.py:16-188`)
- Hereda `SintelTenantBaseModel`. `uuid` propio, único. FK `empresa` (PROTECT).
- Identificación: `tipo_persona`, `tipo_documento`, `numero_documento`,
  `digito_verificacion`, `razon_social`, `nombre_comercial`.
- Tributario: `regimen_tributario`, `actividad_economica_ciiu`,
  `responsable_iva`, `gran_contribuyente`, `autoretenedor`.
- Retención (ver H2 — código muerto de datos): `es_retenedor`,
  `aplica_retefuente`/`retefuente_porcentaje`, `aplica_reteica`/
  `reteica_porcentaje`, `aplica_reteiva`/`reteiva_porcentaje`.
- Contacto/comercial/bancario: `email_contacto`, `telefono_contacto`,
  `direccion`, `ciudad`, `departamento`, `plazo_pago_dias`, `banco`,
  `tipo_cuenta`, `numero_cuenta` (sin integración real a `apps/tenant/bancos`,
  ver H8).
- Soft-delete: `activo` (bool). Hard-delete solo permitido si `activo=False`.
- `UniqueConstraint(empresa, tipo_documento, numero_documento)`.
- `codigo_contable` **ya no existe** (eliminado, migraciones 0007/0017) —
  coherente con ADR de desacoplamiento contable (§6.2
  `arquitectura_general.md`).

### `Representante` (`models.py:339-437`, migración `0018`)
- Hereda `SintelTenantBaseModel`, `uuid` propio, `empresa` FK directa.
- **`ForeignKey` a `Proveedor`** (CASCADE) — patrón real: **1 Proveedor → N
  Representantes**, con `es_principal` (bool) para marcar el principal.
  `RepresentanteBusinessService.eliminar_representante()` impide borrar el
  único principal restante.
- `UniqueConstraint(empresa, proveedor, numero_documento)`.
- Ver H7 — modelo casi idéntico a `clientes.ContactoCliente`, duplicado sin
  abstracción compartida.

### `CuentasPagar` (`models.py:191-336`)
- Historial: `CuentaPorPagar` → `Cartera` → `CuentasPagar` (migraciones
  0010-0014, todas el mismo día 2026-06-03).
- Campos: `proveedor` FK (CASCADE), `numero_factura`, `factura_uuid`
  (soft-ref, sin FK), `orden_compra_uuid` (soft-ref, sin FK), `valor_total`,
  `valor_pagado`, `saldo` (calculado), `estado_pago`.
- **Máquina de estados real** (`estado_pago`, único con estos 3 valores —
  no existe `VENCIDA`/`ANULADA`, no se inventan): `SIN_PAGO`, `PARCIAL`,
  `PAGADA`. Recalculado en `save()`.
- **El modelo NO es la fuente primaria del listado.** El listado real
  (`CuentasPagarSelector.qs_list_facturas_compra`) lee `Factura.naturaleza=
  'COMPRA'` directamente; `CuentasPagar` solo persiste abonos y las CxP
  generadas desde Compras sin factura. `qs_list_unificado()` combina ambas
  fuentes (Facturas + CxP sueltas). Ver H6 — riesgo de doble conteo.

---

## 3. Integraciones (verificadas, con veredicto)

| Integración | Veredicto | Detalle |
|---|---|---|
| **Proveedor → Compras** | ✅ Correcto | FK real + `PROTECT` (`compras/models.py:153-158`), sin snapshot (correcto: documento interno vivo), DSV con `empresa_id` en create/update. |
| **Proveedor → Facturas** | ✅ Correcto, con 1 riesgo conocido | Referencia blanda `proveedor_uuid` + snapshot fiscal (`emisor_*`), resolución/creación automática del proveedor desde XML (`resolver_o_crear_desde_factura_compra`) — evita "proveedor fantasma". Riesgo real: ver H6 (doble CxP). |
| **Proveedor → Contabilidad/Retenciones** | ✅ Sin violación de ADR-001 | `proveedores` no importa `contabilidad`, no crea `AsientoContable`/`MovimientoContable`. El cálculo real de retenciones vive en `ConfiguracionRetenciones`/`RetencionesService` (por NIT), no en `Proveedor`. Ver H2 — campos muertos en el modelo. |
| **Proveedor → Bancos** | ⚠️ Sin integración real | Campos sueltos de texto (`banco`, `numero_cuenta`), sin FK ni referencia a `apps/tenant/bancos`. No es un bug — es informativo, tal como está diseñado hoy. |
| **Permisos** | ✅ Fuente correcta, ⚠️ granularidad binaria | Usa `apps.tenant.api.permissions` (fuente permitida). `IsTenantAdminOrReadOnly`: lectura para cualquier miembro, escritura (incl. pagos) solo ADMIN. No usa `HasTenantRole` graduado. Ver H3 — decisión de negocio pendiente. |
| **Multi-tenancy** | ✅ Correcto | Todos los métodos de `ProveedorSelector`/`CuentasPagarSelector`/`RepresentanteSelector` exigen y aplican `empresa_id`. Sin querysets sin filtrar. |

---

## 4. Hallazgos — clasificados

### Código muerto / roto (sin ambigüedad de negocio — se corrige directamente)

- **H1 — Namespace JS dual.** `proveedores.api.js`/`proveedores.utils.js`
  definen `window.AppProveedor.*` como namespace primario, con un wrapper de
  compatibilidad hacia `window.Sintel.Proveedores.*`. Pero **todo el resto
  del código real** (`proveedores_form.js`, `proveedores_main.js`,
  `features/representante_*.js`, `features/cuentas_pagar_*.js`) consume
  exclusivamente `window.Sintel.Proveedores.*` / `window.Sintel.Representante.*`.
  `window.AppProveedor` no tiene consumidores propios. Acción: eliminar el
  namespace `AppProveedor` muerto, dejar `window.Sintel.Proveedores` como
  único SSoT (consistente con el resto del proyecto — `clientes` usa
  `window.AppCliente`, pero proveedores en la práctica ya migró a
  `Sintel.Proveedores` en todos los consumidores reales).

- **H4 — Código muerto/roto en `ProveedorServiceMixin`** (`services/
  api_mixins.py:51-77`): `get_qs_detail()` usa `self.kwargs.get('pk')`
  (debería ser `'uuid'`, nunca coincide); `service_crear_proveedor()`/
  `service_actualizar_proveedor()` llaman a métodos de **clase**
  `create_proveedor()`/`update_proveedor()` que no existen en
  `ProveedorBusinessService` (los reales son de instancia: `crear_proveedor`/
  `actualizar_proveedor`). Ninguno de los tres se invoca en la práctica
  (`viewsets.py` implementa `create/update/partial_update` directamente).
  Acción: eliminar los 3 métodos muertos.

- **H5 — Documentación desactualizada.** Frontend descrito como Tabulator
  cuando el Directorio y Cuentas por Pagar son server-rendered
  (django-tables2+HTMX) desde la migración "Fase 5-BIS" (no documentada en
  ningún `.agent/*.md`); 5 archivos enlazados desde `README.md` no existen;
  nombres de archivo JS obsoletos (`proveedores.form.js` → real
  `proveedores_form.js`; `cartera_list.js` → real `cuentas_pagar_list.js`).
  Acción: reescribir `README.md` y los docs desactualizados con el estado
  real verificado en esta auditoría (este documento + `PROVEEDORES_FLOW.md`).

- **Gaps de test** (sin duplicar los existentes — ver inventario abajo):
  no hay `test_representante*.py` dedicado (CRUD, DSV, unicidad, regla
  "no borrar único principal", HTTP real vía `RepresentanteViewSet`); no
  hay `test_multitenant_isolation.py` para `CuentasPagar` (ya señalado como
  `NP-PROV-001` en auditoría previa, sigue abierto); no hay test de
  `CuentasPagarBusinessService.registrar_abono` (monto > saldo, acumulación,
  transición de estado).

### Hallazgos que requieren decisión (no inferibles del código con seguridad)

- **H2 — Campos de retención muertos en `Proveedor`.** `retefuente_porcentaje`
  y equivalentes existen en el modelo, se sanean y exponen vía API
  (create/update), pero **ningún cálculo real los lee** (verificado: 0
  referencias de uso en todo `apps/tenant/`). El motor real de retenciones
  vive en `contabilidad.ConfiguracionRetenciones`, indexado por NIT. Una
  auditoría previa (`F34_proveedores_AUDIT.md`) ya eliminó la *lógica* muerta
  que los leía, pero **dejó los campos deliberadamente intactos** (no estaba
  en su alcance). Riesgo: un usuario admin edita `retefuente_porcentaje`
  esperando que afecte facturas futuras, y no ocurre nada — doble fuente de
  verdad silenciosa, justo el antipatrón que `ADR-001` advierte.

- **H3 — Permisos binarios (lectura-todos / escritura-solo-ADMIN).** La
  misión pide explícitamente distinguir "puede consultar / crear / modificar
  / eliminar / **pagar**" (§17), pero hoy `IsTenantAdminOrReadOnly` no separa
  esos niveles — ni siquiera `registrar-abono` (pagar) tiene un permiso
  distinto al de crear/editar. No hay evidencia de que esto sea un bug; podría
  ser una política de negocio deliberada (control estricto sobre movimientos
  de dinero).

- **H6 — Riesgo de doble conteo de CxP.** Una misma compra puede generar
  obligación por dos caminos independientes que no se reconcilian: (a)
  aprobación de Orden de Compra (`CuentasPagar` con `orden_compra_uuid`), y
  (b) llegada posterior de la Factura electrónica real de esa compra (leída
  directo de `Factura`, sin tocar `CuentasPagar`). Si ambas ocurren para la
  misma compra, `qs_list_unificado()` las muestra como dos obligaciones
  separadas. El propio código lo documenta como "fuera de alcance
  deliberado" (`compras/services/business_service.py:416-420`), pero la
  misión (§12) pide explícitamente evitar esto.

- **H7 — `Representante` duplica `clientes.ContactoCliente`.** Mismo
  propósito (persona de contacto de una entidad de negocio), campos casi
  idénticos (`nombre_completo`, `cargo`, `email`/`email_contacto`,
  `telefono`/`telefono_contacto`, flag principal), sin modelo/mixin
  abstracto compartido. La misión (§4-6) pide explícitamente verificar esto
  antes de crear una entidad nueva — ya se creó como clase independiente en
  vez de generalizar. `Representante` ya está en producción con datos y UI
  completa; fusionar retroactivamente con `ContactoCliente` es un refactor
  de mayor alcance que toca 2 dominios (`proveedores` y `clientes`).

### Informativos (no requieren acción, quedan documentados)

- Órdenes de Compra anuladas después de aprobadas no reversan la `CuentasPagar`
  ya generada (limitación conocida, documentada en el propio código).
- `services.py` legacy plano coexiste con el paquete `services/` (algunos
  tests viejos siguen importando de ahí) — verificar en fase de
  implementación si tiene consumidores de producción o es solo residual de
  tests.
- No existe `CuentasPagarCRUDService` dedicado — el CRUD de CxP vive
  directo en `business_service.py`, a diferencia del patrón usado en
  Proveedor/Representante (selector+crud+business separados). Inconsistencia
  de estilo, bajo riesgo.

---

## 5. Inventario de tests existentes (para no duplicar — REUSE/UPDATE/DEPRECATE)

| Archivo | Cobertura |
|---|---|
| `test_proveedores_api_and_service.py` | Create/update vía servicio legacy, smoke GET list, filtro empresa_id |
| `test_idempotence_v2614.py` | Idempotencia a nivel servicio, 201 primer POST / 400 segundo POST duplicado, Zero Trust (empresa inválida) |
| `test_organizational_context_adoption.py` | Divergencia `OrganizationalContext` vs `resolve_tenant_empresa()` en `ProveedorViewSet` |
| `test_auth_session_smoke.py` | SessionAuthentication no da 401; 1 test deprecado comentado (`CompraProveedorViewSet`, eliminado v2.40) |
| `test_tabla_cuentas_pagar_view.py` | Vista server-rendered CxP: render, filtro estado, búsqueda, inclusión de CxP sin factura |
| `test_tabla_view.py` | Vista server-rendered Directorio: render, búsqueda |

**Gaps confirmados** (no cubiertos por lo anterior): `Representante` CRUD
completo vía HTTP, `CuentasPagar` aislamiento multi-tenant, `registrar_abono`
reglas de negocio.

---

## 6. Matriz API (§16 de la misión)

| Recurso | GET list | GET detail | POST | PUT/PATCH | DELETE |
|---|---|---|---|---|---|
| Proveedor | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED (soft/hard condicional) |
| Representante | IMPLEMENTED | IMPLEMENTED (vía list con filtro) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED |
| CuentasPagar | IMPLEMENTED (unificado Factura+CxP) | IMPLEMENTED | IMPLEMENTED | NOT_APPLICABLE (por diseño — solo `registrar-abono`, no edición libre) | NOT_APPLICABLE (no existe estado ANULADA) |

---

## Siguiente

Ver `docs/proveedores/PROVEEDORES_RELEASE_GATE.md` (se completará al cierre)
para el veredicto final. Decisiones H2/H3/H6/H7 requieren respuesta del
usuario antes de decidir su alcance de implementación — el resto de los
hallazgos (H1, H4, H5, gaps de test) se implementan directamente en la
siguiente fase.
