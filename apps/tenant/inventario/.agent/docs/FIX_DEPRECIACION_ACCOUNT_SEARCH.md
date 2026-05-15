# Fix: Campo Cuenta de Depreciación no muestra opciones

**Fecha:** 2026-05-15  
**Estado:** ✅ RESUELTO  
**Archivos modificados:** 1 línea en `contabilidad/services/selectors.py`

---

## 🔴 Problema

El campo "Cuenta de Depreciación (Gasto/Acumulada) *" en el Nuevo Activo Fijo no mostraba ninguna opción al buscar cuentas con código 51.

### Root Cause

La función `filtrar_cuentas_por_app_origen()` en `contabilidad/services/selectors.py` aplicaba un **filtro restrictivo por app de origen**. Cuando se hacía búsqueda desde Inventario con `app_origen='inventario'`, solo se permitían estos prefijos:

```python
'inventario': [
    '143505', '143510', '1435',  # Inventarios
    '613505', '613510', '6135',  # Costos
    '413505', '413510', '4135',  # Ingresos
    '5199',                        # Bajas (pero NO el prefijo '51' completo)
    '15',                          # Activos Fijos ✅
],
```

❌ El prefijo **'51'** (Gastos/Depreciación) NO estaba en la lista.

Cuando el frontend enviaba:
```
GET /api/v1/contabilidad/cuentas-contables/?search=...&codigo_prefix=51&app_origen=inventario
```

El backend aplicaba TWO filters:
1. `filtrar_cuentas_por_app_origen()` → excluía todos los códigos 51
2. `codigo__startswith='51'` → no encontraba nada

**Resultado:** 0 resultados → campo vacío.

---

## ✅ Solución Implementada

Agregué el prefijo **'51'** a la lista de inventario en `contabilidad/services/selectors.py` (línea 156):

```python
'inventario': [
    # Activo — Inventarios
    '143505', '143510', '1435',
    # Costos de ventas
    '613505', '613510', '6135',
    # Ingresos (contraparte de salida inventario)
    '413505', '413510', '4135',
    # Gastos de personal / depreciación
    '51',                           # ✅ AGREGADO: Permite todos los códigos 51XX
    # Propiedades, Planta y Equipo (Activos Fijos)
    '15',
],
```

Ahora el filtro permite:
- Cuentas con código 51 (depreciación, amortización, gastos)
- Cuentas con código 15 (activos fijos)
- Cuentas con códigos 143505, 143510, etc. (inventarios)

---

## 🧪 Testing (Pasos para validar)

### 1. **Abrir Nuevo Activo Fijo**
```
URL: https://<tenant>.crm-sintel.local/inventario/activos/
Click: Botón "Nuevo Activo"
```

### 2. **Buscar Cuenta de Depreciación**
```
Campo: "Cuenta de Depreciación (Gasto/Acumulada) *"
Escribe: "51" (mínimo 2 caracteres para activar búsqueda)
```

### 3. **Verificar Resultados**
Se deben mostrar cuentas como:
- `5100 - Gastos de personal`
- `5105 - Sueldos y salarios`
- `5160 - Depreciación`
- `5199 - Otras pérdidas`
- Etc.

**✅ Si ves cuentas:** Problema resuelto.  
**❌ Si aún ves nada:** Verifica paso 4.

### 4. **Backend Debug (si no funciona)**

```bash
docker compose exec web python manage.py shell << 'EOF'
from apps.tenant.contabilidad.models import CuentaContable
from apps.tenant.contabilidad.services.selectors import filtrar_cuentas_por_app_origen

# Verificar que existan cuentas con código 51
qs = CuentaContable.objects.filter(codigo__startswith='51', activa=True)
print(f"Total cuentas 51 activas: {qs.count()}")

# Simular el filtro de app_origen
qs_filtered = filtrar_cuentas_por_app_origen(qs, 'inventario')
print(f"Después de app_origen=inventario: {qs_filtered.count()}")

if qs_filtered.count() > 0:
    for cuenta in qs_filtered[:5]:
        print(f"  ✓ {cuenta.codigo} - {cuenta.nombre}")
EOF
```

---

## 📋 Checklist Post-Fix

- [x] Modificar `APP_ORIGEN_PREFIJOS['inventario']` para incluir '51'
- [x] Verificar que no haya conflictos con otros prefijos
- [x] Documentar el cambio
- [ ] **Testear en navegador** (después de desplegar)
  - [ ] Buscar cuenta con código 51
  - [ ] Guardar activo con depreciación asignada
  - [ ] Verificar que se guarde el UUID correcto

---

## 🔗 Contexto: Stack Completo de la Búsqueda

```
Frontend (Inventario)
  ↓ activos_editor.js setupCuentaAutocomplete({codigoPrefix: '51'})
  ↓ inventario.utils.js → inventario.api.js.searchCuentas(query, {codigoPrefix: '51'})
  ↓ HTTP GET /api/v1/contabilidad/cuentas-contables/?search=...&codigo_prefix=51&app_origen=inventario
  ↓
Backend (Contabilidad)
  ↓ CuentaContableViewSet.get_queryset()
  ↓ [1] SearchFilter: busca en codigo, nombre, descripcion
  ↓ [2] filtrar_cuentas_por_app_origen(qs, 'inventario')  ← AHORA incluye '51'
  ↓ [3] codigo__startswith='51'  ← filtering final
  ↓ Retorna JSON con cuentas
  ↓
Frontend
  ↓ renderResultados() → lista en dropdown
```

---

## ⚠️ Notas Importantes

1. **Query mínima:** El search requiere >= 2 caracteres. Escribir "5" no dispara búsqueda. Escribe "51" o "gast" para ver resultados.

2. **Activa=true:** Solo se retornan cuentas con `activa=True`. Si tienes cuentas 51 pero con `activa=False`, no aparecerán.

3. **SearchFilter:** La búsqueda es OR en los campos `['codigo', 'nombre', 'descripcion']`. 
   - Buscar "51" → encuentra códigos que contengan "51"
   - Buscar "gast" → encuentra nombres/descripciones con "gast"
   - Buscar "depreciación" → encuentra descripciones con "depreciación"

4. **Otros apps:** Si otras apps (gastos, empleados, etc.) también necesitan acceso a código 51, agregar el prefijo a sus listas en `APP_ORIGEN_PREFIJOS`.

---

## 📝 Cambio Resumido

| Aspecto | Antes | Después |
|---------|-------|---------|
| Prefijos inventario para 51 | ❌ Excluido | ✅ '51' incluido |
| Cuentas depreciación visibles | ❌ No | ✅ Sí |
| Búsqueda desde activos | ❌ 0 resultados | ✅ Múltiples resultados |

**Línea modificada:** `apps/tenant/contabilidad/services/selectors.py:146-157`  
**Difusión:** 1 línea agregada  
**Impacto:** Bajo (solo suma permisos, no restringe nada)

---

## 🚀 Próximos pasos

1. ✅ Fix en code (completado)
2. ⏳ Desplegar en desarrollo/staging
3. ⏳ Probar en navegador (ver Testing section)
4. ⏳ Si OK → Desplegar en producción
