# Pruebas de Humo — Fase 2 (Cargar http.js en tenant/base.html)

**Fecha:** 2026-05-02  
**Estado:** ✅ ARCHIVOS VERIFICADOS

---

## Verificaciones Backend (OK)

| Verificación | Resultado | Evidencia |
|---|---|---|
| `http.js` en source (console) | ✅ | `apps/public/console/static/js/http.js` existe |
| `http.js` en source (tenant) | ✅ | `apps/tenant/core/static/js/http.js` existe |
| Archivos idénticos (MD5) | ✅ | `c370508473277b9f7f397c87dd2804f3` (ambos) |
| Colectados en staticfiles | ✅ | `staticfiles/js/http.js` presente |
| Script tag en template | ✅ | `<script src="{% static 'js/http.js' %}"></script>` en línea 129 |
| Orden de carga correcto | ✅ | Después de `jwt-auth.js`, antes de `page_assets_body` |

---

## Pruebas en Navegador (DevTools Console)

### Test 1: Función existe y tiene la versión correcta

```javascript
typeof window.http === 'function' && window.http.__version__ === '3.4'
```
**Resultado esperado:** `true`

---

### Test 2: Métodos están disponibles

```javascript
['get', 'post', 'patch', 'put', 'delete'].every(m => typeof window.http[m] === 'function')
```
**Resultado esperado:** `true`

---

### Test 3: APIs de módulos se inicializan

```javascript
// En página /clientes/
typeof window.clientesAPI === 'object' && 
typeof window.clientesAPI.list === 'function' &&
typeof window.clientesAPI.create === 'function'
```
**Resultado esperado:** `true`

---

### Test 4: Llamada real (función)

```javascript
// En página /clientes/ o /inventario/
const res = await window.http('GET', '/api/v1/clientes/?page_size=1');
console.log('Status:', res.status, 'OK:', res.ok, 'Has data:', !!res.data);
```
**Resultado esperado:**
```
Status: 200 OK: true Has data: true
```

---

### Test 5: Llamada real (método objeto)

```javascript
// En página /console/tenants/
const data = await window.http.get('/api/public/v1/tenants/?page_size=1');
console.log('Count:', data.count, 'Results:', Array.isArray(data.results));
```
**Resultado esperado:**
```
Count: <número> Results: true
```

---

## Checklist de Verificación

- [ ] Recargar página con `Ctrl+F5` (limpiar cache)
- [ ] Ejecutar Test 1 → `true` ✅
- [ ] Ejecutar Test 2 → `true` ✅
- [ ] Ir a `/clientes/` y ejecutar Test 3 → `true` ✅
- [ ] Ejecutar Test 4 → Status 200 ✅
- [ ] Ir a `/console/tenants/` y ejecutar Test 5 → data cargada ✅
- [ ] Consola: NINGÚN error rojo (TypeError, ReferenceError) ✅
- [ ] Network tab: request a `js/http.js` retorna 200 ✅

---

## Si algún test falla

1. Abre DevTools → Network tab
2. Recarga (`F5`)
3. Busca `http.js` en la lista de requests
4. Si está en rojo (4xx/5xx):
   - Anota el código de error
   - Copia el status code exacto
5. Si NO aparece en la lista:
   - Captura de pantalla de Network tab
   - Reporta que `http.js` no fue solicitado (problema de template)

---

**Próximo paso:** cuando todos los tests pasen ✅, proceder a **Fase 3** (verificación por módulo).
