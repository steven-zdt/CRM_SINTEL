# CORE — Mapa de Flujos y Secuencias

**Version:** 3.5.0
**App:** `apps/tenant/core/`

---

## 📂 Navegación de Documentación
- [🏗️ Arquitectura de Microtareas](core_microtasks_architecture.md)
- [⚖️ Lógica de Negocio y Reglas SSoT](core_business_logic.md)
- [🏠 Portal de Auditoría](../AUDITORIA_FLUJO_CORE.md)

---

## 1. Ciclo de Vida de una Petición (Middleware Chain)

Este flujo describe cómo viaja una petición desde el host hasta el ViewSet, asegurando el aislamiento del tenant.

```mermaid
sequenceDiagram
    participant C as Cliente (Browser/Mobile)
    participant M1 as ForceNoPortMiddleware
    participant M2 as TenantMainMiddleware
    participant M3 as SintelExceptionMiddleware
    participant M4 as MembershipGuard
    participant V as ViewSet (Core/App)
    participant DB as PostgreSQL (Tenant Schema)

    C->>M1: Request (tenant.sintel.com)
    M1->>M2: Clean Hostname
    M2->>DB: Lookup Domain (public)
    DB-->>M2: schema_name: "tenant_abc"
    M2->>M2: set_schema("tenant_abc")
    M2->>M3: Request Processed
    M3->>M4: Authentication Check (Dual-Auth)
    M4->>DB: Verify Membership (public)
    DB-->>M4: Authorized
    M4->>V: Execute Action
    V->>DB: Query (tenant_abc schema)
    DB-->>V: Results
    V-->>C: JSON Standard Response
```

## 2. Pipeline de Ingesta Universal (`document_router`)

Flujo de materialización de documentos (facturas, gastos, etc.) desde fuentes externas.

```mermaid
graph TD
    A[Pipeline Externo] -->|POST DTO| B(Core Document Router)
    B -->|Mapeo de Tipo| C{Tipo de Documento?}
    
    C -->|Factura| D[FacturaMaterializer]
    C -->|Gasto| E[GastoMaterializer]
    C -->|Contable| F[AsientoMaterializer]
    
    D --> G[DSV & Business Logic]
    E --> G
    F --> G
    
    G --> H[Atomic CRUD Service]
    H -->|Commit| I[(PostgreSQL Tenant)]
    H -->|Error| J[Rollback & 400 Response]
```

## 3. Resolución de Identidad y Dual-Auth

```mermaid
sequenceDiagram
    participant UI as Frontend (Tabulator/Fetch)
    participant API as Core Auth ViewSet
    participant JWT as JWTAuthentication
    participant SESS as SessionAuthentication
    participant DB as public.AuthUser

    UI->>API: Request with Header/Cookie
    API->>JWT: Check Bearer Token
    alt Token Valido
        JWT-->>API: User Context
    else Token Invalido/Ausente
        API->>SESS: Check Session Cookie
        alt Sesion Valida
            SESS-->>API: User Context
        else Fallo Total
            API-->>UI: 401 Unauthorized
        end
    end
    API->>DB: Check Active Membership
    DB-->>API: Membership Status
```

---
**Última actualización:** 2026-05-09
