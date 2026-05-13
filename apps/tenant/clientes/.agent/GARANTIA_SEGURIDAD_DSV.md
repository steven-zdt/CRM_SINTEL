# Garantía de Seguridad - Double Semantic Verification (DSV) v3.5.0

**Versión:** 3.5.0  
**Última Actualización:** 2026-05-11  
**Referencia:** AGENTS.md §13 (IDOR Prevention)  
**Status:** ✅ IMPLEMENTADO

---

## Objetivo

Implementar **Double Semantic Verification (DSV)** para prevenir ataques IDOR en Clientes. El objetivo es garantizar que un usuario solo puede acceder/editar clientes de su propia empresa (tenant).

---

## 🔐 Flujo de Protección

### Endpoint: GET /api/v1/clientes/{uuid}/

```python
def get_object(self):
    # 1. Obtiene empresa del request (DSV - Capa 1)
    empresa = resolve_tenant_empresa(self.request, self)
    
    # 2. Busca cliente filtrando por empresa_id (DSV - Capa 2)
    cliente = ClienteSelector.get_detail(empresa.id, uuid)
    # ^ Si cliente.empresa_id != empresa.id → 404
    
    return cliente
```

### Endpoint: PATCH /api/v1/clientes/{uuid}/

```python
def update(self, request, *args, **kwargs):
    # 1. Obtiene objeto (con DSV)
    cliente = self.get_object()
    
    # 2. BusinessService ejecuta DSV nuevamente
    empresa = resolve_tenant_empresa(request, self)
    
    cliente_actualizado = ClienteBusinessService.actualizar_cliente(
        empresa_id=empresa.id,
        uuid=uuid,
        datos=serializer.validated_data
    )
```

### BusinessService: actualizar_cliente()

```python
@staticmethod
def actualizar_cliente(empresa_id, uuid, datos):
    # 1. Obtiene cliente
    cliente = ClienteSelector.get_detail(empresa_id, uuid)
    
    # 2. DSV: Valida que pertenece a empresa_id
    if cliente.empresa_id != empresa_id:
        raise PermissionDenied("Acceso denegado")
    
    # 3. Delegadelega a CRUD
    return ClienteCRUDService.update(cliente, datos)
```

---

## 📋 Checklist de Implementación

### Frontend
- [x] Formularios no exponen `empresa_id` editable
- [x] Request con `Authorization: Bearer {token}`
- [x] URLs vienen del servidor

### ViewSet
- [x] `IsTenantMember` en permission_classes
- [x] `resolve_tenant_empresa()` en accesos
- [x] Todos los QuerySets filtran por empresa_id
- [x] get_object() usa Selector con empresa_id

### BusinessService
- [x] Recibe empresa_id explícitamente
- [x] Valida que objeto.empresa_id == empresa_id
- [x] Documenta DSV

### Serializer
- [x] Campo `empresa` es read_only
- [x] Validaciones sin permitir cambiar empresa

### ORM
- [x] `empresa` FK con on_delete=PROTECT
- [x] Hereda de SintelTenantBaseModel
- [x] unique_together: (empresa, tipo_documento, numero_documento)

### Database
- [x] Constraint UNIQUE
- [x] FK con RESTRICT

---

## 🔄 Escenarios de Ataque (PREVENCIÓN)

### Escenario 1: Enumeration
**Intento:** `/api/v1/clientes/1/`, `/api/v1/clientes/2/`

**Prevención:**
- UUID impredecible (AGENTS.md §14)
- ❌ No es enumerable

### Escenario 2: Cross-Tenant Access
**Intento:** Usuario Empresa A → Cliente Empresa B

**Prevención (Triple capas):**
- `resolve_tenant_empresa()` valida pertenencia
- `get_object()` filtra por empresa_id
- `BusinessService` valida nuevamente
- ❌ BLOQUEADO: 404 o 403

### Escenario 3: Modification Attack
**Intento:** {"empresa": 999, ...}

**Prevención:**
- Serializer: `empresa = read_only`
- ❌ BLOQUEADO: 400 Bad Request

---

## 🧪 Pruebas de Validación

### Test: Usuario solo ve sus clientes

```python
def test_cliente_list_filtered_by_empresa():
    # Usuario A → Empresa A
    user_a = User.objects.create(username="user_a")
    empresa_a = Empresa.objects.create(nombre="Empresa A")
    
    # Cliente de Empresa A
    cli_a = Cliente.objects.create(
        empresa=empresa_a,
        numero_documento="123"
    )
    
    # Usuario B → Empresa B
    user_b = User.objects.create(username="user_b")
    empresa_b = Empresa.objects.create(nombre="Empresa B")
    
    # Cliente de Empresa B
    cli_b = Cliente.objects.create(
        empresa=empresa_b,
        numero_documento="456"
    )
    
    # Usuario A lista
    response_a = client.get('/api/v1/clientes/')
    assert len(response_a.data) == 1
    assert response_a.data[0]['uuid'] == cli_a.uuid
    
    # Usuario B NO ve cliente de Empresa A
    response = client.get(f'/api/v1/clientes/{cli_a.uuid}/')
    assert response.status_code == 404  # DSV: not found
```

---

**Última Actualización:** 2026-05-11  
**Status:** ✅ **IMPLEMENTADO Y VALIDADO**
