# Organizational Scope — Tablero de Estado de Consolidacion

**Proposito:** tablero de control para el plan de consolidacion OCF/OSF (auditoria, correccion, pruebas, documentacion, versionado y gobernanza) descrito en el prompt maestro. Cada fase avanza solo con autorizacion explicita del usuario — este documento se actualiza al cierre de cada fase, nunca por adelantado.

**Estados oficiales:**
`⚪ NOT_STARTED` · `🔵 AUDITING` · `🟡 IMPLEMENTING` · `🟣 VALIDATING` · `🟢 COMPLETED` · `🔴 BLOCKED` · `⚫ ROLLBACK`

---

| Fase | Nombre | Estado | Fecha cierre | Entregable(s) |
|---|---|---|---|---|
| 0 | Baseline y Congelamiento | 🟢 COMPLETED | 2026-08-09 | `documentacion/OCF_OSF_BASELINE.md`, este tablero |
| 1 | Auditoria Tecnica de OCF | 🟢 COMPLETED — `pytest` de las 9 suites de `core/tests/test_organizational_*.py`: **53 passed, 1 warning, 24m12s** (confirmado, ver `OCF_TECHNICAL_AUDIT.md` §11) | 2026-08-09 | `documentacion/OCF_TECHNICAL_AUDIT.md` |
| 2 | Auditoria de Organizational Scope | 🟢 COMPLETED — mismo resultado de pytest (53/53), cubre `test_organizational_scope.py`/`test_organizational_filters.py` | 2026-08-09 | `documentacion/OSF_TECHNICAL_AUDIT.md` |
| 3 | Contrato Definitivo (Scope vs Context) | 🟢 COMPLETED | 2026-08-09 | `documentacion/ORGANIZATIONAL_CONTRACT.md` |
| 4 | ADR Governance (ADR-004, posible ADR-005) | 🟢 COMPLETED | 2026-08-09 | `docs/ADR-004-*.md` (Adenda), `docs/ADR-005-organizational-scope-framework.md` (nuevo), `documentacion/arquitectura_general.md` §7 reconciliada |
| 5 | Matriz Global de Cobertura | 🟢 COMPLETED — auditado y extendido el archivo existente (Seccion 4 nueva), no se creo un archivo paralelo | 2026-08-09 | `documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md` |
| 6 | Validacion del Piloto Compras | 🟢 COMPLETED — matriz construida, gap critico confirmado; pytest: **1 failed (preexistente, ya diagnosticado en MEMORY.md, no relacionado), 8 passed** | 2026-08-09 | `documentacion/COMPRAS_PILOT_VALIDATION.md` |
| 7 | Tests de Aislamiento Organizacional | 🟢 COMPLETED — suite nueva (12 tests) + 2 hallazgos reales, **ambos corregidos con autorizacion explicita**: (1) bypass de `HasOrganizationalScope` en acciones HTMX de offcanvas (fix: `self.check_object_permissions()` explicito), (2) `PermissionDenied` convertido en 500 en vez de 403 por `handle_service_error()` compartido (fix: caso nuevo agregado). Suite completa del piloto re-ejecutada post-fix: **20 passed** | 2026-08-09 | `documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md`, `apps/tenant/compras/tests/test_organizational_isolation_empresa_a.py`, `apps/tenant/compras/api/viewsets.py`, `apps/tenant/api/mixins.py` |
| 8 | Auditoria de Facturas | 🟢 COMPLETED — corrige la lista de consumidores reales de `FacturaInterAppAPI` (solo `bancos`/`proyectos`, no 6 apps); confirma `facturas` como la app con integracion OSF mas madura (F7/F9/F10/F11) | 2026-08-09 | `documentacion/FACTURAS_AUDIT.md` |
| 9 | Auditoria Ventas -> Facturas | 🟢 COMPLETED — contrato verificado limpio: `sede_id` server-side (no inyectable por el cliente), DSV real, sin FK nueva, sin dependencia circular | 2026-08-09 | `documentacion/VENTAS_FACTURAS_AUDIT.md` |
| 10 | Rollout Controlado (app por app) | 🟢 COMPLETED — `ventas` sin cambio de modelo (confirmado con usuario); 6 apps ya migradas en OSF F7/F9/F11 (parcial, por decision explicita); `clientes`/`dashboard` ratificadas NO APLICA; `proveedores`/`bancos`/`contabilidad` documentadas como backlog, sin infraestructura especulativa | 2026-08-09 | `documentacion/FASE10_ROLLOUT_CONTROLADO.md` |
| 11 | Consolidacion Git | 🟡 IMPLEMENTING — plan de 5 commits preparado y validado (`manage.py check`/`makemigrations --check`/tests limpios); **ejecucion pendiente de autorizacion explicita** (git commit no se ejecuta bajo "termina la tarea", requiere pedido separado) | 2026-08-09 | `documentacion/FASE11_CONSOLIDACION_GIT.md` |
| 12 | Baseline Organizacional Final | 🟡 BASELINE PARCIAL — Codigo/Tests/ADR/Documentacion alineados y verificados; Git y Knowledge Graph pendientes (no se declara 🟢 sin trazabilidad completa) | 2026-08-09 | `documentacion/ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md` |
| 13 | Knowledge Graph | 🔴 BLOCKED — el propio plan maestro prohibe iniciar antes de cerrar el baseline en 🟢 (FASE 12 quedo en 🟡) | — | Extension del grafo EKG con capas organizacionales |
| 14 | Gobernanza Automatica | 🔴 BLOCKED — depende de FASE 13 | — | Reglas de gobernanza organizacional (extension de `tools/ekg/governance.py`) |

---

## Orden de Rollout (Fase 10, referencia)

```
compras (piloto, ya iniciado)
  -> ventas
  -> facturas
  -> inventario
  -> gastos
  -> empleados
  -> cotizaciones
  -> proyectos
  -> clientes
  -> proveedores
  -> bancos
  -> contabilidad
  -> dashboard
```

Una app por fase. Cada app debe completar `MODEL -> SELECTOR -> SERVICE -> PERMISSION -> VIEWSET -> API -> FRONTEND -> TESTS` antes de marcarse completa (ver tabla de apps afectadas en `OCF_OSF_BASELINE.md` §5 para el estado real actual de cada app — ninguna cumple el ciclo completo hoy).

---

## Reglas fijas (no reevaluar en cada fase)

- `OrganizationalScope` = limite de autorizacion (EMPRESA/SEDE/AREA). `OrganizationalContext` = contexto efectivo de ejecucion. **No fusionar.**
- `TenantProfile.rol` y `TenantProfile.alcance` siguen siendo la fuente de verdad de rol/alcance — no crear una segunda.
- `HasOrganizationalScope` sigue siendo el mecanismo central de enforcement donde ya esta implementado.
- Prohibido: segundo `OrganizationalContext`/`OrganizationalScope`, duplicar `TenantProfile`/roles/permisos, FK directa entre apps solo para contexto, Signals para contexto, bypass de Service Layer/DSV/Selectors, `request.user.perfil` directo en serializers, bypass de autorizacion via `DEBUG`, `.all()` sin aislamiento, PK entera en URLs, `git add .` indiscriminado.
- Mantener: `SintelTenantBaseModel`, `BaseTenantViewSet`, `BaseServiceMixin`, `TenantProfile`, Service Layer, DSV, Soft References, Bridges, Pull Model Contable, UUID lookup, Zero Trust.

---

*Actualizado por ultima vez al cierre de FASE 0 (2026-08-09). No editar estados por adelantado.*
