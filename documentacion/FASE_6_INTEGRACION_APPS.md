# FASE 6 — Integración de Otras Apps al Pipeline Universal

**Fecha:** 2026-02-10  
**Estado:** ✅ Patrón de Integración Documentado

## 🎯 Objetivo

Permitir que otras apps de negocio (`apps/tenant/gastos`, `apps/tenant/inventario`, `apps/tenant/ordenes_compra`, etc.) puedan usar el mismo pipeline universal de documentos (`document_parser` + `document_ingest`) con:

- ✔️ Su propio validador especializado
- ✔️ Su propia interpretación DTO → Dominio
- ✔️ Sus propias reglas de negocio
- ✔️ Sin duplicar parsers
- ✔️ Respetando SSoT y Domain-Driven Design

## 📋 Pasos para Integrar una Nueva App

### 1. Crear Validador Especializado

Crear archivo: `apps/services/document_ingest/validations/{app_name}.py`

```python
from typing import Dict, Any, Tuple, List, Optional
from .base import BaseValidator

class {AppName}Validator(BaseValidator):
    @property
    def document_type(self) -> str:
        return "{tipo_documento}"
    
    @property
    def app_name(self) -> str:
        return "{app_name}"
    
    def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
        # Validaciones específicas de la app
        missing_fields = []
        errors = []
        
        # Validar campos obligatorios
        required = ["totales", "fecha_emision", "emisor", "receptor"]
        for r in required:
            if r not in dto or dto[r] is None:
                missing_fields.append(r)
                errors.append(f"Campo obligatorio faltante: {r}")
        
        # Validaciones de negocio específicas
        # ...
        
        if missing_fields or errors:
            return False, "validation_error", missing_fields + errors
        
        return True, None, []
```

### 2. Registrar Validador

En `apps/services/document_ingest/validations/__init__.py`:

```python
from .{app_name} import {AppName}Validator

def _register_default_validators():
    # ... validadores existentes ...
    register_validator({AppName}Validator())
```

### 3. Crear Función de Materialización DTO → Dominio

Crear archivo: `apps/tenant/{app_name}/services.py`

```python
from typing import Dict, Any, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import {Modelo}

def materializar_{tipo}_desde_dto(dto: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Materializa un {Tipo} desde DTO JSON unificado.
    
    Mapeo DTO → Dominio:
    - dto["fecha_emision"] → {Modelo}.fecha
    - dto["emisor"]["nit"] → {Modelo}.proveedor_nit
    - dto["totales"]["total"] → {Modelo}.total
    - dto["numero"] → {Modelo}.numero
    
    Reglas:
    - Idempotencia: Previene duplicados usando número de documento
    - Transaccional: Todo o nada
    - Multi-tenant: Opera en el contexto del tenant actual
    
    Returns:
        Tupla (result, status_code):
        - result: {"id": int, "numero": str, "created": bool, ...}
        - status_code: 200 (actualizado), 201 (creado), 409 (duplicado), 422 (validación)
    """
    numero = dto.get("numero", "")
    if not numero:
        raise ValidationError({"error": "missing_number", "message": "Número no encontrado"})
    
    # Extraer datos del DTO
    fecha_emision = dto.get("fecha_emision", "")
    emisor = dto.get("emisor", {})
    proveedor_nit = emisor.get("nit", "")
    
    totales = dto.get("totales", {})
    total = Decimal(str(totales.get("total", "0.00")))
    
    # Validaciones de negocio
    if total <= 0:
        raise ValidationError({"error": "invalid_total", "message": "Total debe ser mayor a cero"})
    
    with transaction.atomic():
        # Idempotencia: verificar si ya existe
        try:
            obj = {Modelo}.objects.get(numero=numero)
            # Actualizar o retornar existente según reglas
            obj.fecha = fecha_emision
            obj.proveedor_nit = proveedor_nit
            obj.total = total
            obj.save()
            
            return {
                "id": obj.id,
                "numero": obj.numero,
                "created": False,
            }, 200
        except {Modelo}.DoesNotExist:
            # Crear nuevo
            obj = {Modelo}.objects.create(
                numero=numero,
                fecha=fecha_emision,
                proveedor_nit=proveedor_nit,
                total=total,
            )
            
            return {
                "id": obj.id,
                "numero": obj.numero,
                "created": True,
            }, 201
```

### 4. Integrar en `ingest_service.py`

En `apps/services/document_ingest/ingest_service.py`, agregar en la sección de materialización:

```python
elif document_type.startswith("{tipo}") or dto_dict.get("type") == "{tipo}":
    from apps.tenant.{app_name}.services import materializar_{tipo}_desde_dto
    try:
        persist_result, persist_code = materializar_{tipo}_desde_dto(dto_dict)
        
        if persist_code in (200, 201):
            return {
                "persisted": True,
                "dto": dto_dict,
                "sha256": sha256_hash,
                "metadata": metadata,
                "id": persist_result.get("id"),
                "numero": persist_result.get("numero"),
                "created": persist_result.get("created", False),
            }, persist_code
        else:
            return {
                "persisted": False,
                "dto": dto_dict,
                "sha256": sha256_hash,
                "metadata": metadata,
                "error": persist_result.get("error"),
                "message": persist_result.get("message"),
            }, persist_code
    except ValidationError as e:
        # Manejar errores de validación
        ...
```

## 📝 Ejemplo: Gastos

### Validador

✅ Creado: `apps/services/document_ingest/validations/gasto.py`

- Valida campos obligatorios: `totales`, `fecha_emision`, `emisor`, `receptor`
- Valida que el gasto no sea 0 o negativo
- Valida fechas y estructura de parties

### Materialización

✅ Creado: `apps/tenant/gastos/services.py`

- `materializar_gasto_desde_dto(dto)` → Mapea DTO a modelo `Gasto`
- Idempotencia por número de documento
- Transaccional con `transaction.atomic()`

### Integración

✅ Integrado en `ingest_service.py`

- Detecta `type: "gasto"` o `document_type.startswith("gasto")`
- Llama a `materializar_gasto_desde_dto()`
- Maneja errores y retorna respuestas estructuradas

## 📝 Ejemplo: Inventario

### Validador

✅ Creado: `apps/services/document_ingest/validations/inventario.py`

- Valida que tenga items (líneas)
- Valida cantidad > 0 en cada línea
- Valida fechas y estructura básica

### Materialización

✅ Creado: `apps/tenant/gastos/services.py` (función `materializar_inventario_desde_dto`)

- Placeholder listo para implementar cuando exista el modelo

## 🔄 Flujo Completo

```
1. Usuario sube documento (XML, PDF, Excel, CSV, TXT)
   ↓
2. ingest_service.ingest_document()
   ↓
3. route(file_bytes) → Parsea a DTO JSON unificado
   ↓
4. normalize(dto) → Agrega metadatos, asegura campo "type"
   ↓
5. run_validations(dto) → Valida con validador específico de la app
   ↓
6. Si preview=True → Retorna DTO sin persistir
   ↓
7. Si preview=False → materializar_{tipo}_desde_dto(dto)
   ↓
8. Persiste en modelo Django del dominio
```

## ✅ Checklist para Nueva App

- [ ] Crear validador en `apps/services/document_ingest/validations/{app_name}.py`
- [ ] Registrar validador en `validations/__init__.py`
- [ ] Crear función `materializar_{tipo}_desde_dto()` en `apps/tenant/{app_name}/services.py`
- [ ] Integrar en `ingest_service.py` (sección de materialización)
- [ ] Probar con documentos de ejemplo
- [ ] Documentar mapeo DTO → Dominio específico de la app

## 🎯 Principios Mantenidos

- **SSoT**: El pipeline produce solo DTO JSON
- **Domain-Driven Design**: Cada app tiene su propia interpretación DTO → Dominio
- **Sin duplicación**: Parsers compartidos, validadores y materialización por app
- **Extensibilidad**: Nuevas apps se agregan sin modificar el core del pipeline
- **Multi-tenant**: Todo opera en el contexto del tenant actual
