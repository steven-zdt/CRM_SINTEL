# Changelog - Módulo Empleados v2.95

## Fecha: 2024-12-XX

### Correcciones y Mejoras Implementadas

#### 1. Campo "Auxilio de Transporte" con Lógica Condicional por Método de Pago

**Problema:** El campo "Auxilio de Transporte" no tenía la misma lógica operativa que "Días Laborados" según el método de pago seleccionado.

**Solución:**
- Se implementaron campos separados según el método de pago:
  - `devengo-auxilio-transporte-dias`: Visible cuando método es "Por Días" o "Por Turnos"
  - `devengo-auxilio-transporte-horas`: Visible cuando método es "Por Horas"
- El cálculo se realiza automáticamente desde el contrato activo:
  - **Por Días/Turnos:** `(auxilio_mensual_del_contrato / 30) * dias_laborados`
  - **Por Horas:** `(auxilio_mensual_del_contrato / 30) * (horas_trabajadas / 8)`
- El valor base siempre se toma del contrato activo (`contrato.auxilio_transporte`)
- El usuario puede editar manualmente el valor calculado si es necesario

**Archivos modificados:**
- `apps/tenant/core/templates/tenant/core/partials/empleados/modals.html`
- `apps/tenant/core/static/core/js/empleados/empleados.modals.js`

---

#### 2. Corrección de Error 400 al Crear Devengo (Nómina)

**Problema:** Error 400 (Bad Request) al intentar crear un devengo debido a campos faltantes o mal configurados.

**Solución:**
- Se agregó el campo `fecha_pago` (requerido) al formulario de nómina
- Se actualizó el serializer `DevengoSerializer` para permitir campos editables:
  - `auxilio_transporte`: De `read_only=True` a `required=False, default=0`
  - `salud_empleado` y `pension_empleado`: De `read_only=True` a `required=False, default=0`
- Se implementó cálculo automático de `dias_laborados` según el método:
  - Por Días/Turnos: Usa el valor del campo
  - Por Horas: Calcula `horas / 8` (días equivalentes)
- Se agregó validación de `fecha_pago` antes de enviar el formulario
- Se mejoró el manejo de errores con mensajes claros en el feedback del modal

**Archivos modificados:**
- `apps/tenant/empleados/api/serializers.py`
- `apps/tenant/core/templates/tenant/core/partials/empleados/modals.html`
- `apps/tenant/core/static/core/js/empleados/empleados.modals.js`

---

#### 3. Corrección de Botones en Columna de Acciones de la Tabla

**Problema:** Los botones en la columna de acciones no funcionaban (Editar, Ver/Editar Contrato, Registrar Pago, Ver Historial).

**Solución:**
- Se mejoró el event delegation usando el contenedor del tab en lugar del grid
- Se agregó manejo de clicks en iconos dentro de los botones
- Se implementó función `handleActionClick()` y `processActionClick()` separadas
- Se agregó fallback al documento completo si no se encuentra el contenedor
- Se agregaron logs detallados para debugging
- Se implementó re-configuración automática de eventos cuando el tab se muestra

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js`

---

#### 4. Corrección de `empleadosModals` no Disponible

**Problema:** Error "empleadosModals no está disponible" al hacer click en los botones.

**Solución:**
- Se agregaron verificaciones de dependencias antes de inicializar el módulo
- Se implementó retry automático si `empleadosModals` no está disponible (espera 100ms)
- Se agregaron logs detallados para identificar problemas de orden de carga
- Se verificó y corrigió el orden de carga de scripts en `assets_empleados.html`
- Se agregaron verificaciones en `empleados.modals.js` para confirmar que el módulo se expuso correctamente

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js`
- `apps/tenant/core/static/core/js/empleados/empleados.modals.js`
- `apps/tenant/core/templates/tenant/core/partials/empleados/assets_empleados.html`

---

#### 5. Corrección de Rutas de Scripts Estáticos

**Problema:** Las rutas de los scripts usaban `tenant/core/js/empleados/` pero los archivos están en `core/js/empleados/`.

**Solución:**
- Se corrigieron las rutas en `assets_empleados.html` para usar `core/js/empleados/` (sin prefijo `tenant/`)
- Se agregó comentario explicativo sobre la ruta correcta

**Archivos modificados:**
- `apps/tenant/core/templates/tenant/core/partials/empleados/assets_empleados.html`

---

#### 6. Corrección de Error de Sintaxis en `empleados.modals.js`

**Problema:** Error de sintaxis "Unexpected token 'else'" en la línea 890.

**Solución:**
- Se eliminó código duplicado en el manejo de errores de `saveDevengo()`
- Se eliminó un `else` sin `if` correspondiente
- Se movió el código de refrescar tabla dentro del bloque `if (res.ok)`
- Se limpió la estructura del código

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.modals.js`

---

#### 7. Corrección de URL con Doble `?` en Historial de Nómina

**Problema:** Error 400 debido a URL mal formada: `?empleado=9?page=1&page_size=10` (doble signo de interrogación).

**Solución:**
- Se cambió de usar `ajaxURLGenerator` personalizado a usar `ajaxParams` (ya que `TabulatorFactory` no permite sobrescribir `ajaxURLGenerator`)
- Se creó función `getCustomParams()` para obtener parámetros personalizados (empleado, fechas)
- Se implementó validación de `params` en `ajaxParams` para manejar casos cuando es `undefined`
- Se agregaron valores por defecto para paginación (page: 1, page_size: 10)
- Se actualizó el botón filtrar para usar `replaceData()` en lugar de `setData()` con URL manual

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.modals.js`

---

### Resumen de Archivos Modificados

1. **Backend:**
   - `apps/tenant/empleados/api/serializers.py`

2. **Frontend - Templates:**
   - `apps/tenant/core/templates/tenant/core/partials/empleados/modals.html`
   - `apps/tenant/core/templates/tenant/core/partials/empleados/assets_empleados.html`

3. **Frontend - JavaScript:**
   - `apps/tenant/core/static/core/js/empleados/empleados.page.js`
   - `apps/tenant/core/static/core/js/empleados/empleados.modals.js`

---

### Funcionalidades Verificadas

✅ Campo "Auxilio de Transporte" se calcula automáticamente desde el contrato según método de pago  
✅ Creación de devengo (nómina) funciona correctamente con todos los campos requeridos  
✅ Botones en columna de acciones funcionan correctamente  
✅ Módulo `empleadosModals` se carga y expone correctamente  
✅ Rutas de scripts estáticos corregidas  
✅ Historial de nómina se carga correctamente con filtros de fecha  
✅ Cálculo proporcional de auxilio de transporte según días/horas trabajadas  
✅ Botón Delete aparece automáticamente para empleados RETIRADOS  
✅ Eliminación definitiva de empleados retirados con confirmación  

---

### Notas Técnicas

- **Orden de carga de scripts:** `empleados.api.js` → `empleados.modals.js` → `empleados.page.js`
- **Event delegation:** Se usa el contenedor del tab (`#tab-empleados`) para capturar eventos
- **Cálculo de auxilio:** Siempre se toma del contrato activo, no se permite valor manual inicial
- **URL de historial:** Se construye usando `ajaxParams` para evitar problemas con múltiples signos de interrogación
- **Eliminación de empleados:** Solo disponible para empleados con estado "RETIRADO", requiere confirmación antes de eliminar

---

---

#### 8. Botón Delete para Empleados RETIRADOS

**Problema:** No había forma de eliminar definitivamente empleados retirados de la base de datos desde la interfaz.

**Solución:**
- Se implementó botón "Delete" en la columna de acciones que aparece automáticamente cuando el estado del empleado es "RETIRADO"
- El botón se muestra inmediatamente después de guardar un empleado con estado "RETIRADO"
- Se implementó función `eliminarEmpleado()` que:
  - Muestra confirmación antes de eliminar
  - Llama al endpoint DELETE del backend
  - Elimina definitivamente el empleado y todos sus registros relacionados (contratos, nóminas)
  - Refresca la tabla automáticamente después de la eliminación
- Se agregó lógica condicional en el formatter de acciones:
  - Si estado es "RETIRADO": Se ocultan botones de contrato y nómina, se muestra botón "Delete"
  - Si estado es "ACTIVO": Se muestran todos los botones normales, no se muestra "Delete"
- La tabla se refresca automáticamente cuando se guarda un empleado con estado "RETIRADO" para mostrar el botón inmediatamente

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js`
- `apps/tenant/core/static/core/js/empleados/empleados.modals.js`

**Backend:**
- El método `destroy()` en `EmpleadoViewSet` ya estaba implementado
- Usa `eliminar_empleado_retirado()` del service layer para eliminación en cascada
- Solo permite eliminar empleados con estado "RETIRADO"

---

### Versión
**v2.95** - Módulo Empleados con flujo secuencial completo, cálculos proporcionales y eliminación de empleados retirados

---

## Fecha: 2026-03-XX

### Migración a Arquitectura v2.60 (Offcanvas + HTMX)

#### 9. Eliminación de Modales - Migración a Offcanvas v2.60

**Problema:** El módulo usaba modales manuales (`empleados.modals.js`) que no seguían la Arquitectura v2.60.

**Solución:**
- Se eliminó completamente `empleados.modals.js` (deprecated)
- Se migró toda la funcionalidad a HTMX + Offcanvas
- Se implementaron contenedores offcanvas globales en `workspace.html`:
  - `#offcanvas-container-empleado`
  - `#offcanvas-container-contrato`
  - `#offcanvas-container-devengo`
  - `#offcanvas-container-historial-nominas`
- Todas las acciones ahora usan `htmx.ajax()` para cargar offcanvas dinámicamente
- Se eliminaron referencias a `empleadosModals` en `empleados.page.js`

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js`
- `apps/tenant/core/templates/tenant/core/partials/empleados/assets_empleados.html`
- `apps/tenant/core/templates/tenant/core/workspace.html`
- `apps/tenant/core/templates/tenant/core/partials/empleados/list.html`

**Archivos eliminados/deprecated:**
- `apps/tenant/core/static/core/js/empleados/empleados.modals.js` (deprecated)
- `apps/tenant/core/templates/tenant/core/partials/empleados/modals.html` (comentado)

---

#### 10. Implementación de Nómina Multitanda

**Problema:** Solo se permitía UNA nómina por empleado por mes, limitando pagos semanales o quincenales.

**Solución:**
- Se modificó el constraint de unicidad en el modelo `Devengo`:
  - **Antes:** `unique_together = ['empleado', 'periodo_mes']`
  - **Después:** `UniqueConstraint(fields=['empleado', 'periodo_mes', 'fecha_pago'], condition=Q(anulado=False))`
- Se implementó validación de solapamiento de días:
  - Función `validar_limite_dias_mes()` en `services.py`
  - Verifica que la suma de `dias_laborados` en el mes no exceda 31 días
  - Retorna error `400 Bad Request` con `code: 'dias_excedidos'` si se excede
- Se actualizó el frontend para manejar múltiples nóminas:
  - Campo `fecha_pago` ahora es obligatorio y parte de la clave de unicidad
  - Mensajes de error específicos para duplicados (409 Conflict) y días excedidos (400 Bad Request)
  - El offcanvas permanece abierto en caso de error para permitir corrección

**Archivos modificados:**
- `apps/tenant/empleados/models.py` (constraint de unicidad)
- `apps/tenant/empleados/services.py` (función `validar_limite_dias_mes()`)
- `apps/tenant/empleados/api/viewsets.py` (validación en `DevengoViewSet.create()`)
- `apps/tenant/core/templates/tenant/core/partials/empleados/devengo_offcanvas.html`
- `apps/tenant/core/static/core/js/empleados/empleados.page.js` (manejo de errores 409 y 400)

**Características:**
- Permite registrar múltiples nóminas en el mismo mes con diferentes `fecha_pago`
- Valida que la suma de días no exceda 31 días del mes
- Mensajes de error claros con detalles de días registrados y total

---

#### 11. Corrección de Error `NameError: name 'Decimal' is not defined` en Eliminación de Nómina

**Problema:** Error 500 al eliminar nómina debido a falta de import de `Decimal` en el método `destroy()`.

**Solución:**
- Se agregó `from decimal import Decimal` al inicio del método `destroy()` en `DevengoViewSet`
- Se corrigió la conversión de `instance.prestamos` a `Decimal` antes de sumar:
  ```python
  nuevo_prestamo = prestamo_actual + Decimal(str(instance.prestamos))
  ```

**Archivos modificados:**
- `apps/tenant/empleados/api/viewsets.py` (método `DevengoViewSet.destroy()`)

**Funcionalidad:**
- Eliminación de nómina funciona correctamente
- Reversión de préstamos al contrato funciona correctamente
- Log de auditoría registra la eliminación

---

#### 12. Implementación de Historial de Nóminas con Event Delegation

**Problema:** Los botones "Ver/Editar" y "Eliminar" en el historial de nóminas no funcionaban porque eran generados dinámicamente por Tabulator.

**Solución:**
- Se implementó event delegation en el contenedor `#offcanvas-historial-nominas`
- Se agregó atributo `data-historial-listener` para evitar múltiples listeners
- Botones "Ver/Editar":
  - Usan `htmx.ajax()` para cargar el offcanvas de nómina
  - Muestran spinner durante la carga
  - Manejan errores con `UIManager.handleError()`
- Botones "Eliminar":
  - Usan `window.http('DELETE', ...)` para enviar petición
  - Muestran confirmación antes de eliminar
  - Refrescan tabla de historial y tabla principal después de eliminar
  - Manejan errores con `UIManager.handleError()`

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js` (función `initHistorialNominas()`)

**Características:**
- Event delegation para botones dinámicos
- Anti-Zombies Pattern: Destruye instancia previa antes de crear nueva
- Validación de parámetros antes de inicializar
- Integración completa con `UIManager` para manejo de errores

---

#### 13. Mejoras en Manejo de Errores (409 Conflict y 400 Bad Request)

**Problema:** Los errores de duplicados y días excedidos no mostraban mensajes claros al usuario.

**Solución:**
- **Error 409 Conflict (Nómina Duplicada):**
  - Mensaje específico: "Ya existe una nómina para este empleado, periodo y fecha de pago"
  - Deshabilita botón "Guardar Nómina" y cambia texto a "Nómina Duplicada (Deshabilitado)"
  - Muestra enlace directo a "Ver Registro Existente" si `devengo_existente_id` está disponible
  - Marca campos `periodo_mes` y `fecha_pago` como inválidos
  - Permite re-habilitar el botón cuando el usuario cambia estos campos
  
- **Error 400 Bad Request (Días Excedidos):**
  - Mensaje específico: "La suma de días laborados excede los 31 días del mes"
  - Muestra detalles: días registrados, días nuevos, total
  - Marca campo `dias_laborados` como inválido
  - Permite re-habilitar el botón cuando el usuario cambia `dias_laborados`

- **Función `reenableButton()`:**
  - Re-habilita botón "Guardar Nómina" cuando el usuario corrige los campos
  - Limpia mensajes de error y clases de validación

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js` (manejadores `htmx:responseError` y `reenableButton()`)

**Características:**
- Mensajes de error claros y accionables
- UX mejorada: El offcanvas permanece abierto para corrección
- Validación en tiempo real con feedback visual

---

#### 14. Corrección de Cierre Condicional de Offcanvas

**Problema:** El offcanvas se cerraba incluso cuando había errores (409, 400), impidiendo que el usuario corrigiera los datos.

**Solución:**
- Se modificó el manejador `htmx:afterOnLoad` para cerrar el offcanvas solo si el status code es `201 Created` (creación exitosa)
- Para errores 409 o 400, el offcanvas permanece abierto
- Se agregó validación del status code antes de cerrar

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js` (manejador `htmx:afterOnLoad`)

**Características:**
- Offcanvas se cierra solo en éxito (201)
- Permite corrección de errores sin perder el contexto
- Refresca tablas solo después de éxito

---

#### 15. Implementación de Anti-Zombies Pattern

**Problema:** Al re-inicializar tablas o módulos, las instancias previas quedaban en memoria causando comportamientos inesperados.

**Solución:**
- Se implementó Anti-Zombies Pattern en todas las funciones de inicialización:
  - `initEmpleadosTable()`: Destruye instancia previa de Tabulator antes de crear nueva
  - `initHistorialNominas()`: Destruye instancia previa y limpia contenedor HTML
  - Event listeners: Usan atributos de marca (`data-historial-listener`) para evitar duplicados

**Archivos modificados:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js`

**Características:**
- Previene memory leaks
- Evita comportamientos inesperados al re-inicializar
- Limpia DOM antes de crear nuevas instancias

---

#### 16. Reversión de Préstamos al Eliminar Nómina

**Problema:** Al eliminar una nómina que tenía préstamos descontados, el préstamo no se revertía al contrato.

**Solución:**
- Se implementó lógica de reversión en `DevengoViewSet.destroy()`:
  - Si la nómina tiene `prestamos > 0`, se revierte al contrato
  - Se actualiza `contrato.prestamos_empresa` sumando el préstamo de la nómina eliminada
  - Se registra en log de auditoría

**Archivos modificados:**
- `apps/tenant/empleados/api/viewsets.py` (método `DevengoViewSet.destroy()`)

**Características:**
- Mantiene integridad financiera
- Registra cambios en log de auditoría
- Usa `Decimal` para cálculos precisos

---

#### 17. Corrección de URL Malformada en Tabulator (Doble `?`)

**Problema:** Error 500 debido a URL malformada con doble signo de interrogación: `?empleado=1?page=1&page_size=10`

**Solución:**
- Se corrigió el `ajaxURLGenerator` en `tabulator.factory.js` para manejar correctamente parámetros existentes
- Se implementó parsing correcto de query parameters antes de agregar nuevos

**Archivos modificados:**
- `apps/tenant/core/static/core/js/common/tabulator.factory.js`

**Características:**
- URLs correctamente formateadas
- Soporte para múltiples parámetros de query
- Compatible con paginación remota de Tabulator

---

#### 18. Validación de Solapamiento de Días (Nómina Multitanda)

**Problema:** No había validación para prevenir que la suma de días laborados en un mes excediera 31 días.

**Solución:**
- Se implementó función `validar_limite_dias_mes()` en `services.py`:
  - Suma todos los `dias_laborados` del mes (excluyendo el registro actual si es update)
  - Valida que el total no exceda 31 días
  - Retorna `ValidationError` con detalles si excede
- Se llama en `DevengoViewSet.create()` y `perform_create()` antes de guardar

**Archivos modificados:**
- `apps/tenant/empleados/services.py` (función `validar_limite_dias_mes()`)
- `apps/tenant/empleados/api/viewsets.py` (validación en `create()` y `perform_create()`)

**Características:**
- Validación Zero Trust en backend
- Mensajes de error detallados con días registrados y total
- Previene registros inválidos antes de intentar guardar

---

### Resumen de Archivos Modificados (v2.60)

1. **Backend:**
   - `apps/tenant/empleados/models.py` (constraint de unicidad para Nómina Multitanda)
   - `apps/tenant/empleados/services.py` (función `validar_limite_dias_mes()`)
   - `apps/tenant/empleados/api/viewsets.py` (método `destroy()`, validaciones en `create()`)

2. **Frontend - Templates:**
   - `apps/tenant/core/templates/tenant/core/partials/empleados/devengo_offcanvas.html`
   - `apps/tenant/core/templates/tenant/core/partials/empleados/historial_nominas_offcanvas.html`
   - `apps/tenant/core/templates/tenant/core/workspace.html` (contenedores offcanvas globales)
   - `apps/tenant/core/templates/tenant/core/partials/empleados/list.html` (eliminación de contenedores locales)

3. **Frontend - JavaScript:**
   - `apps/tenant/core/static/core/js/empleados/empleados.page.js` (migración completa a HTMX + Offcanvas)
   - `apps/tenant/core/static/core/js/common/tabulator.factory.js` (corrección de URL malformada)

4. **Frontend - Assets:**
   - `apps/tenant/core/templates/tenant/core/partials/empleados/assets_empleados.html` (eliminación de `empleados.modals.js`)

---

### Funcionalidades Verificadas (v2.60)

✅ Migración completa a Offcanvas + HTMX (sin modales)  
✅ Nómina Multitanda: Múltiples nóminas por mes con diferentes fechas de pago  
✅ Validación de solapamiento de días (no exceder 31 días)  
✅ Eliminación de nómina con reversión de préstamos  
✅ Historial de nóminas con botones funcionales (Ver/Editar, Eliminar)  
✅ Manejo de errores mejorado (409 Conflict, 400 Bad Request)  
✅ Offcanvas permanece abierto en caso de error para corrección  
✅ Anti-Zombies Pattern implementado en todas las inicializaciones  
✅ Event delegation para botones dinámicos en Tabulator  
✅ Corrección de URL malformada en Tabulator  
✅ Import de `Decimal` corregido en método `destroy()`  

---

### Notas Técnicas (v2.60)

- **Arquitectura:** Migración completa a v2.60 (Offcanvas + HTMX, sin modales)
- **Nómina Multitanda:** Permite múltiples pagos por mes diferenciados por `fecha_pago`
- **Validación de Días:** Backend valida que la suma no exceda 31 días (Zero Trust)
- **Event Delegation:** Todos los botones dinámicos usan event delegation
- **Anti-Zombies:** Todas las inicializaciones destruyen instancias previas
- **Error Handling:** `UIManager.handleError()` integrado en todos los flujos
- **Reversión de Préstamos:** Automática al eliminar nómina con préstamos descontados
- **Orden de carga de scripts:** `empleados.api.js` → `empleados.page.js` (sin `empleados.modals.js`)

---

### Versión
**v2.60** - Módulo Empleados con Arquitectura Offcanvas + HTMX, Nómina Multitanda, y validaciones mejoradas