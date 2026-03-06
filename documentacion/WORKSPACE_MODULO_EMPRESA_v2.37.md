# 📋 Workspace Módulo Empresa v2.37 - Documentación Definitiva

**Versión:** 2.37  
**Fecha:** 2026-02-10  
**Estado:** ✅ **SOLUCIONADO Y ESTABILIZADO - NO MODIFICAR SIN REVISIÓN ARQUITECTÓNICA**

> **⚠️ ADVERTENCIA CRÍTICA:** Este módulo ha sido completamente refactorizado y estabilizado. Cualquier modificación debe seguir estrictamente las reglas documentadas aquí. Cambios no alineados con esta documentación pueden romper la funcionalidad.

---

## 🎯 Objetivo

El módulo Empresa en el workspace (`workspace/#empresa`) implementa dos módulos completamente independientes:

1. **EmpresaModule** → Consume `/api/v1/empresas/`
2. **MailInboxConfigModule** → Consume `/api/v1/empresas/mail-inbox-config/`

Ambos módulos funcionan de forma totalmente independiente, cada uno con su propia tabla DataTable, sin interferencias mutuas.

---

## 📐 Arquitectura y Reglas Obligatorias

### A) Backend (API)

#### 1. Serializer: `EmpresaListSerializer`

**Ubicación:** `apps/tenant/empresa/api/serializers.py`

**Reglas OBLIGATORIAS:**
- ✅ **Solo expone campos mínimos:** `nit`, `direccion`, `telefono`, `email_contacto`, `regimen_tributario`, `moneda`
- ✅ **NO expone:** `id`, `razon_social`, `logo`, `website`, `created_at`, `updated_at`, ni ningún campo pesado
- ✅ **Alias de campo:** `regimen_tributario` es un alias de `regimen_renta_codigo` (compatibilidad con UI)
- ✅ **Read-only:** Todos los campos son `read_only_fields`

**Código de referencia:**
```python
class EmpresaListSerializer(serializers.ModelSerializer):
    regimen_tributario = serializers.CharField(source='regimen_renta_codigo', read_only=True)
    
    class Meta:
        model = Empresa
        fields = (
            'nit',
            'direccion',
            'telefono',
            'email_contacto',
            'regimen_tributario',  # Alias de regimen_renta_codigo
            'moneda',
        )
        read_only_fields = fields
```

**⚠️ PROHIBIDO:**
- Agregar campos adicionales sin justificación arquitectónica
- Exponer `id` o campos pesados en LIST
- Cambiar el nombre de `regimen_tributario` sin actualizar JS y tests

#### 2. ViewSet: `EmpresaViewSet.list()`

**Ubicación:** `apps/tenant/empresa/api/viewsets.py`

**Reglas OBLIGATORIAS:**
- ✅ **Retorna array directo:** `[]` si no hay empresa, `[data]` si hay 1 empresa (singleton)
- ✅ **Usa `EmpresaListSerializer`** para la acción `list`
- ✅ **Endpoint:** `GET /api/v1/empresas/`

**Código de referencia:**
```python
def list(self, request: Request, *args, **kwargs) -> Response:
    qs = self.get_queryset()
    empresa = qs.first()
    
    if empresa:
        serializer = self.get_serializer(empresa, context=self.get_serializer_context())
        return Response([serializer.data], status=status.HTTP_200_OK)
    else:
        return Response([], status=status.HTTP_200_OK)
```

**⚠️ PROHIBIDO:**
- Cambiar el formato de respuesta (debe ser array, no objeto paginado)
- Usar `EmpresaSerializer` en lugar de `EmpresaListSerializer` para `list`

---

### B) Frontend (HTML)

#### 1. Partial: `empresa_list.html`

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/empresa/empresa_list.html`

**Reglas OBLIGATORIAS:**
- ✅ **Exactamente 7 columnas** en `<thead>` (en este orden):
  1. NIT
  2. Dirección
  3. Teléfono
  4. Email
  5. Régimen
  6. Moneda
  7. Acciones (con `class="text-end"`)
- ✅ **Selector de tabla:** `id="tabla-empresa"` (NO `table-empresa` ni otros)
- ✅ **Shell puro:** NO renderizar datos server-side, solo estructura HTML vacía

**Código de referencia:**
```html
<table id="tabla-empresa" class="table table-striped w-100">
  <thead>
    <tr>
      <th>NIT</th>
      <th>Dirección</th>
      <th>Teléfono</th>
      <th>Email</th>
      <th>Régimen</th>
      <th>Moneda</th>
      <th class="text-end">Acciones</th>
    </tr>
  </thead>
  <tbody></tbody>
</table>
```

**⚠️ PROHIBIDO:**
- Agregar o quitar columnas sin actualizar JS y tests
- Cambiar el `id` de la tabla
- Renderizar datos en el HTML (debe ser shell vacío)

---

### C) Frontend (JavaScript)

#### 1. Módulo: `empresa.page.js`

**Ubicación:** `apps/tenant/core/static/core/js/empresa/empresa.page.js`

**Reglas OBLIGATORIAS:**

##### a) Fetcher Resiliente
- ✅ **Función:** `fetchEmpresaList()` (async)
- ✅ **Maneja:** Índice HATEOAS → colección Y colección directa
- ✅ **Logging:** `[empresa.page]` con URL índice, URL colección, rows.length
- ✅ **Manejo 401:** Inteligente (no redirige, muestra mensaje en feedback)

**Código de referencia:**
```javascript
async function fetchEmpresaList() {
  const indexUrl = API_BASE;
  console.info(`[${MOD}.page] Fetch índice:`, indexUrl);
  
  const idxRes = await fetch(indexUrl, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  });
  
  // Manejo 401 inteligente
  if (idxRes.status === 401) {
    // Mostrar mensaje, no redirigir
    throw new Error('Sesión expirada');
  }
  
  const idxPayload = await idxRes.json();
  
  // Caso A: índice HATEOAS
  if (idxPayload?.empresas) {
    const collectionUrl = idxPayload.empresas;
    // Seguir enlace...
  }
  
  // Caso B: colección directa
  const rows = Array.isArray(idxPayload?.results) ? idxPayload.results
             : (Array.isArray(idxPayload) ? idxPayload : []);
  return rows;
}
```

##### b) Columnas Alineadas
- ✅ **Exactamente 7 columnas** (en este orden):
  1. `nit`
  2. `direccion`
  3. `telefono`
  4. `email_contacto`
  5. `regimen_tributario`
  6. `moneda`
  7. `Acciones` (render function con botones)

**Código de referencia:**
```javascript
const columns = [
  { data: 'nit', title: 'NIT', render: (data) => data || '-' },
  { data: 'direccion', title: 'Dirección', render: (data) => data || '-' },
  { data: 'telefono', title: 'Teléfono', render: (data) => data || '-' },
  { data: 'email_contacto', title: 'Email', render: (data) => data || '-' },
  { 
    data: 'regimen_tributario', 
    title: 'Régimen',
    render: (data) => {
      if (!data) return '-';
      const badges = { 'ORDINARIO': 'success', 'ESPECIAL': 'warning', 'SIMPLE': 'info' };
      return `<span class="badge bg-${badges[data] || 'secondary'}">${data}</span>`;
    }
  },
  { data: 'moneda', title: 'Moneda', render: (data) => data || 'COP' },
  {
    data: null,
    title: 'Acciones',
    orderable: false,
    searchable: false,
    className: 'text-end',
    render: (data, type, row) => {
      if (!row || !row.nit) return '-';
      return `
        <div class="btn-group">
          <button class="btn btn-sm btn-outline-primary" data-action="ver" data-id="${encodeURIComponent(row.nit || '')}">Ver</button>
          <button class="btn btn-sm btn-outline-secondary" data-action="editar" data-id="${encodeURIComponent(row.nit || '')}">Editar</button>
        </div>
      `;
    }
  }
];
```

##### c) Inicialización Segura
- ✅ **Valida:** Existencia del elemento, visibilidad, `<thead><th>`
- ✅ **Destruye:** Instancia previa si existe
- ✅ **Valida:** Mismatch `<th>` vs columnas (warning, no crash)
- ✅ **Maneja:** Estado vacío (mensaje en feedback)

**⚠️ PROHIBIDO:**
- Cambiar el orden de las columnas sin actualizar HTML y tests
- Agregar columnas sin justificación
- Usar `id` en lugar de `nit` para acciones
- Cambiar el selector `TABLE_ID = '#tabla-empresa'`

---

### D) Tests (Smoke)

**Ubicación:** `tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py`

**Tests OBLIGATORIOS que actúan como salvaguardas:**

1. ✅ `test_empresa_api_endpoint_accessible`: Verifica endpoint y campos mínimos
2. ✅ `test_empresa_api_empty_list`: Verifica array vacío `[]`
3. ✅ `test_empresa_api_with_data`: Verifica 1 fila con campos correctos
4. ✅ `test_empresa_table_columns`: Verifica exactamente 7 columnas
5. ✅ `test_empresa_table_empty_state`: Verifica mensaje vacío

**⚠️ PROHIBIDO:**
- Eliminar o modificar estos tests sin justificación
- Agregar tests que contradigan las reglas documentadas

---

## 🔒 Salvaguardas y Validaciones

### 1. Validación de Columnas

**Test crítico:** `test_empresa_table_columns`
- Cuenta `<th>` en la tabla
- Verifica que sean exactamente 7
- Verifica nombres de columnas

**Si este test falla:** Revisar HTML y JS para alineación.

### 2. Validación de Campos API

**Test crítico:** `test_empresa_api_with_data`
- Verifica que solo se expongan campos mínimos
- Verifica que NO se expongan campos prohibidos (`id`, `razon_social`, etc.)

**Si este test falla:** Revisar `EmpresaListSerializer`.

### 3. Validación de Selector

**Validación manual:** Verificar que `TABLE_ID = '#tabla-empresa'` en JS coincida con `id="tabla-empresa"` en HTML.

**Si hay mismatch:** La tabla no se inicializará.

---

## 📝 Checklist de Modificaciones

**ANTES de modificar este módulo, verificar:**

- [ ] ¿La modificación está alineada con la arquitectura v2.37?
- [ ] ¿Se actualizaron HTML, JS y Serializer de forma consistente?
- [ ] ¿Se ejecutaron los tests de smoke y pasaron?
- [ ] ¿Se actualizó esta documentación si cambió la arquitectura?
- [ ] ¿Se consultó con el equipo de arquitectura?

**Si alguna respuesta es NO:** **NO proceder** sin revisión arquitectónica.

---

## 🚫 Cambios Prohibidos Sin Justificación

1. **Agregar columnas** sin actualizar HTML, JS y tests
2. **Cambiar el selector** `#tabla-empresa` sin actualizar todas las referencias
3. **Exponer campos adicionales** en `EmpresaListSerializer` sin justificación
4. **Cambiar el formato de respuesta** del endpoint (debe ser array)
5. **Eliminar o modificar tests** de smoke sin reemplazo equivalente
6. **Renderizar datos server-side** en el HTML (debe ser shell vacío)

---

## 📚 Referencias

- **Arquitectura General:** `documentacion/arquitectura_general.md`
- **Reglas UI Tenant Apps:** `documentacion/REGLAS_UI_TENANT_APPS.md`
- **Informe Empresa:** `documentacion/INFORME_COMPLETO_APP_EMPRESA.md`

---

## ✅ Estado Final

**Fecha de estabilización:** 2026-02-10  
**Versión:** 2.37  
**Tests:** ✅ Todos pasando  
**Documentación:** ✅ Completa  
**Salvaguardas:** ✅ Implementadas

**Este módulo está COMPLETAMENTE FUNCIONAL y ESTABILIZADO. No modificar sin seguir este documento.**

---

**Última actualización:** 2026-02-10  
**Mantenido por:** Equipo de Arquitectura SINTEL
