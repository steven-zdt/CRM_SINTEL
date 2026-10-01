# PROMPT — CORRECCIÓN DE LÓGICA DE NEGOCIO
# COTIZACIÓN → REQUISICIÓN → COMPRA
## CRM_SINTEL / SINTEL ERP

Actúa como arquitecto y desarrollador senior del repositorio real `CRM_SINTEL`.

OBJETIVO:
Corregir e implementar en código la regla de negocio definitiva:

COTIZACIÓN ACEPTADA
        ↓ 1:1
REQUISICIÓN
        ↓ 1:N
ORDEN(ES) DE COMPRA
        ↓
RECEPCIÓN
        ↓
INVENTARIO
        ↓
FACTURA / CXP
        ↓
CONTABILIDAD

## 1. REGLA DE NEGOCIO DEFINITIVA

La única relación obligatoria de una Requisición es la Cotización origen.

```text
Requisición
├── cotizacion  OBLIGATORIA
├── proyecto    OPCIONAL
└── factura     OPCIONAL
```

NO debe existir una Requisición creada independientemente.

NO debe permitirse:
- crear Requisición sin Cotización;
- crear Requisición desde Cotización no aceptada;
- cambiar posteriormente la Cotización origen mediante PATCH;
- reutilizar una misma Cotización aceptada para crear dos Requisiciones.

Regla cardinal:

```text
1 Cotización ACEPTADA = máximo 1 Requisición
1 Requisición = exactamente 1 Cotización
1 Requisición = 1..N Ordenes de Compra
```

## 2. SSoT REAL DE COTIZACIONES

Antes de modificar, inspecciona el código real de:

```text
apps/tenant/cotizaciones/
```

La implementación actual usa una máquina de estados y el estado real que representa aceptación es:

```text
ACEPTADA
```

NO crear ni renombrar estados a `APROBADA` sin evidencia real del código actual.

Para esta integración:

```python
Cotizacion.Estado.ACEPTADA
```

es la condición habilitante.

NO modificar `CotizacionService.convertir_a_venta()` ni mezclar el flujo comercial `Cotizacion → Venta` con abastecimiento.

## 3. ORIGEN DE LA REQUISICIÓN

La Requisición debe crearse únicamente mediante una operación de dominio tipo:

```python
RequisicionBusinessService.crear_desde_cotizacion(...)
```

Ambos caminos deben terminar en el mismo servicio:

```text
Cotización → Crear Requisición
Compras → Buscar Cotización → Crear Requisición
```

Nunca duplicar la lógica en ViewSet, frontend, MCP o AI tools.

## 4. LISTADO DE REQUISICIONES

Dentro de:

```text
workspace/#compras
```

crear/integrar la pestaña:

```text
Requisiciones
```

Agregar botón:

```text
Vincular Cotización
```

o:

```text
Nueva Requisición desde Cotización
```

Al pulsarlo, abrir buscador de Cotizaciones.

El buscador debe mostrar exclusivamente:

```text
empresa actual
+
estado = ACEPTADA
+
sin Requisición existente
```

Permitir buscar por:

```text
numero_cotizacion
cliente
fecha
texto
```

con paginación server-side.

No cargar todas las cotizaciones al navegador.

## 5. UX OBLIGATORIA

Flujo:

```text
Requisiciones
    ↓
Vincular Cotización
    ↓
Buscar
    ↓
Seleccionar Cotización ACEPTADA
    ↓
crear Requisición
```

Después de seleccionar:

```text
Cotización: COT-00015
Estado: ACEPTADA
```

mostrar datos derivados de la Cotización y permitir únicamente completar los campos opcionales:

```text
Proyecto [opcional]
Factura  [opcional]
Observaciones
```

Los items deben originarse de `CotizacionItem`.

No exigir al usuario reconstruir manualmente la Requisición.

## 6. MODELO

Crear el submódulo dentro de Compras siguiendo la arquitectura real existente:

```text
apps/tenant/compras/requisiciones/
```

No crear un módulo paralelo fuera de Compras.

Usar `SintelTenantBaseModel` o `SedeAwareModel` según la decisión organizacional real. No inventar una tercera base.

Modelos mínimos, sujetos a auditoría previa:

```text
RequisicionCompra
RequisicionCompraItem
RequisicionDocumento
RequisicionHistorialEstado
```

La entidad principal debe tener una relación obligatoria con `Cotizacion`.

Preferir integridad de BD:

```text
UniqueConstraint(empresa, cotizacion)
```

si es compatible con el modelo real.

No usar solamente:

```python
if exists()
```

para prevenir duplicados.

## 7. INTEGRIDAD DE COTIZACIÓN

Al crear desde una Cotización:

1. resolver tenant/empresa;
2. resolver Cotización;
3. verificar `empresa_id`;
4. verificar permisos;
5. bloquear la Cotización con `select_for_update()` si aplica;
6. verificar `estado == ACEPTADA`;
7. verificar que no exista Requisición;
8. crear Requisición;
9. crear sus items;
10. registrar historial;
11. commit atómico.

Usar:

```text
transaction.atomic()
+
select_for_update()
+
UniqueConstraint
```

cuando corresponda.

## 8. IDEMPOTENCIA

Si dos llamadas simultáneas intentan:

```text
crear Requisición desde COT-00015
```

el resultado debe ser:

```text
1 sola Requisición
```

Nunca 2.

La operación debe ser idempotente según el contrato API del proyecto:

```text
primera llamada → crea
segunda llamada → devuelve existente
```

o `409 Conflict` si esa es la convención establecida; elegir una sola estrategia y documentarla.

## 9. ORIGEN INMUTABLE

Una vez creada:

```text
REQ-00008 ← COT-00015
```

no permitir:

```text
PATCH cotizacion=COT-00016
```

El origen es histórico y debe quedar inmutable.

Si se necesita otra Cotización:

```text
cancelar Requisición
crear nueva Requisición
```

según workflow.

## 10. PROYECTO

`Proyecto` es OPCIONAL.

Debe poder existir:

```text
Cotización
→ Requisición
```

sin Proyecto.

También:

```text
Cotización
→ Requisición
→ Proyecto
```

si corresponde.

Validar siempre:

```text
misma empresa/tenant
+
DSV
+
OrganizationalScope
```

pero no hacer obligatorio el proyecto.

## 11. FACTURA

`Factura` es OPCIONAL.

Casos válidos:

```text
Cotización
→ Requisición
→ OrdenCompra
```

sin factura.

O:

```text
Cotización
→ Requisición
→ Factura existente
```

O:

```text
Cotización
→ Requisición
→ OrdenCompra
→ Factura posterior
```

Facturas continúa siendo SSoT fiscal.

No duplicar en Requisición datos fiscales como CUFE, XML, estado DIAN, etc., salvo snapshot explícitamente justificado.

## 12. CENTRO DE COSTOS

NO llamar a la Requisición “Centro de Costos”.

La Requisición es:

```text
expediente/origen/justificación de abastecimiento
```

El Centro de Costos, si existe, pertenece al SSoT contable.

Antes de crear cualquier campo:

```text
auditar apps/tenant/contabilidad/
auditar apps/tenant/gastos/
auditar apps/tenant/proyectos/
```

Si existe SSoT:

```text
Requisición → referencia a CentroCosto
```

Si no existe:

```text
DEFERRED
```

No inventar un nuevo sistema de centros de costo dentro de Compras.

## 13. ORDEN DE COMPRA

A partir de esta modificación, toda NUEVA OrdenCompra debe requerir una Requisición válida:

```text
requisicion existe
+
requisicion pertenece a empresa
+
requisicion.cotizacion existe
+
cotizacion.estado == ACEPTADA
```

Auditar TODOS los puntos de creación:

```text
ViewSet
BusinessService
CRUDService
imports
tasks
management commands
document intake
MCP
AI tools
```

No permitir un bypass.

Frontend solo ayuda al UX.

Backend debe imponer la regla.

DB debe proteger integridad cuando sea posible.

## 14. MULTIPLES ORDENES

Debe soportarse:

```text
REQ-00008
 ├── OC-00031
 ├── OC-00032
 └── OC-00033
```

Esto permite dividir una misma necesidad entre varios proveedores.

Por tanto:

```text
Requisición → OrdenCompra = 1:N
```

## 15. ATENCIÓN PARCIAL

La Requisición debe permitir seguimiento:

```text
solicitado
ordenado
recibido
pendiente
```

No agregar campos redundantes si pueden derivarse de las Ordenes/Recepciones.

Preferir SSoT transaccional + selectors/aggregates.

Ejemplo:

```text
REQ: 100 unidades
OC1: 60
OC2: 40
=> ATENDIDA
```

y:

```text
REQ: 100
OC1: 60
=> PARCIALMENTE_ATENDIDA
```

## 16. STATES

Definir máquina de estados separada de Cotización:

```text
BORRADOR
PENDIENTE_APROBACION
APROBADA
RECHAZADA
EN_PROCESO_COMPRA
PARCIALMENTE_ATENDIDA
ATENDIDA
CANCELADA
```

Pero no confundir:

```text
Cotización ACEPTADA
```

con:

```text
Requisición APROBADA
```

La primera significa aceptación comercial.

La segunda significa aprobación interna de abastecimiento, si el workflow interno la requiere.

No inventar una segunda aprobación si el negocio real no la necesita; primero revisar contratos existentes.

## 17. SERVICE LAYER

Seguir la estructura vigente:

```text
requisiciones/
├── services/
│   ├── business_service.py
│   ├── crud_service.py
│   ├── selectors.py
│   ├── api_mixins.py
│   └── __init__.py
├── api/
│   ├── serializers.py
│   ├── viewsets.py
│   ├── urls.py
│   └── __init__.py
├── models.py
└── ...
```

No colocar reglas complejas en serializers.

No colocar lógica de negocio en JavaScript.

No usar Django Signals.

## 18. API

Auditar primero las convenciones del router actual.

Como base:

```text
GET  /api/v1/compras/requisiciones/
POST /api/v1/compras/requisiciones/
GET  /api/v1/compras/requisiciones/{uuid}/
PATCH /api/v1/compras/requisiciones/{uuid}/
DELETE /api/v1/compras/requisiciones/{uuid}/
```

Acciones de dominio:

```text
GET  /api/v1/compras/requisiciones/cotizaciones-disponibles/
POST /api/v1/compras/requisiciones/from-cotizacion/
POST /api/v1/compras/requisiciones/{uuid}/crear-orden/
GET  /api/v1/compras/requisiciones/{uuid}/ordenes/
GET  /api/v1/compras/requisiciones/{uuid}/historial/
```

No crear endpoints duplicados si ya existe un patrón equivalente.

## 19. DOCUMENTOS

La Requisición puede centralizar documentos, pero sin convertirlos todos en relaciones obligatorias.

Tipos posibles:

```text
COTIZACION
FACTURA
PROYECTO
DOCUMENTO_SOPORTE
OTRO
```

La Cotización origen NO debe tratarse como simple adjunto: es la relación de negocio principal.

## 20. MULTITENANT / IDOR

Bloquear:

```text
Tenant A → Cotización Tenant B
Tenant A → Requisición Tenant B
Tenant A → Proyecto Tenant B
Tenant A → Factura Tenant B
```

Aplicar:

```text
empresa_id
DSV
OrganizationalScope
permissions
UUID lookup
```

Nunca confiar en `empresa_id` enviado por frontend.

## 21. HISTORIAL

Crear/usar historial append-only para:

```text
CREADA_DESDE_COTIZACION
PENDIENTE_APROBACION
APROBADA
RECHAZADA
EN_PROCESO_COMPRA
PARCIALMENTE_ATENDIDA
ATENDIDA
CANCELADA
```

Registrar:

```text
estado anterior
estado nuevo
usuario
fecha
comentario
```

No borrar historia.

## 22. MIGRACIONES

Antes de modificar `OrdenCompra`, auditar datos históricos.

Si existen órdenes antiguas sin Requisición:

```text
NO inventar vínculos.
```

Aplicar estrategia compatible:

```text
requisicion nullable inicialmente
↓
nuevas órdenes requieren requisición
↓
backfill solo con evidencia real
↓
NOT NULL solamente si históricamente es seguro
```

No romper registros existentes.

## 23. FRONTEND — NO DUPLICAR INFRAESTRUCTURA

Reutilizar las convenciones actuales de Compras:

```text
tab
server-side grid
offcanvas
event delegation
HTMX
namespace JS
Sintel/Core helpers
```

No duplicar `assets`.

No cargar dos veces scripts.

No crear un segundo sistema HTTP/API.

## 24. OPENAPI

Documentar:

```text
Cotización requerida
Proyecto opcional
Factura opcional
```

y las acciones:

```text
from-cotizacion
cotizaciones-disponibles
crear-orden
```

## 25. AI / MCP

No crear WRITE tools nuevas automáticamente.

La regla existente del AI Engine debe seguir aplicando.

Si en el futuro existe:

```text
crear_requisicion
crear_orden
aprobar_requisicion
```

deben ser:

```text
tenant-scoped
permission-aware
auditadas
riesgo explícito
```

No habilitar WRITE solo por crear endpoints.

## 26. ORDEN DE IMPLEMENTACIÓN

### FASE 0 — INSPECCIÓN

Auditar primero:

```text
cotizaciones
compras
proyectos
facturas
proveedores
inventario
contabilidad
```

Buscar:

```text
modelos
services
selectors
ViewSets
URLs
templates
JS
migrations
imports
consumidores
EKG
```

NO ejecutar tests.

### FASE 1 — DISEÑO Y MODELOS

Implementar Requisición y relación obligatoria con Cotización.

Definir constraints.

NO ejecutar tests.

### FASE 2 — SERVICE LAYER

Implementar:

```text
crear_desde_cotizacion()
cotizaciones_disponibles()
crear_orden_desde_requisicion()
progreso
workflow
idempotencia
locking
```

NO ejecutar tests.

### FASE 3 — API

Implementar endpoints y permisos.

NO ejecutar tests.

### FASE 4 — FRONTEND

Implementar búsqueda desde listado de Requisiciones.

NO ejecutar tests.

### FASE 5 — ORDEN DE COMPRA

Hacer obligatoria Requisición para nuevas OC.

Eliminar bypasses.

NO ejecutar tests.

### FASE 6 — DOCUMENTACIÓN

Actualizar arquitectura y documentos de Compras.

NO ejecutar tests.

### FASE 7 — AUTOAUDITORÍA

Revisar repo-wide:

```text
no requisición sin cotización
no cotización no aceptada
no reutilización
no cambio de origen
proyecto opcional
factura opcional
no bypass de OC
no cross-tenant
no signal
no duplicación SSoT
```

NO ejecutar tests.

## 27. DETENCIÓN PARA AUTORIZACIÓN

Cuando las fases anteriores estén completamente implementadas, detenerse y pedir ÚNICAMENTE autorización para ejecutar tests.

Mensaje:

```text
IMPLEMENTACIÓN DE COTIZACIÓN → REQUISICIÓN → COMPRA COMPLETADA.

La autoauditoría de código e integración está terminada.

La única fase pendiente es TESTING.

¿AUTORIZAS EJECUTAR LOS TESTS?
```

No ejecutar pytest ni suite de integración antes de esa autorización.

## 28. FASE FINAL — TESTS

Después de autorización ejecutar pruebas para:

### Cotización

```text
ACEPTADA → permite
BORRADOR → bloquea
ENVIADA → bloquea
RECHAZADA/CANCELADA/ARCHIVADA → bloquea
```

usando únicamente los estados realmente existentes en el código.

### Requisición

```text
sin cotización → bloquea
cotización inválida → bloquea
cross tenant → bloquea
cotización duplicada → evita duplicado
cambio de cotización → bloquea
```

### Relación

```text
1 cotización → 1 requisición
1 requisición → N ordenes
```

### Opcionales

```text
sin proyecto → válido
sin factura → válido
```

### Orden

```text
OC sin requisición → bloquea
OC con requisición válida → permite
OC con cotización origen no aceptada → bloquea
```

### Concurrencia

Simular dos solicitudes simultáneas sobre la misma Cotización ACEPTADA.

Esperado:

```text
1 Requisición
```

### Integración

```text
Requisición
→ Orden
→ Recepción
→ Inventario
```

sin regresiones.

### Seguridad

```text
IDOR
cross tenant
permissions
organizational scope
```

### Checks finales

```text
python manage.py check
python manage.py makemigrations --check --dry-run
```

y la suite de regresión del proyecto según su infraestructura vigente.

## 29. REPARACIÓN POST-TEST

Si hay fallos reales:

```text
analizar
→ clasificar
→ corregir código
→ revisar impacto
→ repetir tests
```

No modificar tests para ocultar regresiones.

## 30. CRITERIO DE CIERRE

Marcar:

```text
COTIZACION_REQUISICION = COMPLETED
```

solo cuando:

```text
[ ] Cotización ACEPTADA origina Requisición
[ ] Cotización no ACEPTADA es rechazada
[ ] una Cotización no puede originar dos Requisiciones
[ ] Cotización es relación obligatoria
[ ] Proyecto es opcional
[ ] Factura es opcional
[ ] origen es inmutable
[ ] Requisición soporta N Ordenes
[ ] OC nueva requiere Requisición
[ ] atención parcial funciona
[ ] DSV funciona
[ ] tenant isolation funciona
[ ] concurrencia funciona
[ ] idempotencia funciona
[ ] no existe bypass
[ ] no se usan Signals de negocio
[ ] Service Layer es SSoT
[ ] búsqueda de Cotizaciones ACEPTADAS funciona
[ ] Cotizaciones usadas no aparecen como disponibles
[ ] documentación actualizada
[ ] tests finales verdes
```

## 31. PRINCIPIO FINAL

No implementar:

```text
Requisición → Cotización opcional
```

La regla correcta es:

```text
COTIZACIÓN ACEPTADA
        ↓
      1:1
        ↓
   REQUISICIÓN
        ↓
      1:N
        ↓
 ORDEN DE COMPRA
```

Proyecto y Factura son contexto opcional.

La Cotización ACEPTADA es el único origen obligatorio de la Requisición.
