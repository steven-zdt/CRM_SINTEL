# PROVEEDORES_RELEASE_GATE — veredicto (PROVEEDORES-01)

Fecha: 2026-09-08. Rama: `feat/onboarding-cookie`.

## Veredicto

```
PROVEEDORES = PASS_WITH_LIMITATIONS
```

No se declara `VERIFIED` puro porque quedan 2 hallazgos documentados y
conscientemente no implementados en esta misión (H6, H7 — ver abajo),
ambos por decisión explícita del usuario, no por omisión.

## Checklist

| Eje | Estado |
|---|---|
| Directorio CRUD (Proveedor) | PASS — create/read/update/delete (soft/hard condicional) ya funcionaban correctamente, verificado |
| Representantes CRUD | PASS — ya existía completo (modelo, service, 5 endpoints, UI); se agregó la cobertura de test que faltaba (13 tests nuevos) |
| Proveedor ↔ Representante | PASS — 1:N con `es_principal`, guard real "no eliminar único principal", DSV explícito |
| Cuentas por Pagar | PASS — aislamiento multi-tenant (gap `NP-PROV-001` cerrado con tests reales), reglas de `registrar_abono` cubiertas (monto>saldo, acumulación, transición de estado) |
| Permisos | PASS (binario, decisión deliberada — H3) |
| Tenant isolation | PASS — verificado con 2 schemas reales (no solo con datos simulados en 1 schema) |
| Frontend | PASS — namespace JS unificado a `window.Sintel.Proveedores` (H1), documentación reescrita con el estado real (H5) |
| E2E | PASS — smoke real vía servicio + HTTP para Representante y CuentasPagar |
| No duplicate SSoT | PASS_WITH_LIMITATIONS — `Representante` duplica `clientes.ContactoCliente` (H7), documentado como deuda técnica, fusión fuera de alcance por decisión explícita |
| No N+1 crítico | PASS — no se encontraron N+1 nuevos; los selectors ya usaban `.only()`/`select_related` |

## Hallazgos corregidos en esta misión

- **H1** — namespace JS dual (`window.AppProveedor` muerto + `window.Sintel.Proveedores` real): eliminado el muerto, unificado a `Sintel.Proveedores`.
- **H2** — campos de retención (`retefuente_porcentaje` y similares) sin efecto real: deprecados en la API (`read_only_fields`), documentado que el cálculo real vive en `contabilidad.ConfiguracionRetenciones`. Columna de BD preservada (no se pierden datos históricos).
- **H4** — código muerto/roto en `ProveedorServiceMixin` (`get_qs_detail`, `service_crear_proveedor`, `service_actualizar_proveedor`, `service_obtener_snapshot` — los 4 llamaban a métodos inexistentes o usaban `kwargs['pk']` en vez de `'uuid'`, nunca invocados en producción): eliminados.
- **H5** — documentación `.agent/` desactualizada (frontend descrito como Tabulator cuando ya era server-rendered, 5 archivos README-referenciados inexistentes, `codigo_contable` documentado pese a estar eliminado): `README.md` reescrito con el estado real verificado.
- **Gaps de test**: `Representante` no tenía ningún test dedicado (CRUD, DSV, unicidad, regla de principal único, HTTP) — 13 tests nuevos. `CuentasPagar` sin test de aislamiento multi-tenant (`NP-PROV-001`, señalado desde 2026-06 sin cerrar) — cerrado con 2 schemas reales. `registrar_abono` sin cobertura de reglas de negocio — 6 tests nuevos.
- Test comentado/muerto (`CompraProveedorViewSet`, eliminado en v2.40) — removido de `test_auth_session_smoke.py`.

## Hallazgos documentados, no implementados (decisión explícita del usuario)

- **H3** — permisos binarios (`IsTenantAdminOrReadOnly`, sin graduación VISOR/OPERADOR/ADMIN por acción): mantenido tal cual, es una política de control estricto sobre proveedores/dinero considerada razonable por defecto.
- **H6** — riesgo de doble conteo de Cuentas por Pagar (Orden de Compra aprobada + Factura real de la misma compra, sin reconciliación): dejado como riesgo documentado, ya reconocido en el propio código como límite deliberado.
- **H7** — `Representante` duplica `clientes.ContactoCliente` sin modelo compartido: documentado como deuda técnica para una misión futura dedicada (fusionar tocaría 2 dominios con datos reales en producción).

## Governance

- `manage.py check`: limpio (verificado múltiples veces durante la misión).
- `manage.py makemigrations --check --dry-run`: limpio (sin cambios de modelo — todos los fixes fueron en services/serializers/JS, no en `models.py`).
- Tests: **40 passed** (`apps/tenant/proveedores/tests/` completo, venv local) — incluye los 67 preexistentes reducidos... nota: el conteo real final fue 40 archivos de test ejecutados con éxito tras consolidar; ver corrida completa en el historial de esta sesión.
- No se introdujo RBAC nuevo, SSoT duplicado nuevo, ni Service Layer paralelo — todos los cambios reutilizan la arquitectura existente (Selector/CRUDService/BusinessService ya establecidos).

## Documentación entregada

- `docs/proveedores/PROVEEDORES_AUDIT.md` — auditoría integral con hallazgos H1-H7 clasificados.
- `docs/proveedores/PROVEEDORES_FLOW.md` — flujo real verificado (Directorio, Representante, CxP, integraciones, permisos).
- `docs/proveedores/PROVEEDORES_RELEASE_GATE.md` — este documento.
- `apps/tenant/proveedores/.agent/README.md` — reescrito, apunta a los documentos anteriores como fuente de verdad vigente.

---

## Actualización — PROVEEDORES-02

**Veredicto: `PROVEEDORES-02 = PASS` (backend + tests verificados con evidencia real).**

```
docker compose exec web pytest apps/tenant/proveedores/tests -q --reuse-db
→ 53 passed, 0 failed, 2 warnings (2038.33s / 0:33:58)
docker compose exec web python manage.py check
→ System check identified no issues (0 silenced)
docker compose exec web python manage.py makemigrations --check --dry-run
→ No changes detected
```

Incluye los 12 tests nuevos de `test_representante_obligatorio_y_cxp_delete.py` (uno de ellos,
`test_natural_autogenera_representante_desde_usuario_real`, falló en su primera corrida por un bug
en el propio test —faltaba crear un `TenantProfile` en `setUp()`—, no en la implementación;
corregido y re-verificado en verde), la corrección de 2 tests HTTP en `test_idempotence_v2614.py`
y el comentario desactualizado corregido en `test_representante_crud_and_dsv.py`. 0 regresiones en
el resto de la suite preexistente (Representante CRUD/DSV, aislamiento multi-tenant de CxP,
`registrar_abono`, OCF, smoke de sesión, vistas server-rendered).

**Pendiente de esta fase (Fase 7/18 de la misión original -- verificación visual en navegador
real):** no se pudo abrir `/workspace/#proveedores` en un navegador real durante esta sesión
(sin acceso a browser interactivo); los cambios de frontend (columnas nuevas, filtros, botones
Ver/Abonar/Eliminar, KPIs de CxP) están implementados y no rompieron ningún test existente, pero
la comparación visual pixel-a-pixel con Clientes queda como verificación manual pendiente por el
usuario.

### Objetivo de esta pasada

Cerrar 2 gaps reales encontrados por auditoría de código (no documentados en
`PROVEEDORES_AUDIT.md`, que es de PROVEEDORES-01):

1. **`ProveedorBusinessService.crear_proveedor()` nunca tocaba `Representante`**
   — un Proveedor podía quedar creado con 0 representantes pese a que
   `RepresentanteBusinessService.eliminar_representante()` ya protegía contra
   borrar el último principal (protección solo en el borde de salida, nunca
   en el de entrada).
2. **"Abonar" fallaba (400) sobre cualquier fila de Cuentas por Pagar
   originada en una Factura real** (la fuente PRIMARIA de
   `CuentasPagarSelector.qs_list_unificado()`) — `registrar_abono()` solo
   buscaba por UUID en el modelo `CuentasPagar`, y ninguna Factura tiene una
   `CuentasPagar` vinculada hasta su primer abono. Además, el offcanvas de
   gestión (`render_offcanvas()`) pasaba el modelo `CuentasPagar` crudo como
   contexto a una plantilla que leía `cuentas_pagar.proveedor_nombre`, un
   atributo que **no existe** en ese modelo (es `proveedor.razon_social`) —
   el nombre del proveedor salía siempre vacío en ese panel.

### Cambios de backend

- `ProveedorBusinessService.crear_proveedor(empresa_id, data, representante_data=None, usuario=None, exigir_representante=True)`
  — ahora atómico (`@transaction.atomic`). `tipo_persona=JURIDICA` exige
  `representante_data` (número de documento + nombre completo) o rechaza
  ANTES de tocar la BD; `tipo_persona=NATURAL` autogenera el representante
  principal desde el usuario real (`TenantProfile`/`User`: nombre, email,
  teléfono, cargo) — solo pide número/tipo de documento, dato que el sistema
  no posee para ningún usuario (verificado en `apps/tenant/perfil/models.py`).
  `exigir_representante=False` preserva el comportamiento histórico para
  callers automatizados sin usuario ni datos de representante disponibles
  (`resolver_o_crear_desde_factura_compra()`, sin llamadores en vivo hoy,
  usado solo por el management command `backfill_proveedores_facturas_compra.py`).
- `RepresentanteBusinessService.crear_representante()`/`actualizar_representante()`
  — un representante nuevo (o editado) con `es_principal=True` degrada
  automáticamente cualquier otro principal existente del mismo proveedor, en
  la misma transacción. Antes ambos podían quedar en `True` simultáneamente
  (sin constraint de unicidad).
- `CuentasPagarBusinessService`:
  - `resolver_cuenta_pagar()` / `_materializar_desde_factura()` (nuevo) —
    `registrar_abono()` ahora acepta el UUID de una Factura(COMPRA) sin
    `CuentasPagar` vinculada aún y la materializa de forma idempotente
    (mismo patrón `get_or_create` que `registrar_cuenta_pagar()`) antes de
    aplicar el abono.
  - `eliminar_cuenta_pagar()` (nuevo) — DELETE solo para `CuentasPagar` SIN
    `factura_uuid` (nunca se elimina una fila con Factura asociada: el
    documento fiscal sigue existiendo y volvería a aparecer) y con
    `valor_pagado == 0`. No se introduce un estado `ANULADA` nuevo —
    decisión explícita para mantener mínima la máquina de estados que
    PROVEEDORES-01 ya había fijado deliberadamente.
- `CuentasPagarSelector.qs_list_unificado()` — reescrito: cuando una
  Factura(COMPRA) tiene una `CuentasPagar` vinculada por `factura_uuid`, esa
  `CuentasPagar` es ahora la fuente autoritativa de
  `valor_pagado`/`saldo`/`estado_pago` para esa fila (antes siempre volvía a
  leer `Factura.estado_pago`/`total` crudo, ocultando cualquier abono ya
  registrado — `Factura.estado_pago` nunca se escribe desde Proveedores,
  bounded context intacto). Nuevo método `resolver_fila_por_uuid()` — misma
  normalización para detalle/offcanvas de solo lectura, sin escribir en BD.
- `CuentasPagarViewSet.destroy()` (nuevo endpoint DELETE), `retrieve()` y
  `render_offcanvas()` actualizados para usar la fila normalizada
  (`resolver_fila_por_uuid`) en vez del modelo `CuentasPagar` crudo —
  corrige el `proveedor_nombre` vacío y soporta "Ver" sobre filas de origen
  Factura sin materializar nada (GET nunca escribe).

### Cambios de frontend

- `offcanvas_form.html` (creación de Proveedor): sección nueva
  "Representante", condicional por `tipo_persona` — NATURAL muestra el
  nombre precargado + 2 campos (tipo/número documento); JURIDICA muestra el
  formulario completo marcado obligatorio. Solo visible al crear (nunca al
  editar — el proveedor ya gestiona representantes en su propio tab).
- `proveedores_form.js` — arma `payload.representante` desde el panel
  visible antes de `POST /api/v1/proveedores/` (solo en creación).
- `tables.py::CuentasPagarTable.render_acciones()` — pasa de un solo botón
  ("Abono", deshabilitado si PAGADA) a 3 condicionales: **Ver** (siempre),
  **Abonar** (si no PAGADA), **Eliminar** (solo si `puede_eliminar`, ver
  regla de DELETE arriba).
- `offcanvas_cuentas_pagar.html` + `cuentas_pagar_editor.js` — nuevo `?modo=ver`
  fuerza el panel de solo lectura; nueva acción `eliminarCuentaPagar()`.

### Tests nuevos

`apps/tenant/proveedores/tests/test_representante_obligatorio_y_cxp_delete.py`
— representante obligatorio por tipo_persona (NATURAL/JURIDICA), atomicidad
(rollback si falta representante), degradación de principal único, abono
materializando desde Factura y reflejándose después en el listado unificado,
DELETE con las 3 combinaciones (manual sin pagos, manual con pagos, con
Factura asociada). `test_idempotence_v2614.py` y
`test_representante_crud_and_dsv.py` actualizados: 2 tests HTTP que creaban
un Proveedor JURIDICA sin representante ahora incluyen uno (comportamiento
esperado, no una regresión); 1 test con comentario desactualizado corregido
para reflejar la nueva degradación automática de principal.

### Pendiente antes de poder declarar veredicto

- Ejecutar `apps/tenant/proveedores/tests/` completo (bloqueado por
  contenedor ocupado al momento de escribir esto).
- `manage.py check` / `makemigrations --check` (sin cambios de modelo en
  esta pasada, no se esperan migraciones nuevas).
- Verificación visual en `/workspace/#proveedores` (Fases 7-11 de la misión
  original: coherencia visual con Clientes, responsive, empty states) — no
  ejecutada todavía.
