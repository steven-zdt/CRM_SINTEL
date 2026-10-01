# PLAN DE IMPLEMENTACIÓN — CENTRO DE APROBACIONES + TRAZABILIDAD DE COMPRAS

## OBJETIVO GENERAL

Evolucionar SINTEL ERP para que el Dashboard tenga un **Centro de Aprobaciones** donde el administrador pueda visualizar, revisar y decidir solicitudes de negocio enviadas para aprobación.

El flujo principal será:

```text
COTIZACIÓN APROBADA
        ↓
REQUISICIÓN
        ↓
ENVIAR PARA APROBACIÓN
        ↓
CENTRO DE APROBACIONES DEL DASHBOARD
        ↓
REVISIÓN INTEGRAL + TRAZABILIDAD
        ↓
APROBAR / RECHAZAR
        ↓
REQUISICIÓN OPERATIVA
        ↓
UNA O VARIAS ÓRDENES DE COMPRA
        ↓
RECEPCIÓN / CXP / INVENTARIO
```

El Centro no será una simple tabla: debe funcionar como **centro de control del proceso**, mostrando origen, contexto, valores, riesgos, historial y relaciones.

---

# 1. GROUNDING SOBRE EL ESTADO REAL DEL PROYECTO

Antes de modificar:

1. Leer `AGENTS.md` completo.
2. Leer:
   - `apps/tenant/dashboard/.agent/AUDITORIA_FLUJO_DASHBOARD.md`
   - `apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md`
   - documentación de `apps/tenant/compras/requisiciones/`.
3. Auditar código real, no asumir que documentación y código están perfectamente alineados.
4. Inspeccionar modelos, estados, servicios, selectors, API, permisos, templates, JS y migraciones.
5. **NO ejecutar tests** durante esta misión.

La arquitectura actual registra que Requisiciones ya existen como submódulo propio de Compras y usan la máquina:

```text
BORRADOR
→ PENDIENTE_APROBACION
→ APROBADA
→ EN_PROCESO_COMPRA
→ PARCIALMENTE_ATENDIDA
→ ATENDIDA
```

con ramas `RECHAZADA`/`CANCELADA`. También registra que la obligatoriedad de Requisición para nuevas OC acaba de activarse, aunque el modelo todavía conserva un FK previo que debe evolucionar para soportar la nueva regla N:N. fileciteturn98file0L214-L231

La arquitectura de presentación usa Service Layer estricto, DSV, OrganizationalScope, UUID y front-end por app; reutilizar esos patrones. fileciteturn99file5L1-L20

---

# 2. NUEVA REGLA DE NEGOCIO

## 2.1. Relación comercial y de abastecimiento

Diseñar:

```text
1 Cotización aprobada
        ↓
N Requisiciones
        ↓
N Órdenes de Compra
```

y:

```text
1 Orden de Compra
        ↓
N Requisiciones
```

Una OC puede consolidar, por ejemplo:

```text
REQ-00008 → Equipos       $35M
REQ-00009 → Materiales    $25M
REQ-00010 → Mano de obra  $15M

OC-00031
├── REQ-00008
└── REQ-00009

OC-00032
└── REQ-00010
```

No resolver esto con un FK único.

---

# 3. MODELO N:N ORDENCOMPRA ↔ REQUISICIÓN

Sustituir/evolucionar el actual:

```text
OrdenCompra.requisicion
```

hacia una relación intermedia equivalente a:

```text
OrdenCompraRequisicion
```

Debe conservar:

- empresa/tenant cuando corresponda;
- orden_compra;
- requisicion;
- trazabilidad de asociación;
- timestamps;
- usuario si existe patrón equivalente.

Auditar primero el FK actual, sus consumidores y los históricos antes de retirarlo.

### Regla futura

```text
NUEVA OC
    ↓
DEBE TENER >= 1 REQUISICIÓN
```

No permitir bypass por API, admin, frontend, MCP, serializer o servicio alterno.

La excepción `es_excepcional` no debe seguir funcionando para nuevas OC si contradice la nueva regla del usuario.

---

# 4. TRAZABILIDAD POR LÍNEA

Auditar `ItemOrdenCompra` y `RequisicionCompraItem`.

Cuando sea técnicamente consistente, cada línea de OC debe poder identificar su origen:

```text
ItemOrdenCompra
      ↓
RequisicionCompraItem
      ↓
RequisicionCompra
      ↓
Cotización
```

Esto permite:

```text
OC-00031

Cámara 4MP       $8M   → REQ-00008 → COT-00025
Cableado         $2M   → REQ-00009 → COT-00025
```

No inventar mapeos heurísticos contra Inventario. La arquitectura registra expresamente que el mapeo CotizacionItem → Inventario no tiene evidencia suficiente para inventarlo. fileciteturn98file0L62-L72

---

# 5. CENTRO DE APROBACIONES EN DASHBOARD

Agregar dentro del Dashboard:

```text
Dashboard
├── Resumen
├── Indicadores
├── ...
└── Centro de Aprobaciones
```

Nombre visible:

**Centro de Aprobaciones**

El Dashboard será la **superficie de control**, no el nuevo dueño de Cotizaciones, Requisiciones u Órdenes de Compra.

Si no existe actualmente un motor genérico de aprobaciones, crear un SSoT transversal/tenant de aprobación y dejar al Dashboard únicamente como consumidor/presentador.

---

# 6. BANNER DE CONTROL

Crear un banner superior:

```text
┌────────────────────────────────────────────────────┐
│ CENTRO DE APROBACIONES                             │
│ 7 solicitudes pendientes de revisión               │
│                                                    │
│ 🔴 2 críticas   🟠 3 con riesgo   🟢 2 normales   │
└────────────────────────────────────────────────────┘
```

Todos los números deben provenir del backend.

Agregar KPI:

- Pendientes.
- Riesgo presupuestal.
- Aprobadas hoy.
- Rechazadas.
- Valor pendiente.
- Antigüedad de solicitudes.

---

# 7. BANDEJA DE APROBACIONES

Nueva tabla server-side con:

```text
Prioridad
Tipo
Documento
Solicitante
Proyecto
Origen
Valor
Riesgo
Tiempo pendiente
Estado
Acción
```

Ejemplo:

```text
🔴 REQUISICIÓN  REQ-00008
Proyecto Torre 3
$35.000.000
⚠ Riesgo 82%
2h 14m
[ REVISAR ]
```

Para funcionalidades nuevas respetar el estándar actual de django-tables2 + HTMX, no introducir una nueva grilla Tabulator sin justificación.

---

# 8. FILTROS Y BÚSQUEDA

Server-side:

```text
Tipo
Estado
Prioridad
Solicitante
Proyecto
Fecha
Rango de valor
Riesgo
```

Búsqueda:

```text
Número
Código
Cotización
Proyecto
Solicitante
```

No cargar todo al navegador.

---

# 9. MOTOR GENÉRICO DE SOLICITUDES DE APROBACIÓN

Auditar si ya existe un SSoT.

Si no existe, implementar un modelo conceptual:

```text
SolicitudAprobacion
```

con:

```text
empresa
 tipo_documento
 objeto_uuid
 estado
 prioridad
 solicitante
 fecha_envio
 fecha_decision
 aprobador
 motivo_rechazo
 observaciones
 version/hash de origen
 snapshot financiero
```

Estados mínimos:

```text
PENDIENTE
APROBADA
RECHAZADA
CANCELADA
```

No usar GenericForeignKey sin auditar antes sus riesgos de tenant isolation.

Preferir un registry explícito:

```text
COTIZACION → resolver Cotizacion
REQUISICION → resolver RequisicionCompra
ORDEN_COMPRA → resolver OrdenCompra
```

---

# 10. HISTORIAL APPEND-ONLY

Crear/adaptar historial de aprobación:

```text
SolicitudAprobacionHistorial
```

Registrar:

```text
CREADA
ENVIADA
VISTA
APROBADA
RECHAZADA
CANCELADA
```

con usuario, timestamp, estado anterior/nuevo, observación y snapshot relevante.

No permitir editar/borrar historial desde CRUD normal.

---

# 11. ENVIAR REQUISICIÓN PARA APROBACIÓN

En Requisición debe existir:

```text
[ Enviar para aprobación ]
```

Flujo:

```text
BORRADOR
   ↓
Enviar
   ↓
PENDIENTE_APROBACION
   ↓
SolicitudAprobacion=PENDIENTE
   ↓
Dashboard
```

Delegar la transición al BusinessService real de Requisiciones.

---

# 12. BLOQUEO DE EDICIÓN DESPUÉS DEL ENVÍO

Cuando una Requisición está en:

```text
PENDIENTE_APROBACION
```

no debe poder alterarse silenciosamente.

Si necesita corrección:

```text
RECHAZADA
→ corregir
→ reenviar
```

Usar solamente transiciones soportadas por la máquina de estados real; no inventar un estado `EN_AJUSTE` si no existe.

---

# 13. SNAPSHOT E INTEGRIDAD

Al enviar para aprobación guardar resumen de control:

```text
valor
número
tipo
documento origen
cotización
proyecto
cantidad de líneas
versión/hash
```

Al aprobar:

```text
recargar documento real
recalcular
comparar con snapshot
```

Si cambió:

```text
BLOQUEAR APROBACIÓN
```

Mostrar:

> El documento cambió después de ser enviado a aprobación. Debe revisarse y reenviarse.

---

# 14. VISTA DETALLE DE APROBACIÓN

Al pulsar:

```text
[ REVISAR ]
```

abrir un Offcanvas amplio/panel lateral.

Usar el helper existente:

```javascript
mostrarOffcanvasSeguro(...)
```

No usar `getOrCreateInstance().show()` directamente.

Diseño:

```text
┌───────────────────────────────────────────────┐
│ REVISAR REQUISICIÓN REQ-00008              X │
├───────────────────────────────────────────────┤
│ Estado: PENDIENTE                            │
│ Solicitante: Juan Pérez                      │
│ Fecha: 26/09/2026 14:20                      │
│                                              │
│ RUTA DEL PROCESO                             │
│                                              │
│ ● COTIZACIÓN COT-00025   [VER]              │
│ │ $100.000.000                               │
│ ● PROYECTO TORRE 3       [VER]               │
│ ● REQUISICIÓN REQ-00008 [VER]                │
│ │ $35.000.000                                │
│ │ ⚠ 35% de Cotización                        │
│ ○ ÓRDENES DE COMPRA                          │
│                                              │
├───────────────────────────────────────────────┤
│ RESUMEN FINANCIERO                           │
│ Cotización:       $100M                      │
│ Requisiciones:     $35M                      │
│ OC comprometidas:   $0                       │
│ Disponible:        $65M                      │
├───────────────────────────────────────────────┤
│ [ RECHAZAR ]                [ APROBAR ]      │
└───────────────────────────────────────────────┘
```

---

# 15. RUTA VISUAL / GRAFO DEL PROCESO

La solicitud debe tener una vista visual tipo timeline + grafo:

```text
             COTIZACIÓN
                  │
                  ▼
               PROYECTO
                  │
                  ▼
              REQUISICIÓN
             ┌────┴─────┐
             ▼          ▼
           OC-31      OC-32
             │          │
             ▼          ▼
         RECEPCIÓN  RECEPCIÓN
```

Cada nodo debe ser interactivo.

Acciones:

```text
VER COTIZACIÓN
VER PROYECTO
VER REQUISICIÓN
VER ORDEN
VER FACTURA
VER CXP
```

Cada documento se abre desde su propio SSoT, mediante Offcanvas/HTMX existente.

---

# 16. SERVICIO DE TRAZABILIDAD

Crear, si no existe equivalente:

```text
ApprovalTraceService
```

Responsabilidad exclusivamente de lectura:

```text
Solicitud
 ↓
resolver documentos relacionados
 ↓
construir nodos
 ↓
construir relaciones
 ↓
calcular resumen
 ↓
retornar DTO
```

No escribir en dominios ajenos.

Contrato conceptual:

```json
{
  "request": {},
  "origin": {},
  "nodes": [],
  "relations": [],
  "timeline": [],
  "financial_summary": {},
  "alerts": []
}
```

---

# 17. CONTROL FINANCIERO COTIZACIÓN → REQUISICIONES

Implementar una única regla:

```text
SUM(Requisiciones activas asociadas a la Cotización)
                 <=
          TOTAL COTIZACIÓN
```

Ejemplo:

```text
COT-00025 = $100M

REQ1 = $60M
REQ2 = $30M
REQ3 = $20M

TOTAL REQUISICIONES = $110M
EXCESO = $10M
```

Mostrar:

```text
🔴 EXCESO SOBRE COTIZACIÓN

Las requisiciones superan en $10.000.000
el valor autorizado de la Cotización.
```

---

# 18. ALERTA Y BLOQUEO

Separar:

### ALERTA

Cuando el uso se acerca al límite, utilizar la configuración real existente; no hardcodear en JS.

### BLOQUEO

Cuando:

```text
SUM(Requisiciones) > Total Cotización
```

no permitir aprobar la nueva Requisición.

El administrador debe visualizar la razón.

---

# 19. QUÉ REQUISICIONES CUENTAN

Auditar los estados reales y definir/documentar cuáles representan compromiso presupuestal.

Como hipótesis a verificar:

```text
PENDIENTE_APROBACION
APROBADA
EN_PROCESO_COMPRA
PARCIALMENTE_ATENDIDA
ATENDIDA
```

y excluir si corresponde:

```text
RECHAZADA
CANCELADA
```

No asumir esta clasificación sin validar la semántica real del código.

---

# 20. SERVICIO CENTRAL DE CONTROL FINANCIERO

Crear/adaptar un único componente:

```text
ProcurementBudgetControlService
```

o reutilizar el equivalente existente.

Debe resolver:

```text
obtener_resumen_cotizacion()
obtener_resumen_requisicion()
obtener_saldo_cotizacion()
obtener_saldo_requisicion()
validar_requisicion()
validar_orden_compra()
validar_consolidacion_oc()
```

Evitar un mega-service si ya existe lógica equivalente distribuida de forma correcta.

Regla arquitectónica:

```text
UNA REGLA
UNA IMPLEMENTACIÓN
MUCHOS CONSUMIDORES
```

---

# 21. NUEVA ORDEN DE COMPRA — BUSCAR REQUISICIONES

Modificar Nueva Orden de Compra.

Primer paso:

```text
[ Buscar Requisiciones ]
```

Permitir selección múltiple:

```text
☑ REQ-00008   Equipos       $35M
☑ REQ-00009   Materiales    $25M
☐ REQ-00010   Mano de obra  $15M
```

Mostrar:

```text
Total disponible seleccionado: $60M
```

Luego construir la OC.

---

# 22. REGLAS DE AGRUPACIÓN DE REQUISICIONES EN UNA OC

Antes de consolidar:

1. Mismo tenant.
2. Todas aprobadas.
3. Ninguna cancelada/cerrada incompatiblemente.
4. Todas con saldo.
5. Líneas válidas.
6. Si existe proveedor obligatorio en Requisición, debe ser compatible con el proveedor de la OC.
7. La asignación de cada Requisición no supera su saldo.
8. La OC no supera la suma de saldos seleccionados.
9. Si todas pertenecen a una Cotización, no se supera el saldo de la Cotización.
10. Si se mezclan Cotizaciones distintas, auditar y bloquear cuando el dominio real considere incompatibles los presupuestos.

---

# 23. CONTROL POR REQUISICIÓN

Para cada Requisición:

```text
valor_requisicion
    -
OC válidas asociadas
    =
saldo_requisicion
```

Debe existir:

```text
comprometido_requisicion <= valor_requisicion
```

Nunca permitir consumo negativo ni doble consumo.

---

# 24. CONTROL DE LA OC CONSOLIDADA

Para una OC con N Requisiciones:

```text
TOTAL OC
   <=
SUM(saldos disponibles de Requisiciones)
```

Y simultáneamente:

```text
por cada Requisición:
consumo nuevo <= saldo individual
```

Esto evita que una sola OC compense artificialmente el exceso de otra Requisición.

---

# 25. CONCURRENCIA

Las operaciones que consuman presupuesto deben usar transacciones y locks sobre el agregado correcto.

Mínimo:

```python
transaction.atomic()
select_for_update()
```

Casos:

```text
crear OC
editar OC
cancelar/anular OC
aprobar Requisición
```

Debe impedirse:

```text
Cotización $100M
Saldo $10M

Usuario A consume $10M
Usuario B consume $10M

RESULTADO PROHIBIDO = $110M
```

---

# 26. APROBAR DESDE DASHBOARD

Nunca hacer:

```python
objeto.estado = "APROBADA"
```

directamente desde el ViewSet.

El flujo debe ser:

```text
ApprovalService.aprobar()
        ↓
revalidación
        ↓
permisos
        ↓
DSV
        ↓
control financiero
        ↓
BusinessService del dominio
        ↓
historial
```

Para Requisición:

```text
PENDIENTE_APROBACION
      ↓
ApprovalService.aprobar()
      ↓
RequisicionBusinessService.aprobar()
      ↓
APROBADA
```

---

# 27. RECHAZO

Acción:

```text
[ RECHAZAR ]
```

Debe exigir:

```text
Motivo
```

Guardar:

```text
usuario
fecha
motivo
estado anterior/nuevo
valor
snapshot
```

No eliminar solicitud.

---

# 28. IDEMPOTENCIA DE APROBACIÓN

Si se aprueba dos veces por concurrencia o doble clic:

```text
una sola decisión
una sola transición efectiva
sin duplicar efectos financieros
```

Usar `select_for_update()` y constraints/guards apropiados.

---

# 29. PERMISOS

Solo ADMIN debe poder acceder inicialmente al Centro de Aprobaciones, utilizando el sistema central de roles/permisos real.

No usar `is_staff` como único criterio.

Cada acción debe volver a verificar permisos en backend.

---

# 30. SEGURIDAD MULTITENANT

Siempre:

```text
usuario
 ↓
membresía válida
 ↓
tenant actual
 ↓
solicitud
 ↓
documento origen
```

Nunca aceptar `empresa_id` arbitrario.

Aplicar DSV y OrganizationalScope.

---

# 31. API DEL CENTRO

Adaptar las rutas reales; conceptualmente:

```text
GET  /api/v1/dashboard/aprobaciones/
GET  /api/v1/dashboard/aprobaciones/{uuid}/
GET  /api/v1/dashboard/aprobaciones/{uuid}/trazabilidad/
POST /api/v1/dashboard/aprobaciones/{uuid}/aprobar/
POST /api/v1/dashboard/aprobaciones/{uuid}/rechazar/
```

Respetar `config/api_urls.py` como SSoT de endpoints.

No duplicar rutas.

---

# 32. API DE REQUISICIONES DISPONIBLES PARA OC

Crear/adaptar endpoint server-side para búsqueda:

```text
GET /api/v1/compras/requisiciones/disponibles-para-orden/
```

Debe devolver, como mínimo:

```text
uuid
numero
cotizacion
proyecto
valor_total
valor_comprometido
saldo
estado
```

Solo aptas para compra.

---

# 33. UX DE NUEVA OC

Flujo:

```text
Nueva OC
   ↓
Buscar Requisiciones
   ↓
selección múltiple
   ↓
ver saldos
   ↓
seleccionar líneas
   ↓
resumen financiero
   ↓
guardar
```

Mostrar:

```text
REQ-08  total $35M  saldo $15M
REQ-09  total $25M  saldo $10M

Disponible total $25M

OC $23M

Saldo $2M
```

Frontend solo ayuda a la UX; backend decide.

---

# 34. ALERTAS VISUALES

Crear estados coherentes con Design System:

```text
🟢 Dentro del presupuesto
🟡 Cerca del límite
🟠 Alta utilización
🔴 Exceso / bloqueo
```

No duplicar lógica de cálculo en JS.

---

# 35. NOTIFICACIONES

Al existir solicitudes pendientes:

```text
Dashboard
↓
Centro de Aprobaciones
↓
badge con cantidad real
```

Si existe sistema de notificaciones, integrarlo mediante servicio explícito.

No Signals de negocio.

---

# 36. DOCUMENTOS ASOCIADOS

Según relaciones reales disponibles mostrar:

```text
Cotización
Proyecto
Requisición
Ordenes de Compra
Recepciones
Factura
CXP
Inventario
```

No inventar relaciones.

Cada nodo debe mostrar estado, valor y fecha cuando exista ese dato.

---

# 37. PRESERVAR SSoT DE DOMINIOS

```text
Cotización       = origen comercial
Requisición      = solicitud/abastecimiento
OrdenCompra      = compra
Factura          = fiscal
CxP              = obligación
Inventario       = stock
Proyecto         = contexto operativo
Dashboard        = presentación/control
Approval SSoT    = workflow de aprobación
```

La aprobación no debe duplicar reglas de negocio de los dominios.

---

# 38. ARQUITECTURA DE SERVICIOS

Mantener:

```text
ViewSet
  ↓
ServiceMixin
  ↓
BusinessService
  ↓
CRUDService
```

Para trazabilidad:

```text
ViewSet
  ↓
Trace Service
  ↓
Selectors de dominios
```

El ViewSet no calcula presupuestos ni cambia estados directamente.

La arquitectura vigente especifica esta separación de responsabilidades. fileciteturn99file5L1-L20

---

# 39. MIGRACIÓN DEL FK ACTUAL

La arquitectura registra que la obligatoriedad de la Requisición para nuevas OC fue activada recientemente y que el modelo actual todavía tiene `OrdenCompra.requisicion` como FK. fileciteturn98file0L5-L10

La nueva solución deberá:

```text
FK único
   ↓
relación N:N
```

Antes de retirar el FK:

1. auditar históricos;
2. contar órdenes sin requisición;
3. determinar evidencia disponible;
4. migrar solo relaciones verificables;
5. no crear datos ficticios.

---

# 40. FASES DE IMPLEMENTACIÓN PARA LA IA EDITORA

## FASE 0 — INSPECT

Leer documentación y código real.

Entregar mapa de impacto interno.

No modificar.

## FASE 1 — DISEÑO DE DOMINIO

Resolver:

```text
Approval SSoT
OC ↔ Requisición N:N
reglas de estados
control financiero
concurrencia
tenant
migración histórica
```

## FASE 2 — MOTOR DE APROBACIONES

Implementar si no existe:

```text
SolicitudAprobacion
Historial
Registry de tipos
Servicios
Permisos
```

## FASE 3 — N:N COMPRAS

Implementar:

```text
OrdenCompraRequisicion
```

y origen por línea donde sea viable.

## FASE 4 — CONTROL FINANCIERO

Implementar SSoT de:

```text
Cotización
→ Requisiciones
→ OC
→ saldos
→ alertas/bloqueos
```

## FASE 5 — FLUJO DE APROBACIÓN

Implementar:

```text
enviar
aprobar
rechazar
historial
snapshot
revalidación
```

## FASE 6 — TRAZABILIDAD

Implementar:

```text
ApprovalTraceService
DTO
Timeline
Grafo
Offcanvas de detalles
```

## FASE 7 — API

Agregar endpoints del centro y búsqueda de Requisiciones para OC.

## FASE 8 — DASHBOARD

Construir:

```text
banner
KPI
bandeja
filtros
alertas
```

## FASE 9 — DETALLE INTERACTIVO

Ruta visual con ventanas/offcanvas para Cotización, Proyecto, Requisición, OC y demás documentos reales.

## FASE 10 — NUEVA OC

Nuevo flujo:

```text
Buscar Requisiciones
→ seleccionar varias
→ validar saldos
→ construir OC
```

## FASE 11 — INTEGRACIONES

Preservar:

```text
Cotizaciones
Proyectos
Compras
Recepciones
CxP
Facturas
Inventario
```

## FASE 12 — DOCUMENTACIÓN

Actualizar:

```text
arquitectura general
compras
requisiciones
dashboard
API/OpenAPI
```

## FASE 13 — AUTOAUDITORÍA

Buscar y corregir:

- bypass de aprobación;
- bypass de límites;
- carreras de concurrencia;
- fuga cross-tenant;
- duplicación de lógica;
- inconsistencias de estados;
- errores de migración;
- inconsistencias frontend/backend;
- rutas API duplicadas;
- Dashboard convertido incorrectamente en SSoT de Compras.

---

# 41. NO EJECUTAR TESTS

Esta misión tiene una instrucción expresa:

**NO ejecutar tests ni pruebas E2E automáticamente.**

No ejecutar:

```text
pytest
manage.py test
Playwright
```

La validación automatizada la realizará manualmente el usuario.

---

# 42. ÚLTIMO PASO — SOLO ENTREGAR COMANDOS

Después de completar implementación + autoauditoría + documentación, la IA editora debe detenerse y entregar únicamente los comandos recomendados para ejecución manual.

No ejecutar ninguno.

Ajustar las rutas a las apps realmente existentes.

Comandos orientativos:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
python manage.py migrate_schemas --shared
python manage.py migrate_schemas --tenant
pytest apps/tenant/compras/requisiciones/tests
pytest apps/tenant/compras/tests
pytest apps/tenant/dashboard/tests
pytest apps/tenant/cotizaciones/tests
```

Si el repositorio requiere otra secuencia real, entregarla en lugar de inventar comandos.

**La IA NO debe ejecutar esos comandos.**

---

# CRITERIOS DE ACEPTACIÓN

La misión queda implementada cuando exista:

1. Dashboard → Centro de Aprobaciones.
2. Banner con pendientes y alertas reales.
3. Bandeja server-side.
4. Requisición → Enviar para aprobación.
5. ADMIN → revisar → ver ruta → aprobar/rechazar.
6. Trazabilidad Cotización/Proyecto/Requisición/OC y demás relaciones reales.
7. `OrdenCompra` nueva exige al menos una Requisición.
8. Una OC puede asociar varias Requisiciones.
9. Una Requisición puede consumirse en varias OC cuando tenga saldo.
10. Control por Requisición.
11. Control acumulado por Cotización.
12. Alerta y bloqueo cuando las Requisiciones superen la Cotización.
13. Control de concurrencia.
14. Historial append-only.
15. Snapshot/revalidación antes de aprobar.
16. Permisos ADMIN en backend.
17. Tenant isolation y DSV.
18. Sin Signals para negocio.
19. Sin duplicación de SSoT.
20. API/OpenAPI/documentación actualizadas.
21. No se ejecutaron tests; solo se entregaron los comandos finales.

---

# VISIÓN FINAL

```text
                         ┌───────────────────────────┐
                         │         DASHBOARD         │
                         │   CENTRO DE APROBACIONES │
                         └─────────────┬─────────────┘
                                       │
                              SOLICITUD PENDIENTE
                                       │
                                       ▼
                           ┌───────────────────────┐
                           │  RUTA + GRAFO + KPI   │
                           └───────────┬───────────┘
                                       │
            ┌──────────────────────────┼─────────────────────────┐
            ▼                          ▼                         ▼
       COTIZACIÓN                   PROYECTO                 REQUISICIÓN
            │                          │                         │
            └──────────────────────────┴─────────────────────────┘
                                       │
                               APROBAR / RECHAZAR
                                       │
                                       ▼
                              REQUISICIÓN APROBADA
                                       │
                         ┌─────────────┴─────────────┐
                         ▼                           ▼
                       OC-001                      OC-002
                   REQ-001/002                   REQ-003
                         │                           │
                         └─────────────┬─────────────┘
                                       ▼
                              RECEPCIÓN / CXP /
                                INVENTARIO

CONTROLES:

REQUISICIONES <= COTIZACIÓN TOTAL
OC <= SALDO DE REQUISICIONES
NUNCA OC SIN REQUISICIÓN
```

El resultado debe sentirse como un **centro de control de procesos de un ERP**, permitiendo al administrador aprobar con contexto completo y mantener trazabilidad financiera desde la Cotización hasta la ejecución de Compras.
