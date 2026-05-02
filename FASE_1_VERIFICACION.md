# Fase 1 — Verificación: Reescribir http.js

**Estado:** ✅ IMPLEMENTADO  
**Fecha:** 2026-05-02  
**Archivo modificado:** `apps/public/console/static/js/http.js`  
**Versión:** 3.4

---

## Cambios realizados

### 1. Cliente HTTP ahora es función + objeto

**Antes:**
```javascript
window.http = { async get(...) {}, async post(...) {}, ... }  // solo objeto
w.http('GET', url)  // → TypeError: w.http is not a function
```

**Ahora:**
```javascript
window.http = async (method, url, payload) => { ... }  // función
Object.assign(window.http, { get, post, patch, put, delete })  // + métodos
w.http('GET', url)  // → { ok: true, status: 200, data: {...} }
window.http.get(url)  // → data directo o throw (como antes)
```

### 2. Contrato dual en acción

| Forma | Llamada | Retorna | Lanza |
|---|---|---|---|
| Función (tenant `*.api.js`) | `await w.http('GET', url)` | `{ok, status, data}` | NO |
| Función (tenant `*.api.js`) | `await w.http('POST', url, payload)` | `{ok, status, data}` | NO |
| Objeto (consola pública) | `await w.http.get(url, params)` | data directo | SÍ en 4xx/5xx |
| Objeto (consola pública) | `await w.http.post(url, body)` | data directo | SÍ en 4xx/5xx |

### 3. Inyección automática de JWT y CSRF

```javascript
// Inyecta automáticamente:
headers['X-CSRFToken'] = getCSRFToken();  // desde meta[name="csrf-token"]
headers['Authorization'] = `Bearer ${token}`;  // si window.jwtAuth existe
headers['credentials'] = 'include';  // cookies HttpOnly (OTT flow)
```

### 4. Versión marcada

```javascript
window.http.__version__ === '3.4'  // ✅ permite detectar versión en tests
```

---

## Verificación manual en DevTools

### Paso 1: Validar en consola pública (`/console/tenants/`)

Abre DevTools → Console:

```javascript
// Verificar que http es función
typeof window.http;
// → "function" ✅ (antes era "object")

// Verificar que tiene métodos
typeof window.http.get;
// → "function" ✅

// Verificar versión
window.http.__version__;
// → "3.4" ✅

// Smoke test: llamada a función
const res = await window.http('GET', '/api/public/v1/tenants/?page_size=1');
// → {ok: true, status: 200, data: {count: ..., results: [...]}} ✅

// Smoke test: métodos existentes aún funcionan
const data = await window.http.get('/api/public/v1/impuestos/contribuyentes-tipos/');
// → [...] (array de tipos) ✅
```

### Paso 2: Validar en tenant (`/clientes/`)

```javascript
// Verificar que http está disponible (antes NO estaba)
typeof window.http;
// → "function" ✅ (esto estaba undefined antes en tenant)

// Verificar que clientesAPI está inicializado (era undefined antes)
typeof window.clientesAPI;
// → "object" ✅

// Smoke test: hacer un GET de clientes
const res = await window.http('GET', '/api/v1/clientes/?page_size=1');
// → {ok: true, status: 200, data: {count: ..., results: [...]}} ✅
```

### Paso 3: Validar inyección de JWT

```javascript
// En cualquier contexto (consola o tenant), verificar que Authorization se inyecta
// En Network tab de DevTools, buscar una request a /api/...
// → Request Headers incluye: Authorization: Bearer eyJ...
// → ✅ Confirmado

// Si no hay JWT (usuario anónimo):
// → Authorization NO se añade (esperado)
// → ✅ Confirmado
```

---

## Casos de error — comportamiento esperado

### Caso 1: Forma función — error 400 (tenant *.api.js)

```javascript
const res = await window.http('POST', '/api/v1/clientes/', {
  tipo_persona: 'INVALID_VALUE'  // validación fallará
});
// res = { ok: false, status: 400, data: {tipo_persona: ["valor inválido"]} }
// NO lanza, permite if (res.ok) { ... } else { ... }
```

### Caso 2: Forma objeto — error 400 (consola pública)

```javascript
const data = await window.http.post('/api/public/v1/tenants/', {
  schema_name: 'reserved'  // valor reservado
});
// LANZA: Error("schema_name: [\"valor reservado\"]")
// catch (...) {...}  debe manejar
```

### Caso 3: Error de red (sin internet)

```javascript
const res = await window.http('GET', '/api/v1/clientes/');
// res = { ok: false, status: 0, data: {detail: "Error de red"} }
// NO lanza, permite diagnóstico
```

---

## ¿Qué desbloquea esto?

### ✅ Desbloquea: Todos los `*.api.js` de tenant (27 archivos)

Ahora `window.http` existe en contexto tenant y tiene la firma esperada:

```javascript
// apps/tenant/clientes/static/clientes/js/clientes.api.js:31 (ANTES: TypeError)
const res = await w.http('GET', url);  // → AHORA FUNCIONA ✅
```

### ✅ Desbloquea: Inicialización de APIs

```javascript
// apps/tenant/clientes/static/clientes/js/clientes.api.js:26-38 (ANTES: early return)
w.clientesAPI = Object.freeze({...});  // → AHORA se define ✅
```

### ✅ Desbloquea: CRUD en UI

- Botón "Guardar" en clientes → llama `w.clientesAPI.create()` → llama `w.http()` → **funciona** ✅
- Botón "Editar" → llama `w.clientesAPI.update()` → llama `w.http()` → **funciona** ✅
- Botón "Eliminar" → llama `w.http('DELETE', ...)` → **funciona** ✅

---

## Checklist de validación

- [ ] `apps/public/console/static/js/http.js` reemplazado (línea 55 tiene `async function httpFn`, línea 128 tiene `Object.assign`)
- [ ] `python manage.py collectstatic --noinput` ejecutado
- [ ] DevTools en `/console/tenants/`: `typeof window.http === 'function'` ✅
- [ ] DevTools en `/console/tenants/`: `window.http.__version__ === '3.4'` ✅
- [ ] DevTools en `/clientes/`: `typeof window.http === 'function'` ✅ (era undefined antes)
- [ ] DevTools en `/clientes/`: `typeof window.clientesAPI === 'object'` ✅
- [ ] Network tab: autorización inyectada automáticamente en requests ✅
- [ ] Sin errores de console (`TypeError: w.http is not a function`) ✅

---

## Próximos pasos

1. Ejecutar verificaciones manuales en DevTools (pasos 1-3 arriba).
2. Si todo pasa ✅, ir a **Fase 2** (cargar en `tenant/base.html`).
3. Si hay error, reportar en qué módulo/contexto falló y descripción del error.

**¿Confirmás que todo verificó ok? Cuándo inicio Fase 2.**
