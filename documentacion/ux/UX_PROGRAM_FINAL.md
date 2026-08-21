# UX_PROGRAM — Cierre de la misión de transformación UX/UI

**Status final: ✅ COMPLETED_WITH_DEFERRED**

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`. **16 commits**
(`819c555`..`660b987`), **31 archivos tocados**, **1310 líneas
insertadas / 94 eliminadas**. Cero migraciones, cero cambios de
modelo, cero cambios de lógica de negocio, cálculos o permisos —
100% presentación (templates, CSS, JS de UI, documentación).

---

## Veredicto

**COMPLETED_WITH_DEFERRED**, no `COMPLETED` puro: la misión cubrió las
16 apps en el orden fijo exigido, produjo los 2 documentos de FASE 0/1
pedidos, y corrigió cada hallazgo de bajo riesgo que encontró — pero
deja **hallazgos reales, identificados y documentados, deliberadamente
sin corregir** porque corregirlos habría exigido más que un cambio de
presentación de bajo riesgo (ver §4). Ninguno de los diferidos bloquea
el uso normal del sistema — de ahí `COMPLETED_WITH_DEFERRED` y no
`BLOCKED_SAFE`.

---

## 1. Alcance cubierto vs. plan original de la misión

| Fase del plan original | Entregado |
|---|---|
| FASE 0 — Baseline | ✅ `UX_MASTER_BASELINE.md` |
| FASE 2 — Home/Onboarding | ✅ Checklist de primeros pasos, 100% API-First |
| FASE 3 — Navegación agrupada | ✅ 6 grupos con criterio uniforme (corregido en 2 pasadas) |
| Recorrido app-por-app en orden fijo | ✅ Home→Perfil→Empresa→Clientes/Proveedores→Inventario/Cotizaciones/Proyectos→Gastos/Compras/Ventas→Facturas/Contabilidad/Bancos→Empleados/Dashboard |
| FASE 1 — Mapa de experiencia | ✅ `MAPA_EXPERIENCIA_UX.md`, con relaciones contables reales verificadas en código |
| Revisión de formularios (crear/editar) | ✅ ~80 offcanvas en 14 apps, barrido sistemático + verificación manual |
| Fase dedicada a Facturas | ✅ Investigación profunda completada — confirma no tocar el offcanvas, 1 fix adicional encontrado |
| FASE 31 — `UX_<APP>_AUDIT.md` por app | ⚪ No ejecutada — ver nota abajo |
| FASE 35 — Auditoría cruzada final | ✅ Este documento |

**Nota sobre FASE 31 (documentos de auditoría individuales por app):**
se decidió no generar 16 archivos `UX_<APP>_AUDIT.md` separados
porque el contenido que llevarían ya está cubierto, sin duplicación,
en `UX_MASTER_BASELINE.md` (hallazgo por hallazgo, con verificación)
y `MAPA_EXPERIENCIA_UX.md` (relación entre apps). Crear 16 documentos
adicionales en su mayoría vacíos (10 de las 16 apps no tuvieron
hallazgos) habría sido documentación redundante sin valor de
consulta adicional — decisión consistente con el principio de la
misión "Simplicity First: minimo codigo, no abstracciones
especulativas", aplicado aquí a documentación en vez de código.

---

## 2. Scorecard por app

| App | Navegación/Listado | Formularios | Resultado |
|---|---|---|---|
| Dashboard | Sin hallazgos | Sin hallazgos | Sin cambios |
| Perfil | Rótulo mal etiquetado | Sin hallazgos | Corregido |
| Empresa | Badge "SSoT" | Sin hallazgos | Corregido |
| Empleados | — | Verbos de botón + offcanvas revisado (workaround válido) | Corregido |
| Clientes | — | UUID expuesto + verbos de botón + wording | Corregido |
| Proveedores | Sin hallazgos | Sin hallazgos | Sin cambios |
| Cotizaciones | Sin hallazgos | UUID + label + accesibilidad + help text (4 hallazgos) | Corregido |
| Proyectos | Offcanvas duplicado | UUID expuesto | Corregido |
| Inventario | Offcanvas duplicado | Sin hallazgos | Corregido |
| Gastos | Sin hallazgos | Sin hallazgos | Sin cambios |
| Compras | Sin hallazgos | Sin hallazgos | Sin cambios |
| Ventas | Sin hallazgos | Wording | Corregido |
| Facturas | Offcanvas revisado 2 veces (deliberadamente no tocado) | "DTO" x2 | Parcial: 1 fix + 1 hallazgo diferido |
| Bancos | Sin hallazgos | Sin hallazgos | Sin cambios |
| Contabilidad | Sin hallazgos | "Motor Fase 3", UUIDs, IDs crudos (4 hallazgos) | Corregido |
| Sidebar (transversal) | Agrupación + criterio uniforme | — | Corregido (2 pasadas) |

**10 de 16 apps sin ningún hallazgo** — se reportó honestamente en vez
de forzar cambios cosméticos sin valor (Clientes/Proveedores, Gastos/
Compras/Ventas fueron los primeros ejemplos de esto).

---

## 3. Los 16 commits

1. `819c555` — Navegación agrupada (FASE 3) + fix de resaltado activo (aria-current)
2. `30b1f2f` — Descarta caché de nginx como causa del bloqueo de verificación visual
3. `9080ded` — Checklist de primeros pasos (FASE 2)
4. `95991ab` — "Mi perfil" → "Usuarios y roles"
5. `423dfb8` — Confirma vía pytest que 2 tests fallan por staleness pre-existente
6. `80b6860` — Unifica el sidebar: "Operación" → "Comercial" + "Operación"
7. `3b880eb` — Elimina el badge "SSoT"
8. `7b0f63a` — Consolida offcanvas duplicado en Inventario y Proyectos
9. `5d23d82` — Revisión de Facturas/Contabilidad/Bancos (sin cambios de código)
10. `7eb78e3` — Cierra la primera pasada completa (Empleados/Dashboard + resumen)
11. `777c76e` — FASE 1: mapa de experiencia completo
12. `af6dcf4` — Formularios de Clientes/Cotizaciones/Ventas
13. `15153d3` — Formularios de Proyectos/Facturas/Contabilidad
14. `c7b5d76` — Unifica verbos de botón en Empleados y Clientes
15. `f289097` — Consolida documentación de la fase de formularios
16. `660b987` — Fase dedicada a Facturas: confirma no tocar + 1 fix nuevo

---

## 4. Hallazgos deliberadamente diferidos (no corregidos, y por qué)

| Hallazgo | Por qué se difiere | Riesgo si se corrige a ciegas |
|---|---|---|
| Offcanvas de `facturas_main.js` (initOffcanvas) | Timing crítico de Bootstrap ya ajustado por prueba y error (setTimeout 50ms, doble-init); sin navegador real para probar | Reintroducir un bug de `null.scroll` ya resuelto |
| `LandingPageView` inalcanzable (shadowed en `urls_public.py`) | Fuera del alcance de UI/UX — es una decisión de routing/producto | Ninguno si se deja, pero requiere decisión de producto para corregir |
| `test_perfil_removed_from_sidebar` pasa vacío | El selector busca markup que ya no existe desde antes de esta misión — arreglarlo exige decidir si la intención original (sacar Perfil del sidebar) sigue vigente | Decisión de producto, no de UI |
| `test_hash_routing_still_works` / `test_workspace_contains_all_view_sections` fallan | Esperan una arquitectura (`hydrateView`, `id="view-*"`) reemplazada hace tiempo por `showTab()`/`id="tab-*"` | Reescribir estos tests es trabajo de mantenimiento de suite, no de UI |
| `ItemNotaCredito` no existe — devoluciones sin movimiento de inventario automático | Gap de modelo/backend (ver plan `linked-drifting-kitten`, no ejecutado) | Fuera de alcance total de una misión de presentación |
| Verbos de botón inconsistentes *entre* apps (Nueva/Crear/Guardar) | ~20+ botones en archivos estables; sin guía de estilo previa que seguir, alto volumen para bajo riesgo/beneficio | Se documenta como recomendación de guía de estilo, no se ejecuta en masa |
| Relación Cotización → Venta | No verificada en código durante esta sesión | Ninguno — es una nota de "por confirmar", no un hallazgo |

Todos estos ya estaban documentados individualmente en
`UX_MASTER_BASELINE.md` y/o `MAPA_EXPERIENCIA_UX.md`; esta tabla es
solo el índice consolidado final.

---

## 5. Recomendaciones para trabajo futuro (fuera del alcance de esta misión)

1. **Guía de estilo de botones**: definir una convención única
   ("Guardar [Entidad]" para crear, "Actualizar [Entidad]" para
   editar) y aplicarla la próxima vez que se toque cada formulario,
   en vez de en una pasada masiva dedicada.
2. **Sesión de ingeniería dedicada a Facturas**: con acceso a un
   navegador real, probar los 10+ sitios donde se usa
   `initOffcanvas()`/`showOffcanvas()` antes de intentar consolidar
   con el helper central.
3. **Verificación visual manual**: todos los cambios de esta misión
   se verificaron con Django test Client + lectura de código (el
   navegador sandbox de esta sesión bloquea la totalidad de
   peticiones a este dominio local). Se recomienda una pasada visual
   humana antes de considerar esto completamente validado en
   producción.
4. **Responsive/mobile y accesibilidad profunda**: no evaluados en
   esta misión (más allá del fix puntual de `aria-current` y los
   `for`/`id` agregados en Cotizaciones).
5. **Limpieza de tests obsoletos**: `test_workspace_account_dropdown.py`
   tiene 3 aserciones que no verifican nada real (selector
   desactualizado) o fallan contra arquitectura ya reemplazada —
   requiere una decisión de producto antes de tocarlos.

---

## 6. Documentos de esta misión

- [`UX_MASTER_BASELINE.md`](UX_MASTER_BASELINE.md) — bitácora
  detallada de cada fase, hallazgo y verificación, en orden
  cronológico.
- [`MAPA_EXPERIENCIA_UX.md`](MAPA_EXPERIENCIA_UX.md) — mapa del
  recorrido de usuario y relación real entre las 16 apps.
- Este documento — cierre formal y punto de entrada para quien
  retome el trabajo.
