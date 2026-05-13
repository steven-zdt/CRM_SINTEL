# 🏗️ Arquitectura de Microtareas (MT-LND): Módulo Landing

Sistema de trazabilidad técnica para la evolución de la fachada pública.

---

## 🛠️ Fase 1: Limpieza y Desacoplamiento (Cleanup)

- `[ ]` **MT-LND-001**: Eliminar vistas legacy de activación de cuenta en `landing/views.py`.
- `[ ]` **MT-LND-002**: Migrar templates de login remanentes a `apps/tenant/core/templates/tenant/core/auth/`.
- `[ ]` **MT-LND-003**: Refactorizar `LandingInfoService` para asegurar que solo retorne datos públicos (No sensibles).

---

## 🧠 Fase 2: SSoT de Branding (Branding Layer)

- `[ ]` **MT-LND-010**: Implementar `LandingBrandingSelector` con soporte para inyección de variables CSS en el `base.html`.
- `[ ]` **MT-LND-011**: Crear validador de dimensiones de logo en `LandingBusinessService`.
- `[ ]` **MT-LND-012**: Centralizar la resolución de Favicons y activos de marca.

---

## 🌐 Fase 3: SEO y Performance (Optimization)

- `[ ]` **MT-LND-020**: Implementar middleware de SEO para inyección de Meta-Tags dinámicos basados en `LandingInfo`.
- `[ ]` **MT-LND-021**: Optimización de carga de imágenes (Lazy loading y formatos WebP).
- `[ ]` **MT-LND-022**: Documentación Swagger para el endpoint público `/api/v1/landing/info/`.

---

## 🎨 Fase 4: Estética y UI (Presentation)

- `[ ]` **MT-LND-030**: Refactorizar `index.html` para usar Partials de Bootstrap 5.
- `[ ]` **MT-LND-031**: Implementar micro-animaciones en el héroe de la landing page (CSS/Vanilla JS).
- `[ ]` **MT-LND-032**: Namespace JS `window.Sintel.Landing` para el manejo de componentes interactivos públicos.
