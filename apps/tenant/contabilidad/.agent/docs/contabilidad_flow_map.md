# CONTABILIDAD — Mapa de Flujos

**Version:** 3.5.0
**App:** `apps/tenant/contabilidad/`

---

## 1. Ciclo de Vida del Asiento Contable

El sistema maneja dos caminos de entrada (Pull vs Manual) y un ciclo de vida basado en estados inmutables.

```mermaid
graph TD
    A[Documento Fuente] -->|Pull Model ETL| B(Estado: BORRADOR)
    C[Usuario UI / IA] -->|Manual On-Demand| D(Estado: APROBADO)
    
    B -->|Edicion Manual| B
    B -->|Validacion Cuadratura| E{¿Cuadrado?}
    E -->|Si| F[Aprobar]
    E -->|No| B
    
    F --> D
    D -->|Cierre de Mes| G(Estado: CERRADO)
    
    style B fill:#fff9c4,stroke:#fbc02d
    style D fill:#c8e6c9,stroke:#388e3c
    style G fill:#f5f5f5,stroke:#9e9e9e
```

---

## 2. Flujo Pull Model (ETL Automático)

Este flujo es orquestado por Celery y procesa documentos de forma masiva e idempotente.

```mermaid
sequenceDiagram
    participant C as Celery Task
    participant E as Extractors (Gastos/Facturas/...)
    participant K as Contabilizador
    participant R as ResolverCuentas (PUC)
    participant DB as Base de Datos

    C->>E: extraer_pendientes(empresa_id)
    E->>DB: Query documentos no contabilizados
    DB-->>E: Lista de documentos
    E->>E: Mapear a TransaccionEconomica DTO
    E->>K: contabilizar(dto)
    
    activate K
    K->>R: resolver_cuenta(concepto, tipo)
    R->>DB: Query ReglaContable
    DB-->>R: Codigo PUC
    R-->>K: Codigo PUC
    
    K->>K: Validar Cuadratura (Debe == Haber)
    K->>DB: Guardar Asiento + Movimientos
    deactivate K
    
    E-->>C: Reportar Stats (OK/Error)
```

---

## 3. Flujo Manual On-Demand (Asistente IA)

Contabilización manual desde la lista de pendientes con soporte de IA.

```mermaid
sequenceDiagram
    participant U as Usuario (UI)
    participant IA as Claude Haiku
    participant BS as ContabilidadBusinessService
    participant C as Contabilizador
    participant DB as Base de Datos

    U->>BS: Sugerir con IA (ctx documento)
    BS->>IA: Prompt con PUC simplificado
    IA-->>BS: JSON [{cuenta_codigo, debe, haber}]
    BS->>BS: Validacion DSV (Seguridad)
    BS-->>U: Sugerencia en Formulario
    
    U->>BS: Confirmar Contabilizacion (Payload)
    BS->>C: contabilizar_documento_manual(dto)
    C->>DB: Incrementar Consecutivo TipoComprobante
    C->>DB: Crear Asiento (Estado: APROBADO)
    DB-->>U: HTMX Swap (Remover de Pendientes)
```

---

## 4. Flujo de Reportes Financieros

Generación de Balance de Prueba y Estado de Resultados.

```mermaid
graph LR
    A[Selector Fecha] --> B[Selectors.py]
    B --> C{Tipo Reporte}
    
    C -->|Balance| D[Balance Prueba Selector]
    C -->|Resultados| E[Estado Resultados Selector]
    
    D --> F[Query Movimientos < Fecha Inicio]
    D --> G[Query Movimientos en Periodo]
    
    F --> H[Calculo Saldo Anterior]
    G --> I[Calculo Movimientos Mes]
    
    H & I --> J[Suma por Naturaleza D/C]
    J --> K[Balance Final]
    
    E --> L[Query Cuentas Clase 4, 5, 6]
    L --> M[Utilidad Bruta / Neta]
```
