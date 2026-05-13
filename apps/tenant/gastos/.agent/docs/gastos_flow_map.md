# 🗺️ Mapa de Flujo: Módulo Gastos (SSoT)

Este documento define la secuencia operativa para el registro de egresos y documentos soporte.

---

## 1. Creación de Documento Soporte y Gasto

```mermaid
sequenceDiagram
    participant UI as Browser (gasto_form.js)
    participant API as GastosViewSet (/api/v1/gastos/)
    participant SRV as GastoBusinessService
    participant RES as ResolucionDIANService
    participant DB as PostgreSQL

    UI->>API: POST Data (Subtotal, Proveedor, Categoria)
    API->>SRV: registrar_gasto_total(empresa, data)
    SRV->>RES: obtener_resolucion_vigente()
    RES-->>SRV: Resolucion ID
    SRV->>RES: obtener_siguiente_consecutivo()
    RES-->>SRV: Numero (Prefijo + Consecutivo)
    SRV->>SRV: calcular_totales_gasto()
    SRV->>DB: INSERT DocumentoSoporte (Inmutable)
    SRV->>DB: INSERT Gasto (Mutable)
    SRV->>DB: INSERT ItemGasto (Generic)
    DB-->>SRV: Success
    SRV-->>API: 201 Created
    API-->>UI: HX-Trigger: "listaGastosChanged"
```

---

## 2. Ciclo de Vida: Desactivación y Anulación

```mermaid
graph TD
    A[Gasto ACTIVO] -->|Botón Desactivar| B[POST /desactivar/]
    B --> C[Estado: ACTIVO=False]
    C -->|Botón Anular| D[POST /anular/]
    D --> E{¿Está Desactivado?}
    E -- NO --> F[Error: Debe desactivar primero]
    E -- SI --> G[Estado: ANULADO=True]
    G --> H[Fin: Consecutivo Bloqueado]
```

---

## 3. Gestión de Resoluciones DIAN

```mermaid
graph LR
    RES[Nueva Resolución] --> VAL{¿Vigente=True?}
    VAL -- SI --> DES[Desactivar resoluciones anteriores]
    VAL -- NO --> SAV[Guardar como inactiva]
    DES --> SAV
    SAV --> USE[Uso en nuevos Gastos]
```

---

## 4. Estructura de Navegación UI (FSD)

- **Panel de Control**: Resumen financiero y botones de acción rápida.
- **Grilla de Gastos**: Listado con Tabulator (Filtros por fecha, proveedor y estado).
- **Grilla de Resoluciones**: Gestión de rangos DIAN.
- **Editor Offcanvas**:
  - `Formulario Gasto`: Captura simplificada de subtotal y retenciones.
  - `Formulario Resolución`: Configuración de prefijos y rangos legales.
