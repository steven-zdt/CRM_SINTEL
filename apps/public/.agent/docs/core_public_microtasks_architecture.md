# 🏗️ Arquitectura de Microtareas (MT-COR-PUB): Módulo Core Public

Sistema de trazabilidad técnica para la evolución de los servicios base globales.

---

## 🛠️ Fase 1: Comunicación y Templates (Communication Layer)

- `[ ]` **MT-COR-PUB-001**: Refactorizar `EmailService` para soportar envío asíncrono nativo vía Celery.
- `[ ]` **MT-COR-PUB-002**: Implementar sistema de tracking de apertura y clics en correos transaccionales.
- `[ ]` **MT-COR-PUB-003**: Rediseñar `base_email.html` con soporte para diseño responsivo en clientes móviles.
- `[ ]` **MT-COR-PUB-004**: Centralizar la gestión de adjuntos en correos (ej. Facturas PDF).

---

## 🧠 Fase 2: Infraestructura y Resolución (Core Layer)

- `[ ]` **MT-COR-PUB-010**: Desarrollar `PublicContextResolver` para manejar redirecciones inteligentes basadas en roles.
- `[ ]` **MT-COR-PUB-011**: Implementar middleware de monitoreo de latencia para el esquema público.
- `[ ]` **MT-COR-PUB-012**: Crear utilidades de auditoría para la validación periódica de la integridad del esquema `public`.

---

## 🌐 Fase 3: API y Autenticación (API Layer)

- `[ ]` **MT-COR-PUB-020**: Optimizar `LoggedTokenVerifyView` para incluir detección de sesión fraudulenta (IP/User-Agent).
- `[ ]` **MT-COR-PUB-021**: Implementar Rate Limiting en todos los endpoints públicos del core.
- `[ ]` **MT-COR-PUB-022**: Documentación Swagger de los servicios base.

---

## 🎨 Fase 4: Estética Global y Branding (Branding Layer)

- `[ ]` **MT-COR-PUB-030**: Centralizar la resolución de Favicons y Logos globales en un solo servicio.
- `[ ]` **MT-COR-PUB-031**: Implementar sistema de notificaciones globales en el sistema para anuncios de mantenimiento.
- `[ ]` **MT-COR-PUB-032**: UI para la previsualización de templates de correo desde la consola administrativa.
