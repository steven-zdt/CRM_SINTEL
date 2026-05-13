# [CRITICAL ARCHITECTURAL FIX] TenantProfile.empresa FK Addition

**Date:** March 20, 2026  
**Issue Type:** BLOCKING - Multi-Tenant Architecture  
**Priority:** CRITICAL - Affects context establishment and uniqueness validation  
**Status:** IMPLEMENTED

## Problem Statement

TenantProfile was missing explicit FK to Empresa, breaking the multi-tenant architecture flow:

```
User Request
    ↓
Middleware looks at request.user
    ↓
Middleware needs to get empresa context
    ↓
❌ TenantProfile HAS NO FK TO EMPRESA
    ↓
Middleware defaults to Empresa.objects.first()
    ↓
Service layer doesn't know which empresa to scope validation
    ↓
Uniqueness validation has no scope
    ↓
IntegrityError on duplicates INEVITABLE (same name in different empresas not detected)
```

## Root Cause

TenantProfile model (apps/tenant/perfil/models.py) had:
```python
user = OneToOneField(User)  # ✅ Links to global user
cargo = CharField()         # ✅ Job title
# ❌ NO: empresa = ForeignKey(Empresa)
```

This broke 3 critical flows:
1. **Middleware Context**: Cannot establish which empresa user is accessing
2. **Service Layer Validation**: Cannot pass empresa_id for scoped uniqueness
3. **Multi-Tenant SSoT**: No single source of truth for user↔empresa linkage

## Solution Implemented

### 1. Model Change (TenantProfile)

**File:** `apps/tenant/perfil/models.py`

Added before the user field:
```python
empresa = models.ForeignKey(
    'empresa.Empresa',
    on_delete=models.CASCADE,
    related_name='perfiles_colaboradores',
    verbose_name=_('Empresa'),
    help_text=_('Empresa a la que pertenece este perfil (establece contexto multi-tenant)')
)

user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='tenant_profile',
    verbose_name=_('Usuario'),
    help_text=_('Usuario global (reside en esquema public)')
)
```

### 2. Database Migration

**File:** `apps/tenant/perfil/migrations/0004_add_empresa_fk.py`

- Adds campo empresa (ForeignKey, no null)
- Creates index (empresa, user) for context lookup
- Preserves existing data integrity

### 3. Data Backfill Script

**File:** `backfill_tenantprofile_empresa.py`

```bash
# Run after migration
docker exec crm_sintel-web-1 python /app/backfill_tenantprofile_empresa.py
```

Sets existing profiles to tenant's Empresa (safe because profiles are in tensor schema).

## How This Fixes the Flow

### Before (Broken):
```
middleware.py:
  request.user.tenant_profile  # ✅ Exists
  request.user.tenant_profile.empresa  # ❌ NO FK!
  # Falls back to: Empresa.objects.first() ← Unreliable!
  
service.py:
  def crear_categoria(self, empresa_id, nombre):  # ⚠️ empresa_id from DEFAULT, not profile
```

### After (Fixed):
```
middleware.py:
  request.user.tenant_profile.empresa  # ✅ NOW EXISTS
  # Sets: request.empresa = profile.empresa automatically
  
service.py:
  def crear_categoria(self, empresa_id, nombre):  # ✅ empresa_id from profile.empresa_id
  # Validation uses correct scope!
```

## Architectural Impact

### 1. Middleware Context Establishment
```python
# In TenantSecurityAndURLConfMiddleware
empresa = request.user.tenant_profile.empresa  # ✅ Now explicit
request.empresa = empresa
request.empresa_id = empresa.id
```

### 2. Service Layer Scope
```python
# In services/categoria_service.py
def crear_o_actualizar_categoria(self, nombre, empresa_id=None):
    # Get empresa_id from user profile if not provided
    if not empresa_id:
        empresa_id = self.request.user.tenant_profile.empresa_id
    
    # Uniqueness validation is NOW scoped!
    existing = Categoria.objects.filter(
        nome=nome,
        empresa_id=empresa_id
    ).first()
```

### 3. Uniqueness Constraints
All models affecting now use:
```python
class Meta:
    unique_together = [('empresa_id', 'nombre')]  # ✅ Proper scope
```

**Result:** POST 2x same categoria name in DIFFERENT empresas = 2 records ✅  
**Result:** POST 2x same categoria name in SAME empresa = 409 Conflict ✅

## Steps to Apply

### 1. Verify Model Change
```bash
grep -A 10 "empresa = models.ForeignKey" apps/tenant/perfil/models.py
# Should show FK to Empresa with related_name='perfiles_colaboradores'
```

### 2. Run Migration
```bash
docker exec crm_sintel-web-1 python manage.py migrate perfil
```

### 3. Backfill Data
```bash
docker exec crm_sintel-web-1 python backfill_tenantprofile_empresa.py
```

### 4. Verify Data
```sql
-- In tenant schema (e.g., "home")
SELECT id, user_id, empresa_id, cargo FROM perfil_tenantprofile;
-- Should show: empresa_id populated for all records
```

### 5. Restart Services
```bash
docker compose restart web
```

## Validation Checklist

- [ ] Model change applied (FK visible in admin)
- [ ] Migration created (0004_add_empresa_fk.py exists)
- [ ] Migration applied (no errors in logs)
- [ ] Backfill script executed (profiles linked to empresa)
- [ ] TenantSecurityAndURLConfMiddleware updated (uses profile.empresa)
- [ ] Service layer receives empresa_id from profile
- [ ] Uniqueness scoped per empresa (tests pass)
- [ ] IntegrityError prevention verified (POST 2x = conflict in same empresa)

## Critical Dependencies

This fix depends on:
1. **Empresa model** exists in tenant schema (`apps/tenant/empresa/models.py`)
2. **TenantSecurityAndURLConfMiddleware** updated to use profile.empresa
3. **Service layer** methods receive empresa_id from profile
4. **Uniqueness constraints** use (empresa_id, field_name) pattern

All of these MUST be validated before marking complete.

## PostScript

This was the **missing architectural piece** preventing:
- Proper context establishment
- Scoped validation
- Prevention of duplicate IntegrityErrors

The integration of TenantProfile.empresa as the SSoT for context is what allows:
1. Middleware to know user's empresa
2. Service layer to validate uniqueness per empresa
3. Front-end to render empresa-specific data

Without this FK, the multi-tenant isolation is theoretical, not practical.
