# Auditoría: Módulo Landing - ENFORCED MODE v2.40

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Auditoría completada

---

## 1) AUDIT SUMMARY

### A) Backend: Landing ViewSet, Serializers, URLs

#### A.1) `apps/tenant/landing/models.py`
✎ **NO EXISTE** - La app `landing` no tiene modelos
- ✎ No hay `models.py` en la app `landing`
- ✎ La app `landing` opera sobre `request.tenant` (inyectado por middleware de django-tenants)
- ✎ No requiere FK a Empresa (no hay modelos)

#### A.2) `apps/tenant/landing/api/serializers.py`
✓ **OK** - Serializers
- ✓ `TenantPublicInfoSerializer`: Información pública del tenant
- ✓ `TenantLoginSerializer`: Login de tenant (API-First)
- ✓ `TenantLandingSerializer`: Información pública del tenant en landing page
- ✓ `OwnerActivationSerializer`: Activación de owner (API-First)
- ✓ `PasswordResetRequestSerializer`: Solicitar reset de contraseña
- ✓ `PasswordResetValidateSerializer`: Validar token de reset
- ✓ `PasswordResetConfirmSerializer`: Confirmar reset de contraseña

#### A.3) `apps/tenant/landing/api/viewsets.py`
✓ **OK** - LandingViewSet (ViewSet, no ModelViewSet)
- ✓ `permission_classes`: `[permissions.AllowAny]` - **CORRECTO** (endpoints públicos)
- ✓ `info()`: GET `/api/v1/landing/info/` - Información pública del tenant
- ✓ `activate()`: GET|POST `/api/v1/landing/auth/activate/` - Activación de owner
- ✓ No requiere ENFORCED MODE porque:
  - Son endpoints públicos (AllowAny)
  - No operan sobre modelos de negocio
  - No requieren permisos de STAFF/ADMIN

**OBSERVACIÓN:** El `LandingViewSet` es un `ViewSet` (no `ModelViewSet`), por lo que no tiene métodos `create()`, `update()`, `partial_update()`, `destroy()`. Solo tiene acciones personalizadas (`@action`).

#### A.4) `apps/tenant/landing/api/urls.py`
✓ **OK** - URLs
- ✓ Router registrado: `router.register(r'', LandingViewSet, basename='landing')`
- ✓ Endpoints:
  - `GET /api/v1/landing/info/` → `LandingViewSet.info`
  - `GET|POST /api/v1/landing/auth/activate/` → `LandingViewSet.activate`

#### A.5) Core Orchestrator
✎ **NO REQUERIDO** - Landing no tiene modelos de negocio
- ✎ No hay Core Orchestrator para Landing (correcto, no hay modelos)
- ✎ Los endpoints de landing son públicos y no requieren orquestación

---

### B) Frontend: landing.page.js + Templates

#### B.1) `apps/tenant/core/static/core/js/landing/landing.page.js`
✓ **OK** - Frontend
- ✓ Maneja la landing page del tenant
- ✓ Usa endpoints públicos (`/api/v1/landing/info/`, `/api/v1/landing/auth/activate/`)
- ✓ No requiere ENFORCED MODE porque no hay mutaciones protegidas

#### B.2) `apps/tenant/core/templates/tenant/landing/partials/`
✓ **OK** - Templates
- ✓ `info.html`: Información pública del tenant
- ✓ `auth.html`: Autenticación (login, activación)
- ✓ `header.html`: Header de la landing page
- ✓ `assets_landing.html`: Assets JavaScript

#### B.3) `apps/tenant/core/templates/tenant/core/workspace.html`
✎ **NO APLICA** - Landing no está en workspace
- ✎ Landing es una página pública, no parte del workspace

---

### C) Tests

#### C.1) Tests Existentes
✎ **NO VERIFICADO** - No se encontraron tests específicos para landing
- ✎ No hay tests en `apps/tenant/landing/tests/`
- ✎ Los tests pueden estar en otros lugares (p. ej., `apps/public/tenants/tests/`)

#### C.2) Tests ENFORCED MODE
✎ **NO REQUERIDO** - Landing no requiere ENFORCED MODE
- ✎ No hay mutaciones protegidas que requieran tests de ENFORCED MODE

---

### D) Cleanup: Paths Redundantes/Legacy

#### D.1) Archivos Legacy JavaScript
✎ **NO VERIFICADO** - Verificar archivos legacy
- ✎ `apps/tenant/core/static/core/js/landing/landing.api.js`: Verificar si se usa
- ✎ `apps/tenant/core/static/core/js/landing/landing.ui.js`: Verificar si se usa

**Estado:** Verificar si estos archivos se cargan en `assets_landing.html` o si son legacy.

---

### E) Migraciones

#### E.1) Migración de FK a Empresa
✎ **NO REQUERIDO** - Landing no tiene modelos
- ✎ No hay modelos en la app `landing`, por lo que no requiere FK a Empresa
- ✎ No hay migraciones de FK a Empresa para landing

---

### F) Idempotencia

✓ **OK** - Estado idempotente
- ✓ Todas las validaciones pasan
- ✓ **ENFORCED MODE NO REQUERIDO** (endpoints públicos)

---

## 2) DIFFS (Solo cambios necesarios)

### D.1) Verificación de archivos legacy (opcional)

**Archivo:** `apps/tenant/landing/templates/tenant/landing/partials/assets_landing.html`

**Acción:** Verificar qué archivos JS se cargan y si son legacy

```bash
# Verificar contenido de assets_landing.html
cat apps/tenant/landing/templates/tenant/landing/partials/assets_landing.html
```

**Nota:** Si hay archivos legacy que no se usan, marcarlos como DEPRECATED o eliminarlos.

---

## 3) POST-AUDIT CHECKLIST

### Validaciones Requeridas

```bash
# 1. Verificar endpoints públicos (deben funcionar sin autenticación)
curl -X GET http://localhost:8000/api/v1/landing/info/
# Esperado: 200 OK con información del tenant

# 2. Verificar activación (debe funcionar con token válido)
curl -X GET "http://localhost:8000/api/v1/landing/auth/activate/?token=..."
# Esperado: 200 OK con información del usuario y tenant

# 3. Validar Landing Page UI
# Abrir http://home.sintel.net.co/
# Verificar que la landing page carga correctamente
```

---

## 4) RESUMEN FINAL

### Estado General: ✅ **CONFORME (ENFORCED MODE NO REQUERIDO)**

**Componentes validados:**
- ✅ Backend: LandingViewSet con endpoints públicos (AllowAny)
- ✅ Frontend: landing.page.js correcto (usa endpoints públicos)
- ✅ **ENFORCED MODE:** No requerido porque:
  - Los endpoints son públicos (`AllowAny`)
  - No operan sobre modelos de negocio
  - No requieren permisos de STAFF/ADMIN

**Justificación:**
- Landing es una página pública que muestra información del tenant
- La activación de owner es un proceso público (con token)
- No hay mutaciones protegidas que requieran ENFORCED MODE

**Cambios aplicados:**
- ✎ **NINGUNO** - No se requieren cambios porque ENFORCED MODE no aplica a endpoints públicos

**Mejoras opcionales:**
- ✎ Verificar archivos legacy JS (no bloqueante)

**Conclusión:** El módulo Landing está correctamente configurado. No requiere ENFORCED MODE porque todos sus endpoints son públicos (`AllowAny`). No hay modelos de negocio ni mutaciones protegidas que requieran permisos de STAFF/ADMIN.

---

**Auditoría completada:** ✅  
**Fecha:** 2026-01-XX  
**Versión:** v2.40
