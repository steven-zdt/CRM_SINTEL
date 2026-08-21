# F34 — Auditoria integral de negocio/arquitectura (SINTEL)

Mision F34: distinta de la auditoria previa (`APP_AUDIT_MASTER_STATUS.md`
/ `APP_AUDIT_MASTER_FINAL.md`, ya cerrada). F34 profundiza en angulos
NO cubiertos antes con el mismo detalle: reglas de negocio
clasificadas (CRITICAL/IMPORTANT/SUPPORTING/DERIVED/PRESENTATIONAL),
mapa de dominio (entidades/relaciones/estados/transiciones),
auditoria de queries N+1 especificas, auditoria estructural de
frontend, comparacion before/after de cambios reales, impact analysis
por cambio. Los tests son solo evidencia puntual, nunca el mecanismo
de descubrimiento -- no se relanzan suites completas salvo que haya
cambio de codigo que lo justifique.

**Inicio:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Reutiliza como base** (no re-deriva desde cero) los hallazgos ya
confirmados en `APP_<app>_AUDIT.md` / `APP_<app>_NORMATIVE_MATRIX.md`
de la auditoria anterior -- F34 se enfoca en las dimensiones nuevas
(reglas de negocio, dominio, N+1, frontend estructural) y en items
deferred que quedaron pendientes ahi.

**Orden de ejecucion (segun F34, distinto al orden de la auditoria
anterior):**
1. core
2. empresa
3. perfil
4. clientes
5. proveedores
6. inventario
7. compras
8. ventas
9. cotizaciones
10. proyectos
11. gastos
12. empleados
13. bancos
14. facturas
15. contabilidad
16. dashboard

---

## Progreso por app

| # | App | Estado | Doc |
|---|-----|--------|-----|
| 1 | core | COMPLETED | `documentacion/audits/apps/F34_core_AUDIT.md` |
| 2 | empresa | COMPLETED | `documentacion/audits/apps/F34_empresa_AUDIT.md` |
| 3 | perfil | COMPLETED | `documentacion/audits/apps/F34_perfil_AUDIT.md` |
| 4 | clientes | COMPLETED | `documentacion/audits/apps/F34_clientes_AUDIT.md` |
| 5 | proveedores | COMPLETED | `documentacion/audits/apps/F34_proveedores_AUDIT.md` |
| 6 | inventario | EN PROGRESO | `documentacion/audits/apps/F34_inventario_AUDIT.md` |
| 7 | compras | PENDIENTE | `documentacion/audits/apps/F34_compras_AUDIT.md` |
| 8 | ventas | PENDIENTE | `documentacion/audits/apps/F34_ventas_AUDIT.md` |
| 9 | cotizaciones | PENDIENTE | `documentacion/audits/apps/F34_cotizaciones_AUDIT.md` |
| 10 | proyectos | PENDIENTE | `documentacion/audits/apps/F34_proyectos_AUDIT.md` |
| 11 | gastos | PENDIENTE | `documentacion/audits/apps/F34_gastos_AUDIT.md` |
| 12 | empleados | PENDIENTE | `documentacion/audits/apps/F34_empleados_AUDIT.md` |
| 13 | bancos | PENDIENTE | `documentacion/audits/apps/F34_bancos_AUDIT.md` |
| 14 | facturas | PENDIENTE | `documentacion/audits/apps/F34_facturas_AUDIT.md` |
| 15 | contabilidad | PENDIENTE | `documentacion/audits/apps/F34_contabilidad_AUDIT.md` |
| 16 | dashboard | PENDIENTE | `documentacion/audits/apps/F34_dashboard_AUDIT.md` |

**F34:** EN PROGRESO (5/16 COMPLETED)

**core (cierre):** sin cambios de codigo -- 2 items deferred de la
auditoria previa (N+1 sospechado en organizational_*, workspace.html
sin re-auditar) cerrados con evidencia nueva (ninguno confirmado como
problema real). Ver `F34_core_AUDIT.md`.
