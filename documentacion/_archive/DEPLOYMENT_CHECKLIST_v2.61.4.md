# ✅ PRE-DEPLOYMENT CHECKLIST v2.61.4

Print this and use as deployment checklist.

---

## ✅ FASE 1: VERIFICACIÓN PRE-INICIA (5 min)

- [ ] **Docker running:** `docker ps` shows crm_sintel-web-1 RUNNING
- [ ] **Workspace clean:** No uncommitted changes (git status)
- [ ] **Backup DB:** Database backed up (if production)
- [ ] **Maintenance window:** Team notified of 15-min maintenance

---

## ✅ FASE 2: COPIAR ARCHIVOS A DOCKER (2 min)

```bash
docker cp repair_ssot_tenantprofile.py crm_sintel-web-1:/app/
docker cp verify_ssot.py crm_sintel-web-1:/app/
```

- [ ] **repair_ssot_tenantprofile.py copied** (no errors in output)
- [ ] **verify_ssot.py copied** (no errors in output)
- [ ] **Verify files exist:** `docker exec crm_sintel-web-1 ls -la /app/*.py`

---

## ✅ FASE 3: EJECUTAR REPAIR (2-5 min)

```bash
docker exec crm_sintel-web-1 python repair_ssot_tenantprofile.py
```

**ESPERADO:** Salida similar a esto:
```
[REPAIR] Phase 1: Cleaning corrupted records...
[REPAIR] Phase 2: Ensuring default Empresa exists...
[REPAIR] Phase 3: Populating NULL empresa_id...
[REPAIR] Phase 4: Resetting sequences...
[REPAIR] Validation... 0 NULL empresa_id ✅
[SUCCESS] REPAIR COMPLETED SUCCESSFULLY ✅
```

- [ ] **Script completa sin error** (exit code 0)
- [ ] **[SUCCESS] ✅ message appears**
- [ ] **NO errors o "ERROR" en output**
- [ ] **NO database locks** (script rápido 2-5 min)

---

## ✅ FASE 4: EJECUTAR MIGRACIONES (1-2 min)

```bash
docker exec crm_sintel-web-1 python manage.py migrate
docker exec crm_sintel-web-1 python manage.py migrate_schemas
```

**ESPERADO:**
```
Operations to perform:
  ...
  Applying tenant.perfil.0006_alter_tenantprofile_empresa_required... OK
  Applying tenant.perfil.0007_data_migration_robust_empresa_population... OK
  ...
```

- [ ] **migrate completa sin error**
- [ ] **0006 migration: OK**
- [ ] **0007 migration: OK**
- [ ] **NO IntegrityError o errors**
- [ ] **NO "relation ... does not exist"**

---

## ✅ FASE 5: EJECUTAR VALIDACIÓN (1 min)

```bash
docker exec crm_sintel-web-1 python verify_ssot.py
```

**ESPERADO:**
```
Check 1/7: No NULL empresa_id... PASSED ✅
Check 2/7: No NULL user_id... PASSED ✅
Check 3/7: No duplicate profiles... PASSED ✅
Check 4/7: Referenced empresas exist... PASSED ✅
Check 5/7: Model field constraints... PASSED ✅
Check 6/7: PostgreSQL sequences... PASSED ✅
Check 7/7: Overall data integrity... PASSED ✅

RESULT: 7/7 checks PASSED ✅
```

- [ ] **All 7 checks PASSED**
- [ ] **RESULT line shows 7/7**
- [ ] **NO "FAILED" anywhere**
- [ ] **Execution time < 30 seconds**

---

## ✅ FASE 6: REINICIAR SERVICIOS (30 seg)

```bash
docker compose restart web
docker exec crm_sintel-web-1 python manage.py collectstatic --noinput
```

**ESPERADO:** Web service reinicia en ~30 segundos

- [ ] **docker compose restart completa sin error**
- [ ] **collectstatic completa**
- [ ] **Web service vuelve a RUNNING**

---

## ✅ FASE 7: VERIFICAR LOGS (2 min)

```bash
# Ver últimos 50 líneas de logs
docker logs crm_sintel-web-1 --tail 50

# Buscar specific errors
docker logs crm_sintel-web-1 | grep -i "error"
docker logs crm_sintel-web-1 | grep -i "relation.*does not exist"
docker logs crm_sintel-web-1 | grep -i "404\|500"
```

**ESPERADO:** Logs limpios, sin errores relacionados a:
- ❌ "relation perfil_tenantprofile does not exist"
- ❌ "IntegrityError"
- ❌ "ProgrammingError"
- ❌ "500 Internal Server Error"

- [ ] **No errors encontrados**
- [ ] **Logs muestran startup limpio**
- [ ] **Application running normal**

---

## ✅ FASE 8: SMOKE TESTING (3 min)

### Test 1: Acceso a ruta pública
```bash
curl -s http://localhost:8000/ | head -20
```
- [ ] **Returns HTML** (200 OK, no 500 error)

### Test 2: Acceso a ruta privada sin login
```bash
curl -s http://localhost:8000/dashboard/
```
- [ ] **Redirects to /login/** (302 redirect)

### Test 3: Middleware función
```bash
docker exec crm_sintel-web-1 python manage.py shell
>>> from apps.public.tenants.models import TenantMembership
>>> TenantMembership.objects.count()  # Should show number > 0
>>> 
```
- [ ] **Can import models without error**
- [ ] **TenantMembership query works**

### Test 4: TenantProfile no tiene NULL empresa_id
```bash
docker exec crm_sintel-web-1 python manage.py shell
>>> from apps.tenant.perfil.models import TenantProfile
>>> TenantProfile.objects.filter(empresa_id__isnull=True).count()
0  # Should be ZERO
>>>
```
- [ ] **Result is 0** (no NULL empresa_id)

---

## ✅ FASE 9: COMPARACIÓN ANTES/DESPUÉS

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| Migration status | ❌ FAILED | ✅ PASSED |
| NULL empresa_id | ❌ Some | ✅ Zero |
| verify_ssot.py | ❌ N/A | ✅ 7/7 PASSED |
| relation error | ❌ Possible | ✅ Fixed (defenses) |
| Logs | ❌ Errors | ✅ Clean |
| App startup | ❌ IntegrityError | ✅ Success |

- [ ] **Verify all BEFORE → DESPUÉS changes completed**

---

## 🚨 IF SOMETHING GOES WRONG

### Scenario A: Repair script fails
```
❌ PROBLEM: repair_ssot_tenantprofile.py shows ERROR
✅ SOLUTION:
  1. Check docker logs for details
  2. Restore database from backup
  3. Re-run repair script
  4. Check REPAIR_GUIDE.md troubleshooting section
```

### Scenario B: Migration fails
```
❌ PROBLEM: python manage.py migrate shows IntegrityError
✅ SOLUTION:
  1. Rollback: python manage.py migrate tenant.perfil 0005
  2. Re-run repair: python repair_ssot_tenantprofile.py
  3. Re-run migrations: python manage.py migrate
  4. Check REPAIR_GUIDE.md for specific error
```

### Scenario C: verify_ssot fails
```
❌ PROBLEM: verify_ssot.py shows some checks FAILED
✅ SOLUTION:
  1. Note which checks failed
  2. Check logs: docker logs crm_sintel-web-1
  3. See POSTMORTEM section "Common Failures"
  4. Re-run repair script if needed
```

### Scenario D: relation "perfil_tenantprofile" does not exist
```
❌ PROBLEM: Still getting this error after deploy
✅ SOLUTION:
  1. This should NOT happen with authz.py improvements
  2. Check that authz.py was updated correctly:
     ```
     docker exec crm_sintel-web-1 grep -n "SHIELD" /app/apps/public/tenants/authz.py
     ```
  3. If not found, authz.py was not updated - rollback and redo
  4. Check middleware order in settings.py
  5. See DIAGNOSTICO_MIDDLEWARE for detailed diagnisis
```

**For any issue:** Check the troubleshooting section in appropriate guide
- **Data issues:** REPAIR_GUIDE_SSoT_Migraciones.md
- **Middleware issues:** DIAGNOSTICO_MIDDLEWARE_TENANTPROFILE_SCHEMA.md
- **General issues:** POSTMORTEM_Migraciones_v2.61.4.md

---

## ✅ FASE 10: FINAL SIGN-OFF

```
Deployment completed: [ ] YES  [ ] NO

If YES, complete:
  [ ] All 10 phases checked
  [ ] All tests passed
  [ ] No errors in logs
  [ ] Application serving requests
  [ ] Smoke tests successful
  [ ] Notify team deployment complete

If NO, complete:
  [ ] Document error message
  [ ] Refer to "IF SOMETHING GOES WRONG" section
  [ ] Consult documentation guides
  [ ] Consider rollback if necessary
```

---

## 📋 SIGNATURES (For Production Deploys)

```
Deployed by:        ________________    Date: _______
Verified by:        ________________    Date: _______
Manager approval:   ________________    Date: _______
```

---

## 🕐 TIMELINE SUMMARY

| Phase | Time | Done? |
|-------|------|-------|
| 1. Pre-flight checks | 5 min | [ ] |
| 2. Copy files | 2 min | [ ] |
| 3. Repair execution | 5 min | [ ] |
| 4. Migrations | 2 min | [ ] |
| 5. Validation | 1 min | [ ] |
| 6. Restart services | 1 min | [ ] |
| 7. Check logs | 2 min | [ ] |
| 8. Smoke tests | 3 min | [ ] |
| 9. Compare results | 2 min | [ ] |
| **TOTAL** | **~25 min** | **[ ]** |

**Total with buffer:** 30-45 minutes recommended

---

## 📞 EMERGENCY CONTACTS

- **Database Issue:** Check Docker logs first, then DB team
- **Middleware Issue:** Review DIAGNOSTICO_MIDDLEWARE guide
- **Code Issue:** Check syntax with `python -m py_compile authz.py`
- **General Issue:** Check POSTMORTEM_Migraciones_v2.61.4.md

---

**Checklist Version:** 1.0  
**Valid for:** v2.61.4  
**Last Updated:** Current Session  
**Print friendly:** Yes

---

**Status:** Ready for deployment ✅
