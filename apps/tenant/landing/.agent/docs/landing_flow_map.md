# 🗺️ Mapa de Flujo: Módulo Landing (SSoT)

Este documento define la secuencia operativa para la fachada pública del tenant.

---

## 1. Ciclo de Carga de Landing Page

```mermaid
sequenceDiagram
    participant USR as Navegador (Público)
    participant LND as Landing UI (index.html)
    participant API as LandingViewSet (/api/v1/landing/info/)
    participant SRV as LandingInfoService
    participant DB as PostgreSQL (Tenant Schema)

    USR->>LND: Acceso a https://schema.sintel.net.co/
    LND->>API: GET /api/v1/landing/info/
    API->>SRV: get_branding_data(empresa)
    SRV->>DB: SELECT branding_metadata FROM LandingInfo
    DB-->>SRV: Branding Data (Logo, Colores, Textos)
    SRV-->>API: DTO Validado
    API-->>LND: 200 OK (JSON)
    LND->>LND: Renderizado Dinámico de Secciones
```

---

## 2. Resolución de Branding Cross-App

```mermaid
graph TD
    A[Cualquier Módulo (Core/Ventas/etc)] --> B{¿Necesita Logo/Colores?}
    B -- SI --> C[GET /api/v1/landing/branding/]
    C --> D[LandingInfoService]
    D --> E[Cache de Branding (Redis/Session)]
    E --> F[Retornar Estilos Corporativos]
    F --> G[Inyectar CSS Variables en el DOM]
```

---

## 3. Redirección de Flujos Protegidos (Aislamiento)

```mermaid
graph TD
    A[Usuario en Landing] --> B{Intenta Acceder a /dashboard/}
    B -- No Autenticado --> C[Redirigir a Core /auth/login/]
    B -- Autenticado --> D[Permitir Acceso]
    
    E[Usuario Invitado] --> F{Intenta Activar Cuenta}
    F --> G[Redirigir a Core /auth/activate/]
```
