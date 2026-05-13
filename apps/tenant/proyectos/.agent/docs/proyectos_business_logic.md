# Lógica de Negocio: Módulo Proyectos v3.5.0

Este documento detalla las reglas de negocio, validaciones y cálculos centrales que rigen el módulo de **Proyectos**.

## 1. Patrón "Snapshot" (Desacoplamiento Estricto)

Para garantizar que el módulo de Proyectos sea autónomo y no dependa de la disponibilidad inmediata de otros módulos (Clientes, Empleados, Inventario), se implementa el patrón de **Snapshot**:

- **Regla**: No se permiten ForeignKeys hacia modelos de otros módulos.
- **Implementación**: Se almacenan el ID referencial (`cliente_id`) y una copia del nombre (`cliente_nombre`) en el momento de la asignación.
- **Sincronización**: Si el nombre cambia en el módulo de origen, el proyecto conserva el nombre original del momento del contrato, a menos que se fuerce una actualización manual.

## 2. Gestión de Fases y Workflow

El ciclo de vida de un proyecto está dividido en fases secuenciales. Cada fase tiene un responsable asignado:

| Fase | Responsable | Acción Principal |
| :--- | :--- | :--- |
| **BORRADOR** | N/A | Definición inicial y proyectado financiero. |
| **INICIO** | Comercial | Legalización de contrato y actas iniciales. |
| **PLANEACION** | Técnico | Diseño, cronograma y pedidos de materiales. |
| **EJECUCION** | Operativo | Gestión de personal y avance físico. |
| **CIERRE** | Administrativo | Liquidación financiera y actas de entrega. |

**Regla de Validación**: El cambio de fase debe ser orquestado por `ProyectoBusinessService.cambiar_fase_proyecto`, asegurando que se capture el snapshot del responsable correspondiente.

## 3. Cálculos Financieros (P&L del Proyecto)

El sistema calcula la rentabilidad en tiempo real basándose en datos capturados:

- **Costo Mano de Obra Real**: Sumatoria de `costo_total_asignacion` de todas las asignaciones activas en `AsignacionPersonal`.
- **Costo Materiales Real**: Sumatoria de (cantidad * precio_unitario) de todos los items en `PedidoProyecto` que tengan estado **APROBADO**.
- **Utilidad Estimada**: `valor_contrato_proyectado` - (`costo_mano_obra_real` + `costo_materiales_real`).
- **Margen de Rentabilidad**: (`utilidad_estimada` / `valor_contrato_proyectado`) * 100.

**Frecuencia**: Los cálculos se disparan en cada orquestación de creación/actualización y mediante tareas de fondo para asegurar precisión financiera.

## 4. Identificadores SSoT (Código de Proyecto)

- **Unicidad**: El código de proyecto es único por empresa (`empresa_id`).
- **Generación**: Si no se proporciona un código manual, el sistema genera uno siguiendo el patrón `PRJ-{timestamp}-{random}`.
- **Idempotencia**: El orquestador valida la existencia del código antes de intentar la creación para evitar colisiones de BD.

## 5. Seguridad y Aislamiento (Zero Trust)

- **Filtrado por Empresa**: Todas las consultas (vía Selectors) incluyen forzosamente `empresa_id`.
- **RBAC**: Solo usuarios con rol `ADMIN` pueden modificar valores financieros críticos o eliminar proyectos. Usuarios con rol `OPERADOR` pueden avanzar fases y gestionar pedidos.
