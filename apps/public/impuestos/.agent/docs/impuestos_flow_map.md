# 🗺️ Mapa de Flujo: Módulo Impuestos (SSoT)

Este documento define la secuencia operativa para la provisión del catálogo tributario.

---

## 1. Ciclo de Consumo desde Tenant (Cross-Schema)

```mermaid
sequenceDiagram
    participant TNT as App Tenant (Facturas/Gastos)
    participant PRV as ImpuestosProvider (Public Schema)
    participant DB as PostgreSQL (Public Schema)

    TNT->>PRV: get_tarifa_iva(codigo="01", tarifa=19)
    PRV->>DB: SELECT * FROM TarifaIVA WHERE codigo="01" AND valor=19
    DB-->>PRV: Tarifa Instance
    PRV-->>TNT: DTO Validado con Metadata DIAN
    TNT->>TNT: Ejecutar Cálculo de Impuesto
```

---

## 2. Pipeline de Actualización Legal (ETL)

```mermaid
graph TD
    A[Staff Admin] --> B[POST /run-pipeline/]
    B --> C[ETLIngestaService]
    C --> D{¿Origen XML/CSV?}
    D -- SI --> E[Parsear Norma Tributaria]
    E --> F[Actualizar Modelos en Esquema Public]
    F --> G[Invalidar Caché de Provider en Tenants]
    G --> H[Notificar Éxito]
```

---

## 3. Resolución de Perfil Tributario

- **Entrada**: Datos del RUT del cliente/proveedor.
- **Proceso**: El `ImpuestosProvider` cruza Responsabilidades RUT + Régimen para determinar el tratamiento fiscal (¿Es retenedor?, ¿Es responsable de IVA?).
- **Salida**: Matriz de impuestos aplicables para la transacción.
