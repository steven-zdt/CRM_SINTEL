# Pruebas de Humo - CRUD MailInboxConfig

## Checklist de Funcionalidad

### ✅ 1. Carga de Lista (READ)
- [ ] Al abrir la vista `#empresa`, se carga automáticamente la lista de configuraciones
- [ ] Si no hay configuraciones, muestra mensaje: "No hay configuraciones guardadas. Haz clic en 'Nueva Configuración' para crear una."
- [ ] Si hay configuraciones, muestra tabla con: ID, Alias, Email, Proveedor, Activo, Acciones
- [ ] Los botones "Editar" y "Eliminar" están presentes en cada fila

### ✅ 2. Botón "Nueva Configuración" (CREATE)
- [ ] Al hacer clic en "Nueva Configuración", se oculta el panel de lista
- [ ] Se muestra el formulario de creación
- [ ] El título del formulario dice "Nueva Configuración"
- [ ] El formulario está limpio (sin datos previos)
- [ ] El campo `config_id` está vacío

### ✅ 3. Crear Configuración (CREATE)
- [ ] Validación: Si falta "nombre", muestra error
- [ ] Validación: Si falta "host", muestra error
- [ ] Validación: Si falta "password" (en creación), muestra error
- [ ] Si selecciona "Gmail" como proveedor:
  - [ ] Se muestra ayuda de Gmail
  - [ ] Se autocompleta host: "imap.gmail.com"
  - [ ] Se autocompleta puerto: 993
  - [ ] SSL se marca automáticamente
- [ ] Al guardar exitosamente:
  - [ ] Muestra mensaje de éxito
  - [ ] Recarga la lista
  - [ ] Oculta el formulario
  - [ ] La nueva configuración aparece en la tabla

### ✅ 4. Editar Configuración (UPDATE)
- [ ] Al hacer clic en "Editar", se carga la configuración
- [ ] El formulario se llena con los datos existentes
- [ ] El título cambia a "Editar Configuración"
- [ ] El campo `config_id` tiene el ID de la configuración
- [ ] El campo password está vacío (no se muestra)
- [ ] Al guardar exitosamente:
  - [ ] Muestra mensaje de éxito
  - [ ] Recarga la lista
  - [ ] Oculta el formulario
  - [ ] Los cambios se reflejan en la tabla

### ✅ 5. Eliminar Configuración (DELETE)
- [ ] Al hacer clic en "Eliminar", muestra confirmación
- [ ] Si cancela, no elimina
- [ ] Si confirma, elimina la configuración
- [ ] Recarga la lista automáticamente
- [ ] La configuración desaparece de la tabla

### ✅ 6. Botón "Cancelar"
- [ ] Al hacer clic en "Cancelar", oculta el formulario
- [ ] Muestra el panel de lista
- [ ] Limpia el formulario
- [ ] Recarga la lista

### ✅ 7. Funciones Globales
- [ ] `window.editMailboxConfig` está disponible
- [ ] `window.deleteMailboxConfig` está disponible
- [ ] Los botones onclick en la tabla funcionan correctamente

## Comandos de Prueba Manual

### 1. Verificar carga inicial
```javascript
// En consola del navegador
window.loadMailboxConfigs();
```

### 2. Verificar botón "Nueva Configuración"
```javascript
// En consola del navegador
document.getElementById("btn-mailbox-new").click();
// Verificar que se muestra el formulario
```

### 3. Verificar funciones globales
```javascript
// En consola del navegador
typeof window.editMailboxConfig; // Debe ser "function"
typeof window.deleteMailboxConfig; // Debe ser "function"
```

### 4. Verificar endpoints API
```bash
# Listar configuraciones
curl -X GET "http://localhost:8000/api/v1/core/empresa/mailbox/configs/" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..."

# Crear configuración
curl -X POST "http://localhost:8000/api/v1/core/empresa/mailbox/configs/" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test Config",
    "provider": "custom",
    "host": "imap.test.com",
    "port": 993,
    "ssl": true,
    "username": "test@test.com",
    "password": "test123",
    "mailbox": "INBOX",
    "is_active": true
  }'
```

## Errores Comunes a Verificar

1. **Error 403 Forbidden**: Verificar que el usuario tenga permisos de ADMIN
2. **Error 500 Internal Server Error**: Verificar logs del servidor
3. **Funciones no definidas**: Verificar que las funciones estén expuestas en `window`
4. **Botones no funcionan**: Verificar que los onclick usen `window.editMailboxConfig` y `window.deleteMailboxConfig`
5. **Formulario no se muestra**: Verificar que los paneles tengan las clases correctas (`hidden`)

## Estado Actual

- ✅ Funciones CRUD implementadas
- ✅ Botón "Nueva Configuración" corregido
- ✅ Funciones expuestas globalmente
- ✅ Validaciones básicas implementadas
- ✅ Manejo de errores implementado
- ✅ Carga automática al abrir vista empresa
