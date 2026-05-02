# Documentación: Refactorización y Limpieza del Módulo de Empleados v2.40

**Fecha:** 2024  
**Versión:** v2.40  
**Módulo:** `apps.tenant.empleados`

---

## 📋 Resumen Ejecutivo

Este documento describe la refactorización completa, limpieza de código y corrección de errores críticos realizados en el módulo de Empleados del sistema SINTEL CRM v2.40. Se implementaron mejoras en la arquitectura, se corrigieron errores de importación y se optimizó el flujo de URLs de la API.

---

## 🎯 Objetivos Cumplidos

### 1. Limpieza General de Código (Refactor & Cleanup)
- ✅ Eliminación de código zombie y funciones muertas
- ✅ Eliminación de importaciones no usadas
- ✅ Alineación en cascada de todos los archivos
- ✅ Pruebas de humo lógicas completadas

### 2. Corrección de Errores Críticos
- ✅ Resuelto `ImportError` para `eliminar_empleado_retirado`
- ✅ Corregido error 404 en endpoints de API
- ✅ Ajustado orden de registro del router DRF

### 3. Implementación de Funcionalidades
- ✅ Eliminación en cascada de empleados retirados
- ✅ Cancelación automática de contratos al retirar empleado
- ✅ Máquina de estados estricta para contratos

---

## 📁 Archivos Modificados

### Backend

#### 1. `apps/tenant/empleados/models.py`
**Cambios:**
- ❌ **Eliminado:** `limit_choices_to={'estado': 'ACTIVO'}` en `Contrato.empleado` (permitía contratos a empleados inactivos)
- ✅ **Mantenido:** Campo `activo` legacy para compatibilidad

**Razón:** Permitir contratos históricos a empleados retirados/inactivos.

#### 2. `apps/tenant/empleados/services.py`
**Funciones Agregadas:**
- ✅ `eliminar_empleado_retirado(empleado)` - Eliminación en cascada con transacciones atómicas
- ✅ `cancelar_contratos_activos_al_retirar(empleado)` - Cancelación automática de contratos

**Funciones Limpiadas:**
- ❌ **Eliminado:** Importación no usada `Q` de `django.db.models`

**Lógica Implementada:**
```python
def eliminar_empleado_retirado(empleado):
    """
    Elimina en cascada:
    1. Todas las nóminas (Devengo) asociadas
    2. Todos los contratos asociados
    3. Finalmente, el empleado mismo
    """
    # Validación estricta: solo RETIRADOS
    # Transacción atómica para garantizar integridad
    # Retorna resumen de lo eliminado
```

#### 3. `apps/tenant/empleados/services/__init__.py`
**Cambios Críticos:**
- ✅ **Agregado:** Exportación de `eliminar_empleado_retirado`
- ✅ **Agregado:** Exportación de `cancelar_contratos_activos_al_retirar`

**Problema Resuelto:**
- El paquete `services/` (carpeta) y el archivo `services.py` causaban conflicto de importación
- Solución: Re-exportación explícita usando `importlib` para cargar desde `services.py`

#### 4. `apps/tenant/empleados/api/serializers.py`
**Cambios:**
- ❌ **Eliminado:** Importación no usada `from django.db import transaction`

**Verificado:**
- ✅ Todos los campos en `read_only_fields` existen en los modelos
- ✅ `EmpleadoListSerializer` expone correctamente el campo `estado`

#### 5. `apps/tenant/empleados/api/viewsets.py`
**Cambios:**
- ❌ **Eliminado:** Importación no usada `JSONRenderer`
- ❌ **Eliminado:** Importación duplicada de parsers en `ContratoViewSet`
- ✅ **Agregado:** Acción `@action cancelar` en `ContratoViewSet` (faltaba)
- ✅ **Agregado:** Método `perform_update()` en `EmpleadoViewSet` para cancelar contratos automáticamente
- ✅ **Refactorizado:** Método `destroy()` para usar service layer

**Lógica Implementada:**
```python
def destroy(self, request, *args, **kwargs):
    """Eliminación usando service layer para cascada automática"""
    resultado = eliminar_empleado_retirado(instance)
    return Response({'resumen': resultado}, status=200)

def perform_update(self, serializer):
    """Cancela contratos activos automáticamente al retirar empleado"""
    if estado_cambia_a_RETIRADO:
        cancelar_contratos_activos_al_retirar(empleado)
```

#### 6. `apps/tenant/empleados/api/urls.py`
**Cambios Críticos:**
- ✅ **Corregido:** Orden de registro del router (sub-rutas primero, ruta base al final)
- ✅ **Simplificado:** Eliminado try/except innecesario en importaciones
- ✅ **Mejorado:** Logging y documentación

**Estructura Final:**
```python
router.register(r'contratos', ContratoViewSet, basename='contrato')
router.register(r'devengos', DevengoViewSet, basename='devengo')
router.register(r'', EmpleadoViewSet, basename='empleado')  # AL FINAL
```

**Razón:** Evitar "greedy matching" - la ruta vacía debe estar al final para que las específicas tengan prioridad.

### Frontend

#### 7. `apps/tenant/core/static/core/js/empleados/empleados.modals.js`
**Funciones Eliminadas (Código Muerto):**
- ❌ `calcularAportesLey()` - Cálculo ahora en backend
- ❌ `calcularProporcional()` - Cálculo ahora en backend

**Funciones Optimizadas:**
- ✅ `confirmarEliminar()` - Ahora recibe `estadoEmpleado` como parámetro, evitando llamada API innecesaria

**Antes:**
```javascript
confirmarEliminar: async (empleadoId, nombreEmpleado) => {
    // Hacía llamada API para verificar estado
    const res = await w.empleadosAPI.get(empleadoId);
    if (res.data.estado !== 'RETIRADO') return;
    // ...
}
```

**Después:**
```javascript
confirmarEliminar: async (empleadoId, nombreEmpleado, estadoEmpleado) => {
    // Validación directa sin llamada API
    if (estadoEmpleado !== 'RETIRADO') return;
    // ...
}
```

#### 8. `apps/tenant/core/static/core/js/empleados/empleados.page.js`
**Cambios:**
- ✅ **Corregido:** Llamada a `confirmarEliminar()` ahora pasa el estado como tercer parámetro
- ✅ **Mejorado:** Escape de comillas simples en nombres para evitar errores de JavaScript

#### 9. `apps/tenant/core/static/core/js/empleados/empleados.api.js`
**Cambios:**
- ✅ **Documentado:** Funciones `updateContrato` y `cancelarContrato` marcadas como disponibles para uso futuro

---

## 🔧 Correcciones de Errores Críticos

### Error 1: ImportError - `eliminar_empleado_retirado`
**Problema:**
```
ImportError: cannot import name 'eliminar_empleado_retirado' 
from 'apps.tenant.empleados.services'
```

**Causa:**
- Conflicto entre paquete `services/` (carpeta) y archivo `services.py`
- El `__init__.py` no exportaba las nuevas funciones

**Solución:**
- Actualizado `services/__init__.py` para re-exportar `eliminar_empleado_retirado` y `cancelar_contratos_activos_al_retirar`
- Agregadas a `__all__` para exportación explícita

### Error 2: 404 Not Found en Endpoints de API
**Problema:**
```
GET /api/v1/empleados/ 404 (Not Found)
GET /api/v1/empleados/summary/ 404 (Not Found)
```

**Causa:**
- Orden incorrecto de registro en el router DRF
- La ruta vacía `r''` capturaba todas las peticiones antes de evaluar rutas específicas

**Solución:**
- Reordenado registro: sub-rutas específicas primero, ruta base al final
- Eliminado try/except innecesario que ocultaba errores de importación

---

## 🎨 Reglas de Negocio Preservadas

### 1. Daisy Chain (Flujo Secuencial)
✅ **Preservado:** Crear Empleado → Activa Modal Contrato → Activa Modal Nómina

### 2. Estado Estricto de Contratos
✅ **Preservado:** Solo 1 Contrato ACTIVO por empleado
- Nuevos contratos nacen en estado `ACTIVO`
- Crear uno nuevo desactiva automáticamente el anterior
- Solo contratos `ACTIVO` son editables

### 3. Cálculo de Nómina
✅ **Preservado:** Base Cotización = Solo Salario (No Transporte)
- Fórmula: `Base = Salario Proporcional`
- Salud/Pensión: 4% cada una sobre base salarial
- Auxilio de transporte NO suma para base de cotización

### 4. Delete Condicional
✅ **Preservado:** Solo permitir borrar empleados con estado `RETIRADO`
- Frontend: Botón DELETE solo visible para `RETIRADO`
- Backend: Validación estricta en `destroy()`
- Service Layer: Eliminación en cascada automática

---

## 📊 Estructura de Funciones del Service Layer

### Funciones Disponibles en `apps.tenant.empleados.services`

| Función | Descripción | Uso |
|---------|------------|-----|
| `qs_empleados_list(empresa)` | QuerySet optimizado para DataTables | ViewSet.list() |
| `get_nomina_summary(empresa)` | Resumen de nómina del mes actual | ViewSet.summary() |
| `anular_devengo_service(devengo_id, empresa)` | Anula un desprendible de pago | ViewSet.anular() |
| `calcular_devengo_proporcional(...)` | Calcula nómina proporcional | ViewSet.previsualizar() |
| `eliminar_empleado_retirado(empleado)` | Eliminación en cascada | ViewSet.destroy() |
| `cancelar_contratos_activos_al_retirar(empleado)` | Cancela contratos al retirar | ViewSet.perform_update() |

---

## 🔗 Estructura de URLs de la API

### Endpoints Principales

```
GET    /api/v1/empleados/                    → Lista de empleados
POST   /api/v1/empleados/                    → Crear empleado
GET    /api/v1/empleados/{id}/               → Detalle de empleado
PATCH  /api/v1/empleados/{id}/               → Actualizar empleado
DELETE /api/v1/empleados/{id}/               → Eliminar empleado (solo RETIRADOS)
GET    /api/v1/empleados/summary/            → Resumen de nómina
GET    /api/v1/empleados/{id}/contrato-disponible/ → Validar contrato activo
```

### Endpoints de Contratos

```
GET    /api/v1/empleados/contratos/          → Lista de contratos
POST   /api/v1/empleados/contratos/         → Crear contrato
GET    /api/v1/empleados/contratos/{id}/    → Detalle de contrato
PATCH  /api/v1/empleados/contratos/{id}/   → Actualizar contrato
POST   /api/v1/empleados/contratos/{id}/cancelar/ → Cancelar contrato
```

### Endpoints de Nómina (Devengos)

```
GET    /api/v1/empleados/devengos/          → Lista de devengos
POST   /api/v1/empleados/devengos/          → Crear devengo
GET    /api/v1/empleados/devengos/ultima-nomina/ → Última nómina pagada
POST   /api/v1/empleados/devengos/previsualizar/ → Previsualizar cálculo
POST   /api/v1/empleados/devengos/{id}/anular/ → Anular devengo
```

---

## 🧪 Pruebas de Humo Realizadas

- [x] ✅ Funciones eliminadas no rompen el cálculo de nómina
- [x] ✅ Todas las importaciones están siendo usadas
- [x] ✅ El endpoint `getLastPayrollInfo` existe y funciona
- [x] ✅ La acción `cancelar` en `ContratoViewSet` existe y funciona
- [x] ✅ El botón DELETE solo aparece para empleados RETIRADOS
- [x] ✅ No hay errores de linter en ningún archivo
- [x] ✅ Las URLs se resuelven correctamente después de reiniciar servidor
- [x] ✅ Las funciones del service layer se importan correctamente

---

## 📈 Mejoras de Rendimiento

### Frontend
- ✅ **Optimizado:** `confirmarEliminar()` elimina 1 llamada API innecesaria
- ✅ **Limpieza:** Eliminadas 2 funciones JavaScript muertas (reducción de ~30 líneas)

### Backend
- ✅ **Limpieza:** Eliminadas 3 importaciones no usadas
- ✅ **Optimización:** Service layer centralizado para lógica de negocio
- ✅ **Transacciones:** Eliminación en cascada usa transacciones atómicas

---

## 🚀 Flujos Implementados

### Flujo de Eliminación de Empleado Retirado

```
1. Usuario intenta eliminar empleado RETIRADO
   ↓
2. Frontend valida estado (sin llamada API)
   ↓
3. Backend: destroy() valida estado RETIRADO
   ↓
4. Service Layer: eliminar_empleado_retirado()
   - Elimina todas las nóminas (Devengo)
   - Elimina todos los contratos
   - Elimina el empleado
   ↓
5. Retorna 200 OK con resumen
```

### Flujo de Transición a RETIRADO

```
1. Usuario actualiza empleado y cambia estado a RETIRADO
   ↓
2. perform_update() detecta el cambio
   ↓
3. Service Layer: cancelar_contratos_activos_al_retirar()
   - Busca contratos ACTIVOS
   - Los marca como INACTIVO
   - Establece fecha_fin = hoy
   ↓
4. Empleado guardado con estado RETIRADO
```

---

## 📝 Notas Técnicas

### Arquitectura de Service Layer

El módulo `services` tiene una estructura especial:
- **Archivo:** `apps/tenant/empleados/services.py` (lógica de negocio)
- **Paquete:** `apps/tenant/empleados/services/` (carpeta con `__init__.py`)

**Solución al conflicto:**
- El `__init__.py` usa `importlib` para cargar directamente desde `services.py`
- Re-exporta todas las funciones explícitamente
- Esto evita conflictos de importación entre el paquete y el archivo

### Orden de Registro en Router DRF

**Regla de Oro:**
1. Registrar rutas específicas primero (`contratos`, `devengos`)
2. Registrar ruta base (`r''`) al final

**Razón:** Evitar "greedy matching" donde la ruta vacía captura todas las peticiones antes de evaluar rutas específicas.

---

## ✅ Checklist de Verificación Post-Refactor

- [x] ✅ Código limpio sin funciones muertas
- [x] ✅ Todas las importaciones están siendo usadas
- [x] ✅ No hay errores de linter
- [x] ✅ Las URLs se resuelven correctamente
- [x] ✅ Las funciones del service layer se importan correctamente
- [x] ✅ El flujo de eliminación funciona correctamente
- [x] ✅ El flujo de transición a RETIRADO funciona correctamente
- [x] ✅ Los endpoints de API responden correctamente
- [x] ✅ La documentación está actualizada

---

## 🔄 Próximos Pasos Recomendados

1. **Testing:** Implementar tests unitarios para las nuevas funciones del service layer
2. **Documentación API:** Actualizar documentación OpenAPI/Swagger con los nuevos endpoints
3. **Monitoreo:** Agregar métricas para seguimiento de eliminaciones y transiciones de estado
4. **Auditoría:** Considerar agregar logs de auditoría para eliminaciones en cascada

---

## 📚 Referencias

- **Arquitectura:** Sintel CRM v2.40 - API-First Multi-Tenant
- **Framework:** Django REST Framework (DRF)
- **Frontend:** Vanilla JavaScript / jQuery
- **Patrón:** Service Layer Pattern

---

**Documentación generada:** 2024  
**Última actualización:** Tras refactorización completa del módulo de Empleados
