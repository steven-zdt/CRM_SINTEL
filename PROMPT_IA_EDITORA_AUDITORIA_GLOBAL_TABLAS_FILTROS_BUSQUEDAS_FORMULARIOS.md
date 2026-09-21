# PROMPT MAESTRO — AUDITORÍA Y CORRECCIÓN GLOBAL DE TABLAS, FILTROS, BÚSQUEDA, URLS Y FORMULARIOS
## SINTEL ERP — Plan por fases con gates de supervisión

**Fecha:** 2026-09-18  
**Fuente principal adjunta:** `arquitectura_general(20260919-003051).md`  
**Objetivo:** unificar y modernizar la presentación de datos en todas las aplicaciones de negocio.

---

# 0. MISIÓN

Ejecutar una auditoría transversal de **todas las apps con listados, tablas, grids y formularios** del SINTEL ERP.

Problemas reportados a corregir:

```text
1. Las tablas dinámicas no funcionan correctamente.
2. Los filtros no funcionan.
3. Las búsquedas no funcionan o funcionan de manera inconsistente.
4. Los títulos/cabeceras de las tablas generan URLs erróneas.
5. No existe filtrado consistente por cada columna/índice.
6. La presentación de datos no está unificada.
7. Las tablas y formularios necesitan modernización.
8. Existe documentación con arquitectura histórica que contradice el código actual.
```

La misión debe dejar una infraestructura reutilizable y consistente para:

```text
LISTADOS
TABLAS
FILTROS
BÚSQUEDA
ORDENAMIENTO
PAGINACIÓN
COLUMNAS
URLS
ACCIONES
ESTADOS VACÍOS
FORMULARIOS
VALIDACIÓN
RESPONSIVE
```

La ejecución obligatoria será:

```text
DISCOVER
→ BASELINE
→ INVENTORY
→ CHOOSE
→ DESIGN
→ BUILD CORE
→ MIGRATE PILOT
→ VALIDATE
→ MIGRATE APPS
→ TEST
→ AUDIT
→ FIX
→ REGRESSION
→ DOCUMENT
→ RELEASE GATE
```

NO comenzar cambiando todas las apps simultáneamente.

---

# 1. FUENTE DE VERDAD

La documentación adjunta declara que el proyecto es:

```text
SINTEL ERP
Version documentada: 3.64.0
```

y registra una evolución importante de la arquitectura.

También contiene **documentation drift** y advierte que determinadas descripciones son históricas.

Ejemplo relevante:

```text
venta_list.js
```

aparece descrito en distintas secciones con referencias a Tabulator y, posteriormente, como listado server-rendered con:

```text
django-tables2 + HTMX
```

La propia documentación establece que las secciones antiguas NO deben utilizarse para reconstruir la arquitectura actual.

Por tanto:

## REGLA

```text
CÓDIGO REAL ACTUAL
>
DOCUMENTACIÓN HISTÓRICA
```

Toda discrepancia debe registrarse antes de corregir.

---

# 2. AUDITORÍA DOCUMENTAL INICIAL

La documentación confirma que existen actualmente patrones de:

```text
Django
DRF
HTMX
Bootstrap
django-tables2
Tabulator histórico / documentado
JavaScript específico por módulo
Service Layer
Selectors
Pagination
SearchFilter
OrderingFilter
```

En Ventas, por ejemplo, aparecen:

```text
SearchFilter
OrderingFilter
search_fields
ordering_fields
server-side pagination
```

pero el modelo documentado no proporciona un contrato transversal de filtrado individual por cada columna.

La misión deberá determinar si esto es la causa sistémica de:

```text
filtros rotos
búsquedas inconsistentes
ordenamiento inconsistente
URLs erróneas
```

---

# 3. OPCIÓN TECNOLÓGICA PROPUESTA

## Opción recomendada para SINTEL ERP

Adoptar como estándar transversal:

```text
DataTables 3.x
+
ColumnControl
+
Bootstrap 5
+
Django REST Framework
+
django-filter
+
HTMX para formularios/offcanvas
```

### Base

DataTables documenta actualmente como estable:

```text
DataTables 3.0.4
```

y el paquete actual de ColumnControl:

```text
ColumnControl 2.0.2
```

El propio ecosistema DataTables proporciona integración con Bootstrap 5 y las extensiones necesarias. citeturn395750search8turn709916search1

### Por qué esta opción encaja

DataTables soporta:

```text
serverSide
paginación
ordenamiento
búsqueda global
búsqueda por columna
columnas configurables
responsive
selección
exportación mediante extensiones
control de visibilidad
```

y ColumnControl proporciona controles específicos por columna, incluyendo:

```text
search
search lists
ordering
dropdowns
```

La documentación oficial muestra explícitamente controles de búsqueda por columna y procesamiento server-side. citeturn395750search0turn395750search2turn395750search7

### Importante

NO utilizar:

```text
DataTables Editor
```

como requisito para esta misión salvo que el proyecto ya tenga licencia y exista una decisión explícita.

Los formularios continuarán manejándose con la infraestructura existente:

```text
HTMX
Bootstrap
DRF
Service Layer
```

---

# 4. JUSTIFICACIÓN DEL SERVER-SIDE

Para SINTEL ERP utilizar:

```javascript
serverSide: true
```

para tablas de negocio.

DataTables indica que en modo server-side el navegador solicita al backend:

```text
página
ordenamiento
búsqueda global
búsqueda por columna
```

y el servidor realiza el procesamiento. Esto está diseñado para grandes volúmenes de registros. citeturn447076search2turn447076search7

Esto es adecuado para:

```text
Facturas
Ventas
Compras
Clientes
Proveedores
Inventario
Gastos
Empleados
Contabilidad
Bancos
Proyectos
Cotizaciones
```

No descargar miles de registros al navegador para filtrarlos con JavaScript.

---

# 5. BACKEND DE FILTRADO

Estándar:

```text
Django REST Framework
+
django-filter
+
SearchFilter
+
OrderingFilter
```

Django REST Framework permite `SearchFilter` y `OrderingFilter`, mientras que django-filter proporciona `FilterSet` y `DjangoFilterBackend` para filtros estructurados por campo. citeturn572436search0turn447076search0

## REGLA

Cada tabla debe definir explícitamente:

```text
searchable_fields
filterable_fields
orderable_fields
```

NO permitir:

```text
ordenamiento arbitrario de cualquier campo
filtros arbitrarios
acceso a campos sensibles
```

DRF recomienda especificar explícitamente `ordering_fields` para limitar qué campos pueden ordenarse. citeturn572436search0

---

# 6. CONTRATO ÚNICO DE TABLA

Crear una definición estándar por listado.

Ejemplo conceptual:

```javascript
const tableSchema = {
    tableId: 'ventas-table',

    endpoint: '/api/v1/ventas/',

    columns: [
        {
            key: 'cliente_nombre',
            field: 'cliente_nombre',
            title: 'Cliente',
            searchable: true,
            filterable: true,
            orderable: true,
            filterType: 'text'
        },
        {
            key: 'fecha_emision',
            field: 'fecha_emision',
            title: 'Fecha',
            searchable: false,
            filterable: true,
            orderable: true,
            filterType: 'date'
        },
        {
            key: 'estado',
            field: 'estado',
            title: 'Estado',
            searchable: false,
            filterable: true,
            orderable: true,
            filterType: 'select'
        }
    ]
}
```

NO copiar literalmente si existe infraestructura semejante.

Crear el contrato en el lugar arquitectónico correcto.

---

# 7. REGLA CRÍTICA: CADA COLUMNA DEBE PODER FILTRARSE

El requisito del usuario es:

> Permitir filtrar las tablas por cada uno de sus índices.

Interpretar operacionalmente como:

```text
cada columna de datos debe tener
un control de búsqueda/filtro cuando sea semánticamente aplicable.
```

Ejemplos:

### Texto

```text
Cliente
Descripción
Nombre
Dirección
Código
```

→ búsqueda contiene / comienza con / coincide.

### Fecha

```text
Fecha emisión
Fecha creación
Vencimiento
```

→:

```text
desde
hasta
igual
```

### Número

```text
Cantidad
Subtotal
IVA
Total
Saldo
```

→:

```text
=
>
>=
<
<=
entre
```

### Choice

```text
Estado
Tipo
Régimen
Categoría
```

→:

```text
dropdown
multi-select
```

### Booleano

```text
Activo
Pagado
Vigente
```

→:

```text
Sí
No
Todos
```

### Relación

```text
Cliente
Proveedor
Empleado
Proyecto
```

→:

```text
selector/search remoto
```

No hacer una consulta gigante de todos los valores si el catálogo es grande.

---

# 8. COLUMNCONTROL

Configurar ColumnControl para proporcionar controles de columna.

Patrón objetivo:

```text
┌───────────────────────────────────────────────────────┐
│ Cliente  │ Estado │ Fecha │ Total │ Acciones          │
├───────────────────────────────────────────────────────┤
│ [buscar] │ [▼]    │ [date]│ [>=] │                   │
├───────────────────────────────────────────────────────┤
│ ...                                                   │
└───────────────────────────────────────────────────────┘
```

ColumnControl permite colocar controles en encabezado/footer y soporta búsqueda por columna. citeturn395750search0turn395750search2

Con server-side, los filtros deben traducirse al backend; DataTables/ColumnControl documenta los parámetros enviados para búsquedas por columna. citeturn395750search10

---

# 9. REGLA PARA NO ROMPER LOS FILTROS

NO permitir que el frontend invente:

```text
?cliente
?estado
?foo
```

sin contrato backend.

Cada filtro debe tener:

```text
frontend key
backend field
lookup
tipo
seguridad
```

Ejemplo:

```text
cliente
→ cliente__razon_social
→ icontains
```

o el campo/selector real que exista.

El mapping debe vivir en backend o en metadata compartida, no disperso por cada JS.

---

# 10. BÚSQUEDA GLOBAL

Cada tabla tendrá:

```text
Buscar...
```

pero la búsqueda global debe utilizar una lista explícita:

```text
search_fields
```

Ejemplo:

```text
Factura:
número
CUFE
cliente
NIT
```

No buscar indiscriminadamente en todas las columnas.

DRF documenta que `SearchFilter` funciona mediante `search_fields` y puede manejar búsquedas relacionadas. citeturn572436search0

---

# 11. PROBLEMA DE URLS ERRÓNEAS EN TÍTULOS

Auditar todas las cabeceras de tablas.

Buscar:

```text
<a href=
href=
url=
reverse
{% url
sort
ordering
querystring
hx-get
hx-post
data-url
```

especialmente dentro de:

```text
<th>
<thead>
table headers
django-tables2
partials
```

## REGLA

Una cabecera de columna NO debe tener una URL fija incorrecta.

Si la cabecera es ordenable:

```text
click header
→ ordenar
→ conservar ruta actual
→ conservar filtros
→ conservar búsqueda
→ conservar paginación válida
```

Ejemplo:

```text
/ventas/?search=cliente&estado=BORRADOR&ordering=total_neto
```

No:

```text
/ventas/detail/
```

ni:

```text
/api/old-endpoint/
```

ni URLs heredadas.

---

# 12. ROUTE RESOLVER ÚNICO

Crear o reutilizar un resolver centralizado para:

```text
list URL
detail URL
create URL
edit URL
delete/action URL
```

La tabla debe conocer:

```text
row id / uuid
```

y usar un contrato de ruta correcto.

Ejemplo conceptual:

```javascript
routes.detail(uuid)
routes.edit(uuid)
routes.action(uuid, action)
```

NO hardcodear URLs en cada renderer.

---

# 13. ACCIONES POR FILA

Cada tabla debe usar un estándar:

```text
Ver
Editar
Acciones
```

según permisos.

No:

```text
href="/algo/..." 
```

hardcodeado dentro de un renderer diferente en cada módulo.

Las acciones deben recibir:

```text
entity
uuid
permissions
routes
```

---

# 14. UUID

Mantener la regla existente:

```text
NO parseInt() sobre UUIDs
```

Usar:

```text
data-uuid
uuid
```

La documentación de Ventas confirma que el proyecto utiliza UUID lookup y que existe una regla explícita de evitar `parseInt()` sobre UUIDs. fileciteturn4file0L90-L95

---

# 15. PAGINACIÓN

El estándar debe ser server-side.

Contrato:

```text
start
length
```

o convertir el protocolo DataTables a:

```text
page
page_size
```

El adaptador será responsable.

No modificar cada endpoint manualmente con código incompatible.

Debe existir:

```text
DataTables → DRF adapter
```

---

# 16. ADAPTADOR DATATABLES → DRF

Crear una capa compartida.

Responsabilidades:

```text
parse_start_length()
parse_global_search()
parse_column_filters()
parse_ordering()
validate_requested_fields()
build_queryset_parameters()
format_datatables_response()
```

Resultado:

```text
DataTables request
        ↓
TableAdapter
        ↓
DRF / django-filter
        ↓
Selector
        ↓
QuerySet
        ↓
Serializer
        ↓
TableAdapter
        ↓
DataTables response
```

---

# 17. PAGINACIÓN Y RESPUESTA

DataTables server-side espera información de:

```text
draw
recordsTotal
recordsFiltered
data
```

El adapter debe convertir el resultado DRF a ese contrato.

No introducir una respuesta diferente por módulo.

---

# 18. SORTING

Cada columna debe declarar:

```text
orderable
backend_field
```

Ejemplo:

```text
Total
→ total_neto
```

NO permitir que el frontend ordene por:

```text
display string
```

cuando exista un campo numérico real.

Ejemplo incorrecto:

```text
"$ 1.500.000"
```

ordenado como texto.

Debe ordenar:

```text
Decimal
```

en backend.

---

# 19. FORMATEO

Cada tabla debe separar:

```text
raw value
```

de:

```text
display value
```

Ejemplo:

```text
raw:
1539520.83

display:
$ 1.539.520,83
```

La búsqueda/ordenamiento debe usar el dato real.

---

# 20. FECHAS

Separar:

```text
valor API
```

de:

```text
valor visual
```

Ejemplo:

```text
2026-09-18
```

visual:

```text
18/09/2026
```

El backend debe filtrar por fecha real.

---

# 21. FILTROS DE RANGO

Para dinero:

```text
Min
Max
```

Para fechas:

```text
Desde
Hasta
```

Para cantidades:

```text
Min
Max
```

Implementar con django-filter cuando sea apropiado.

---

# 22. ESTADO DE TABLA

Todas las tablas deben soportar:

```text
LOADING
READY
EMPTY
ERROR
FILTERED_EMPTY
```

## Empty

```text
No hay registros.
```

## Filtered empty

```text
No encontramos resultados con los filtros actuales.
[Limpiar filtros]
```

## Error

```text
No fue posible cargar los datos.
[Reintentar]
```

No dejar tablas congeladas o blancas.

---

# 23. BOTÓN "LIMPIAR FILTROS"

Toda tabla con filtros debe tener:

```text
[Limpiar filtros]
```

Debe eliminar:

```text
búsqueda global
filtros por columna
ordenamiento opcional
página
```

y volver a:

```text
page = 1
```

---

# 24. ESTADO PERSISTENTE

Evaluar:

```text
StateRestore
```

solo después de estabilizar filtros.

No convertirlo en requisito de primera fase.

Una vez estable:

```text
recordar filtros
columnas visibles
orden
página
```

para mejorar UX.

---

# 25. EXPORTACIÓN

Evaluar una segunda etapa:

```text
Buttons
```

para:

```text
Excel
CSV
PDF
copiar
```

No implementar exportación antes de estabilizar:

```text
filtros
búsqueda
orden
permisos
```

---

# 26. RESPONSIVE

Usar:

```text
Responsive
```

de DataTables cuando sea necesario.

En móvil:

```text
columnas prioritarias visibles
columnas secundarias ocultables
acciones siempre accesibles
```

No destruir información; ocultar columnas secundarias de forma controlada.

---

# 27. COLUMN VISIBILITY

Evaluar:

```text
colVis
```

para permitir:

```text
Mostrar/Ocultar columnas
```

Solo para tablas con muchas columnas.

No permitir ocultar:

```text
identificador crítico
acciones obligatorias
```

si afecta el flujo.

---

# 28. CHECKBOX / SELECCIÓN

Para tablas que requieran operaciones masivas:

```text
Select
```

Ejemplos:

```text
Facturas
Ventas
Compras
Proveedores
```

La selección debe ser compatible con:

```text
serverSide
paginación
acciones masivas
```

Nunca asumir que seleccionar "todos" significa solo la página actual sin informarlo.

---

# 29. FORMULARIOS — NUEVO ESTÁNDAR VISUAL

Modernizar formularios sin romper Service Layer.

Estructura:

```text
┌────────────────────────────────────────────┐
│ Título                                     │
│ Descripción corta                          │
├────────────────────────────────────────────┤
│ Información principal                      │
│                                            │
│ Campo            Campo                     │
│ Campo            Campo                     │
│                                            │
│ Información adicional                      │
│ Campo            Campo                     │
│                                            │
├────────────────────────────────────────────┤
│ [Cancelar]                    [Guardar]    │
└────────────────────────────────────────────┘
```

Usar patrones Bootstrap 5 existentes.

Bootstrap documenta controles consistentes, labels y tipos HTML correctos para los campos. citeturn986136search1turn986136search2

---

# 30. VALIDACIÓN DE FORMULARIOS

Mantener:

```text
cliente
+
backend
```

La validación final siempre debe estar en servidor.

Bootstrap soporta estados:

```text
.is-invalid
.is-valid
.invalid-feedback
.valid-feedback
```

y recomienda asociar correctamente los mensajes a los campos. citeturn986136search0

---

# 31. MENSAJES DE ERROR

Cada error debe aparecer junto al campo cuando sea un error de validación:

```text
NIT inválido
Fecha requerida
Valor no válido
```

Errores globales:

```text
No fue posible guardar.
```

Nunca:

```text
alert("error")
```

genérico para todo.

---

# 32. FORMULARIOS HTMX

Mantener HTMX para:

```text
offcanvas
carga parcial
acciones
feedback
```

La documentación oficial de HTMX confirma el modelo `hx-get`, `hx-post`, `hx-put`, `hx-patch`, `hx-delete` y eventos de error `htmx:responseError`. citeturn447076search1

No reemplazar HTMX por otra arquitectura solo para modernizar visualmente.

---

# 33. DISEÑO VISUAL UNIFICADO

Crear un sistema visual común:

```text
table-wrapper
table-toolbar
table-search
table-filter
table-status
table-empty
table-error
table-actions
form-section
form-grid
form-actions
```

No copiar CSS de una app a otra.

Crear tokens/componentes compartidos.

---

# 34. TABLA ESTÁNDAR OBJETIVO

Cada listado debe parecerse funcionalmente a:

```text
┌──────────────────────────────────────────────────────────────┐
│ Título                               [+ Nuevo] [Actualizar] │
│ Descripción                                                 │
├──────────────────────────────────────────────────────────────┤
│ Buscar...  [Filtros]                         [Limpiar]      │
├──────────────────────────────────────────────────────────────┤
│ Cliente      Estado       Fecha       Total        Acciones │
│ [buscar]     [▼]         [desde/hasta] [min/max]            │
├──────────────────────────────────────────────────────────────┤
│ Empresa A    Activo       18/09/26     $...        [...]    │
│ Empresa B    Pendiente    17/09/26     $...        [...]    │
├──────────────────────────────────────────────────────────────┤
│ Mostrando 1–25 de 250                     ‹ 1 2 3 ... ›     │
└──────────────────────────────────────────────────────────────┘
```

---

# FASE 0 — DISCOVER

## Auditar repo completo

Buscar:

```text
<th
<thead
<table
django-tables2
Tabulator
DataTable
DataTables
search_fields
filter_backends
OrderingFilter
SearchFilter
DjangoFilterBackend
filterset_fields
FilterSet
href=
hx-get=
hx-post=
{% url
reverse(
data-url
```

Generar inventario:

```text
app
template
JS
API
selector
serializer
backend filter
table library
estado
```

### Gate

```text
PASS = 100% del árbol analizado
FAIL = apps omitidas
BLOCKED = fuente de código no disponible
```

---

# FASE 1 — BASELINE SISTÉMICO

Para cada app clasificar:

```text
TABLA ACTIVA
TABLA ESTÁTICA
TABLA SERVER-SIDE
TABLA CLIENT-SIDE
TABLA HTMX
TABLA django-tables2
TABLA Tabulator
TABLA DataTables
```

Separar:

```text
actual
histórico
huérfano
```

No migrar un componente histórico que ya no está en uso.

---

# FASE 2 — AUDITORÍA DE FILTROS

Por cada tabla:

```text
búsqueda global
filtro por columna
ordenamiento
paginación
filtros de estado
filtros de fecha
filtros numéricos
filtros relacionales
```

Probar cada uno.

Crear matriz:

| App | Tabla | Columna | Search | Filter | Order | Backend | Estado |
|---|---|---|---|---|---|---|---|

---

# FASE 3 — AUDITORÍA DE URLs

Repo-wide buscar:

```text
href=
{% url
reverse(
data-url
hx-get
hx-post
location.href
window.location
```

Validar:

```text
list
detail
create
edit
delete
action
ordering
pagination
```

Eliminar:

```text
URLs muertas
URLs de endpoints históricos
URLs absolutas incorrectas
rutas duplicadas
rutas hardcodeadas
```

---

# FASE 4 — DECISIÓN Y SPIKE

Construir una tabla piloto con:

```text
DataTables 3.0.4
ColumnControl 2.0.2
Bootstrap 5
DRF
django-filter
```

Elegir una app representativa:

```text
Ventas
```

porque la documentación ya evidencia:

```text
server-side
SearchFilter
OrderingFilter
HTMX
```

Probar:

```text
búsqueda global
filtro por columna
fecha
número
estado
ordenamiento
paginación
URLs
acciones
responsive
```

### Gate

No migrar las demás apps hasta demostrar:

```text
global search = PASS
column filters = PASS
ordering = PASS
pagination = PASS
row actions = PASS
tenant = PASS
permissions = PASS
```

---

# FASE 5 — TABLE CORE COMPARTIDO

Crear una infraestructura compartida:

```text
TableManager
TableSchema
TableAdapter
TableFilters
TableUrlResolver
TableState
```

Los nombres definitivos deben seguir la arquitectura real.

Responsabilidades:

```text
inicializar tabla
registrar columnas
mapear filtros
mapear ordering
mapear paginación
manejar errores
refrescar
limpiar filtros
resolver URLs
```

---

# FASE 6 — CONTRATO BACKEND

Para cada endpoint de listado implementar:

```text
search
column filters
ordering
pagination
```

usando:

```text
DRF
django-filter
Selector
Service Layer
```

NO mover la lógica de negocio al frontend.

---

# FASE 7 — PILOTO COMPLETO VENTAS

Migrar:

```text
list ventas
```

a la infraestructura nueva.

Conservar:

```text
Ver
Editar
Anular
Vincular Factura
Sincronizar Facturas
```

No romper la integración Facturas ↔ Ventas.

---

# FASE 8 — MIGRACIÓN APP POR APP

Orden sugerido:

```text
Ventas
↓
Facturas
↓
Clientes
↓
Proveedores
↓
Compras
↓
Cotizaciones
↓
Inventario
↓
Gastos
↓
Empleados
↓
Proyectos
↓
Bancos
↓
Contabilidad
↓
resto de apps descubiertas
```

El orden final debe ajustarse al inventario real.

Cada app debe terminar con:

```text
PASS
```

antes de comenzar la siguiente.

---

# FASE 9 — FORMULARIOS

Por cada app:

```text
Nuevo
Editar
Detalle
Gestión
```

unificar:

```text
layout
labels
spacing
inputs
selects
feedback
botones
secciones
loading
errores
```

No cambiar reglas de negocio.

---

# FASE 10 — PRUEBAS POR TABLA

Cada tabla debe probar:

```text
1. carga inicial
2. búsqueda global
3. filtro columna texto
4. filtro columna fecha
5. filtro columna numérica
6. filtro choice
7. filtro relacional
8. orden ascendente
9. orden descendente
10. paginación
11. limpiar filtros
12. estado vacío
13. error
14. acciones
15. refresh
```

No todos los tipos aplican a todas las tablas; registrar:

```text
NOT_APPLICABLE
```

cuando corresponda.

---

# FASE 11 — TEST DE SEGURIDAD

Por cada endpoint/listado:

```text
Tenant A
Tenant B
```

Validar:

```text
no fuga de registros
no fuga mediante search
no fuga mediante filters
no fuga mediante ordering
no fuga mediante detail URL
```

Probar manipulación de:

```text
uuid
filter field
ordering field
search
page
```

---

# FASE 12 — TEST DE RENDIMIENTO

Medir:

```text
50
500
5.000
50.000+
```

según datos disponibles.

Comprobar:

```text
consulta
count
recordsFiltered
paginación
render
```

Buscar:

```text
N+1
queries duplicadas
SELECT *
joins innecesarios
```

Optimizar con:

```text
select_related
prefetch_related
only
indexes
```

respetando los Selectors existentes.

---

# FASE 13 — VALIDACIÓN VISUAL

Revisar cada app:

```text
desktop
tablet
móvil
```

Validar:

```text
overflow
anchos
sticky headers
acciones
botones
filtros
formularios
offcanvas
modal
```

---

# FASE 14 — DOCUMENTATION DRIFT

Actualizar documentación eliminando contradicciones.

Especialmente cualquier referencia que indique:

```text
Tabulator
```

cuando el código ya use otro sistema.

No eliminar historia útil; marcarla como:

```text
HISTÓRICO
```

y separar:

```text
ARQUITECTURA ACTUAL
```

de:

```text
ARQUITECTURA HISTÓRICA
```

---

# FASE 15 — RELEASE GATE GLOBAL

Crear:

```text
docs/ux/TABLES_FORMS_RELEASE_GATE.md
```

Debe incluir:

```text
apps auditadas
tablas auditadas
formularios auditados
URLs auditadas
filtros auditados
búsquedas auditadas
tests
errores
deuda técnica
```

---

# 35. ARCHIVO DE SUPERVISIÓN

Crear:

```text
docs/remediation/TABLES_FORMS_MIGRATION_STATUS.md
```

Formato:

```markdown
# Tables & Forms Migration Status

Fecha:
Versión:

## Estado global

STATUS: IN_PROGRESS

| Fase | Estado | Evidencia |
|---|---|---|
| 0 Discover | ... | ... |
| 1 Baseline | ... | ... |
| 2 Filtros | ... | ... |
| 3 URLs | ... | ... |
| 4 Spike | ... | ... |
| 5 Core | ... | ... |
| 6 Backend | ... | ... |
| 7 Ventas | ... | ... |
| 8 Facturas | ... | ... |
| 9 Clientes | ... | ... |
| 10 Proveedores | ... | ... |
| 11 Compras | ... | ... |
| 12 Cotizaciones | ... | ... |
| 13 Inventario | ... | ... |
| 14 Gastos | ... | ... |
| 15 Empleados | ... | ... |
| 16 Proyectos | ... | ... |
| 17 Bancos | ... | ... |
| 18 Contabilidad | ... | ... |
| 19 Tests | ... | ... |
| 20 Seguridad | ... | ... |
| 21 Performance | ... | ... |
| 22 Visual | ... | ... |
| 23 Docs | ... | ... |
```

Estados permitidos:

```text
PENDING
IN_PROGRESS
PASS
FAIL
BLOCKED
NOT_APPLICABLE
```

---

# 36. REGLA DE GATE

Cada fase debe ejecutar:

```text
IMPLEMENT
→ TEST
→ INSPECT
→ RECORD
→ FIX
→ RETEST
→ PASS
```

No avanzar con:

```text
FAIL
```

No declarar:

```text
PASS
```

sin evidencia.

---

# 37. CHECKLIST GLOBAL DE ACEPTACIÓN

```text
[ ] Todas las tablas fueron inventariadas.
[ ] Todas las tablas activas tienen backend de filtros.
[ ] Todas las tablas tienen búsqueda global cuando aplica.
[ ] Todas las columnas filtrables tienen filtro.
[ ] Fechas tienen filtros adecuados.
[ ] Números tienen filtros adecuados.
[ ] Choices tienen filtros adecuados.
[ ] Relaciones tienen filtros adecuados.
[ ] Ordenamiento funciona.
[ ] Paginación funciona.
[ ] "Limpiar filtros" funciona.
[ ] URLs de títulos/cabeceras son correctas.
[ ] URLs de acciones son correctas.
[ ] No existen rutas hardcodeadas obsoletas.
[ ] Tenant isolation funciona.
[ ] Permisos funcionan.
[ ] Loading funciona.
[ ] Empty state funciona.
[ ] Error state funciona.
[ ] Tablas son responsive.
[ ] Formularios tienen presentación uniforme.
[ ] Formularios muestran errores correctamente.
[ ] Backend sigue siendo fuente de verdad.
[ ] Service Layer no fue violado.
[ ] Selectors no fueron bypassed.
[ ] No existen N+1 nuevos.
[ ] No se introducen duplicaciones.
[ ] No se rompe HTMX.
[ ] No se rompe Facturas.
[ ] No se rompe Ventas.
[ ] No se rompe Compras.
[ ] No se rompe Inventario.
[ ] No se rompe Contabilidad.
[ ] Tests pasan.
[ ] Documentación está actualizada.
```

---

# 38. REGLAS ABSOLUTAS

NO:

```text
migrar todas las apps simultáneamente
crear una tabla diferente para cada módulo
duplicar código de filtros
duplicar paginadores
duplicar resolvers de URL
filtrar solamente en JavaScript
buscar solamente en datos cargados en DOM
permitir ordering libre sobre campos no autorizados
hacer filtros sin backend
crear URLs hardcodeadas por componente
usar UUID como entero
hacer parseInt(UUID)
eliminar DSV
bypassear Selectors
poner lógica de negocio en JS
poner lógica fiscal en JS
romper HTMX
reintroducir arquitectura histórica
mantener dos librerías de tablas activas sin justificación
declarar PASS sin evidencia
```

---

# 39. REGLA SOBRE TABULATOR

La documentación adjunta contiene referencias históricas a Tabulator.

No asumir que Tabulator está actualmente activo en todas las apps.

Primero comprobar uso real:

```text
imports
instanciación
HTML
bundle
assets
eventos
```

Si una app realmente utiliza Tabulator:

```text
documentar
```

y migrarla progresivamente.

Si no existe uso real:

```text
no reintroducirlo
```

---

# 40. REGLA SOBRE DJANGO-TABLES2

No eliminar automáticamente:

```text
django-tables2
```

Primero localizar consumidores reales.

Una vez migradas todas las tablas interactivas:

```text
evaluar si queda algún uso legítimo
```

Puede mantenerse para tablas simples/estáticas si existe una justificación técnica, pero no debe coexistir como segundo framework interactivo sin motivo.

---

# 41. OPCIÓN FINAL RECOMENDADA

Para el sistema actual:

```text
                     SINTEL ERP
                          │
                 ┌────────┴────────┐
                 │ TABLE CORE       │
                 │ COMPARTIDO       │
                 └────────┬────────┘
                          │
                 DataTables 3.x
                          │
                 ColumnControl
                          │
                     Bootstrap 5
                          │
                    AJAX/HTTP
                          │
                   DRF Adapter
                          │
                  django-filter
                          │
                    Selectors
                          │
                   Service Layer
                          │
                       ORM
```

Formularios:

```text
Bootstrap 5
+
HTMX
+
DRF/backend validation
+
Service Layer
```

Esta opción aprovecha la arquitectura actual en lugar de reemplazar todo el stack. DataTables ofrece actualmente procesamiento server-side y controles de columna, Bootstrap 5 como integración oficial, mientras DRF y django-filter ya proporcionan piezas naturales para el filtrado y ordenamiento en backend. citeturn447076search2turn395750search0turn447076search4turn447076search0

---

# 42. ORDEN FINAL DE EJECUCIÓN

```text
DISCOVER
      ↓
BASELINE
      ↓
INVENTORY
      ↓
AUDIT URLS
      ↓
AUDIT SEARCH/FILTERS
      ↓
SPIKE DATATABLES
      ↓
PASS
      ↓
TABLE CORE
      ↓
DRF FILTER CONTRACT
      ↓
VENTAS PILOT
      ↓
PASS
      ↓
FACTURAS
      ↓
CLIENTES
      ↓
PROVEEDORES
      ↓
COMPRAS
      ↓
COTIZACIONES
      ↓
INVENTARIO
      ↓
GASTOS
      ↓
EMPLEADOS
      ↓
PROYECTOS
      ↓
BANCOS
      ↓
CONTABILIDAD
      ↓
RESTO DE APPS
      ↓
FORMULARIOS
      ↓
SEGURIDAD
      ↓
PERFORMANCE
      ↓
VISUAL QA
      ↓
REGRESSION
      ↓
DOCUMENTATION
      ↓
RELEASE GATE
```

# 43. RESULTADO ESPERADO

Al finalizar, cualquier usuario del SINTEL ERP debe encontrar el mismo comportamiento conceptual en los listados:

```text
Buscar
Filtrar por columna
Ordenar
Paginar
Limpiar filtros
Ver estado
Ver
Editar
Acciones
```

sin importar si está en:

```text
Ventas
Facturas
Compras
Clientes
Proveedores
Inventario
Gastos
Empleados
Proyectos
Bancos
Contabilidad
Cotizaciones
```

El objetivo no es solamente "cambiar el aspecto".

El objetivo es construir un **contrato único de presentación y consulta de datos**, de manera que:

```text
TABLA
=
DATOS
+
FILTROS
+
BÚSQUEDA
+
ORDEN
+
PAGINACIÓN
+
URLS
+
PERMISOS
+
ESTADOS
+
ACCIONES
```

con una implementación consistente y verificable.

## FIN DEL PROMPT
