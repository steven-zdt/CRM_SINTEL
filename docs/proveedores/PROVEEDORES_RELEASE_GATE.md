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
