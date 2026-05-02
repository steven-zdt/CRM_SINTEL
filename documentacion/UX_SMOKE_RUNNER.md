# UX Smoke Runner - Guía de Uso

## 🧪 Smoke UX Runner v2.37

Sistema de pruebas automatizadas que simula interacciones de usuario reales en el workspace de SINTEL.

## 📋 Características

- ✅ Simula clicks reales en botones
- ✅ Abre modales reales del sistema
- ✅ Llena formularios con datos de prueba
- ✅ Selecciona opciones en dropdowns
- ✅ Navega entre tabs del workspace
- ✅ Espera DataTables y carga de datos
- ✅ Log en tiempo real con timestamps
- ✅ 100% UI-driven (no usa llamadas directas a CRUD)

## 🚀 Cómo Ejecutar

### 1. Iniciar el servidor Django

```bash
python manage.py runserver
```

### 2. Visitar el workspace con el parámetro `uxsmoke=1`

```
http://localhost:8000/workspace/?uxsmoke=1
```

O en producción:

```
http://home.sintel.com:8000/workspace/?uxsmoke=1
```

### 3. El panel de test aparecerá

El panel aparecerá en la parte superior de la página con:
- Botón "Ejecutar Todo" para ejecutar todas las suites
- Botones individuales para cada suite
- Área de log en tiempo real

### 4. Ejecutar las pruebas

**Opción A: Ejecutar todas las suites**
- Haz click en el botón "Ejecutar Todo"
- Todas las suites se ejecutarán secuencialmente
- El log mostrará el progreso en tiempo real

**Opción B: Ejecutar una suite individual**
- Haz click en el botón de la suite que deseas probar
- Solo esa suite se ejecutará
- Útil para debugging o pruebas específicas

## 📦 Suites Disponibles

### CRUD Completo
1. **clientes** - Crea un cliente nuevo
2. **proveedores** - Crea un proveedor nuevo
3. **gastos** - Crea un gasto nuevo
4. **empleados** - Crea un empleado nuevo

### Refresco de DataTables
5. **facturas** - Refresca la tabla de facturas
6. **contabilidad_cuentas** - Refresca la tabla de cuentas
7. **contabilidad_asientos** - Refresca la tabla de asientos
8. **inventario_activos** - Refresca la tabla de activos

### Alta de Items
9. **inventario_catalogo** - Crea un item en el catálogo

### Modales
10. **empresa** - Abre el modal de edición de empresa
11. **perfil** - Abre el modal de edición de perfil

## 🔍 Interpretación del Log

El log muestra:
- ✅ **Verde**: Operación exitosa
- ⚠️ **Amarillo**: Advertencia (elemento no encontrado, pero no crítico)
- ❌ **Rojo**: Error (fallo en la ejecución)

Ejemplo de log:
```
[12:34:56.789] ✅ Iniciando simulación UX: Clientes
[12:34:56.990] ✅ Navegando a tab: clientes
[12:34:57.200] ✅ Tab clientes activado
[12:34:57.400] ✅ Click en botón Crear Cliente
[12:34:57.600] ✅ Modal crear-cliente abierto
[12:34:57.750] ✅ Formulario llenado
[12:34:57.950] ✅ Click en botón Guardar
[12:34:59.150] ✅ Creación simulada finalizada
[12:35:00.200] ✅ Suite Clientes completada
```

## 🛠️ Verificación de Archivos

Ejecuta el script de verificación:

```bash
python scripts/verificar_ux_smoke.py
```

Este script verifica que:
- El panel esté presente en `workspace.html`
- El script `workspace_ux_smoke.js` exista
- Todas las suites estén definidas
- Las funciones principales estén presentes

## 📝 Notas Técnicas

### Selectores HTML

Los tests usan selectores reales del sistema:
- Botones: `#btn-{modulo}-crear`, `#btn-{modulo}-guardar`
- Modales: `#modal-crear-{modulo}`, `#modal-editar-{modulo}`
- Campos: `#{modulo}-create-{campo}`, `#{modulo}-edit-{campo}`

### Delays

Los tests incluyen delays para simular comportamiento humano:
- 150ms entre escrituras de campos
- 200ms después de clicks
- 500ms-1500ms para esperar respuestas del servidor

### Compatibilidad

- ✅ No rompe la implementación previa
- ✅ Solo se carga con `?uxsmoke=1`
- ✅ No interfiere con el uso normal del workspace
- ✅ Funciona con todos los módulos estandarizados

## 🐛 Troubleshooting

### El panel no aparece
- Verifica que la URL tenga `?uxsmoke=1`
- Revisa la consola del navegador por errores JavaScript
- Verifica que `workspace_ux_smoke.js` se esté cargando

### Los tests fallan
- Verifica que el servidor Django esté corriendo
- Revisa que estés autenticado
- Verifica que los módulos estén correctamente inicializados
- Revisa el log para ver qué elemento no se encontró

### Los modales no se abren
- Verifica que Bootstrap esté cargado
- Revisa que los IDs de los botones sean correctos
- Verifica que los event listeners estén activos

## 📚 Archivos Relacionados

- `apps/tenant/core/templates/tenant/core/workspace.html` - Panel de test
- `apps/tenant/core/static/core/js/tests/workspace_ux_smoke.js` - Lógica de tests
- `scripts/verificar_ux_smoke.py` - Script de verificación
