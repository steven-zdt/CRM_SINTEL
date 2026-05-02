# FASE 7 — Router de Dominio y Validadores por App

**Fecha:** 2026-02-10  
**Estado:** ✅ Implementado

## 🎯 Objetivo

Crear un router de dominio centralizado que permita:
- Materialización personalizada por app según `dto["type"]`
- Validación específica por tipo de documento antes de persistir
- Extensibilidad sin modificar el core del pipeline
- Multi-tenant: Operación en el contexto del tenant actual
- Idempotencia delegada a cada servicio de dominio

## 📋 Componentes Implementados

### 7.1 Router de Dominio Centralizado

**Ubicación:** `apps/tenant/core/document_router.py`

**Rol:** Selecciona la función de materialización correcta según `dto["type"]` y la ejecuta en el contexto del tenant actual.

**Funciones principales:**

```python
def materialize_document(dto: Dict[str, Any], request_id: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
    """
    Materializa un documento desde DTO JSON canónico.
    
    Flujo:
    1. Extrae dto["type"] (tipo base: "invoice", "creditnote", "gasto", etc.)
    2. Selecciona materializador registrado
    3. Ejecuta en contexto del tenant actual
    4. Retorna resultado estructurado
    """
```

**Materializadores registrados:**

- `"invoice"` → `apps.tenant.facturas.services.guardar_factura_desde_dto`
- `"creditnote"` → `apps.tenant.facturas.services.guardar_nota_credito_desde_dto`
- `"gasto"` → `apps.tenant.gastos.services.materializar_gasto_desde_dto`
- `"inventario"` → `apps.tenant.inventario.services.materializar_inventario_desde_dto`

**Registro de nuevos materializadores:**

```python
from apps.tenant.core.document_router import register_materializer

def materializar_mi_tipo_desde_dto(dto: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    # Implementación
    return {"id": 123, "numero": "DOC001", "created": True}, 201

register_materializer("mi_tipo", materializar_mi_tipo_desde_dto)
```

### 7.2 Validadores por App (FASE 4-5)

**Ubicación:** `apps/services/document_ingest/validations/`

**Rol:** Validaciones específicas por tipo de documento antes de la materialización.

**Validadores implementados:**

- `FacturaValidator` → Valida CUFE, totales coherentes, fechas, parties
- `NotaCreditoValidator` → Valida CUDE, referencia obligatoria, totales
- `GastoValidator` → Valida total > 0, proveedor requerido, fecha válida
- `InventarioValidator` → Valida items, cantidades, unidades

**Ejecución:** Los validadores se ejecutan automáticamente en `ingest_service.py` antes de la materialización (FASE 5).

### 7.3 Integración en `ingest_service.py`

**Cambios realizados:**

1. **Import del router de dominio:**
```python
from apps.tenant.core.document_router import materialize_document
```

2. **Reemplazo de lógica específica por router:**
```python
# Antes (FASE 6): Lógica específica por tipo
if document_type.startswith("invoice"):
    from apps.tenant.facturas.services import guardar_factura_desde_dto
    persist_result, persist_code = guardar_factura_desde_dto(dto_dict, xml_text=None)
elif document_type.startswith("gasto"):
    # ... lógica específica para gastos
# ...

# Ahora (FASE 7): Router centralizado
persist_result, persist_code = materialize_document(dto_dict, request_id=request_id)
```

3. **Flujo completo:**
```
1. route(file_bytes) → Parsea documento a DTO
2. normalize(dto) → Normaliza y agrega metadatos
3. run_validations(dto) → Valida con validador específico (FASE 5)
4. preview → Retorna DTO sin persistir
5. materialize_document(dto) → Router de dominio (FASE 7)
   → Selecciona materializador según dto["type"]
   → Ejecuta en contexto del tenant actual
   → Retorna resultado estructurado
```

### 7.4 Manejo de Tipos Desconocidos

**Comportamiento:**

- Si `dto["type"]` no está registrado → Retorna `415` (tipo no soportado)
- Si `dto["type"]` es `None` o vacío → Retorna `400` (tipo faltante)
- Logging estructurado con `schema_name` y `request_id`

**Ejemplo de respuesta:**

```json
{
  "error": "type_not_supported",
  "message": "Tipo de documento 'tipo_desconocido' no soportado en dominio. Tipos disponibles: invoice, creditnote, gasto, inventario"
}
```

### 7.5 Observabilidad y Errores Deterministas

**Logging estructurado:**

- `document_router_materializing` → Inicio de materialización
- `document_router_materialized` → Materialización exitosa
- `document_router_materialization_failed` → Error de validación
- `document_router_materialization_error` → Error interno
- `document_router_type_not_supported` → Tipo no soportado

**Códigos de estado HTTP:**

- `200` → Documento actualizado (idempotencia)
- `201` → Documento creado
- `400` → Tipo faltante o DTO inválido
- `409` → Duplicado (idempotencia)
- `415` → Tipo no soportado
- `422` → Error de validación de negocio
- `500` → Error interno

**Formato de errores:**

```json
{
  "error": "validation_error",
  "message": "Mensaje descriptivo para el cliente"
}
```

Nunca se expone traza cruda al cliente.

## 📝 Servicios de Dominio

### Factura

**Ubicación:** `apps/tenant/facturas/services.py`

**Funciones:**
- `guardar_factura_desde_dto(dto, xml_text)` → Materializa factura
- `guardar_nota_credito_desde_dto(dto, xml_text)` → Materializa nota crédito

**Idempotencia:** Por CUFE/CUDE

### Gasto

**Ubicación:** `apps/tenant/gastos/services.py`

**Función:**
- `materializar_gasto_desde_dto(dto)` → Materializa gasto

**Idempotencia:** Por número de documento

### Inventario

**Ubicación:** `apps/tenant/inventario/services.py`

**Función:**
- `materializar_inventario_desde_dto(dto)` → Materializa inventario

**Idempotencia:** Por número de documento

## 🔄 Flujo Completo del Pipeline

```
1. Usuario sube documento (XML, PDF, Excel, CSV, TXT)
   ↓
2. ingest_service.ingest_document()
   ↓
3. route(file_bytes) → Parsea a DTO JSON unificado
   ↓
4. normalize(dto) → Agrega metadatos, asegura campo "type"
   ↓
5. run_validations(dto) → Valida con validador específico por app
   ↓
6. Si preview=True → Retorna DTO sin persistir
   ↓
7. Si preview=False → materialize_document(dto)
   ↓
8. Router de dominio selecciona materializador según dto["type"]
   ↓
9. Materializador ejecuta en contexto del tenant actual
   ↓
10. Persiste en modelo Django del dominio
```

## ✅ Criterios de "Hecho"

- [x] `dto["type"]` enruta a la función de materialización correcta
- [x] Operación dentro del esquema del tenant actual (django-tenants)
- [x] Validadores plug-in por type se ejecutan antes de persistir
- [x] Errores con códigos HTTP apropiados (409, 422, 415, etc.)
- [x] No hay parsing/normalización en `apps/tenant` (respeta SSoT)
- [x] Logging estructurado con `schema_name` y `request_id`
- [x] Documentación actualizada

## 🧪 Próximos Pasos (Tests)

**Unitarios de router:**
- Resuelve correctamente `invoice`, `creditnote`, `gasto`, `inventario`
- Rechaza tipos no registrados con `415`
- Maneja errores de validación con `422`

**De validadores plug-in:**
- Errores `422` esperados para cada tipo
- Mensajes claros y deterministas

**Multitenant:**
- `TenantTestCase` / `FastTenantTestCase`
- Verificar aislamiento por esquema
- Verificar contexto correcto del tenant

## 📚 Referencias

- **FASE 4-5:** Sistema de validadores plug-in
- **FASE 6:** Patrón de integración para otras apps
- **django-tenants:** Multi-tenancy por esquema
- **SSoT:** Single Source of Truth para parsing
