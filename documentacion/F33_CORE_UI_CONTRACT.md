# F33.2-F33.9 — Core UI Contract

Cubre F33.2 (contrato conceptual), F33.3 (Table), F33.4 (Offcanvas), F33.5
(Form), F33.6 (Estados), F33.7 (Notificaciones), F33.8 (Filtros), F33.9
(Cards) en un solo documento -- la mayoria de estas secciones apuntan a
infraestructura que YA EXISTE (confirmado en F33.0/F33.1) o son
consolidaciones de duplicados existentes, no componentes nuevos. Separarlas
en 8 documentos individuales seria sobre-documentar algo que en su mayoria
ya esta resuelto.

**Principio rector (F33, regla de no-sobrediseño):** este proyecto es
HTMX + Bootstrap 5.3 + django-tables2 + Vanilla JS ES6+, sin build step.
Un componente de UI puramente presentacional (una card, un badge) no
necesita ser un objeto JS en runtime -- puede y debe ser un Django template
tag server-side, igual que `{% render_table %}` ya lo es. Reservar
`window.Sintel.Core.UI` para lo que es genuinamente interactivo/con estado
en el navegador (Offcanvas, Confirm). Esto es composicion de primitivas
pequeñas, no un framework de componentes.

---

## F33.3 — Table Contract

**Ya resuelto, sin cambios.** django-tables2 + HTMX es el patron estandar
confirmado (F33.0 §7): >25 sitios en 11 apps, 0 duplicacion, 0
implementaciones hand-rolled de paginacion. La unica cobertura que faltaba
(wording de `empty_text`) se resuelve en F33.6, no aqui. **No crear
`Sintel.Core.UI.Table`** -- ya existe y funciona: `{% render_table table %}`.

Regla reafirmada (ya en AGENTS.md, sin cambios): tablas nuevas usan
django-tables2+HTMX, nunca Tabulator. Las excepciones ya justificadas
(inventario en migracion, ver F31.6) no se tocan.

---

## F33.4 — Offcanvas Contract (CONSOLIDACION, no componente nuevo)

**Hallazgo (F33.0 §12):** existen 2 helpers "safe" con adopcion
comparable -- `Sintel.Core.mostrarOffcanvasSeguro` (~25 archivos) y
`UIManager.handleOffcanvas` (~22 archivos) -- mas 6 instanciaciones crudas
y 6+ copias manuales del mismo snippet de fallback.

**Decision de diseño:** `mostrarOffcanvasSeguro` es el nombrado
oficialmente en AGENTS.md §26 y tiene mas adopcion nominal, pero
`UIManager.handleOffcanvas` cubre un caso que el otro no maneja (cierre
explicito via `action='hide'`). En vez de elegir uno y perder capacidad,
`mostrarOffcanvasSeguro` se extiende (F33.13, migracion controlada) para
aceptar una accion opcional (`mostrarOffcanvasSeguro(el, {action: 'show'|'hide'})`,
default `'show'` para no romper los ~25 consumidores existentes), y
`UIManager.handleOffcanvas` se convierte en un alias fino que delega en
el, dejando UN SOLO cuerpo de logica real. Los 6 sitios con
`new bootstrap.Offcanvas()` crudo y los 6+ snippets copiados a mano migran
a la funcion consolidada.

**No se ejecuta la migracion completa de los ~47 archivos en esta pasada**
(violaria la regla "nunca refactor masivo + migracion masiva en la misma
operacion"). Se ejecuta sobre el app piloto (F33.10) primero, se valida, y
la expansion controlada (F33.13) continua desde ahi.

**Contrato final (una vez consolidado):**
```javascript
window.Sintel.Core.mostrarOffcanvasSeguro(elOrId, { action: 'show' } = {})
// action: 'show' (default, compat con los ~25 usos actuales) | 'hide'
// Dispone cualquier instancia previa + limpia backdrops huerfanos antes
// de show(). Unico punto de entrada -- UIManager.handleOffcanvas queda
// como alias deprecado que delega aqui, no se elimina de inmediato para
// no romper los ~22 consumidores existentes sin migrar primero.
```

---

## F33.5 — Form Contract

**Sin hallazgos de duplicacion real en F33.0** (fuera de alcance explicito
del inventario -- las cajas `#form-X-feedback` ya son consistentes, F33.0
§10c). Los patrones de input/select/date/file ya siguen las convenciones
de `.agents/skills/frontend/vanilla-js.md` (namespace, DOM Shield,
recoleccion de FormData) y `crud-fsd.md`. **No se crea `Sintel.Core.UI.Form`**
-- no hay evidencia de repeticion que lo justifique. Si una fase futura
encuentra duplicacion real (p.ej. auditando validacion de campos), se
revisita con evidencia, no antes.

---

## F33.6 — Estados UI (Loading / Empty / Error)

**Loading** (F33.0 §2): el patron HTMX-panel (~15 archivos, ya
consistente) se formaliza como partial, sin cambiar su HTML:
```django
{% include 'tenant/core/partials/loading_state.html' with entity="facturas" %}
```
El spinner Tabulator legacy no se toca (atado a F33.3, fuera de alcance).
Los 2 prototipos Tailwind confirmados muertos se eliminan (ver §Limpieza
mas abajo).

**Empty** (F33.0 §3): 2 acciones separadas --
1. Diccionario de wording compartido para `empty_text` de django-tables2
   (NO un componente, solo constantes Python reutilizables):
   ```python
   # apps/tenant/core/tables_i18n.py
   def empty_text(entidad_plural, genero='o'):
       return f"Sin {entidad_plural} registrad{genero}s"
   ```
   Uso: `empty_text = empty_text("facturas")` en cada `Meta` de `tables.py`.
   No obligatorio migrar los `tables.py` existentes en esta pasada (seria
   refactor masivo); se adopta en tablas nuevas y en el piloto.
2. Partial compartido para el patron hand-rolled (icono + texto),
   reemplazando los 6 sitios + 1 sub-variante:
   ```django
   {% include 'tenant/core/partials/empty_state.html' with entity="contactos" %}
   ```

**Error** (F33.0 §4): sin accion -- es un patron de una sola app
(`contabilidad`), no hay repeticion cross-app que justifique
consolidacion. Sigue siendo `APP_SPECIFIC`.

---

## F33.7 — Notificaciones

**Ya resuelto, sin cambios.** `UIManager` (`ui-manager.js`) ya es el SSoT
de success/warning/error/info via SweetAlert2, confirmado como el unico
sistema de toast en uso (F33.0 §4, ~38 archivos JS lo consumen). Ninguna
app tiene su propio sistema de notificaciones. **No se crea
`Sintel.Core.UI.Toast`** -- ya existe como `window.UIManager`.

---

## F33.8 — Filtros y Busqueda (CANDIDATE_SHARED real)

**Hallazgo (F33.0 §6):** comportamiento HTMX ya unificado (debounce,
`hx-trigger`, `name="q"" identicos en todos los sitios encontrados); solo
el markup wrapper diverge en 3 variantes. Se consolida en un partial, sin
tocar el comportamiento HTMX ya correcto:

```django
{% include 'tenant/core/partials/filter_bar.html' with placeholder="Buscar factura..." target="#facturas-panel" %}
```

No se introduce ninguna libreria de filtros adicional (regla explicita de
la mision). El patron de pills de filtro de `clientes_list.html` (unico en
su tipo) no se generaliza sin mas evidencia de repeticion -- queda
`APP_SPECIFIC` por ahora.

---

## F33.9 — Cards (CANDIDATE_SHARED real)

**Hallazgo (F33.0 §1):** card de metrica (icono+numero+label) copiada
verbatim en 7 archivos, con 0 adopcion en otras 7 apps. Se diferencian 3
tipos segun la mision (metric/entity/summary/action) -- el inventario solo
encontro evidencia real de repeticion para el tipo **metric card**; los
otros 3 tipos no tienen evidencia de duplicacion en este codebase, no se
inventan.

```django
{% load sintel_ui %}
{% sintel_kpi_card icon="receipt" color="primary" value=total_facturas label="Facturas" %}
```

Implementacion: `apps/tenant/core/templatetags/sintel_ui.py`, un
`simple_tag` o `inclusion_tag` que renderiza el markup ya identificado en
F33.0 §1 sin alterarlo (mismo HTML final, solo se deja de copiar-pegar).

---

## Resumen del contrato final

| Pieza | Tipo | Estado |
|---|---|---|
| Table | Server-side (django-tables2) | Ya existe, sin cambios |
| Offcanvas | JS (`Sintel.Core.mostrarOffcanvasSeguro`) | Existe, se consolida (retira el duplicado) |
| Form | -- | No se crea (sin evidencia) |
| Loading | Server-side (template partial) | Nuevo, minimo |
| EmptyState | Server-side (template partial + helper Python) | Nuevo, minimo |
| ErrorState | -- | No se crea (`APP_SPECIFIC`, sin repeticion cross-app) |
| Confirm | JS (`window.UIManager.confirm()`) | Existe, subutilizado -- se promueve su adopcion (F33.13), no se crea otro |
| Filters | Server-side (template partial) | Nuevo, minimo |
| Card (KPI) | Server-side (template tag) | Nuevo, minimo |

**Deliberadamente NO se crea `window.Sintel.Core.UI` como namespace JS
nuevo** -- de las 10 piezas conceptuales de la mision, 6 ya existen o son
server-side (no ameritan un objeto JS), y las 2 que SI son JS (`Offcanvas`,
`Confirm`) ya tienen su implementacion real bajo namespaces existentes
(`Sintel.Core.mostrarOffcanvasSeguro`, `window.UIManager`). Crear un
namespace envolvente adicional solo para re-exportar lo que ya existe
seria indireccion sin valor -- viola "preferir primitivas pequeñas,
contratos claros, composicion" tanto como crear un componente universal
innecesario.

## Limpieza (evidencia, no especulacion)

Codigo muerto confirmado en F33.0, candidato a eliminacion (se ejecuta
junto con el piloto, F33.10-11, no antes de tener spec E2E de regresion
lista):
- 2 prototipos Tailwind huerfanos (`dashboard/static/tenant/dashboard/index.html`
  + 5 hermanos bajo `core/static/tenant/core/*/index.html`).
- `empresa/templates/tenant/empresa/modals.html` (3 modals CRUD completos, ~213 lineas).
- Modal confirmar-eliminar muerto en `compras/compras_list.html` y `gastos/gastos_list.html`.
