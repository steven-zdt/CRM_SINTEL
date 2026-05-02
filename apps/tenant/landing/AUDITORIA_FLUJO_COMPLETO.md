# AUDITORIA_FLUJO_COMPLETO - apps/tenant/landing v2.61

## 1. Propósito y Responsabilidades (SSoT)
Tras la centralización v2.61 en la aplicación `core`, la aplicación `landing` ha sido despojada de sus responsabilidades críticas de aprovisionamiento, seguridad e identidad.

- **Responsabilidad Única**: Presentación estática e informativa del tenant (Landing Page). sirve el branding y metadatos básicos.
- **Responsabilidad Eliminada**: El aprovisionamiento de nuevos administradores (OTT), el "Onboarding" y la **Activación de Cuenta** han sido migrados a `apps/tenant/core`.
- **Aislamiento**: No interactúa con otros modelos de negocio de manera directa; actúa como una shell de presentación pública.

## 2. Flujo Funcional (E2E)

### 2.1. Landing Page (Pública)
1. El usuario accede a `https://<schema>.sintel.com/`.
2. `LandingViewSet.info` (`/api/v1/landing/info/`) sirve el branding y metadatos básicos.
3. El frontend (Vanilla JS) renderiza el `index.html`.

- **Responsabilidad Migrada**: El proceso de establecer contraseña inicial para usuarios invitados ha sido migrado a `apps/tenant/core` (`/api/v1/core/auth/activate/`).
- **Nota**: Los activos físicos (`activate.html`, `login.html`, etc.) han sido migrados a `apps/tenant/core/static/tenant/core/auth/` para centralizar la gestión de identidad en el shell de Core.

## 3. Arquitectura Técnica

### Backend (Service Layer)
- `services/landing_info_service.py`: Única fuente de verdad para datos de branding.
- `api/viewsets.py`: Expone los endpoints mínimos de información.

### Frontend (FSD Partial Architecture)
- **Partials UI**: Ubicados en `templates/tenant/landing/partials/`.
- **Independencia**: Los assets de `landing` no dependen de `core` para visualización, pero `core` ahora gestiona el asset crítico `onboard.html`.

## 4. Impacto en Nuevos Tenants
- Los nuevos administradores ya NO pasan por `landing` para su primer inicio de sesión.
- Son redirigidos automáticamente por el orquestador público (`apps/public/tenants/services/onboarding.py`) hacia `apps/tenant/core/static/core/onboard.html`.
- La herencia de sesión (JWT Proxying via HttpOnly Cookies) es validada exclusivamente por `CoreAuthViewSet.consume_ott`.

## 5. Validación de Reglas
- ✅ **Aislamiento SSoT**: No hay cruce de lógica con otros modelos.
- ✅ **Gateway Directo**: Consume sus propios endpoints de `/api/v1/landing/`.
- ✅ **Cero Caracteres Especiales**: Cumple con `AGENTS.md`.
