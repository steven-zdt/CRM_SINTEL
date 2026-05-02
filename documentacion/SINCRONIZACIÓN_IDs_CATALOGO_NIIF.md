# 🔗 SINCRONIZACIÓN DE IDs — Catálogo NIIF v2.61

## Problema Identificado
El script buscaba `input-buscador-niif` pero el template usa `input-buscar-catalogo`.

---

## IDs CORRECTOS (Template HTML)

**Archivo:** `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/cuenta_offcanvas_form.html`

| Elemento | ID Correcto | Línea | Atributo |
|----------|-------------|-------|----------|
| Select Tipo | `select-tipo-cuenta` | 41 | `id="select-tipo-cuenta" name="tipo"` |
| Input Buscador | `input-buscar-catalogo` | 61 | `id="input-buscar-catalogo"` |
| Botón Búsqueda | `btn-buscar-catalogo` | 64 | `id="btn-buscar-catalogo"` |
| Contenedor Resultados | `catalogo-resultados` | 72 | `id="catalogo-resultados"` |
| Info Catálogo | `catalogo-info` | 73 | `id="catalogo-info"` |

---

## Sincronización en Scripts

### ✅ catalogo_integration_v2.js (ACTUALIZADO)

**Línea 72:** Búsqueda en scope
```javascript
const input = (scope && scope.querySelector('#input-buscar-catalogo, input[data-catalogo-search]'))
  || d.getElementById('input-buscar-catalogo');
```

**Línea 86:** Búsqueda global
```javascript
const input = findElement(['#input-buscar-catalogo', 'input[data-catalogo-search]']);
```

**Línea 71:** Select tipo
```javascript
const select = scope.querySelector('select[name="tipo"], #select-tipo-cuenta, #select-tipo');
```

**Línea 74:** Botón búsqueda
```javascript
const button = scope.querySelector('#btn-buscar-catalogo, button[data-catalogo-search-btn]');
```

**Línea 75:** Resultados
```javascript
const resultados = scope.querySelector('#catalogo-resultados, [data-catalogo-results]');
```

### ✅ catalogo_audit.js (ACTUALIZADO)

**Línea 78:** Input buscador
```javascript
inputBuscador: d.getElementById('input-buscar-catalogo'),
```

**Línea 86:** Mensaje de auditoría
```javascript
console.log('  - #input-buscar-catalogo (CORRECTO):', elements.inputBuscador ? `✅ (disabled=${elements.inputBuscador.disabled})` : '❌');
```

---

## Flujo de Búsqueda de Elementos

```
getCatalogoElements(contextEl)
    ↓
┌─────────────────────────────────────────────────────────┐
│ ESTRATEGIA 1: Buscar en scope del offcanvas/form       │
├─────────────────────────────────────────────────────────┤
│ - select[name="tipo"]                                   │
│ - #input-buscar-catalogo                               │
│ - #btn-buscar-catalogo                                 │
│ - #catalogo-resultados                                 │
└─────────────────────────────────────────────────────────┘
    ↓ (Si no encuentra todos)
┌─────────────────────────────────────────────────────────┐
│ ESTRATEGIA 2: Búsqueda global en document              │
├─────────────────────────────────────────────────────────┤
│ - select[name="tipo"]                                   │
│ - #input-buscar-catalogo                               │
│ - #btn-buscar-catalogo                                 │
│ - #catalogo-resultados                                 │
└─────────────────────────────────────────────────────────┘
    ↓
Retorna: { select, input, button, resultados, scope }
```

---

## Verificación en Consola

```javascript
// Ver todos los IDs que existen en la página
document.querySelectorAll('[id*="buscador"], [id*="buscar"], [id*="catalogo"]').forEach(el => {
    console.log(`ID: ${el.id} | Tag: ${el.tagName} | Disabled: ${el.disabled || 'N/A'}`);
});

// Resultado esperado:
// ID: select-tipo-cuenta | Tag: SELECT | Disabled: N/A
// ID: input-buscar-catalogo | Tag: INPUT | Disabled: true/false
// ID: btn-buscar-catalogo | Tag: BUTTON | Disabled: true/false
// ID: catalogo-resultados | Tag: DIV | Disabled: N/A
// ID: catalogo-info | Tag: DIV | Disabled: N/A
```

---

## Comandos de Auditoría Actualizados

```javascript
// Ejecutar auditoría completa (ahora con IDs correctos)
CatalogoAudit.runFullAudit()

// Ver estado actual
CatalogoIntegration.debug()

// Forzar sincronización
CatalogoAudit.forceSyncNow()

// Ver elementos encontrados
CatalogoAudit.checkDOMElements()
```

---

## Cambios Realizados

| Archivo | Cambio | Línea |
|---------|--------|-------|
| `catalogo_integration_v2.js` | Removido `#input-buscador-niif` de búsqueda | 72, 86 |
| `catalogo_audit.js` | Actualizado mensaje de auditoría | 86 |
| `cuenta_offcanvas_form.html` | Sin cambios (IDs ya correctos) | 41, 61, 64, 72, 73 |

---

## Estado Actual

✅ **Sincronización completada**
- Template HTML: IDs correctos
- catalogo_integration_v2.js: Busca IDs correctos
- catalogo_audit.js: Audita IDs correctos
- Delegación de eventos: Activa y funcional
- HTMX: Sincronizado con eventos afterSwap y load

---

## Próximos Pasos

1. Recarga la página (Ctrl+F5)
2. Abre la consola (F12)
3. Ejecuta: `CatalogoAudit.runFullAudit()`
4. Todos los checks deben ser ✅
5. Selecciona un tipo en el campo "Tipo"
6. El input "Buscar en Catálogo NIIF" debe habilitarse automáticamente

---

**Última actualización:** v2.61 - Sincronización de IDs  
**Estado:** Listo para testing
