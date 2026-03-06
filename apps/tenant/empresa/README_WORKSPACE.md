# ⚠️ Módulo Empresa en Workspace - NO MODIFICAR SIN REVISIÓN

**Versión:** 2.37  
**Estado:** ✅ **ESTABILIZADO - NO MODIFICAR SIN SEGUIR DOCUMENTACIÓN**

---

## 📚 Documentación Obligatoria

**ANTES de modificar cualquier archivo relacionado con el módulo Empresa en el workspace, LEER:**

👉 **`documentacion/WORKSPACE_MODULO_EMPRESA_v2.37.md`**

Este documento contiene:
- ✅ Reglas arquitectónicas obligatorias
- ✅ Código de referencia para cada componente
- ✅ Lista de cambios prohibidos
- ✅ Checklist de modificaciones
- ✅ Salvaguardas y validaciones

---

## 🧪 Tests de Validación

**Ejecutar ANTES de cualquier modificación:**

```bash
# Tests de smoke (funcionalidad básica)
pytest tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py -v

# Tests de integridad (estructura completa)
pytest tests/tenant/core/smoke/test_workspace_empresa_integridad.py -v
```

**Si algún test falla:** NO proceder sin corregir primero.

---

## 📁 Archivos Críticos

### Backend
- `apps/tenant/empresa/api/serializers.py` → `EmpresaListSerializer`
- `apps/tenant/empresa/api/viewsets.py` → `EmpresaViewSet.list()`

### Frontend
- `apps/tenant/core/templates/tenant/core/partials/empresa/empresa_list.html`
- `apps/tenant/core/static/core/js/empresa/empresa.page.js`

### Tests
- `tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py`
- `tests/tenant/core/smoke/test_workspace_empresa_integridad.py`

---

## ⚠️ Reglas Críticas (Resumen)

1. **Serializer:** Solo expone 6 campos: `nit`, `direccion`, `telefono`, `email_contacto`, `regimen_tributario`, `moneda`
2. **HTML:** Exactamente 7 columnas (6 datos + Acciones)
3. **JS:** Selector `#tabla-empresa`, columnas alineadas con Serializer
4. **Endpoint:** Retorna array `[]` o `[data]`, NO objeto paginado

---

## 🚫 Prohibido Sin Justificación

- Agregar/quitar columnas sin actualizar todos los componentes
- Cambiar selector `#tabla-empresa`
- Exponer campos adicionales en `EmpresaListSerializer`
- Cambiar formato de respuesta del endpoint
- Eliminar tests de smoke

---

**Última actualización:** 2026-02-10  
**Mantenido por:** Equipo de Arquitectura SINTEL
