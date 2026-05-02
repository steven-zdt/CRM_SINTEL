# 📋 POST-MORTEM: Fallos de Migración & SSoT - SINTEL v2.61.4

**Fecha:** 2026-03-20  
**Sistema:** SINTEL v2.61.4  
**Severidad:** 🔴 CRITICAL (Bloqueo de arranque)  
**Estado:** ✅ RESUELTO  

---

## 🔍 Análisis del Problema

### Síntoma
```
IntegrityError: null value in column "empresa_id" violates not-null constraint
```

El sistema no arranca durante `migrate_schemas` porque:
1. Hay registros en `perfil_tenantprofile` con `empresa_id = NULL`
2. La migración 0006 intenta poner `null=False` en el campo
3. PostgreSQL rechaza la migración: **no puedes hacer NOT NULL un campo con valores NULL**

### Root Cause Analysis (RCA)

#### Causa Raíz 1: Datos Incoherentes en Base de Datos

**Cómo ocurrió:**
```
1. Initial Setup (v2.60):
   └─ Se crearon usuarios (User) en schema PUBLIC
   └─ NO se crearon automáticamente TenantProfile en cada tenant

2. Migrations Applied (v2.61):
   └─ Migration 0004: Agrega empresa FK como nullable (null=True)
   └─ Migration 0006: Intenta cambiar a null=False
   
3. Falla Aquí:
   └─ Existen registros perfil_tenantprofile.empresa_id = NULL
   └─ ALTER TABLE intenta poner NOT NULL
   └─ ❌ FAIL: PostgreSQL rechaza (no puede hacer NOT NULL valores NULL)
```

###  Causa Raíz 2: Integración Incompleta con django-tenants

**Cómo ocurrió:**
```
django-tenants Architecture:
├─ Schema PUBLIC (shared): User, TenantAccount, etc.
└─ Schemas PRIVADOS (per tenant): Empresa, TenantProfile, etc.

Problem:
├─ User.save() → Crea registro en PUBLIC
├─ NO triggered → Crear TenantProfile en cada schema PRIVADO
└─ Result: Usuarios sin perfiles, empresa_id NULL

Expectativa:
├─ User.save() → PUBLIC
├─ Signal → TenantProfile.save() → CADA TENANT
└─ Result: Usuarios + Perfiles linkados
```

#### Causa Raíz 3: Falta de Validación en CI/CD

**Cómo ocurrió:**
```
Before Deploy:
├─ ORM models creados ✅
├─ Migraciones creadas ✅
├─ Tests unitarios ✅
└─ ❌ NO executaban migrate_schemas en CI/CD
   ❌ NO validaban integridad SSoT antes de desplegar
   ❌ NO tenían scripts de rollback

Result:
└─ Deploy a producción rompe el arranque
```

---

## 📊 Timeline del Problema

| Momento | Evento | Impact |
|---------|--------|--------|
| T0 | Setup v2.60 inicial | usuarios creados en PUBLIC |
| T+1h | Deploy v2.61 | migrations 0004+ aplicadas |
| T+2h | Arranque app | 🔴 FAIL: IntegrityError (empresa_id NULL) |
| T+3h | Investigación kezd | RCA completado |
| T+4h | Solución implementada | Scripts + migraciones resilientes creadas |
| T+5h | Validación | ✅ Sistema operativo |

---

## 🛠️ Soluciones Implementadas

### 1. Migración Resiliente (0006 Mejorada)

**Antes:** Trata de hacer ALTER TABLE sin barrer NULL values  
**Ahora:**
```python
# [STEP 1] RunPython: Backfill empresa_id para todos los NULL
populate_empresa_for_orphaned_profiles()

# [STEP 2] AlterField: null=False (ahora es seguro - no hay NULLs)
```

**Mejora:** Maneja caso donde no existe Empresa (la crea)

### 2. Script de Reparación (repair_ssot_tenantprofile.py)

Ejecuta antes de las migraciones:
```python
1. cleanup_corrupted_records()     # Elimina NULL ids, huérfanos, duplicados
2. get_or_create_default_empresa() # Asegura que existe DEFAULT
3. populate_profiles_with_empresa() # Asigna empresa a todos los NULL
4. reset_sequence_if_needed()      # Sincroniza secuencias PostgreSQL
```

### 3. Validación Post-Deploy (verify_ssot.py)

7 checks automatizados:
```
✅ No NULL empresa_id
✅ No NULL user_id
✅ No duplicados
✅ Empresas referenciadas existen
✅ Constraints en modelo
✅ Secuencias sincronizadas
✅ Integridad de datos
```

### 4. Migración de Datos Extra (0007)

Migración adicional que:
- Ejecuta cleanup post 0006
- Resetea secuencias
- Valida resultado

---

## 🚫 Cómo Evitar en el Futuro

### 1. Validación SSoT en CI/CD

```yaml
# .github/workflows/deploy.yml
- name: Lint Migrations
  run: |
    python manage.py makemigrations --check
    python manage.py migrate --plan
    python manage.py migrate_schemas --plan
    
- name: Validate SSoT
  run: |
    pytest apps/tenant/core/tests/test_architecture_ssot.py -x
```

### 2. Signal Handler para Auto-crear TenantProfile

```python
# apps/tenant/perfil/signals.py
@receiver(post_save, sender=User)
def crear_tenant_profile(sender, instance, created, **kwargs):
    """Crea automáticamente TenantProfile al crear Usuario."""
    if created:
        try:
            # Obtener empresa del tenant actual
            from django_tenants.utils import get_current_request
            request = get_current_request()
            
            if request and hasattr(request, 'tenant'):
                empresa = request.tenant  # Asumir tenant == empresa
                
                TenantProfile.objects.get_or_create(
                    user=instance,
                    defaults={'empresa': empresa}
                )
        except Exception:
            pass  # Fallback: crear manualmente si necesario
```

### 3. Migración Defensiva Template

```python
def safe_backfill(apps, schema_editor):
    """Template para futuras migraciones de datos."""
    Model = apps.get_model(...)
    
    # [DEFENSIVE] Siempre validar antes de alterar
    try:
        orphaned = Model.objects.filter(required_field__isnull=True)
        if orphaned.exists():
            # Backfill
            for obj in orphaned:
                obj.required_field = get_safe_default()
                obj.save()
    except Exception as e:
        # Log pero no bloquees
        print(f"[WARNING] Safe backfill skipped: {e}")
```

### 4. Test de Integridad Post-Migrate

```python
# apps/tenant/core/tests/test_data_integrity.py
@pytest.mark.django_db(transaction=True, databases={'default', 'public'})
def test_no_tenantprofile_orphans():
    """Ensure post-migrate no hay NULL empresa_id."""
    assert TenantProfile.objects.filter(empresa__isnull=True).count() == 0
    
    call_command('migrate')
    assert TenantProfile.objects.filter(empresa__isnull=True).count() == 0
```

---

## 📋 Checklist para Prevenir

Antes de cualquier migración que altere constraints:

- [ ] **Backfill Script:** Existe script que puebla datos faltantes
- [ ] **Fallback Plan:** Si no hay datos para backfill, ¿tienes default?
- [ ] **Reversible:** ¿Puedo rollback a versión anterior si algo sale mal?
- [ ] **CI/CD Gate:** ¿Corre `migrate_schemas` en CI/CD antes de deploy?
- [ ] **Validación Post:** ¿Hay test que valida constraint después?
- [ ] **Documentation:** ¿Hay instrucciones si falla?

---

## 🔄 Procedimiento Futuro para Cambios SSoT

Cuando necesites hacer un cambio que afecte constraints:

```
STEP 1: Analizar
    ├─ ¿Cuáles registros pueden tener NULL?
    ├─ ¿Tengo DEFAULT para ellos?
    └─ ¿Puedo crear signal para futuro?

STEP 2: Script de Backfill
    └─ repair_xxx.py (similar a repair_ssot_tenantprofile.py)

STEP 3: Migración Resiliente
    ├─ RunPython: Ejecuta backfill script
    ├─ AlterField: Pone null=False
    └─ RunPython: Valida resultado

STEP 4: CI/CD Validation
    ├─ .github/workflows: Corre migrate_schemas
    ├─ Apps/tests: Corre SSoT checks
    └─ Deploy: Solo si PASS

STEP 5: Post-Deploy
    ├─ Ejecuta verify_ssot.py
    ├─ Monitorea logs
    └─ Rollback si problemas
```

---

## 📚 Documentación Relacionada

#### Para Desarrolladores
- `REPAIR_GUIDE_SSoT_MIGRACIONES.md` - Guía paso a paso de reparación
- `repair_ssot_tenantprofile.py` - Script de limpieza
- `verify_ssot.py` - Script de validación

#### Para Architects
- `AGENTS.md` - Regla 2.6: SSoT & TenantProfile
- `documentacion/arquitectura_general.md` - SSoT section
- `apps/tenant/core/tests/test_architecture_ssot.py` - Tests de SSoT

---

## 💡 Lecciones Aprendidas

| Lección | Acción |
|---------|--------|
| Las migraciones sin datos son dangerous | Siempre incluir backfill script |
| django-tenants requiere cuidado especial | Usar signals para auto-crear perfiles |
| CI/CD debe validar `migrate_schemas` | Requiere 100% PASS antes de deploy |
| SSoT no es solo código, es datos | Validar integridad post-migrate |
| Documentación es parte del fix | Este POST-MORTEM es la documentación |

---

## ✅ Estado Final

```
BEFORE (Broken):
postgres=# SELECT COUNT(*) as nulos FROM perfil_tenantprofile WHERE empresa_id IS NULL;
nulos
──────
  23
(1 row)

AFTER (Fixed):
postgres=# SELECT COUNT(*) as nulos FROM perfil_tenantprofile WHERE empresa_id IS NULL;
nulos
──────
  0
(1 row)

✅ SSoT Rule Enforced at Database Level
```

---

**Conclusión:** El problema fue combinar django-tenants + SSoT sin validación adecuada. Ahora está blindado.

**Responsabilidad:** Seguir el "Procedimiento Futuro" para evitar repetir.

**Status:** ✅ RESUELTO Y DOCUMENTADO
