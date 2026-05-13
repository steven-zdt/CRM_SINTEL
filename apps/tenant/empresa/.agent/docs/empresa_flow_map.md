# 🗺️ Mapa de Flujo: Módulo Empresa (SSoT)

Este documento define la secuencia operativa del Módulo de Empresa, desde la identidad básica hasta la integración técnica de ingesta.

---

## 1. Ciclo de Vida: Identidad y Singleton

El sistema garantiza que cada tenant tenga exactamente una identidad corporativa configurada.

```mermaid
sequenceDiagram
    participant UI as Browser (Empresa.main.js)
    participant API as API Gateway (/api/v1/empresas/)
    participant SRV as EmpresaBusinessService
    participant DB as PostgreSQL (Tenant Schema)

    UI->>API: GET /mi-empresa/
    API->>SRV: EmpresaSelector.get_empresa_emisor_data()
    SRV->>DB: SELECT * FROM empresa_empresa WHERE singleton_key='default'
    DB-->>SRV: Data
    SRV-->>API: DTO (SSoT Emisor)
    API-->>UI: JSON (Hydrate View)

    Note over UI, DB: Mutación de Datos
    UI->>API: PATCH /update-identity/
    API->>SRV: update_empresa_data(payload)
    SRV->>SRV: Validate NIT/DV Format
    SRV->>DB: UPDATE (Atomic Transaction)
    DB-->>SRV: Success
    SRV-->>API: Response 200
    API-->>UI: UIManager.notifySuccess()
```

---

## 2. Flujo de Configuración MailInbox (Ingesta)

Configuración técnica para la captura automática de documentos externos.

```mermaid
graph TD
    A[Inicio: Formulario MailInbox] --> B{Validar Datos}
    B -- Invalido --> C[Error 400: Campos Requeridos]
    B -- Valido --> D[Cifrar Credenciales]
    D --> E[Guardar en DB]
    E --> F[Botón: Test de Conexión]
    F --> G[Celery Task: VerifyIMAP]
    G --> H{¿Conexión Exitosa?}
    H -- SI --> I[Estado: ACTIVO + Notificación]
    H -- NO --> J[Estado: ERROR + Detalle Técnico]
```

---

## 3. Consumo Cross-Module (SSoT)

Cómo otros módulos consumen la información de la empresa.

```mermaid
graph LR
    EMP[Módulo Empresa] -- SSoT Emisor --> FAC[Facturación]
    EMP -- SSoT Emisor --> NOM[Nómina]
    EMP -- Credentials --> ING[Ingestor Celery]
    ING -- Raw Docs --> PRO[Proveedores]
```

---

## 4. Estructura de Navegación UI

- **Dashboard Principal**: Tarjeta de resumen de identidad.
- **Configuración (Offcanvas)**:
  - Tab 1: Datos Legales (NIT, Razón Social).
  - Tab 2: Ubicación y Contacto.
  - Tab 3: Configuración MailInbox.
  - Tab 4: Logos y Marca.
