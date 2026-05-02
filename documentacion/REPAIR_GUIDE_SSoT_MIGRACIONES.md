# 🔧 GUÍA DE REPARACIÓN: Migraciones & SSoT - SINTEL v2.61.4

**Problema:** La tabla `perfil_tenantprofile` tiene registros sin `empresa_id`, impidiendo hacer null=False  
**Solución:** Migración resiliente + script de limpieza + validación  
**Tiempo estimado:** 10-15 minutos

---

## 🚨 DIAGNÓSTICO RÁPIDO

**Si ves este error:**
```
null value in column "id" violates not-null constraint
```

O este:
```
IntegrityError: null value in column "empresa_id" violates not-null constraint
```

**Entonces necesitas ejecutar ESTA GUÍA ✅**

---

## 📋 PASO 1: Preparación

### 1.1 Verificar que Docker está corriendo

```bash
docker compose ps
# Debe mostrar crm_sintel-web-1 como "Up"
```

Si no está corriendo:
```bash
docker compose up -d
docker wait --time 30  # Esperar 30 segundos
```

### 1.2 Ver los logs actuales

```bash
docker logs crm_sintel-web-1 | tail -100
# Busca líneas con "IntegrityError" o "null value"
```

---

## 🧹 PASO 2: Ejecutar Script de Limpieza

Este script:
- ✅ Borra registros corruptos (id NULL)
- ✅ Elimina perfiles huérfanos (usuario no existe)
- ✅ Merge de perfiles duplicados
- ✅ Crea Empresa DEFAULT si no existe
- ✅ Puebla todos los TenantProfile con empresa_id
- ✅ Resetea secuencias de PostgreSQL

### 2.1 En Docker (Recomendado)

```bash
# Copiar script al contenedor
docker cp repair_ssot_tenantprofile.py crm_sintel-web-1:/app/

# Ejecutar
docker exec crm_sintel-web-1 python /app/repair_ssot_tenantprofile.py
```

**Esperado:**
```
==============================================================================
  SSoT RESILIENT REPAIR SCRIPT - TenantProfile & Empresa
==============================================================================

[STEP 1] CLEANING CORRUPTED RECORDS
==============================================================================
[CLEAN 1A] ✅ No records with NULL id found
[CLEAN 1B] ✅ No orphaned profiles found
...

[STEP 5] VALIDATING FINAL STATE
==============================================================================
[OK] ✅ All profiles have empresa_id set
[SUCCESS] ✅ REPAIR COMPLETED SUCCESSFULLY
```

### 2.2 En Local (Alternativa)

```bash
cd c:\Users\Administrator\Documents\crm_sintel

# Activar venv si necesario
. venv\Scripts\Activate.ps1

# Ejecutar
python repair_ssot_tenantprofile.py
```

---

## 🔄 PASO 3: Ejecutar Migraciones

### 3.1 Aplicar migraciones a los esquemas

```bash
# Migración estándar (esquema público)
docker exec crm_sintel-web-1 python manage.py migrate

# Migraciones a esquemas de tenants
docker exec crm_sintel-web-1 python manage.py migrate_schemas
```

**Esperado:**
```
Operations to perform:
  Apply all migrations for: ...

Running migrations:
  Applying perfil.0004_add_empresa_fk... OK
  Applying perfil.0005_remove_tenantprofile_perfil_tprof_empresa_user_idx... OK
  Applying perfil.0006_alter_tenantprofile_empresa_required... OK
  Applying perfil.0007_data_migration_robust_empresa_population... OK
```

Si ves errores:
```bash
# Ver detalle del error
docker logs crm_sintel-web-1 | tail -50

# Si la migración 0007 falla, continúa - el script 2.1 ya hizo el trabajo
```

### 3.2 Verificar integridad

```bash
# Copiar script de verificación
docker cp verify_ssot.py crm_sintel-web-1:/app/

# Ejecutar
docker exec crm_sintel-web-1 python /app/verify_ssot.py
```

**Esperado:**
```
==============================================================================
  SSoT COMPLIANCE CHECK - TenantProfile & Empresa
==============================================================================

[CHECK 1] TenantProfile.empresa_id (NOT NULL constraint)
✅ PASS: All X profiles have empresa_id set

[CHECK 2] TenantProfile.user_id (NOT NULL constraint)
✅ PASS: All X profiles have user_id set

[CHECK 3] No Duplicate Profiles (unique user_id)
✅ PASS: No duplicate profiles found

...

  SUMMARY
==============================================================================
  ✅ PASS: TenantProfile.empresa NOT NULL
  ✅ PASS: TenantProfile.user_id NOT NULL
  ✅ PASS: No Duplicate Profiles
  ✅ PASS: Referenced Empresas Exist
  ✅ PASS: Field Constraints
  ✅ PASS: Sequence Synchronization
  ✅ PASS: Data Integrity

  Total: 7/7 checks passed

🎉 ALL CHECKS PASSED - System is SSoT compliant!
```

---

## 🚀 PASO 4: Iniciar la Aplicación

### 4.1 Detener y reiniciar servicios

```bash
# Detener contenedor web
docker compose stop web

# Reiniciar
docker compose up -d web

# Esperar a que inicie
sleep 10
docker logs crm_sintel-web-1 | tail -30
```

**Busca:**
```
Starting development server at http://0.0.0.0:8000/
```

### 4.2 Probar acceso

```bash
# Probar endpoint
curl -X GET http://localhost:8000/api/health/ -v

# Esperado: 200 OK
```

---

## 📊 PASO 5: Validación Final

### 5.1 Ejecutar tests de arquitectura

```bash
docker exec crm_sintel-web-1 python -m pytest \
  apps/tenant/core/tests/test_architecture_ssot.py -xvs
```

**Esperado:**
```
test_all_tenant_models_have_empresa_fk PASSED
test_empresa_fk_field_constraints PASSED
test_base_model_consistency_check PASSED

=================== 3 passed in 5.86s ====================
```

### 5.2 Chequeo SQL directo

```bash
# Conectar a PostgreSQL en Docker
docker exec -it crm_sintel-postgres-1 psql -U postgres -d sintel

# En el prompt de psql:
SELECT COUNT(*) as total FROM perfil_tenantprofile;
SELECT COUNT(*) as sin_empresa FROM perfil_tenantprofile WHERE empresa_id IS NULL;
SELECT COUNT(*) as sin_user FROM perfil_tenantprofile WHERE user_id IS NULL;

# Esperado:
# total | <cualquier número>
# sin_empresa | 0
# sin_user | 0

# Salir con: \q
```

---

## ✅ PASO 6: Confirmación de Éxito

Cuando veas:

```
✅ PASO 2: Script de limpieza ejecutado sin errores
✅ PASO 3: Migraciones aplicadas (0004, 0005, 0006, 0007)
✅ PASO 4: Aplicación iniciada sin IntegrityError
✅ PASO 5: Tests de arquitectura PASSED
✅ PASO 6: Queries SQL muestran 0 registros nulos
```

**ENTONCES: ✅ REPARACIÓN COMPLETADA**

---

## 🆘 TROUBLESHOOTING

### Problema: Script de limpieza toma mucho tiempo

**Causa:** Muchos registros en la tabla  
**Solución:** Esperar (puede tomar varios minutos con 10k+ registros)

```bash
# Ver progreso en otro terminal
docker logs crm_sintel-web-1 -f
```

### Problema: Migración 0006 falla con "column already exists"

**Causa:** El Script 2.1 ya limpió los datos  
**Solución:**

```bash
# Marcar 0006 como aplicada sin ejecutarla
docker exec crm_sintel-web-1 python manage.py migrate perfil 0005
docker exec crm_sintel-web-1 python manage.py migrate_schemas --schema=public perfil 0005
```

Luego continúa con Paso 3.2

### Problema: PostgreSQL "relation does not exist"

**Causa:** Esquema desincronizado  
**Solución:**

```bash
# Resetear migraciones y la tabla
docker exec crm_sintel-web-1 python manage.py migrate perfil zero
docker exec crm_sintel-web-1 python manage.py migrate_schemas --schema=home perfil zero

# Luego ir a Paso 3
```

### Problema: No hay Empresa en la base de datos

**Verificar:**
```bash
docker exec -it crm_sintel-postgres-1 psql -U postgres -d sintel

# En psql:
SELECT * FROM empresa_empresa LIMIT 5;
```

**Si está vacío:**
```bash
# Crear una Empresa default
INSERT INTO empresa_empresa (
  id, razon_social, numero_id, tipo_id
) VALUES (
  1, 'SINTEL Default', '0000000000', 'NIT'
);
```

---

## 🔄 Resumen Completo (TL;DR)

```bash
# 1. Copiar scripts
docker cp repair_ssot_tenantprofile.py crm_sintel-web-1:/app/
docker cp verify_ssot.py crm_sintel-web-1:/app/

# 2. Ejecutar limpieza
docker exec crm_sintel-web-1 python /app/repair_ssot_tenantprofile.py

# 3. Ejecutar migraciones
docker exec crm_sintel-web-1 python manage.py migrate
docker exec crm_sintel-web-1 python manage.py migrate_schemas

# 4. Verificar
docker exec crm_sintel-web-1 python /app/verify_ssot.py

# 5. Reiniciar
docker compose restart web

# 6. Validar tests
docker exec crm_sintel-web-1 python -m pytest \
  apps/tenant/core/tests/test_architecture_ssot.py -x

# ✅ LISTO
```

---

## 📚 Archivos Relacionados

| Archivo | Propósito |
|---------|-----------|
| `repair_ssot_tenantprofile.py` | Script principal de limpieza |
| `verify_ssot.py` | Script de validación |
| `apps/tenant/perfil/migrations/0007_*.py` | Migración de datos resiliente |
| `AGENTS.md` - Regla 2.6 | Documentación SSoT |

---

## ⏱️ Timeline Esperado

```
Paso 1 (Prep):         1 min
Paso 2 (Limpieza):     2-5 min (depende del tamaño)
Paso 3 (Migraciones):  2-3 min
Paso 4 (Restart):      2 min
Paso 5 (Validación):   1 min
────────────────────────────
Total:                10-15 min
```

---

**Status:** ✅ LISTO PARA EJECUTAR  
**Responsabilidad:** Solo ejecutar en orden - el sistema maneja el resto  
**Soporte:** Ver sección TROUBLESHOOTING si hay problemas

🚀 **Comienza por PASO 1 arriba**
