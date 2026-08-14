# F33.14-D — Filter/Search Bar: Inventario y Adopción Controlada

Mismo rigor que F33.14-A/B/C: auditoría completa ANTES de tocar código,
lectura de cada candidato completo (no solo grep de la firma
superficial), ningún hallazgo `APP_SPECIFIC`/`KEEP` convertido
automáticamente en `SHARED`.

## Metodología

1. Grep de `data-search-input` (firma exacta del target) sobre
   `apps/tenant/**/*.html` -- solo 4 archivos (incluye el propio
   partial). Insuficiente: la mayoria de las apps ya tenian barras de
   busqueda HTMX antes de F33.8 sin adoptar ese atributo.
2. Grep ampliado de `keyup changed delay:400ms` (la firma real del
   mecanismo de busqueda con debounce, independiente de que atributo
   use) sobre `apps/tenant/**/*.html` -- **22 archivos**, confirma que
   el inventario original de F33.0 (que listaba 8 apps para este batch)
   subestimo la duplicacion real, mismo patron ya visto en F33.14-A/B/C.
3. Lectura completa de cada sitio con contexto (wrapper, boton,
   atributos `data-*`, mecanismo de disparo del boton) para clasificar:
   ¿markup byte-identico al target (`input-group input-group-sm w-auto`
   + `data-search-input`/`data-module` + boton `data-action="search"`)?
   ¿o una familia visual/funcional distinta?

## F33.14-D INVENTARIO

```
Candidatos encontrados: 21 archivos (22 con el propio partial)
├── SHARED_CANDIDATE: 2  (compras, gastos -- 3 sitios)
├── DUPLICATE:         8  (2 sub-familias reales -- 10 sitios)
└── KEEP (patron "input bare", sin wrapper ni boton): 13  (19 sitios)

Migraciones ejecutadas: 2 archivos, 3 sitios
```

## Detalle por candidato

### SHARED_CANDIDATE (migrado)

| # | Archivo | Evidencia | Accion |
|---|---|---|---|
| 1 | `compras/compras_list.html` (`#search-compra`) | Markup byte-identico: `input-group input-group-sm w-auto` + `data-search-input` + `data-module="compras"` + boton `data-action="search"` | **Migrado** |
| 2 | `gastos/gastos_list.html` (`#search-gasto`, `#gastos-search-resolucion`) | Mismo patron exacto, 2 sitios | **Migrado**, 2/2 |

### DUPLICATE -- familia A: "input-group con icono prefijo, sin boton" (4 archivos, 4 sitios)

| # | Archivo | Evidencia | Accion |
|---|---|---|---|
| 3 | `clientes/clientes_list.html` (`#search-cliente`) | `input-group input-group-sm` (sin `w-auto`, usa `style="max-width:300px"`) + `<span class="input-group-text">` con icono ANTES del input (el target no tiene icono, el boton va DESPUES) + `hx-include` para combinar con filtros activos -- estructura visual y funcional distinta | No migrado |
| 4 | `proyectos/proyectos_list.html` (`#search-proyecto`) | Mismo patron exacto que #3 (icono-prefijo, `hx-include` de filtros) | No migrado |
| 5 | `ventas/list_ventas.html` (`#search-venta`) | Mismo patron exacto que #3/#4 | No migrado |
| 6 | `facturas/list_factura.html` (`#search-factura`) | Mismo patron exacto que #3-#5, con la diferencia adicional de que el propio input NO tiene `hx-get` -- es referenciado externamente via `hx-include`/`from:#search-factura` en los paneles de las 2 pestañas (ventas/compras) | No migrado |

Los 4 archivos comparten el mismo patron real y consistente entre si
(icono `bi-search` como prefijo dentro del `input-group`, sin boton
explicito, casi siempre con `hx-include` para combinar con filtros por
pestaña/estado) -- es una familia visual genuina, distinta del target,
no una migracion pendiente.

### DUPLICATE -- familia B: "input-group w-auto + boton, pero no byte-identico" (2 archivos, 4 sitios)

| # | Archivo | Evidencia | Accion |
|---|---|---|---|
| 7 | `bancos/list_bancos.html` (`#search-cuenta`, `#search-extracto`) | Wrapper `input-group input-group-sm w-auto` coincide, pero **no tiene boton de busqueda en absoluto** (el `btn-primary` adyacente es "Nueva Cuenta"/"Nuevo Extracto", no búsqueda) ni `data-search-input` -- migrar anadiria un boton que hoy no existe, cambio de UI real | No migrado |
| 8 | `proveedores/proveedores_list.html` (`#search-proveedor`, `#search-cuentas-pagar`) | Wrapper coincide y SI tiene boton, pero el boton dispara su PROPIO `hx-get`+`hx-include="#search-proveedor"` (HTMX declarativo autosuficiente) en vez de depender del handler JS `data-action="search"` que usa el target -- mecanismo de disparo distinto, y el input no tiene `data-search-input`/`data-module` | No migrado |

### KEEP -- familia "input bare, sin wrapper ni boton" (13 archivos, 19 sitios)

| Archivo(s) | Sitios | Evidencia |
|---|---|---|
| `contabilidad/partials/list_asientos.html`, `list_cuentas.html`, `list_periodos.html`, `list_plantillas.html`, `list_retenciones.html` | 5 | `input.form-control.form-control-sm` (2 con `style="width:240px"`) directo, sin `<div class="input-group">`, `type="search"` nativo (el navegador provee el boton de limpiar, de ahi el trigger `search` en el evento), varios con `hx-include` de multiples filtros dropdown |
| `empleados/empleados_list.html` | 5 | 4 sitios bare (`form-control form-control-sm`, `style="max-width:400px"`) + 1 variante compacta anidada (`input-group input-group-sm ms-auto` con `style="max-width:120px"`, `font-size:.72rem`, dentro de un mini-panel de nomina) -- ninguno coincide con el target |
| `empresa/empresa_list.html` | 3 | `form-control` (sin `-sm`), sin wrapper ni boton |
| `empresa/mailinbox_list.html` | 1 | Mismo patron bare que `empresa_list.html` |
| `perfil/partials/list.html` | 1 | Mismo patron bare |
| `inventario/list_activos.html`, `list_productos.html`, `list_categorias.html`, `list_servicios.html` | 4 | Mismo patron bare (2 con `style="max-width:..."`) |

Ningun sitio de esta familia usa `input-group` ni boton de busqueda --
migrarlos al target implicaria anadir un wrapper y un boton que hoy no
existen visualmente, cambio de diseno real en 13 archivos, no una
migracion mecanica.

## Verificación de la migración ejecutada

- Render directo del `{% include %}` vía `Template().render()` con un
  `search_url` de prueba (la resolucion real de `{% url %}` requiere
  contexto de tenant/schema, no disponible en un shell aislado): output
  estructuralmente byte-idéntico al markup original.
- `{% url 'app:vista' as var %}` seguido de `search_url=var` es el mismo
  patron ya usado en el repo (`empleados/partials/tabla_liquidacion_detalle.html:24`)
  -- misma resolución de URL que la version inline anterior, sin cambio
  de comportamiento.
- `manage.py check`: PASS.
- Governance (`tools.organizational_governance.cli --report`): **FINAL
  STATUS: PASS**.
- E2E: ver `F33_STATUS_REPORT.md`.

## Pendiente, documentado con evidencia (no omisión)

| Candidato | Qué falta para decidir |
|---|---|
| Familia A "icono-prefijo" (`clientes`, `proyectos`, `ventas`, `facturas` -- 4 archivos) | ¿Extender `filter_bar.html` con una variante "icono-prefijo sin boton", o mantenerla fuera del alcance del primitivo actual? Decision de diseno, no solo tecnica -- es la familia mas consistente y candidata mas fuerte para una 2a variante del partial |
| `bancos/list_bancos.html` | ¿Anadir el boton de busqueda que falta (cambio de UX real) o dejar el primitivo opcional-sin-boton? |
| `proveedores/proveedores_list.html` | ¿Migrar el boton a depender del handler JS `data-action="search"` (cambio de mecanismo, requiere confirmar que el JS de esa pagina no dependa de la firma HTMX propia del boton actual)? |
| Familia "input bare" (13 archivos) | La mas alejada del target -- requeriria anadir wrapper + boton en 13 archivos, cambio de diseno visual explicito fuera del alcance de "adopcion controlada" |

Ninguno se ejecuta en esta pasada -- cada uno requiere su propia
decisión de diseño con evidencia adicional, consistente con la regla
"no sobrediseño" de la misión.
