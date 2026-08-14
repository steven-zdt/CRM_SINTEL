# F33.14-A — Card KPI: Inventario y Adopción Controlada

Auditoría evidence-based en las 17 apps tenant, ANTES de tocar ningún
archivo, siguiendo la regla explícita: `buscar candidato → verificar
duplicación real → spot-check visual → migrar si aporta valor → test →
siguiente candidato`. No se convierte automáticamente ningún hallazgo
`APP_SPECIFIC` en `SHARED`.

## Metodología

Grep en 3 pasadas de precisión creciente sobre `apps/tenant/**/*.html`:
1. Firma exacta del target (`rounded-circle...bg-opacity-10` + `fs-4
   fw-bold`) -- confirma los 7 sitios ya documentados en F33.0.
2. `rounded-circle` sola -- 11 archivos, incluye falsos positivos
   (círculos de avatar/foto).
3. `kpi|metric-card|stat-card|dashboard-card` (case-insensitive) -- 28
   archivos, mayoría falsos positivos de `card-body d-flex` genérico;
   filtrado por lectura de cada candidato nuevo.
4. `kpi_[a-z_]+` (convención de nombre de variable Django) -- confirma
   2 implementaciones adicionales independientes no detectadas por la
   auditoría original de F33.0 (`compras`, `inventario`).

Cada candidato nuevo se leyó completo (no solo grep) antes de
clasificar, incluyendo su archivo JS asociado cuando el markup se
genera dinámicamente.

## F33.14-A INVENTARIO

```
Candidatos encontrados: 16
├── SHARED_CANDIDATE: 3  (clientes, proyectos*, cotizaciones)
├── APP_SPECIFIC:      3  (empleados-liquidacion, proyectos-tareas-cortas, dashboard)
├── DUPLICATE:          6  (ventas, gastos, facturas-list, compras, inventario x2)
└── KEEP:                4  (facturas-offcanvas-editar, perfil, empleados x2)

Migraciones ejecutadas: 2 archivos completos + 1 parcial (4/6 cards)
Archivos afectados: 2 (clientes/partials/tabla_clientes.html,
                        proyectos/partials/tabla_proyectos.html)
```

`*` proyectos solo migró parcialmente (4 de 6 cards) -- ver detalle.

## Detalle por candidato

| # | Archivo | Clasificación | Evidencia | Acción |
|---|---|---|---|---|
| 1 | `clientes/partials/tabla_clientes.html` (6 cards) | **SHARED_CANDIDATE** | Markup byte-idéntico al target (`sintel_kpi_card`: circle 40px, `fs-4 fw-bold`, `small text-muted`, `col-6 col-md-4 col-xl-2`, `gap-2 py-3`), valores server-rendered `{{ kpis.x }}`, sin acoplamiento JS por `id` | **Migrado**, 6/6 cards |
| 2 | `proyectos/partials/tabla_proyectos.html` (6 cards) | **SHARED_CANDIDATE (parcial)** | 4 cards byte-idénticas al target. Las otras 2 ("Avance Prom.", "Cartera Total") usan `bg-purple` (no es una clase Bootstrap estándar, requiere override `!important` inline) y `font-size:0.9rem` custom para un valor monetario largo -- personalización real, no descuido | **Migrado 4/6**; las 2 restantes se dejan intactas, documentadas como personalización real, no como pendiente |
| 3 | `cotizaciones/list.html` (6 cards) | **SHARED_CANDIDATE, bloqueado** | Markup byte-idéntico al target, PERO los valores usan `id="kpi-cot-total"` etc. con placeholder `-`, actualizados dinámicamente por `cotizaciones.table.js` (`document.getElementById(...).textContent = ...`). `sintel_kpi_card` no acepta un parámetro `id` -- migrar rompería el mecanismo de actualización | **NO migrado.** Requiere una decisión de diseño explícita (extender el primitivo con un `id` opcional) antes de tocar este archivo -- no se hace en esta pasada sin evidencia de que otros candidatos también lo necesiten (ver #5, #4) |
| 4 | `ventas/partials/tabla_ventas.html` (4 cards) | **DUPLICATE** (estilo propio, no el target) | Círculo 38px (no 40px), icono `font-size:1.1rem` explícito, valor `font-size:1.15rem` (no `fs-4`), label en mayúsculas con letter-spacing (no `small text-muted`), borde izquierdo de color de 3px por card, grid `col-xl-3` (no `col-xl-2`) | No migrado -- migrar a `sintel_kpi_card` tal como existe cambiaría el diseño visual (tamaño, borde de acento, tipografía del label). Es un estilo deliberadamente distinto, no una copia descuidada |
| 5 | `facturas/list_factura.html` (2 cards) | **DUPLICATE** (mismo estilo que #4) + acoplamiento JS | Mismo patrón visual que ventas (38px, borde de acento, label mayúsculas) Y valores actualizados por `id` desde JS (`ventas-total-neto`, `compras-total-neto`) | No migrado -- mismas 2 razones que #4 y #3 combinadas |
| 6 | `gastos/partials/tabla_gastos.html` (4 cards) | **DUPLICATE** (estilo propio) | Círculo 42px (no 40px), icono con `fs-5` explícito, `gap-3` (no `gap-2`), grid `col-md-3` (no `col-xl-2`), y una de las 4 cards usa `fs-6` en vez de `fs-4` para un valor monetario (`$ resumen.total_gastos_mes`) -- inconsistencia interna real dentro del propio archivo | No migrado -- mismo motivo que ventas: estilo propio con variación de tamaño de fuente intencional |
| 7 | `compras/partials/tabla_compras.html` (4 cards) | **DUPLICATE** (dentro de sí mismo) | 4 cards idénticas entre sí (`card bg-light border-0` + `<h4 class="mb-0 fw-bold">`), pero es un estilo plano SIN ícono -- estructuralmente distinto del target (que siempre lleva ícono en círculo). Duplicación real, pero no mapea al primitivo actual | No migrado -- requeriría una variante nueva del primitivo ("KPI sin ícono") o aceptar el cambio visual de agregarle un ícono. Ninguna decisión se toma sin evidencia de que otra app también lo necesite |
| 8 | `inventario/partials/tabla_activos.html` (5-6 cards dinámicas) | **DUPLICATE** (compartido con #9) | Estilo "chip compacto" propio (`.kpi-card`/`.kpi-label`/`.kpi-val`, con `<style>` inline duplicado en el propio archivo), sin ícono, sin card wrapper -- filas horizontales densas. El propio archivo dice "Presentación Compacta" en su comentario de cabecera -- diseño deliberado para una vista densa | No migrado -- estilo genuinamente distinto (compacto vs espacioso), pero SÍ es duplicación real con #9 dentro de la misma app |
| 9 | `inventario/partials/tabla_productos.html` (3-4 cards dinámicas) | **DUPLICATE** (compartido con #8) | Mismas clases CSS `.kpi-card`/`.kpi-label`/`.kpi-val` que #8, con su propio `<style>` duplicado otra vez en este archivo -- 2 copias del mismo CSS dentro de la misma app | No migrado -- candidato real para un partial/estilo compartido LOCAL a `inventario` (no necesariamente al `Sintel.Core` global), pendiente de una decisión de diseño propia, distinta de la de `sintel_kpi_card` |
| 10 | `empleados/offcanvas_detalle_liquidacion.html` ("KPI Strip") | **APP_SPECIFIC** | Franja horizontal de 3 columnas (`flex-fill` + `border-end`), sin card wrapper, sin ícono -- vive dentro del header de un offcanvas de detalle de una sola liquidación, contexto muy específico | No migrar -- forzarlo al patrón de card grid sería un cambio de layout, no una deduplicación |
| 11 | `proyectos/partials/tabla_tareas_cortas.html` ("KPI Strip") | **APP_SPECIFIC** | Mismo patrón visual de franja que #10 (`flex-fill` + `border-end`), pero vive en un panel compacto de tareas cortas, app y contexto distintos a #10 pese a la similitud visual | No migrar -- misma razón que #10; la similitud visual entre #10 y #11 no confirma que compartan el mismo caso de uso (uno es header de detalle, otro es panel de lista compacta) |
| 12 | `dashboard/list_dashboard.html` + `dashboard_main.js` (`widgetCard()`/`metricBox()`) | **APP_SPECIFIC** | Componente compuesto: una card con título/subtítulo (ícono + texto) que contiene VARIAS `metricBox()` pequeñas agrupadas -- concepto de UI distinto a "una card = una métrica" del target. Migrarlo perdería el agrupamiento visual (varias métricas relacionadas bajo un mismo título) | No migrar -- es un widget compuesto, no una card KPI simple |
| 13 | `facturas/offcanvas_editar_factura.html` (2 sitios, cliente/proveedor) | **KEEP (falso positivo)** | NO es una card de métrica -- es una card de información de entidad (ícono de persona/camión + razón social + nombre comercial), dentro de un formulario de edición. Coincidía con el grep de `rounded-circle` pero es semánticamente distinto | Sin acción -- correctamente excluido, no es "KPI" |
| 14 | `perfil/offcanvas_detalle_perfil.html` (avatar) | **KEEP (falso positivo)** | Círculo con inicial del usuario o foto de avatar -- no es una métrica | Sin acción |
| 15 | `empleados/offcanvas_editar_empleado.html` (foto de perfil) | **KEEP (falso positivo)** | Círculo de preview de foto del empleado -- no es una métrica | Sin acción |
| 16 | `empleados/offcanvas_crear_empleado.html` (foto de perfil) | **KEEP (falso positivo)** | Mismo patrón que #15, en el formulario de creación | Sin acción |

## Corrección a la auditoría original de F33.0

El inventario original (F33.0, agente de exploración) afirmaba "7
archivos, copiado verbatim" y clasificaba `ventas`/`facturas`/`gastos`
junto con `clientes`/`proyectos`/`cotizaciones` como el mismo hallazgo.
Esta auditoría más profunda (lectura completa de cada archivo, no solo
grep de la firma superficial) encontró que **solo 3 de los 7 son
realmente byte-idénticos al target** -- los otros 4 tienen
personalizaciones visuales reales (tamaño, acento de color, tipografía)
o acoplamiento funcional con JavaScript (`id` para actualización
dinámica) que el inventario original no distinguió. Migrarlos sin este
nivel de detalle habría violado la regla explícita de `sintel_ui.py`:
*"no se cambia ningún pixel de lo que ya funciona"*.

Además se encontraron **2 implementaciones completamente nuevas** no
detectadas en F33.0 (`compras`, `inventario` x2) que usan la convención
de nombre `kpi_*` en el contexto Django mas no coinciden con la firma de
grep original.

## Verificación de la migración ejecutada

- Render directo del tag vía `Template().render()`: output byte-idéntico
  al markup original (confirmado antes de aplicar a los templates).
- `manage.py check`: PASS.
- Governance (`tools.organizational_governance.cli --report`): **FINAL
  STATUS: PASS**.
- E2E: **29/29 PASS** (contenedor `web` reiniciado preventivamente antes
  de la corrida, limpio en el primer intento).

## Pendiente, documentado con evidencia (no omisión)

| Candidato | Qué falta para decidir |
|---|---|
| `cotizaciones` | Decisión de diseño: ¿extender `sintel_kpi_card` con un parámetro `id` opcional (bajo riesgo, no rompe los 10 consumidores actuales), o dejarlo fuera del primitivo compartido? |
| `ventas` / `facturas` (estilo "acento de color") | ¿Es un 2° estilo de card KPI legítimo (crear `sintel_kpi_card_compact` o un parámetro de variante), o se homologa visualmente al estilo actual? Requiere decisión de producto/diseño, no solo técnica |
| `gastos` | Mismo dilema que ventas, más la inconsistencia interna ya presente (fs-4 vs fs-6) que ni siquiera es autoconsistente hoy |
| `compras` | Estilo sin ícono -- ¿nueva variante del primitivo, o se le agrega ícono (cambio visual real)? |
| `inventario` (activos + productos) | Duplicación real intra-app confirmada -- candidato limpio para un partial LOCAL a `inventario`, independiente de la decisión sobre el primitivo global |

Ninguno de estos se ejecuta en esta pasada -- cada uno requiere su
propia decisión de diseño con evidencia adicional (no "para no dejar
nada pendiente"), consistente con la regla "no sobrediseño" de la
misión.
