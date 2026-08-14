# F33.14-B — Empty State: Inventario y Adopción Controlada

Mismo rigor que F33.14-A (Card KPI): auditoría completa ANTES de tocar
código, lectura de cada candidato completo (no solo grep de la firma
superficial), ningún hallazgo `APP_SPECIFIC` convertido automáticamente
en `SHARED`.

## Metodología

1. Grep de la firma exacta del target (`bi-inbox`, icono usado por
   `sintel_empty_state`) sobre `apps/tenant/**/*.html` -- 8 archivos
   (incluye el propio partial).
2. Grep de nombres de variable/clase alternativos (`empty-state`,
   `no-data`, `sin-registros`, etc.) -- confirma 2 candidatos más no
   capturados por la firma de ícono.
3. Lectura completa de cada candidato (no solo la línea con match) para
   determinar mecanismo de toggle (JS por `data-attr` vs `id`),
   estructura DOM (`div` standalone vs fila de `<table>`), y wrapper
   visual (card plano vs `alert-info`).
4. Verificación repo-wide de liveness antes de decidir "migrar" vs
   "eliminar" -- un candidato resultó ser código muerto, no un caso de
   migración.

## F33.14-B INVENTARIO

```
Candidatos encontrados: 8
├── SHARED_CANDIDATE: 1  (clientes_list.html, 2 sitios)
├── DUPLICATE:         4  (2 sub-variantes reales, 2 archivos c/u)
├── KEEP (patrón distinto, no migrable): 2  (table {% empty %} rows)
└── OBSOLETE (código muerto):             1  (contactos_list.html)

Migraciones ejecutadas: 1 archivo, 2 sitios
Código muerto eliminado: 1 archivo completo
```

## Detalle por candidato

| # | Archivo | Clasificación | Evidencia | Acción |
|---|---|---|---|---|
| 1 | `clientes/clientes_list.html` (`data-empty-state="contactos"`, `data-empty-state="cartera"`) | **SHARED_CANDIDATE** | Markup byte-idéntico al target (`text-center py-5` + `style="display:none"` + `bi-inbox` `font-size:2.5rem` + `<p class="mt-2 text-muted">`), toggle vía JS con selector `[data-empty-state="X"]` (`clientes.list.js:31`) -- coincide exactamente con el parámetro `data_attr` del primitivo | **Migrado**, 2/2 sitios |
| 2 | `clientes/contactos_list.html` | **OBSOLETE (código muerto)** | 0 referencias en todo el repo salvo el propio archivo y 2 menciones documentales (`.agent/AUDITORIA_FLUJO_CLIENTES.md`, `F33_SHARED_UI_INVENTORY.md`). Ningún `{% include %}`, ninguna vista Python lo renderiza. Contenía una sub-variante del empty state (ícono+texto en un solo `<p>`), pero como el archivo entero está muerto, no hay nada que "migrar" | **Eliminado** (evidencia: 0 consumidores confirmado repo-wide) |
| 3 | `clientes/offcanvas_detalle_cliente.html` (`id="historial-facturas-empty"`) | **DUPLICATE** (sub-variante "compacta") | Usa `id` (no `data-attr`) para el toggle JS, `text-center py-4` (no `py-5`), ícono `font-size:2rem` (no `2.5rem`), párrafo con `text-muted small` (no solo `text-muted`) -- tamaño reducido deliberado para un sub-panel dentro de un offcanvas | No migrado -- el primitivo actual no acepta un parámetro `id`, y forzar el tamaño `py-5`/`2.5rem` cambiaría el diseño compacto intencional |
| 4 | `proveedores/offcanvas_form.html` (`id="historial-compras-empty"`) | **DUPLICATE** (misma sub-variante que #3) | Mismo patrón exacto que #3 (`id`, `py-4`, `font-size:2rem`) en una app distinta -- confirma que es una sub-variante real y repetida, no un caso aislado | No migrado -- mismo motivo que #3. Es un candidato limpio para una futura variante "compacta" del primitivo (o un segundo `data_attr`/`id` opcional), no para forzarlo al primitivo actual |
| 5 | `proveedores/partials/representantes_directory.html` (`id="representantes-directory-empty"`) | **DUPLICATE** (sub-variante propia, wrapper `alert-info`) | `alert alert-info` en vez de card plano, `d-none` (no `style="display:none"`), `id` no `data-attr`, ícono `bi-inbox` | No migrado -- wrapper visual distinto (alerta vs card), cambio de diseño real |
| 6 | `proveedores/partials/list_representantes.html` (`id="representantes-empty-state"`) | **DUPLICATE** (4ª sub-variante, distinta de #5 pese a estar en la misma app) | `alert alert-info py-4`, pero usa `bi-info-circle` (no `bi-inbox`) y texto inline sin `<p>` separado -- **ni siquiera coincide con #5**, que está en la misma app (`proveedores`) para la misma entidad conceptual ("representantes") | No migrado -- inconsistencia real dentro de la propia app `proveedores` (2 archivos, mismo concepto, 2 estilos distintos), documentado como hallazgo, no resuelto en esta pasada |
| 7 | `bancos/offcanvas_detalle_extracto.html` (`{% empty %}` dentro de `<tr>`) | **KEEP (patrón distinto)** | No es un `<div>` standalone -- es la cláusula `{% empty %}` de un bucle Django dentro de una fila de tabla (`<td colspan="6">`). Estructuralmente incompatible con el primitivo (que asume un contenedor de bloque, no una celda con `colspan`) | Sin acción -- es un patrón "empty row de tabla", válido y distinto, no la misma duplicación |
| 8 | `facturas/offcanvas_editar_factura.html` (`{% empty %}` dentro de `<tr>`) | **KEEP (mismo patrón que #7)** | Misma estructura de fila de tabla con `{% empty %}` | Sin acción -- mismo motivo que #7 |

## Verificación de la migración ejecutada

- Render directo del tag vía `Template().render()`: output byte-idéntico
  al markup original (confirmado antes de aplicar).
- `manage.py check`: PASS.
- Governance (`tools.organizational_governance.cli --report`): **FINAL
  STATUS: PASS**.
- E2E: **29/29 PASS** (contenedor `web` reiniciado preventivamente antes
  de la corrida, limpio en el primer intento).

## Pendiente, documentado con evidencia (no omisión)

| Candidato | Qué falta para decidir |
|---|---|
| `clientes/offcanvas_detalle_cliente.html` + `proveedores/offcanvas_form.html` (sub-variante compacta) | ¿Extender `sintel_empty_state` con un parámetro `id` opcional y un modificador de tamaño, o crear una 2ª primitiva "compacta"? Requiere decisión de diseño, no solo técnica |
| `proveedores/partials/representantes_directory.html` + `list_representantes.html` | Estos 2 archivos de la MISMA app, para el MISMO concepto, tienen 2 estilos de empty-state distintos entre sí (ni siquiera coinciden entre ellos) -- antes de crear una 3ª variante compartida, valdría la pena homologar estos 2 primero dentro de `proveedores` |

Ninguno se ejecuta en esta pasada -- cada uno requiere su propia
decisión de diseño con evidencia adicional, consistente con la regla
"no sobrediseño" de la misión.
