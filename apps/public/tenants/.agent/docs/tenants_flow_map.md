# 🗺️ Mapa de Flujo: Módulo Tenants (SSoT)

Este documento define la secuencia operativa para la gestión de inquilinos y esquemas.

---

## 1. Pipeline de Onboarding (E2E)

```mermaid
sequenceDiagram
    participant USR as Cliente (Registro)
    participant API as TenantsViewSet (/onboard/)
    participant SRV as OnboardingService
    participant TNT as Client Model (TenantMixin)
    participant CLY as Celery (Worker)
    participant DB as PostgreSQL

    USR->>API: POST {email, empresa_nombre, subdominio}
    API->>SRV: execute_onboarding(data)
    SRV->>DB: Validar Email / Subdominio
    SRV->>TNT: Create Client (schema_name, owner)
    TNT->>DB: CREATE SCHEMA schema_name
    SRV->>CLY: Dispatch migrate_schemas(schema_name)
    CLY->>DB: Aplicar Migraciones al Esquema
    SRV->>DB: Create TenantMembership (Primary Admin)
    SRV->>DB: Send Welcome Email (Invitation OTT)
    SRV-->>API: Response {login_url, client_id}
    API-->>USR: Success
```

---

## 2. Resolución de Esquema por Petición (Middleware)

```mermaid
graph TD
    A[HTTP Request] --> B[TenantMiddleware]
    B --> C[Extraer Host de la URL]
    C --> D[Buscar Domain en Esquema Public]
    D --> E{¿Existe?}
    E -- SI --> F[Set connection.schema = client.schema_name]
    E -- NO --> G[404 Not Found / Redirigir a Landing Global]
    F --> H[Continuar con la View]
```

---

## 3. Manejo de Errores de Infraestructura (DLQ)

- **FailedTenantTask**: Si la tarea Celery de migración o seeding falla, el registro se guarda con el `traceback` y el payload original.
- **Reintento**: Los administradores pueden relanzar la tarea desde la Consola Central tras corregir la causa raíz.
