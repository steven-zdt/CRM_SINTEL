# Pruebas de Humo - Módulo Clientes

## Objetivo
Verificar que las funciones de **Crear**, **Editar** y **Eliminar** funcionan correctamente en el módulo de Clientes.

## Pre-requisitos
1. Acceso al workspace: `http://[tenant].sintel.net.co/workspace/#clientes`
2. Usuario autenticado con permisos de administrador
3. Al menos un cliente existente en la base de datos (para pruebas de edición/eliminación)

---

## Prueba 1: Crear Cliente

### Pasos:
1. Navegar a `workspace/#clientes`
2. Hacer clic en el botón **"Nuevo"**
3. Llenar el formulario:
   - Tipo Persona: Persona Natural
   - Tipo Documento: Cédula de Ciudadanía
   - Número Documento: `1234567890` (único)
   - Razón Social: `Cliente Prueba`
   - Email: `prueba@test.com`
   - Teléfono: `3001234567`
   - Estado: Activo
4. Hacer clic en **"Guardar"**

### Resultado Esperado:
- ✅ Modal se cierra automáticamente
- ✅ Notificación de éxito: "Cliente guardado exitosamente"
- ✅ El nuevo cliente aparece en la tabla (primera página)
- ✅ El cliente tiene ID asignado

### Validación Adicional:
- Verificar en la consola del navegador (F12) que no hay errores
- Verificar que la tabla se recarga correctamente

---

## Prueba 2: Editar Cliente

### Pasos:
1. En la tabla de clientes, localizar un cliente existente
2. Hacer clic en el **icono de editar** (lápiz) en la columna "Acciones"
3. Modificar algún campo (ej: cambiar el email a `editado@test.com`)
4. Hacer clic en **"Guardar"**

### Resultado Esperado:
- ✅ Modal se cierra automáticamente
- ✅ Notificación de éxito: "Cliente guardado exitosamente"
- ✅ La tabla se actualiza mostrando los cambios
- ✅ Los cambios persisten al recargar la página

### Validación Adicional:
- Verificar que el título del modal dice "Editar Cliente"
- Verificar que todos los campos se llenan correctamente
- Verificar en la consola que no hay errores

---

## Prueba 3: Eliminar Cliente

### Pasos:
1. En la tabla de clientes, localizar un cliente existente
2. Hacer clic en el **icono de eliminar** (basura) en la columna "Acciones"
3. Confirmar la eliminación en el diálogo de confirmación
4. Verificar que el cliente desaparece de la tabla

### Resultado Esperado:
- ✅ Diálogo de confirmación aparece: "¿Está seguro de que desea eliminar este cliente?"
- ✅ Si se cancela, el cliente NO se elimina
- ✅ Si se confirma, notificación de éxito: "Cliente eliminado exitosamente"
- ✅ El cliente desaparece de la tabla (soft delete: `activo=False`)
- ✅ La tabla se recarga automáticamente

### Validación Adicional:
- Verificar que el cliente eliminado NO aparece en búsquedas
- Verificar en la base de datos que `activo=False` (soft delete)
- Verificar en la consola que no hay errores

---

## Prueba 4: Validación de Duplicados

### Pasos:
1. Intentar crear un cliente con un documento que ya existe
2. Llenar el formulario con:
   - Tipo Documento: Mismo que un cliente existente
   - Número Documento: Mismo que un cliente existente
3. Hacer clic en **"Guardar"**

### Resultado Esperado:
- ✅ Error de validación: "Ya existe un cliente registrado con este tipo y número de documento en esta empresa."
- ✅ El modal NO se cierra
- ✅ El formulario muestra el error claramente

---

## Prueba 5: Búsqueda y Filtrado

### Pasos:
1. En el campo de búsqueda, escribir parte de la razón social de un cliente
2. Verificar que la tabla se filtra automáticamente (con debounce de 300ms)
3. Limpiar el campo de búsqueda
4. Verificar que la tabla muestra todos los clientes nuevamente

### Resultado Esperado:
- ✅ La búsqueda funciona en tiempo real
- ✅ Los resultados se filtran correctamente
- ✅ La paginación se resetea a la primera página al buscar

---

## Prueba 6: Paginación Remota

### Pasos:
1. Si hay más de 10 clientes, verificar que aparece la paginación
2. Navegar a la página 2
3. Hacer clic en "Editar" en un cliente de la página 2
4. Guardar los cambios
5. Verificar que la tabla vuelve a la página 1 y muestra el cliente editado

### Resultado Esperado:
- ✅ La paginación funciona correctamente
- ✅ Después de crear/editar/eliminar, la tabla vuelve a la página 1
- ✅ Los datos se cargan desde el servidor (no client-side)

---

## Checklist Final

- [ ] Crear cliente funciona correctamente
- [ ] Editar cliente funciona correctamente
- [ ] Eliminar cliente funciona correctamente (soft delete)
- [ ] Validación de duplicados funciona
- [ ] Búsqueda funciona en tiempo real
- [ ] Paginación remota funciona
- [ ] Iconos de acciones se muestran correctamente (Font Awesome)
- [ ] Notificaciones de éxito/error se muestran
- [ ] No hay errores en la consola del navegador
- [ ] La tabla se recarga automáticamente después de operaciones

---

## Errores Conocidos y Soluciones

### Error: "Cliente no encontrado" al editar
**Solución**: Verificar que el ID del cliente existe y pertenece a la empresa del tenant actual.

### Error: "No tiene permisos para eliminar este cliente"
**Solución**: Verificar que el usuario tiene permisos de administrador o staff.

### Error: Iconos no se muestran
**Solución**: Verificar que Font Awesome está cargado correctamente en `base.html`.

---

## Notas Técnicas

- **Soft Delete**: Los clientes eliminados se marcan como `activo=False`, no se eliminan físicamente
- **Paginación**: La paginación es remota (server-side), los datos se cargan desde el servidor
- **Búsqueda**: La búsqueda se realiza en `razon_social`, `numero_documento`, `email`, `nombre_comercial`
- **CSRF**: Todas las operaciones requieren token CSRF válido
