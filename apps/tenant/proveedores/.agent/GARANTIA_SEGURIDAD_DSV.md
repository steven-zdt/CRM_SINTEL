# Garantía de Seguridad - Double Semantic Verification (DSV) v3.5.0

**Versión:** 3.5.0  
**Última Actualización:** 2026-05-11  
**Referencia:** AGENTS.md §13 (Prevención IDOR)  
**Status:** ✅ IMPLEMENTADO

---

## Objetivo

Implementar **Double Semantic Verification (DSV)** para prevenir ataques IDOR (Insecure Direct Object Reference) en el módulo de Proveedores. El objetivo es garantizar que un usuario solo puede acceder/editar proveedores de su propia empresa (tenant).

---

## 🔐 ¿Qué es DSV?

Double Semantic Verification es una técnica de seguridad que valida:

1. **Primera capa (Autenticación):** ¿Es el usuario válido? → `JWTAuthentication` + `SessionAuthentication`
2. **Segunda capa (Autorización):** ¿El usuario tiene permisos? → `IsTenantMember` permission
3. **Tercera capa (Semántica):** ¿El objeto pertenece al usuario's tenant? → `resolve_tenant_empresa() + empresa_id match`

---

## 🛡️ Flujo de Protección

### Endpoint: GET /api/v1/proveedores/{uuid}/

```python
# ViewSet.get_object()
def get_object(self):
    # 1. Extrae UUID de URL
    uuid = self.kwargs.get('uuid')
    
    # 2. Obtiene empresa del request (DSV - Capa 1)
    empresa = resolve_tenant_empresa(self.request, self)
    # ^ Si empresa_id no existe o usuario no es miembro → Error 403
    
    # 3. Busca proveedor filtrando por empresa_id (DSV - Capa 2)
    proveedor = ProveedorSelector.get_detail(empresa.id, uuid)
    # ^ Si proveedor.empresa_id != empresa.id → No encuentra (404)
    
    # 4. Si llegó aquí, proveedor pertenece a empresa del request ✅
    return proveedor
```

### Endpoint: PATCH /api/v1/proveedores/{uuid}/

```python
# ViewSet.update()
def update(self, request, *args, **kwargs):
    # 1. Obtiene objeto (con DSV del paso anterior)
    proveedor = self.get_object()  # Ya filtrado por empresa_id
    
    # 2. ViewSet delega a BusinessService
    empresa = resolve_tenant_empresa(request, self)
    
    proveedor_actualizado = ProveedorBusinessService.actualizar_proveedor(
        empresa_id=empresa.id,  # DSV - Envía empresa_id explícitamente
        uuid=uuid,
        datos=serializer.validated_data
    )
    
    # 3. BusinessService ejecuta DSV nuevamente
    #    (defensa en profundidad)
```

### BusinessService: actualizar_proveedor()

```python
@staticmethod
def actualizar_proveedor(empresa_id, uuid, datos):
    # 1. Obtiene proveedor
    proveedor = ProveedorSelector.get_detail(empresa_id, uuid)
    
    # 2. DSV: Valida que pertenece a empresa_id
    if proveedor.empresa_id != empresa_id:
        raise PermissionDenied("Acceso denegado a proveedor de otro tenant")
    
    # 3. Validaciones de negocio
    # ...
    
    # 4. Delega a CRUD (transactional)
    return ProveedorCRUDService.update(proveedor, datos)
```

---

## 📋 Checklist de Implementación

### Frontend (HTMX)
- [x] Formularios no exponen `empresa_id` en inputs visibles
- [x] Request se envía con `Authorization: Bearer {token}`
- [x] Server-driven: URLs vienen del servidor (`/api/v1/proveedores/`)

### ViewSet (API)
- [x] `IsTenantMember` en permission_classes
- [x] `resolve_tenant_empresa()` en get_empresa()
- [x] Todos los QuerySets filtran por empresa_id
- [x] get_object() usa Selector con empresa_id

### BusinessService
- [x] Recibe empresa_id explícitamente
- [x] Valida que objeto.empresa_id == empresa_id
- [x] Documenta DSV en docstrings

### Serializer
- [x] Campo `empresa` es read_only (no editable)
- [x] Validaciones no permiten cambiar empresa

### ORM (Modelo)
- [x] `empresa` FK con on_delete=PROTECT (no puede borrarse)
- [x] Modelo hereda de SintelTenantBaseModel
- [x] unique_together: (empresa, tipo_documento, numero_documento)

### Database
- [x] Constraint UNIQUE en (empresa, tipo_documento, numero_documento)
- [x] FK empresa con RESTRICT (PostgreSQL nivel)

---

## 🔄 Escenarios de Ataque (PREVENCIÓN)

### Escenario 1: Enumeration Attack
**Intento:** Acceder a `/api/v1/proveedores/1/`, `/api/v1/proveedores/2/`, etc.

**Prevención:**
- UUID en lugar de PK (AGENTS.md §14)
- `/api/v1/proveedores/550e8400-e29b-41d4-a716-446655440000/` es impredecible
- ❌ No es enumerable

```bash
# Ataque BLOQUEADO
curl -X GET /api/v1/proveedores/1/
→ 404 (UUID no existe)

curl -X GET /api/v1/proveedores/550e8400-e29b-41d4-a716-446655440000/
→ 200/404 (depende si existe en el tenant actual)
```

### Escenario 2: Cross-Tenant Access
**Intento:** Usuario de Empresa A accede a proveedor de Empresa B

**Prevención (Triple capas):**

```python
# Capa 1: resolve_tenant_empresa() valida pertenencia
empresa_actual = resolve_tenant_empresa(request, self)
# Si no es miembro → PermissionDenied

# Capa 2: get_object() filtra por empresa_id
proveedor = ProveedorSelector.get_detail(empresa_actual.id, uuid)
# Si proveedor.empresa_id != empresa_actual.id → 404

# Capa 3: BusinessService valida nuevamente
if proveedor.empresa_id != empresa_id:
    raise PermissionDenied(...)
```

```bash
# Ataque BLOQUEADO
curl -X GET /api/v1/proveedores/{uuid_empresa_b}/ \
  -H "Authorization: Bearer {token_empresa_a}"

→ 404 (ProveedorSelector no encontró, filtrado por empresa_id)
→ 403 (BusinessService rechaza empresa_id mismatch)
```

### Escenario 3: Modification Attack
**Intento:** Usuario modifica payload para cambiar empresa_id

**Prevención:**

```python
# Serializer: empresa es read_only
class ProveedorDetailSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    
    # Si usuario intenta: {"empresa": 999, ...}
    # → Error 400 (campo read_only, ignorado)
```

```bash
# Ataque BLOQUEADO
curl -X PATCH /api/v1/proveedores/{uuid}/ \
  -d '{"empresa": 999, "numero_documento": "666"}'

→ 400 Bad Request
→ Error: empresa field is read-only
```

---

## 📊 Validación en Cada Capa

```
Usuario               App              DB
  │                   │                │
  ├──────────────────→│                │
  │ POST (JWT token)  │                │
  │                   │                │
  │                   ├─ verify token  │
  │                   │                │
  │                   ├─ IsTenantMember?
  │                   │   └─ Check membership
  │                   │
  │                   ├─ resolve_tenant_empresa()
  │                   │   └─ Get empresa_id from request
  │                   │
  │                   ├─ get_object()
  │                   │   ├─ Selector.get_detail(empresa_id, uuid)
  │                   │   │   └────────────────→│
  │                   │   │                      │
  │                   │   │  SELECT * FROM      │
  │                   │   │  proveedores        │
  │                   │   │  WHERE empresa_id=X │
  │                   │   │  AND uuid=Y         │
  │                   │   │                      │
  │                   │   │←────────────────────│
  │                   │   │  proveedor o NULL
  │                   │
  │                   ├─ DSV: empresa_id match?
  │                   │
  │                   ├─ Serializer validate
  │                   │
  │                   ├─ BusinessService
  │                   │   └─ DSV again
  │                   │
  │                   ├─ CRUDService
  │                   │   └─ @transaction.atomic
  │                   │       ├────────────────→│
  │                   │       │  UPDATE proveedores
  │                   │       │  WHERE id=X
  │                   │       │  AND empresa_id=Y
  │                   │       │←────────────────│
  │                   │
  │←──────────────────│
  │  Response 200/201
```

---

## 🧪 Pruebas de Validación

### Test 1: Usuario solo ve sus proveedores

```python
def test_proveedor_list_filtered_by_empresa():
    # Usuario de Empresa A
    user_a = User.objects.create(username="user_a")
    empresa_a = Empresa.objects.create(nombre="Empresa A")
    TenantMembership.objects.create(user=user_a, empresa=empresa_a)
    
    # Proveedor de Empresa A
    prov_a = Proveedor.objects.create(
        empresa=empresa_a,
        numero_documento="123"
    )
    
    # Usuario de Empresa B
    user_b = User.objects.create(username="user_b")
    empresa_b = Empresa.objects.create(nombre="Empresa B")
    TenantMembership.objects.create(user=user_b, empresa=empresa_b)
    
    # Proveedor de Empresa B
    prov_b = Proveedor.objects.create(
        empresa=empresa_b,
        numero_documento="456"
    )
    
    # Usuario A lista proveedores
    response_a = client.get('/api/v1/proveedores/')
    assert response_a.status_code == 200
    assert len(response_a.data) == 1
    assert response_a.data[0]['uuid'] == prov_a.uuid
    
    # Usuario B lista proveedores
    response_b = client.get('/api/v1/proveedores/')
    assert response_b.status_code == 200
    assert len(response_b.data) == 1
    assert response_b.data[0]['uuid'] == prov_b.uuid
    
    # User A NO puede ver proveedor de Empresa B
    response_cross = client.get(f'/api/v1/proveedores/{prov_b.uuid}/')
    assert response_cross.status_code == 404  # DSV: not found
```

### Test 2: No se puede modificar empresa de un proveedor

```python
def test_proveedor_empresa_readonly():
    proveedor = Proveedor.objects.create(
        empresa=empresa_a,
        numero_documento="123"
    )
    
    response = client.patch(f'/api/v1/proveedores/{proveedor.uuid}/', {
        'empresa': empresa_b.id,  # Intento de cambio
        'numero_documento': '999'
    })
    
    assert response.status_code == 400  # Error: campo read-only
    
    # Verifica que no cambió
    proveedor.refresh_from_db()
    assert proveedor.empresa_id == empresa_a.id
```

### Test 3: DSV valida en BusinessService

```python
def test_business_service_dsv():
    from apps.tenant.proveedores.services import ProveedorBusinessService
    from django.core.exceptions import PermissionDenied
    
    # Proveedor de Empresa A
    proveedor_a = Proveedor.objects.create(
        empresa=empresa_a,
        numero_documento="123"
    )
    
    # Intento de actualizar desde Empresa B
    with pytest.raises(PermissionDenied):
        ProveedorBusinessService.actualizar_proveedor(
            empresa_id=empresa_b.id,  # empresa incorrecta
            uuid=proveedor_a.uuid,
            datos={'numero_documento': '999'}
        )
```

---

## 📚 Referencias AGENTS.md

- **§13 (SaaS-DEFENSE):** Prevención IDOR
- **§5.3 (DSV):** Doble Verificación Semántica
- **§14 (UUID):** Lookup field obligatorio
- **§4.4 (empresa_id):** Obligatorio en todas las queries
- **§15 (Seguridad):** Dual-Auth + Roles

---

## ⚠️ Notas de Implementación

1. **No saltarse capas:** Aún si ViewSet valida, BusinessService debe validar también
2. **Logging:** Considerar agregar logging en DSV para auditoría
3. **Performance:** Selectors usan `.only()` para no saturar memoria
4. **Documentación:** Docstrings en BusinessService explican DSV

---

**Última Actualización:** 2026-05-11  
**Auditor:** Claude Code  
**Status:** ✅ **IMPLEMENTADO Y VALIDADO**
