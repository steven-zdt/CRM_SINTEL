# PLAN DE ACCIÓN
## NUEVA REQUISICIÓN DE COMPRA
### Información General + Contexto + Items Solicitados

## 1. OBJETIVO

Rediseñar y ajustar únicamente el formulario:

**Compras → Requisiciones → Nueva Requisición de Compra**

para que el usuario construya la requisición en tres sub-secciones claramente separadas:

1. **Información General**
2. **Contexto**
3. **Items Solicitados**

La nueva experiencia debe conservar la arquitectura existente, reutilizar el Service Layer y las relaciones ya implementadas, y evitar duplicar lógica entre frontend, serializers y servicios.

No se debe modificar en esta fase:

- flujo de aprobación;
- Centro de Aprobaciones;
- generación de Orden de Compra;
- recepción de compras;
- facturas;
- contabilidad;
- lógica general de Cotizaciones;
- lógica general de Proyectos.

---

# 2. ESTRUCTURA FUNCIONAL DEL FORMULARIO

La pantalla debe quedar conceptualmente así:

```text
Nueva Requisición de Compra

┌───────────────────────────────────────────────┐
│ INFORMACIÓN GENERAL                            │
│                                               │
│ Plantilla de Numeración *                     │
│ Cliente *                                     │
│ Fecha de solicitud *                          │
│ Prioridad *                                   │
│ Número de requisición                         │
│                                               │
└───────────────────────────────────────────────┘

┌───────────────────────────────────────────────┐
│ CONTEXTO                                      │
│                                               │
│ Cotizaciones                                  │
│ [ + Vincular cotización ]                     │
│                                               │
│ Tabla de cotizaciones vinculadas              │
│                                               │
│ Proyecto                                      │
│ [ + Vincular proyecto ]                       │
│                                               │
│ Tabla de proyecto vinculado                   │
│                                               │
└───────────────────────────────────────────────┘

┌───────────────────────────────────────────────┐
│ ITEMS SOLICITADOS                             │
│                                               │
│ Items provenientes de cotizaciones            │
│ + posibilidad de edición manual               │
│                                               │
│ Tabla de items                                │
│                                               │
└───────────────────────────────────────────────┘
```

---

# 3. INFORMACIÓN GENERAL

Esta sección debe contener **únicamente** los campos solicitados para esta fase.

## 3.1 Plantilla de Numeración *

Campo obligatorio.

Debe utilizar exactamente el mecanismo existente de:

**Compras → Nueva Plantilla de Numeración**

La plantilla debe corresponder al tipo documental:

```text
REQUISICION
```

No crear un segundo sistema de consecutivos.

La misma infraestructura utilizada actualmente para Orden de Compra debe ser reutilizada/generalizada para Requisiciones.

### Comportamiento

El usuario selecciona:

```text
Plantilla de Numeración *
```

El sistema debe mostrar únicamente plantillas:

- pertenecientes al tenant actual;
- activas;
- compatibles con el tipo documental REQUISICION;
- válidas según la configuración actual del módulo.

No debe permitirse seleccionar una plantilla de Orden de Compra como plantilla de Requisición.

---

# 4. NÚMERO DE REQUISICIÓN

## 4.1 Campo solo lectura

El formulario debe mostrar:

```text
Número de requisición
REQ-000001
```

pero el usuario **nunca debe poder escribirlo ni modificarlo**.

El número debe provenir exclusivamente de:

```text
Plantilla de Numeración
        ↓
Servicio de numeración existente de Compras
        ↓
Nuevo número único de Requisición
```

## 4.2 Regla fundamental

Nunca permitir:

```text
Requisición 001
Requisición 001
```

aunque:

- se cancele;
- se rechace;
- se elimine un borrador;
- otro usuario cree simultáneamente otra requisición.

El número asignado no debe volver a utilizarse.

## 4.3 Momento de asignación

La asignación debe ser realizada por backend y de manera transaccional.

No consumir consecutivos únicamente porque el usuario abrió el formulario o cambió la plantilla.

El frontend solamente debe presentar:

```text
Número asignado automáticamente
```

hasta que el backend haya efectuado la creación real.

Una vez creada:

```text
Número de requisición: REQ-000123
```

queda persistido y es de solo lectura.

## 4.4 Concurrencia

Reutilizar la lógica de concurrencia actualmente utilizada por Compras:

```text
transaction.atomic()
+
select_for_update()
+
incremento seguro del consecutivo
```

El número debe quedar protegido también por una restricción de unicidad a nivel de base de datos para el alcance definido por la arquitectura actual.

No implementar numeración directamente desde JavaScript.

---

# 5. CLIENTE *

Debe ser obligatorio.

Debe utilizarse el **Cliente SSoT existente** de:

```text
apps/tenant/clientes/
```

No crear datos duplicados del cliente dentro de Requisiciones.

### UI

Utilizar selector/buscador:

```text
Buscar cliente...
```

La búsqueda debe permitir localizar clientes utilizando los mismos criterios y componentes ya utilizados en el resto del ERP.

Una vez seleccionado:

```text
Cliente:
Sintel Technology S.A.S.
NIT: XXXXXXXX-X
```

Debe quedar asociado mediante su identificador real.

---

# 6. FECHA DE SOLICITUD *

Campo obligatorio.

Debe aparecer como:

```text
Fecha de solicitud *
[ 28/09/2026 ]
```

La fecha inicial podrá utilizar la fecha actual del sistema, pero debe permanecer editable mientras la requisición se encuentre en BORRADOR.

El valor definitivo debe ser enviado al backend y validado allí.

No confiar exclusivamente en la fecha enviada por JavaScript.

---

# 7. PRIORIDAD *

Campo obligatorio.

Debe reutilizar las opciones de prioridad que ya maneja Requisiciones.

Ejemplo conceptual:

```text
Prioridad *
[ Normal ▼ ]
```

No introducir nuevos valores si ya existe un catálogo/enum en la implementación actual.

La UI debe mostrar claramente:

- campo obligatorio;
- valor actual;
- mensaje de validación si queda vacío.

---

# 8. VALIDACIÓN DE INFORMACIÓN GENERAL

Antes de permitir la creación de una requisición válida:

```text
Plantilla        → obligatoria
Cliente          → obligatorio
Fecha solicitud  → obligatoria
Prioridad        → obligatoria
Número           → generado por backend
```

Nunca aceptar desde frontend:

```text
numero_documento = "REQ-000001"
```

como valor definido manualmente por el usuario.

El backend debe ignorar cualquier intento de modificación manual del número.

---

# 9. CONTEXTO

La sección **Contexto** debe simplificarse.

No agregar campos adicionales por ahora.

Debe contener únicamente:

```text
Cotizaciones
Proyecto
```

El objetivo es indicar de dónde proviene la necesidad de compra y, opcionalmente, a qué proyecto está asociada.

---

# 10. VINCULAR COTIZACIONES

## 10.1 Relación funcional

Una Requisición puede tener:

```text
0..N Cotizaciones
```

Esto es coherente con la relación `RequisicionCotizacion` ya existente.

Ejemplo:

```text
REQ-000154

├── Cotización COT-00120
├── Cotización COT-00125
└── Cotización COT-00131
```

---

# 11. BOTÓN "VINCULAR COTIZACIÓN"

En Contexto:

```text
Cotizaciones

[ + Vincular cotización ]
```

Al hacer clic debe abrir un modal/offcanvas de búsqueda.

Ejemplo:

```text
┌───────────────────────────────────────────────┐
│ Vincular cotización                           │
│                                               │
│ Buscar: [________________________] 🔍         │
│                                               │
│ Cotización  Cliente             Total         │
│ COT-00120   Cliente ABC         $2.500.000   │
│ COT-00125   Cliente ABC         $3.200.000   │
│                                               │
│                         [Seleccionar]          │
└───────────────────────────────────────────────┘
```

---

# 12. REGLA: COTIZACIONES SIN REQUISICIÓN

Cuando el usuario pulse:

```text
Vincular cotización
```

la búsqueda debe mostrar únicamente cotizaciones que:

```text
NO tengan una Requisición asociada
```

La condición debe aplicarse en backend.

No utilizar solamente:

```javascript
cotizacion.requisicion == null
```

como mecanismo de seguridad.

El backend debe volver a verificar la disponibilidad al momento de vincular.

Esto evita problemas de concurrencia cuando dos usuarios intenten seleccionar la misma cotización.

---

# 13. SELECCIONAR COTIZACIÓN

Al seleccionar una cotización:

1. Validar tenant.
2. Validar existencia.
3. Validar que no esté ya asociada.
4. Validar que la cotización pueda vincularse.
5. Validar coherencia con el Cliente de la Requisición.
6. Registrar la relación `RequisicionCotizacion`.
7. Actualizar el formulario.
8. Sincronizar sus Items.

Si la cotización ya fue vinculada por otro usuario entre la búsqueda y la selección:

```text
No disponible
La cotización ya está asociada a otra requisición.
```

No mostrar error técnico.

---

# 14. COHERENCIA CLIENTE ↔ COTIZACIÓN

Como la Requisición ahora exige Cliente, debe existir una validación de coherencia.

Ejemplo:

```text
Requisición:
Cliente = Cliente A

Cotización seleccionada:
Cliente = Cliente B
```

Debe bloquearse.

Mensaje:

```text
La cotización seleccionada pertenece a un cliente diferente
al cliente de la requisición.
```

No modificar automáticamente el cliente de la Requisición al seleccionar una cotización.

El Cliente seleccionado en Información General es la fuente de verdad.

---

# 15. TABLA DE COTIZACIONES VINCULADAS

Cuando el usuario agregue una cotización, debe aparecer inmediatamente en el formulario.

Ejemplo:

| Cotización | Cliente | Fecha | Total | Acciones |
|---|---|---|---:|---|
| COT-00120 | Cliente ABC | 28/09/2026 | $2.500.000 | 🗑 |
| COT-00125 | Cliente ABC | 28/09/2026 | $3.200.000 | 🗑 |

La tabla debe tener una columna:

```text
Acciones
```

con al menos:

```text
Eliminar vínculo
```

---

# 16. QUITAR COTIZACIÓN

Al pulsar eliminar:

```text
🗑
```

debe eliminarse únicamente:

```text
RequisicionCotizacion
```

No borrar:

- Cotización;
- CotizacionItem;
- Cliente;
- Proyecto;
- datos comerciales.

Después de quitarla, la cotización debe volver a aparecer disponible para vincular cuando corresponda.

---

# 17. VINCULAR PROYECTO

En Contexto:

```text
Proyecto

[ + Vincular proyecto ]
```

Debe utilizarse el `Proyecto` existente.

La arquitectura actual ya define la relación:

```text
Requisicion.proyecto
```

como relación directa opcional `0..1`.

Por tanto:

```text
Una Requisición
        ↓
0 o 1 Proyecto
```

No crear en esta fase una nueva tabla N:N para proyectos.

---

# 18. BUSCADOR DE PROYECTO

Al pulsar:

```text
+ Vincular proyecto
```

abrir:

```text
┌───────────────────────────────────────────────┐
│ Vincular proyecto                             │
│                                               │
│ Buscar: [________________________] 🔍         │
│                                               │
│ Proyecto       Nombre             Estado      │
│ PRO-001        Proyecto Alpha     Activo      │
│ PRO-002        Proyecto Beta      Activo      │
│                                               │
│                         [Seleccionar]          │
└───────────────────────────────────────────────┘
```

El sistema agrega el seleccionado al formulario.

---

# 19. TABLA DE PROYECTO

Mostrar:

| Proyecto | Nombre | Estado | Acciones |
|---|---|---|---|
| PRO-001 | Proyecto Alpha | Activo | 🗑 |

Como la relación actual es `0..1`, no se debe permitir agregar un segundo proyecto simultáneamente.

Si ya existe uno:

```text
Ya existe un proyecto asociado.
```

El usuario debe quitarlo primero.

---

# 20. ELIMINAR PROYECTO

La acción:

```text
🗑
```

solamente debe quitar la asociación.

No eliminar el proyecto.

Después:

```text
Proyecto
[ + Vincular proyecto ]
```

queda nuevamente disponible.

---

# 21. ITEMS SOLICITADOS

Esta sección es fundamental.

Debe quedar separada visualmente de Información General y Contexto.

Su objetivo es construir el detalle real que la Requisición terminará solicitando.

La Requisición ya dispone de `RequisicionCompraItem`.

---

# 22. ORIGEN DE LOS ITEMS

Existen dos formas de alimentar Items Solicitados:

### A. Desde Cotizaciones

Cuando se vincula una cotización:

```text
Cotizacion
      ↓
CotizacionItem
      ↓
RequisicionCompraItem
```

Los datos deben aparecer automáticamente.

### B. Manual

El usuario debe poder agregar y editar items manualmente.

La edición manual debe estar disponible siempre.

---

# 23. SINCRONIZACIÓN INICIAL DE COTIZACIÓN

Al agregar:

```text
COT-00120
```

sus items deben cargarse automáticamente en:

```text
Items Solicitados
```

Por ejemplo:

| Producto/Servicio | Descripción | Cantidad | Unidad | Valor | IVA | Total |
|---|---|---:|---|---:|---:|---:|
| Cámara IP | Cámara 4MP | 10 | UND | $300.000 | 19% | $3.570.000 |
| NVR | NVR 32CH | 1 | UND | $2.000.000 | 19% | $2.380.000 |

El usuario no debe tener que copiar manualmente cada línea.

---

# 24. MÚLTIPLES COTIZACIONES

Cuando existan varias cotizaciones:

```text
Cotización A
Cotización B
Cotización C
```

los Items Solicitados deben construirse a partir de las líneas de esas cotizaciones.

La implementación debe mantener trazabilidad del origen cuando esa información esté disponible.

Ejemplo:

| Item | Descripción | Cantidad | Origen |
|---|---|---:|---|
| Cámara IP | Cámara 4MP | 10 | COT-00120 |
| NVR | NVR 32CH | 1 | COT-00120 |
| UPS | UPS 3KVA | 2 | COT-00125 |

Esto permitirá posteriormente saber de qué cotización salió inicialmente cada línea.

---

# 25. EDICIÓN MANUAL SIEMPRE DISPONIBLE

Después de sincronizar los datos de una cotización, el usuario debe poder modificar:

- descripción;
- cantidad;
- unidad;
- valor estimado;
- IVA;
- valores calculados según las reglas existentes.

La cotización funciona como fuente inicial de datos, pero la Requisición debe conservar su propio snapshot de Items.

No convertir `CotizacionItem` en el SSoT de los Items de la Requisición.

La Requisición debe poder continuar existiendo aunque posteriormente cambie la cotización.

---

# 26. EVITAR SOBRESCRITURA SILENCIOSA

La sincronización inicial puede ser automática.

Pero una vez que el usuario modifica manualmente un Item:

```text
Cotización → Item
             ↓
        sincronización inicial
             ↓
      usuario modifica Item
```

no se debe sobrescribir silenciosamente esa modificación posteriormente.

Si en el futuro se implementa:

```text
Actualizar desde cotización
```

debe ser una acción explícita del usuario.

Para esta fase no es necesario crear todavía un sistema avanzado de comparación de diferencias.

---

# 27. AGREGAR ITEMS MANUALMENTE

Debe existir un botón:

```text
[ + Agregar item ]
```

para permitir crear una línea incluso cuando no existe ninguna cotización.

Ejemplo:

```text
Item 1
Producto/Servicio: [ Buscar ]
Descripción:        [................]
Cantidad:           [ 1 ]
Unidad:             [ UND ]
Valor estimado:     [ ............. ]
IVA:                [ ............. ]
Total:              $..............
```

---

# 28. ELIMINAR ITEMS

Cada fila debe disponer de:

```text
Acciones → Eliminar
```

La eliminación solamente afecta:

```text
RequisicionCompraItem
```

No eliminar:

- Producto;
- Servicio;
- Cotización;
- CotizacionItem.

---

# 29. REGLA DE ITEMS OBLIGATORIOS

Una Requisición válida debe contener:

```text
>= 1 Item
```

No permitir crear una requisición definitiva sin Items.

Mensaje:

```text
Debe existir al menos un item solicitado.
```

Esta validación debe existir tanto en:

```text
Frontend
```

como en:

```text
Backend
```

El frontend mejora UX.

El backend mantiene la regla real.

---

# 30. FLUJO COMPLETO DE USUARIO

El flujo esperado debe ser:

```text
Nueva Requisición
        │
        ▼
Información General
        │
        ├── Selecciona Plantilla
        ├── Selecciona Cliente
        ├── Selecciona Fecha
        ├── Selecciona Prioridad
        └── Número generado por backend
        │
        ▼
Contexto
        │
        ├── Vincular cotización
        │       ├── Buscar
        │       ├── Seleccionar
        │       ├── Agregar tabla
        │       └── Sincronizar Items
        │
        └── Vincular proyecto
                ├── Buscar
                ├── Seleccionar
                └── Agregar tabla
        │
        ▼
Items Solicitados
        │
        ├── Items sincronizados
        ├── Editar
        ├── Agregar
        └── Eliminar
        │
        ▼
Guardar Requisición
```

---

# 31. REGLAS DE SERVICIO

Toda la lógica crítica debe permanecer en:

```text
ViewSet
   ↓
ServiceMixin
   ↓
RequisicionBusinessService
   ↓
CRUD / Selectors
```

No introducir reglas de negocio en:

- JavaScript;
- template HTML;
- signals;
- serializers como única fuente de verdad.

Debe mantenerse el patrón Service Layer existente del módulo.

---

# 32. OPERACIONES QUE DEBE CENTRALIZAR EL BUSINESS SERVICE

Como mínimo:

```text
crear_requisicion()

asignar_numero_requisicion()

validar_plantilla_numeracion()

validar_cliente()

vincular_cotizacion()

desvincular_cotizacion()

vincular_proyecto()

desvincular_proyecto()

sincronizar_items_desde_cotizacion()

agregar_item_manual()

actualizar_item()

eliminar_item()

validar_requisicion_para_guardar()
```

No crear múltiples implementaciones de la misma regla.

---

# 33. VALIDACIONES DE SEGURIDAD

Todas las relaciones deben validarse contra el tenant actual.

Especialmente:

```text
Plantilla
Cliente
Cotización
Proyecto
Producto/Servicio
Requisición
```

Nunca confiar únicamente en UUID enviados por frontend.

Debe mantenerse el patrón de DSV utilizado por el proyecto.

---

# 34. API / ENDPOINTS

Reutilizar la raíz existente:

```text
/api/v1/compras/requisiciones/
```

Agregar o adaptar únicamente los recursos necesarios para:

```text
Buscar cotizaciones disponibles
Vincular cotización
Desvincular cotización

Buscar proyectos
Vincular proyecto
Desvincular proyecto

Obtener Items
Sincronizar Items
Crear/editar/eliminar Items
```

No crear endpoints duplicados para acciones que ya existan.

---

# 35. UX DEL FORMULARIO

La pantalla debe utilizar el mismo lenguaje visual de Compras.

### Información General

Campos organizados en grid:

```text
Plantilla              Cliente
Fecha solicitud        Prioridad
Número requisición
```

El número debe tener apariencia de:

```text
campo informativo / readonly
```

y no de entrada editable.

### Contexto

Dos bloques:

```text
Cotizaciones
[+ Vincular cotización]

Proyecto
[+ Vincular proyecto]
```

Cada vínculo debe visualizarse inmediatamente en una tabla.

### Items Solicitados

Tabla amplia y editable.

---

# 36. ESTADOS DE LA UI

Mientras se busca:

```text
Buscando cotizaciones...
```

Mientras se vincula:

```text
Vinculando...
```

Mientras se sincronizan Items:

```text
Sincronizando Items...
```

Al eliminar:

```text
Eliminando vínculo...
```

Nunca permitir dobles clics que produzcan solicitudes duplicadas.

---

# 37. MENSAJES DE NEGOCIO

Los mensajes deben ser funcionales, no errores técnicos.

Ejemplo incorrecto:

```text
IntegrityError: duplicate key...
```

Correcto:

```text
La cotización seleccionada ya está asociada a otra requisición.
```

Incorrecto:

```text
ValidationError null constraint
```

Correcto:

```text
Debe seleccionar un cliente.
```

---

# 38. CRITERIOS DE ACEPTACIÓN

### Información General

- Plantilla es obligatoria.
- Cliente es obligatorio.
- Fecha de solicitud es obligatoria.
- Prioridad es obligatoria.
- Número es generado automáticamente.
- Número no es editable.
- El número utiliza la plantilla seleccionada.
- El usuario nunca introduce manualmente el número.
- No existen números duplicados.

### Cotizaciones

- Se pueden vincular múltiples cotizaciones.
- Solo se muestran cotizaciones disponibles según la regla de asociación.
- Una cotización no puede vincularse dos veces.
- Una cotización no puede quedar asociada simultáneamente a dos requisiciones.
- El cliente de la cotización debe ser coherente con la requisición.
- Las cotizaciones aparecen en tabla.
- Existe acción eliminar.
- Eliminar no borra la cotización.

### Proyecto

- Es opcional.
- Se puede buscar.
- Se puede seleccionar.
- Aparece en tabla.
- Tiene acción eliminar.
- No se elimina el proyecto.
- La Requisición admite únicamente el vínculo de proyecto contemplado por el modelo actual `0..1`.

### Items

- Al vincular una cotización se cargan automáticamente sus Items.
- Los Items pueden editarse manualmente.
- Se pueden agregar Items manualmente.
- Se pueden eliminar Items.
- Una Requisición no puede guardarse sin al menos un Item.
- Los Items quedan almacenados como datos propios de la Requisición.
- La edición manual no se sobrescribe silenciosamente.

---

# 39. ORDEN DE IMPLEMENTACIÓN

## FASE 1 — Auditoría del formulario actual

Revisar únicamente:

```text
templates de Nueva Requisición
JS del formulario
API requisiciones
serializers
ViewSet
BusinessService
Selectors
modelos existentes
```

Identificar qué existe actualmente y reutilizarlo.

No modificar todavía.

---

## FASE 2 — Información General

Implementar:

```text
Plantilla
Cliente
Fecha solicitud
Prioridad
Número readonly
```

Con validación frontend + backend.

---

## FASE 3 — Numeración

Conectar Requisición con el sistema existente de Plantillas de Numeración.

Garantizar:

```text
tenant
tipo documental
consecutivo
atomicidad
unicidad
no reutilización
```

No tocar la lógica existente de Orden de Compra fuera de la generalización estrictamente necesaria.

---

## FASE 4 — Contexto / Cotizaciones

Implementar:

```text
Vincular cotización
Buscador
Filtro disponibles
Selección
Tabla
Eliminar
Múltiples cotizaciones
Validación de cliente
```

---

## FASE 5 — Contexto / Proyecto

Implementar:

```text
Vincular proyecto
Buscador
Selección
Tabla
Eliminar
0..1 según modelo existente
```

---

## FASE 6 — Items Solicitados

Implementar:

```text
Carga automática desde cotización
Múltiples cotizaciones
Edición manual
Agregar manual
Eliminar
Cálculos
>= 1 item
```

---

## FASE 7 — Integración final del formulario

Verificar que:

```text
Información General
        +
Contexto
        +
Items
```

se guarden como una única operación coherente.

Si falla una validación crítica, no debe quedar una Requisición parcialmente creada.

Utilizar `transaction.atomic()` en las operaciones transaccionales.

---

# 40. REGLA IMPORTANTE PARA ESTA FASE

No convertir el formulario en un formulario enorme.

La pantalla debe quedar deliberadamente limitada a:

```text
INFORMACIÓN GENERAL
    Plantilla
    Cliente
    Fecha
    Prioridad
    Número

CONTEXTO
    Cotizaciones
    Proyecto

ITEMS SOLICITADOS
    Items
```

No agregar todavía:

- documentos;
- facturas;
- proveedores;
- aprobadores;
- centros de costo;
- condiciones comerciales;
- recepción;
- órdenes de compra;
- campos adicionales no solicitados.

---

# 41. PRUEBAS — ÚLTIMO PASO Y SOLO MANUALES

No ejecutar pruebas automatizadas durante las fases anteriores.

Las pruebas se realizan exclusivamente al final mediante UI.

### Caso 1

Crear Requisición sin Plantilla.

Resultado:

```text
Bloqueado.
```

### Caso 2

Crear sin Cliente.

Resultado:

```text
Bloqueado.
```

### Caso 3

Crear sin Fecha.

Resultado:

```text
Bloqueado.
```

### Caso 4

Crear sin Prioridad.

Resultado:

```text
Bloqueado.
```

### Caso 5

Seleccionar Plantilla.

Resultado:

```text
Número generado automáticamente / mostrado readonly
```

### Caso 6

Intentar modificar el número.

Resultado:

```text
No permitido.
```

### Caso 7

Vincular una cotización disponible.

Resultado:

```text
Cotización aparece en tabla.
Items aparecen automáticamente.
```

### Caso 8

Vincular segunda cotización.

Resultado:

```text
Las dos aparecen.
Los Items de ambas quedan disponibles.
```

### Caso 9

Intentar vincular una cotización ya asignada.

Resultado:

```text
Bloqueado.
```

### Caso 10

Eliminar cotización.

Resultado:

```text
Se elimina solamente el vínculo.
```

### Caso 11

Vincular proyecto.

Resultado:

```text
Proyecto aparece en tabla.
```

### Caso 12

Eliminar proyecto.

Resultado:

```text
Se elimina solamente el vínculo.
```

### Caso 13

Editar manualmente un Item proveniente de cotización.

Resultado:

```text
La modificación permanece.
```

### Caso 14

Agregar Item manual.

Resultado:

```text
Item agregado correctamente.
```

### Caso 15

Eliminar todos los Items.

Resultado:

```text
Guardar bloqueado:
Debe existir al menos un item solicitado.
```

### Caso 16

Crear Requisición completa.

Resultado esperado:

```text
Requisición creada
Número único
Cliente asociado
Plantilla asociada
Fecha
Prioridad
Cotizaciones asociadas
Proyecto opcional
Items almacenados
```

---

# 42. RESULTADO FINAL ESPERADO

El usuario debe percibir el formulario como un flujo sencillo:

```text
1. ¿Qué requisición estoy creando?
   → Plantilla
   → Cliente
   → Fecha
   → Prioridad
   → Número automático

2. ¿De dónde nace la necesidad?
   → Cotizaciones
   → Proyecto opcional

3. ¿Qué necesito comprar?
   → Items sincronizados
   → Edición manual
```

La arquitectura interna continúa siendo:

```text
Cotización
    │
    ├───────────────┐
    │               │
    ▼               ▼
RequisicionCotizacion
    │
    ▼
RequisicionCompra
    │
    ├── Proyecto 0..1
    │
    └── RequisicionCompraItem 1..N
```

manteniendo la Requisición como el expediente de abastecimiento previo a la Orden de Compra y aprovechando los modelos ya establecidos en la implementación actual.

# 43. REGLA SSoT

La implementación final debe respetar:

```text
Cliente
    → Clientes

Cotización
    → Cotizaciones

Proyecto
    → Proyectos

Plantilla / Consecutivo
    → Compras / Numeración

Item de Requisición
    → Requisiciones

Requisición
    → Requisiciones
```

La cotización aporta datos iniciales al formulario, pero no reemplaza a la Requisición como dueño de sus propios Items.
