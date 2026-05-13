# 🗺️ Mapa de Flujo: Módulo Core Public (SSoT)

Este documento define la secuencia operativa para los servicios transversales globales.

---

## 1. Ciclo de Envío de Email Transaccional

```mermaid
sequenceDiagram
    participant APP as Módulo Invocador (Tenants/Accounts)
    participant SRV as EmailService (Public Core)
    participant RND as Template Renderer
    participant SMTP as Proveedor SMTP/Anymail

    APP->>SRV: send_invitation_email(user, tenant_url)
    SRV->>RND: render_to_string("emails/invitation.html", context)
    RND-->>SRV: HTML String
    SRV->>SMTP: Enviar Email (Async via Celery opcional)
    SMTP-->>SRV: Success (Message-ID)
    SRV-->>APP: Log Message-ID
```

---

## 2. Resolución de Entrada (Redirección Inteligente)

```mermaid
graph TD
    A[Acceso a /] --> B[PublicIndexView]
    B --> C{¿Está Autenticado?}
    C -- NO --> D[Redirigir a Landing Global / Landing del Tenant]
    C -- SI --> E{¿Es Staff / Admin?}
    E -- SI --> F[Redirigir a /console/]
    E -- NO --> G[Redirigir a Selección de Tenant]
```

---

## 3. Validación de Token con Auditoría

- **Flujo**: El frontend envía el token a `/api/v1/core/token/verify/`.
- **Proceso**:
    1. Validar firma del token (SimpleJWT).
    2. Si es válido, registrar acceso en `ConsoleActionLog` (opcional).
    3. Retornar metadatos del usuario (nombre, rol global).
