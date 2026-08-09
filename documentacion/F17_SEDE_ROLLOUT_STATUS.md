# F17 — Rollout Controlado por App — Estado

**Fecha:** 2026-08-09
**Estado:** 🟢 F17 COMPLETED (como documentación de estado real — ver nota de alcance en
`documentacion/F15_BASELINE.md` "Decisión de alcance para F15-F20": no se ejecutaron migraciones
nuevas en esta fase, consistente con el §5 del propio prompt maestro y con
`documentacion/FASE10_ROLLOUT_CONTROLADO.md`, ya cerrado en la consolidación anterior)

| # | App | Sede-aware | Área-aware | Estado real | Detalle |
|---|---|:---:|:---:|---|---|
| F17.1 | compras | ✅ `SedeAwareModel`, NOT NULL | ✅ opcional | 🟢 Piloto oficial completo | `COMPRAS_PILOT_VALIDATION.md` |
| F17.2 | ventas | N/A (por diseño) | N/A | 🟢 Completo por diseño | Sede resuelta por contexto al facturar, no campo propio — confirmado con el usuario |
| F17.3 | facturas | 🟡 campo nullable, filtro null-safe | ❌ sin campo | 🟡 Parcial (deliberado) | `FACTURAS_AUDIT.md` |
| F17.4 | inventario | 🟡 campo nullable, filtro null-safe | ❌ | 🟡 Parcial | `ORGANIZATIONAL_SCOPE_MATRIX.md` §4.1 |
| F17.5 | clientes | ❌ | ❌ | ⚪ NO recomendado | Decisión de negocio explícita |
| F17.6 | proveedores | ❌ | ❌ | 🔴 Backlog no priorizado | Candidato débil, sin caso de uso confirmado |
| F17.7 | cotizaciones | 🟡 campo nullable, filtro null-safe | ❌ | 🟡 Parcial | — |
| F17.8 | proyectos | 🟡 campo nullable, filtro null-safe | ❌ | 🟡 Parcial | — |
| F17.9 | gastos | 🟡 campo nullable, filtro null-safe | ❌ | 🟡 Parcial | — |
| F17.10 | empleados | 🟡 campo nullable, filtro null-safe | ✅ único con campo `area` propio | 🟡 Parcial (más completo que las demás 🟡) | — |
| F17.11 | bancos | ❌ (solo texto libre `sucursal`) | ❌ | 🔴 Backlog no priorizado | Candidato plausible, sin caso de uso confirmado |
| F17.12 | contabilidad | ❌ | ❌ | 🔴 Backlog no priorizado | Solo plausible para `AsientoContable`/`MovimientoContable`, nunca el catálogo/períodos |
| F17.13 | dashboard | ❌ (agregado) | ❌ | ⚪ NO recomendado tal como está diseñado | Requeriría rediseño del modelo de snapshot, no un rollout |

## Por qué no se migró nada nuevo en esta fase (registrado, no un olvido)

1. **El propio prompt maestro lo prohíbe en su §5**: "El objetivo NO es poner sede_id en todas las
   tablas... NO migración masiva inicial. Primero: DESCUBRIR → CLASIFICAR → MODELAR → VALIDAR →
   MIGRAR." El paso DESCUBRIR/CLASIFICAR/MODELAR/VALIDAR **ya se ejecutó** en FASE 5 de la
   consolidación anterior (`ORGANIZATIONAL_SCOPE_MATRIX.md`) — y concluyó que 5 de las 6 apps
   restantes (`clientes`, `dashboard` explícitamente NO; `proveedores`, `bancos`, `contabilidad`
   sin caso de uso confirmado) no tienen la necesidad de negocio verificada que el propio §5 exige
   antes de MIGRAR.
2. **Decisión explícita del usuario sobre `ventas`** (2 turnos atrás, misma sesión): no agregar
   campo `sede`. F17.2 del orden de este prompt pedía exactamente eso — se registra el conflicto
   (no se sobrescribe silenciosamente) y se mantiene la decisión vigente como SSoT, consistente con
   el protocolo de conflictos del propio §0 de la fase F13/F14 anterior.
3. **No se re-litiga la decisión de FASE 10** (`documentacion/FASE10_ROLLOUT_CONTROLADO.md`) — ya
   cerrada, con razón documentada por app.

**Estado: 🟢 F17 COMPLETED (como estado real documentado — 2 apps completas, 6 parciales
deliberadas, 2 explícitamente no aplicables, 3 backlog sin caso de uso, 0 migraciones nuevas).**
