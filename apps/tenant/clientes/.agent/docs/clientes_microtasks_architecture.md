# CLIENTES — Arquitectura de Microtareas

**Version:** 3.5.0
**App:** `apps/tenant/clientes/`
**Estado:** Auditoria v2.62.1 Sincronizada

---

## 1. Resumen Arquitectonico

La aplicacion `clientes` implementa un patron **Feature-Sliced Design (FSD)** con una capa de servicios desacoplada. Gestiona la identidad de terceros (Clientes) y sus puntos de contacto (Contactos), actuando como fuente de verdad para modulos transaccionales como `facturas` y `proyectos`.

### Componentes Clave:
- **Service Layer:** Division estricta en `selectors.py` (Lectura), `crud_service.py` (Escritura Base) y `business_service.py` (Orquestacion Compleja).
- **Double Semantic Verification (DSV):** Garantia de aislamiento multi-tenant en cada transaccion.
- **Zero Waste Queries:** Optimizacion de consultas via `.only()` y Prefetch selectivo.
- **Dual-Auth Bridge:** Soporte nativo para JWT y SessionAuth.

### Documentacion Relacionada:
- [Flow Map (Mapa de Flujos)](clientes_flow_map.md)
- [Business Logic (Logica de Negocio)](clientes_business_logic.md)

---

## 2. Mapa de Archivos (Estructura FSD)

```
apps/tenant/clientes/
├── models.py                        # Cliente, ContactoCliente (Heredan de SintelTenantBaseModel)
├── api/
│   ├── viewsets.py                  # Endpoints REST + HTMX Offcanvas
│   ├── serializers.py               # Serializers con NormalizationMixin
│   ├── mixins.py                    # Inyeccion de servicios en ViewSets
│   └── urls.py                      # Router (Orden critico: contactos antes de '')
├── services/
│   ├── selectors.py                 # Consultas optimizadas (.only)
│   ├── crud_service.py              # Operaciones atomicas de DB
│   ├── business_service.py          # Logica de Upsert y Sincronizacion
│   └── api_mixins.py                # Mixins de infraestructura de servicios
├── templates/tenant/
│   ├── clientes/                    # Templates locales del dominio Clientes
│   └── contactos/                   # Templates locales del dominio Contactos
├── static/clientes/js/
│   ├── clientes.api.js              # Wrapper de API (SSoT de endpoints)
│   ├── clientes.list.js             # Orquestador de Tabulator y Eventos
│   ├── clientes.editor.js           # Manejo de formularios y DOM Shield
│   └── clientes.contactos.js        # Logica especifica de contactos
└── docs/                            # Documentacion tecnica de la app
```

---

## 3. Microtareas Atomicas: Auditoria y Cumplimiento

### M1: Cumplimiento de Estandares Core (v3.5)
- [x] Heredar todos los modelos de `SintelTenantBaseModel`.
- [x] Implementar `DSV` en `get_object()` de los ViewSets.
- [x] Aplicar `.only()` en todos los selectors (`LIST_FIELDS`, `DETAIL_FIELDS`).
- [x] Eliminar logica de negocio de serializers y views, moviendola a `business_service.py`.
- [x] Asegurar `@transaction.atomic` en todos los metodos de escritura.

### M2: Optimizacion de Interfaz (v2.62)
- [x] Implementar Prefetch de contacto principal (`is_principal=True`) para la columna Encargado.
- [x] Estandarizar endpoints `render-offcanvas` a `detail=True` con URL kwargs.
- [x] Sincronizar IDs de Offcanvas y botones entre JS y Templates.
- [x] Implementar `UIManager.handleOffcanvas` para gestion segura de backdrops.

### M3: Deuda Tecnica y Roadmap (PENDIENTE)
- [ ] **Migracion a UUID:** Cambiar `lookup_field = "id"` por `lookup_field = "uuid"` en todos los ViewSets y Serializers.
- [ ] **Limpieza de Codigo:** Eliminar comentarios legacy `# WARNING: vX.Y` y notas de desarrollo.
- [ ] **Consolidacion de Mixins:** Unificar `api/mixins.py` con `services/api_mixins.py` para evitar duplicidad.
- [ ] **UX Consistency:** Eliminar el `confirm()` innecesario en `editContacto` para igualar el flujo de clientes.

---

## 4. Riesgos y Observaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| **Exposicion de IDs (PK)** | Medio | Implementar `uuid` como lookup field (M3). |
| **Duplicidad de Mixins** | Bajo | Refactorizar imports hacia una unica fuente de verdad en `services/`. |
| **N+1 en Listado Global** | Bajo | Ya mitigado con Prefetch en `ClienteViewSet` y `select_related` en `ContactoSelector`. |

---

## 5. Checklist de Verificacion Final
- [x] Aislamiento Tenant (Zero Trust)
- [x] Rendimiento (Zero Waste)
- [x] Idempotencia (Upsert en Business Service)
- [x] Atomicidad (Transacciones)
- [x] Modularidad (FSD Assets)
