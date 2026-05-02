# ✅ VERIFICACIÓN EN TIEMPO REAL — Catálogo NIIF v2.61

## Cambio Permanente Implementado

Se agregó la lógica de sincronización del buscador **directamente en `catalogo_service.js`** con un listener de `htmx:afterSettle`. Esto garantiza que la sincronización ocurra automáticamente cuando el offcanvas se inyecta dinámicamente.

---

## Archivo Modificado

**Archivo:** `apps/tenant/contabilidad/static/contabilidad/js/catalogo_service.js`

**Cambios:**
- Función `sincronizarBuscadorNIIF(target)` agregada (líneas 287-355)
- Listener de `htmx:afterSettle` agregado (líneas 360-375)
- Exportación de función para llamadas manuales (línea 380)

**IDs Verificados:**
- Select tipo: `select[name="tipo"]` ✅
- Input buscador: `#input-buscar-catalogo` ✅
- Botón búsqueda: `#btn-buscar-catalogo` ✅

---

## Verificación Paso a Paso

### PASO 1: Recarga la página

```
Ctrl+F5 (limpiar caché)
```

**Resultado esperado en consola:**
```
[catalogo.service] ✅ CARGADO
```

---

### PASO 2: Abre la consola

```
F12 → Pestaña "Console"
```

---

### PASO 3: Abre "Crear Cuenta Contable"

1. En la página de cuentas, haz clic en **"+ Crear Cuenta"**
2. Se abrirá el offcanvas vía HTMX

**Resultado esperado en consola:**
```
[catalogo.service] 🎯 htmx:afterSettle detectado en offcanvas de cuentas
[catalogo.service] 🔄 Sincronizando buscador NIIF...
[catalogo.service] ✅ Elementos encontrados:
  - Select tipo: select-tipo-cuenta
  - Input buscador: input-buscar-catalogo
  - Botón búsqueda: btn-buscar-catalogo
[catalogo.service] 📋 Tipo actual: ""
[catalogo.service] ✅ Sincronización completada
```

---

### PASO 4: Selecciona "PASIVO" en el campo Tipo

1. En el offcanvas, busca el campo **"Tipo"**
2. Selecciona **"PASIVO"** del dropdown

**Resultado esperado en consola:**
```
[catalogo.service] 🎯 Tipo cambiado a: "PASIVO"
[catalogo.service] ✅ Buscador HABILITADO para tipo: PASIVO
```

**Resultado esperado en la UI:**
- ✅ El input "Buscar en Catálogo NIIF" cambia de **gris a blanco** (se habilita)
- ✅ El placeholder dice: **"Buscar en cuentas de PASIVO..."**
- ✅ El botón de búsqueda se habilita
- ✅ El cursor se mueve automáticamente al input

---

### PASO 5: Prueba con otro tipo

1. Selecciona **"ACTIVO"** en el campo Tipo

**Resultado esperado en consola:**
```
[catalogo.service] 🎯 Tipo cambiado a: "ACTIVO"
[catalogo.service] ✅ Buscador HABILITADO para tipo: ACTIVO
```

**Resultado esperado en la UI:**
- ✅ El placeholder actualiza: **"Buscar en cuentas de ACTIVO..."**

---

### PASO 6: Deselecciona el tipo

1. Selecciona **"Seleccione tipo..."** (opción vacía)

**Resultado esperado en consola:**
```
[catalogo.service] 🎯 Tipo cambiado a: ""
[catalogo.service] ❌ Buscador DESHABILITADO
```

**Resultado esperado en la UI:**
- ✅ El input vuelve a **gris** (se deshabilita)
- ✅ El placeholder vuelve a: **"Primero seleccione tipo..."**
- ✅ El botón se deshabilita

---

## Logs Esperados Completos

Si todo funciona correctamente, deberías ver estos logs en orden:

```
[catalogo.service] ✅ CARGADO
[catalogo.service] 🎯 htmx:afterSettle detectado en offcanvas de cuentas
[catalogo.service] 🔄 Sincronizando buscador NIIF...
[catalogo.service] ✅ Elementos encontrados:
  - Select tipo: select-tipo-cuenta
  - Input buscador: input-buscar-catalogo
  - Botón búsqueda: btn-buscar-catalogo
[catalogo.service] 📋 Tipo actual: ""
[catalogo.service] ✅ Sincronización completada
[catalogo.service] 🎯 Tipo cambiado a: "PASIVO"
[catalogo.service] ✅ Buscador HABILITADO para tipo: PASIVO
```

---

## Checklist de Verificación

- [ ] Recargué la página (Ctrl+F5)
- [ ] Abrí la consola (F12)
- [ ] Hice clic en "+ Crear Cuenta"
- [ ] Vi el log: `🎯 htmx:afterSettle detectado`
- [ ] Vi el log: `✅ Elementos encontrados`
- [ ] Seleccioné "PASIVO"
- [ ] Vi el log: `✅ Buscador HABILITADO para tipo: PASIVO`
- [ ] El input cambió de gris a blanco
- [ ] El placeholder dice: "Buscar en cuentas de PASIVO..."
- [ ] El botón de búsqueda se habilitó
- [ ] El cursor se movió al input automáticamente

---

## Solución de Problemas

### ❌ No veo logs de sincronización

**Causa:** El script no se cargó o HTMX no disparó el evento

**Solución:**
1. Recarga la página (Ctrl+F5)
2. Verifica que `catalogo_service.js` esté cargado: `typeof window.CatalogoService` debe ser `"object"`
3. Abre la consola ANTES de hacer clic en "+ Crear Cuenta"
4. Verifica que HTMX esté cargado: `typeof window.htmx` debe ser `"object"`

### ❌ El buscador no se habilita aunque veo los logs

**Causa:** Los IDs en el template no coinciden

**Solución:**
1. En consola, ejecuta:
   ```javascript
   document.querySelector('select[name="tipo"]')
   document.getElementById('input-buscar-catalogo')
   document.getElementById('btn-buscar-catalogo')
   ```
2. Todos deben retornar elementos (no `null`)
3. Si alguno es `null`, el ID no existe en el template

### ❌ El placeholder no actualiza

**Causa:** El listener de `change` no se registró correctamente

**Solución:**
1. En consola, ejecuta:
   ```javascript
   const select = document.querySelector('select[name="tipo"]');
   select.dispatchEvent(new Event('change', { bubbles: true }));
   ```
2. Esto dispara manualmente el evento `change`
3. Si se habilita, el problema es que el evento no se dispara automáticamente

---

## Comandos Útiles en Consola

```javascript
// Ver si CatalogoService está disponible
typeof window.CatalogoService

// Llamar a sincronización manualmente
window.CatalogoService.sincronizarBuscador(document.querySelector('.offcanvas'))

// Ver estado del buscador
document.getElementById('input-buscar-catalogo').disabled

// Ver tipo actual
document.querySelector('select[name="tipo"]').value

// Disparar evento change manualmente
document.querySelector('select[name="tipo"]').dispatchEvent(new Event('change', { bubbles: true }))
```

---

## Resumen de Cambios

| Componente | Cambio | Líneas |
|-----------|--------|--------|
| `catalogo_service.js` | Función `sincronizarBuscadorNIIF()` agregada | 287-355 |
| `catalogo_service.js` | Listener `htmx:afterSettle` agregado | 360-375 |
| `catalogo_service.js` | Exportación de función para llamadas manuales | 380 |

---

## Flujo Garantizado

```
1. Usuario abre "+ Crear Cuenta"
   ↓
2. HTMX inyecta offcanvas
   ↓
3. htmx:afterSettle dispara
   ↓
4. sincronizarBuscadorNIIF() se ejecuta
   ↓
5. Obtiene elementos del offcanvas
   ↓
6. Registra listener de change en select tipo
   ↓
7. Inicializa estado del buscador (deshabilitado)
   ↓
8. Usuario selecciona "PASIVO"
   ↓
9. change event dispara
   ↓
10. Buscador se habilita
    - Input: disabled = false
    - Placeholder: "Buscar en cuentas de PASIVO..."
    - Botón: disabled = false
    - Focus automático
```

---

## Próximos Pasos

1. **Recarga la página** (Ctrl+F5)
2. **Abre consola** (F12)
3. **Sigue los PASOS 1-6** de "Verificación Paso a Paso"
4. **Verifica que veas los logs esperados**
5. **Confirma que el buscador se habilita/deshabilita correctamente**

---

**Estado:** ✅ Cambio permanente implementado en `catalogo_service.js`  
**Versión:** v2.61 - Sincronización HTMX integrada  
**Última actualización:** Marzo 9, 2026
