# 🗺️ Mapa de Flujo: Módulo Perfil (SSoT)

Este documento define la secuencia operativa para la gestión de acceso e identidad.

---

## 1. Flujo de Invitación: Usuario Nuevo -> Perfil Tenant

```mermaid
sequenceDiagram
    participant ADM as Admin UI (offcanvas_crear_perfil.html)
    participant API as PerfilViewSet (/api/v1/perfil/perfiles/)
    participant SRV as PerfilBusinessService
    participant USR as User Service (Public Schema)
    participant DB as PostgreSQL (Tenant Schema)

    ADM->>API: POST {email, nombre, rol, empresa_id}
    API->>SRV: create_profile_for_user(empresa, data)
    SRV->>USR: ¿Existe usuario por email?
    alt No Existe
        USR->>USR: Create User (unusable_password)
    end
    USR-->>SRV: User Instance
    SRV->>SRV: Validar si ya tiene perfil en este Tenant
    SRV->>DB: INSERT TenantProfile {user, empresa, rol}
    DB-->>SRV: Success
    API-->>ADM: 201 Created (HX-Trigger: "perfilesChanged")
```

---

## 2. Resolución de Perfil Actual (`/me/`)

```mermaid
graph TD
    A[GET /perfiles/me/] --> B[Obtener User de la Sesión/JWT]
    B --> C[Buscar TenantProfile(user, empresa_actual)]
    C --> D{¿Es owner_email de la Empresa?}
    D -- SI --> E[Garantizar Rol ADMIN]
    D -- NO --> F[Retornar Rol Actual]
    E --> G[Update Profile si es necesario]
    F --> H[Response 200 JSON]
    G --> H
```

---

## 3. Protección de Integridad en Cambio de Roles

```mermaid
graph TD
    ROL[PATCH /assign-rol/] --> VAL{¿Es el Perfil Actual ADMIN?}
    VAL -- NO --> ERR1[Error: No tiene permisos]
    VAL -- SI --> CHK{¿Es el ÚLTIMO ADMIN del Tenant?}
    CHK -- SI --> REJ{¿Intenta degradarse a OPERADOR/VISOR?}
    REJ -- SI --> ERR2[Error: No puede eliminar al último admin]
    REJ -- NO --> OK[Actualizar Rol]
    CHK -- NO --> OK
```

---

## 4. Estructura de Navegación UI (FSD)

- **User Management**: Tabla Tabulator con listado de colaboradores y sus roles.
- **Detalle de Perfil**: Vista de solo lectura para el administrador.
- **Editor de Perfil Propio**: Sección especial para que el usuario actual actualice su avatar y preferencias.
- **Buscador Cross-Tenant**: (Opcional) Funcionalidad de administrador para invitar usuarios que ya existen en otros tenants de la plataforma.
