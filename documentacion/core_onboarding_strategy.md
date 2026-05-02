# Centralización del Aprovisionamiento en Core App - SINTEL v3.4

## Objetivo
Cumpliendo con la filosofía SSoT de SINTEL, el proceso de finalización de aprovisionamiento de tenants privados (validación OTT, generación de sesión e interfaz de bienvenida inicial) debe dejar de depender de la aplicación `landing` y ser migrado/centralizado estrictamente en la aplicación núcleo `apps/tenant/core`.

## User Review Required
> [!IMPORTANT]
> **Nueva Norma Arquitectónica**: A partir de ahora, todo el flujo de inicio de sesión de nuevos tenants y su interfaz de bienvenida (Onboarding silencioso) pertenecerá EXCLUSIVAMENTE a la app `core`. La app `landing` será despojada de estas responsabilidades de seguridad/aprovisionamiento para actuar puramente como presentación informativa (si es necesaria).

## Proposed Changes

### 1. [Componente: Interfaz de Usuario UI (Frontend)]

#### [NUEVO] [core/onboard.html](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/core/static/core/js/onboard.html)
- **Migración**: Mover el archivo actual `apps/tenant/landing/static/tenant/landing/onboard.html` hacia el estático de `core`: `apps/tenant/core/static/core/onboard.html`.
- **Modificación**: Actualizar los *paths* estáticos internos (`/static/tenant/landing/...` a `/static/tenant/core/...`).

#### [NUEVO/MODIFICADO] [services/onboarding.py](file:///c:/Users/Administrator/Documents/crm_sintel/apps/public/tenants/services/onboarding.py)
- **Migración de Redirect**: Modificar la función `crear_tenant_service` (que genera la URL del OTT en el backend público) para que su redirección ya no apunte a `/static/tenant/landing/onboard.html`, sino de forma definitiva a la nueva ruta central `/static/tenant/core/onboard.html`.

### 2. [Componente: Tests de Integración]

#### [MODIFICAR/MOVER] [test_core_onboarding_flow.py](file:///c:/Users/Administrator/Documents/crm_sintel/apps/public/tenants/tests/test_onboarding_cookie_flow.py)
- Renombrar conceptual o físicamente el test actual `test_onboarding_cookie_flow.py`.
- Actualizar las descripciones del docstring y dependencias para dejar claro que esta es la prueba maestra (E2E) que certifica que *Core API* orquesta el login del tenant.

### 3. [Componente: Core API (Backend)]
- **Confirmación**: La lógica HTTP de consumo en `apps/tenant/core/api/viewsets.py` (`consume_ott`) ya se migró exitosamente aquí y está funcionando. Este paso valida que dicha función sea ahora inamovible (SSoT de Autenticación de Nuevos Tenants).

## Verification Plan
1. **Paso A**: Eliminar físicamente `onboard.html` de `landing` y colocarlo en `core`.
2. **Paso B**: Actualizar en Python el string resultante de la redirección.
3. **Paso C**: Ejecutar nuevamente la suite de pruebas (`test_onboarding_cookie_flow.py`) para confirmar que el ciclo cerrado sigue emitiendo HTTP 200 y cookies válidas sin depender en lo absoluto del módulo `landing`.
