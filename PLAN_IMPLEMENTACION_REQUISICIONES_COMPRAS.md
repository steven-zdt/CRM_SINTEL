# PLAN DE IMPLEMENTACIÓN — SUBMÓDULO REQUISICIONES EN COMPRAS
## CRM_SINTEL — SINTEL ERP

**Fecha:** 2026-09-25  
**Módulo padre:** `apps/tenant/compras/`  
**Submódulo nuevo:** `apps/tenant/compras/requisiciones/`  
**Objetivo:** convertir la Requisición en el documento formal que origina y justifica el abastecimiento y que debe existir antes de crear una Orden de Compra.

---

# 0. INSTRUCCIONES OPERATIVAS PARA LA IA EDITORA

## 0.1 Modo de ejecución

Trabajar en modo:

```text
INSPECT
  ↓
PLAN
  ↓
IMPLEMENT
  ↓
SELF-AUDIT
  ↓
CORRECT
  ↓
RE-AUDIT
  ↓
NEXT PHASE
```

Repetir este loop hasta cerrar todas las fases.

## 0.2 Regla crítica sobre tests

**NO EJECUTAR pytest, unittest, suite de tests, pruebas E2E ni pruebas de integración durante las fases de implementación.**

Los tests son la **última fase global**.

La IA editora debe:

1. implementar todas las fases anteriores;
2. hacer autoauditoría estática;
3. revisar referencias y consumidores;
4. comprobar que las migraciones propuestas estén coherentes;
5. llegar a la fase final de testing;
6. **pedir autorización explícita al usuario para ejecutar los tests**;
7. ejecutar los tests únicamente después de recibir autorización;
8. corregir los fallos encontrados;
9. repetir la validación final según corresponda.

No solicitar autorización para inspeccionar archivos, leer documentación, modificar código, crear migraciones, actualizar documentación ni ejecutar análisis estático que no constituya una suite de pruebas.

---

# 1. CONTEXTO REAL VERIFICADO

La documentación arquitectónica de SINTEL indica que el ciclo `Cotización → OrdenCompra → Inventario` permanece expresamente diferido porque `CotizacionItem` no dispone de una referencia confiable al catálogo real de Inventario. No se debe inventar un matching heurístico. [Arquitectura General v3.64.0, DOC-M51, §D]

También está documentado que:

- Cotizaciones tiene máquina de estados real y flujo `Cotizacion → Venta → Factura`.
- Compras actualmente administra `PlantillaOrdenCompra`, `OrdenCompra`, `ItemOrdenCompra`, `RecepcionCompra` y `RecepcionCompraItem`.
- Compras ya incorpora `proveedor`, `proyecto`, `documento_soporte`, `sede`, `area` y sincronización con Cuentas por Pagar.
- La Orden de Compra tiene validación de empresa/tenant, sede, área, proveedor, proyecto y documento soporte mediante DSV.
- La recepción confirmada alimenta Inventario.
- El módulo Compras ya utiliza Service Layer, Selectors, serializers, ViewSets y UUID como lookup.
- La documentación del módulo Compras indica expresamente que la creación de órdenes es actualmente el centro del flujo del módulo.

El documento de arquitectura también muestra que `Proyecto` ya tiene campos históricos como `factura_costo` y `factura_costo_numero`, descritos como “Factura (Centro de Costos)”. Esto **no debe confundirse** con una futura entidad contable `CentroCosto`.

---

# 2. DECISIÓN ARQUITECTÓNICA PRINCIPAL

## 2.1 La Requisición será el expediente de abastecimiento

La entidad nueva debe representar:

> “Necesidad formal de adquirir bienes o servicios, con su justificación, contexto organizacional, documentación soporte y trazabilidad del proceso de abastecimiento.”

Debe ser la **entidad origen** del proceso de Compras.

Flujo objetivo:

```text
NECESIDAD
   ↓
REQUISICIÓN
   ↓
APROBACIÓN
   ↓
COTIZACIÓN / SOPORTES
   ↓
ORDEN DE COMPRA
   ↓
RECEPCIÓN
   ↓
INVENTARIO / SERVICIO
   ↓
FACTURA / CUENTA POR PAGAR
   ↓
CONTABILIDAD
```

No asumir que todos los procesos recorren todos los pasos.

Ejemplos válidos:

```text
Requisición
   ↓
OrdenCompra
```

```text
Requisición
   ↓
Cotización
   ↓
OrdenCompra
```

```text
Requisición
   ↓
OrdenCompra
   ↓
Factura
```

```text
Requisición
   ↓
Proyecto
   ↓
Cotización
   ↓
OrdenCompra
   ↓
Recepción
   ↓
Factura
```

---

# 3. IMPORTANTE — NO LLAMAR A LA REQUISICIÓN “CENTRO DE COSTOS”

La intención funcional del usuario es que la Requisición centralice todas las dependencias de un proceso.

Eso es correcto.

Pero arquitectónicamente debe distinguirse:

```text
REQUISICIÓN
= expediente / origen / contexto del abastecimiento
```

de:

```text
CENTRO DE COSTOS
= dimensión contable/financiera
```

La Requisición puede contener o vincular un centro de costo, pero no debe convertirse en el centro de costos contable.

Diseño recomendado:

```text
Requisición
 ├── contexto de abastecimiento
 ├── justificación
 ├── solicitante
 ├── sede
 ├── área
 ├── proyecto
 ├── cotizaciones
 ├── facturas/soportes
 ├── órdenes de compra
 └── clasificación contable / centro de costo (si existe)
```

Si actualmente no existe una entidad `CentroCosto` real en Contabilidad, **no inventarla dentro de Compras**.

En su lugar, dejar una frontera explícita:

```text
centro_costo_id / centro_costo_codigo
```

solamente si existe un SSoT contable real.

Si no existe, documentar el campo como `deferred`.

---

# 4. OBJETIVO FUNCIONAL

Una Orden de Compra no debe poder crearse normalmente sin:

```text
Requisición aprobada
```

Excepción únicamente mediante una regla explícita para casos especiales, por ejemplo:

```text
COMPRA_URGENTE
```

o

```text
COMPRA_EXCEPCIONAL
```

La excepción debe quedar auditada y nunca ser un bypass silencioso.

Regla por defecto:

```text
OrdenCompra.requisicion = OBLIGATORIA
```

---

# 5. MODELO DE DOMINIO PROPUESTO

## 5.1 `RequisicionCompra`

Ubicación:

```text
apps/tenant/compras/requisiciones/models.py
```

Usar obligatoriamente:

```python
SedeAwareModel
```

si la requisición pertenece a una sede/área.

Nunca heredar directamente de:

```python
models.Model
```

ni crear una base paralela.

Campos mínimos recomendados:

```text
uuid
empresa
sede
area
numero_documento
fecha_solicitud
fecha_necesidad
solicitante
responsable_aprobacion
tipo
prioridad
estado
justificacion
observaciones
moneda
subtotal_estimado
impuestos_estimados
total_estimado
centro_costo_codigo / referencia contable (solo si existe SSoT)
created_at
updated_at
```

## 5.2 Estados

No usar un campo libre.

Propuesta:

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

Flujo:

```text
BORRADOR
   ↓
PENDIENTE_APROBACION
   ↓
APROBADA
   ↓
EN_PROCESO_COMPRA
   ↓
PARCIALMENTE_ATENDIDA
   ↓
ATENDIDA
```

Ramas:

```text
PENDIENTE_APROBACION → RECHAZADA
BORRADOR → CANCELADA
APROBADA → CANCELADA
```

No permitir saltos arbitrarios.

---

# 6. NUMERACIÓN

La Requisición debe disponer de numeración propia.

No reutilizar:

```text
numero_documento de OrdenCompra
```

ni:

```text
consecutivo de Cotizacion
```

Recomendación:

```text
REQ-000001
REQ-000002
...
```

Crear un mecanismo similar a las plantillas actuales, pero verificar primero si el sistema ya dispone de un SSoT reutilizable para numeración antes de crear otra abstracción.

Reglas:

```text
unique(empresa, numero_documento)
```

y asignación atómica.

Mantener:

```text
transaction.atomic()
+
select_for_update()
```

donde corresponda.

La documentación actual de Compras ya identifica el consecutivo de OrdenCompra como un área sensible a concurrencia; la Requisición debe nacer con la misma protección.

Django permite expresar integridad con `UniqueConstraint` y `CheckConstraint`, y PostgreSQL debe recibir dichas invariantes siempre que puedan garantizarse a nivel de base de datos.

---

# 7. MODELO DE LÍNEAS

Crear:

```text
RequisicionCompraItem
```

Campos:

```text
uuid
requisicion
descripcion
item_inventario_uuid
item_inventario_tipo
cantidad
unidad_medida
valor_unitario_estimado
porcentaje_iva
valor_iva_estimado
subtotal_estimado
total_estimado
observaciones
```

`item_inventario_uuid` puede continuar siendo soft reference si esa es la política vigente del dominio.

No crear una FK cruzada artificial solamente para llenar un requisito.

---

# 8. JUSTIFICACIÓN Y SOPORTES

La Requisición debe poder registrar por qué existe.

Agregar:

```text
justificacion
observaciones
```

La documentación soporte debe ser extensible.

No crear una columna nueva por cada documento si se prevé crecimiento.

Crear un submodelo:

```text
RequisicionDocumento
```

con:

```text
uuid
requisicion
tipo
nombre
numero_referencia
documento_uuid
archivo
descripcion
created_at
```

Tipos iniciales:

```text
COTIZACION
FACTURA
PROYECTO
ORDEN_INTERNA
DOCUMENTO_SOPORTE
OTRO
```

Pero distinguir:

```text
documento interno real
```

de:

```text
documento externo adjunto
```

No asumir que todos los documentos tienen un UUID de otro módulo.

---

# 9. REFERENCIAS TRANSVERSALES

## 9.1 Regla principal

La Requisición debe centralizar referencias, pero sin crear acoplamiento indiscriminado entre todos los módulos.

Usar primero relaciones directas donde la relación sea estable y semánticamente necesaria.

Ejemplos:

```text
RequisicionCompra → Proyecto
RequisicionCompra → Cotizacion
RequisicionCompra → Factura
RequisicionCompra → OrdenCompra
```

pero antes de añadir cada FK:

1. comprobar modelo real;
2. comprobar ciclo de importación;
3. comprobar política SSoT;
4. comprobar `on_delete`;
5. comprobar tenant isolation;
6. comprobar que no se duplica una relación existente.

---

# 10. RECOMENDACIÓN PARA CENTRALIZAR MUCHAS REFERENCIAS

Como una requisición puede terminar teniendo:

```text
1..N cotizaciones
1..N facturas
1..N órdenes
0..N proyectos relacionados
```

no limitar la arquitectura a columnas únicas.

Crear un patrón de relación explícito cuando sea necesario:

```text
RequisicionCotizacion
RequisicionFactura
RequisicionOrdenCompra
```

Cada relación debe tener:

```text
uuid
requisicion
documento_origen
tipo_relacion
es_principal
observacion
created_at
```

No crear `GenericForeignKey` como primera opción.

La prioridad debe ser:

```text
FK real
>
soft reference controlada
>
relación genérica solo como último recurso documentado
```

La integridad referencial real debe utilizarse cuando la relación lo permita.

---

# 11. RELACIÓN CON PROYECTOS

El proyecto debe ser un contexto de negocio, no convertirse en el dueño de la requisición.

Relación:

```text
Proyecto
   ↑
   │
Requisición
   │
   ├── items
   ├── cotizaciones
   ├── compras
   └── soportes
```

Puede haber:

```text
0..N requisiciones por proyecto
```

No asumir:

```text
1 proyecto = 1 requisición
```

---

# 12. RELACIÓN CON COTIZACIONES

La documentación actual confirma que Cotización ya tiene máquina de estados y ciclo comercial formal, mientras el tramo de abastecimiento Cotización→OrdenCompra continúa diferido.

Por tanto:

**NO modificar CotizacionService.convertir_a_venta().**

El nuevo flujo debe agregarse como flujo paralelo:

```text
Requisición
   ↓
Cotización de compra / soporte de proveedor
   ↓
Requisición aprobada
   ↓
OrdenCompra
```

No reutilizar ciegamente una Cotización comercial de cliente como si fuera una cotización de proveedor.

Primero determinar el tipo de cotización real existente en SINTEL.

Si el sistema solo tiene la Cotización comercial de cliente:

```text
NO convertirla semánticamente en cotización de compra.
```

Crear una relación de soporte o introducir un concepto separado únicamente si la auditoría del dominio confirma que hace falta.

---

# 13. RELACIÓN CON FACTURAS

La factura puede:

```text
NO existir al crear requisición
```

por lo tanto:

```text
Factura = opcional
```

Debe ser posible:

```text
Requisición
   ↓
OrdenCompra
   ↓
Factura
```

y también:

```text
Requisición
   ↓
Factura externa existente
```

La relación debe quedar documentada como:

```text
evidencia posterior
```

cuando la factura aparece después de la compra.

No bloquear una requisición porque no tenga factura.

---

# 14. RELACIÓN CON ORDEN DE COMPRA

Esta es la integración principal.

Modificar:

```text
apps/tenant/compras/models.py
```

para agregar la referencia a la requisición.

Preferiblemente:

```python
requisicion = models.ForeignKey(
    "compras.RequisicionCompra",
    on_delete=models.PROTECT,
    related_name="ordenes_compra",
)
```

pero verificar el `app_label` real antes de escribir la FK.

Regla:

```text
OrdenCompra APROBADA
    DEBE tener requisición aprobada
```

No permitir:

```text
BORRADOR -> APROBADA
```

si la requisición:

```text
no existe
```

o está:

```text
BORRADOR
PENDIENTE_APROBACION
RECHAZADA
CANCELADA
```

---

# 15. MÚLTIPLES ÓRDENES DESDE UNA REQUISICIÓN

Debe permitirse:

```text
1 Requisición
   ├── OrdenCompra A
   ├── OrdenCompra B
   └── OrdenCompra C
```

Ejemplo:

```text
Requisición REQ-001
    Necesita:
      cámaras
      cable
      instalación

Cotización A:
      cámaras

Cotización B:
      cable

Proveedor A:
      cámaras

Proveedor B:
      cable

Resultado:
      OC-001 proveedor A
      OC-002 proveedor B
```

Por esto:

```text
Requisición -> OrdenCompra
```

debe ser:

```text
1:N
```

no `1:1`.

---

# 16. ATENCIÓN PARCIAL

La Requisición debe controlar cuánto ya fue atendido.

Por cada item:

```text
cantidad_solicitada
cantidad_aprobada
cantidad_ordenada
cantidad_recibida
cantidad_cancelada
cantidad_pendiente
```

No guardar todos como campos si algunos pueden derivarse de relaciones reales.

Preferir:

```text
SSoT transaccional
+
selectors/aggregates
```

y solamente cachear totales cuando exista justificación real de rendimiento.

---

# 17. REGLA DE ATENCIÓN

Ejemplo:

```text
Requisición:
100 unidades

OC-001:
60

OC-002:
40
```

resultado:

```text
ordenado = 100
pendiente = 0
estado = ATENDIDA
```

Otro:

```text
Requisición:
100

OC:
60
```

resultado:

```text
ordenado = 60
pendiente = 40
estado = PARCIALMENTE_ATENDIDA
```

No permitir superar la cantidad aprobada salvo una política explícita de sobrecompra.

---

# 18. SERVICE LAYER

Crear:

```text
apps/tenant/compras/requisiciones/services/
```

con separación:

```text
business_service.py
crud_service.py
selectors.py
services.py
api_mixins.py
```

siguiendo estrictamente la arquitectura existente del módulo.

Operaciones principales:

```text
crear_requisicion()
actualizar_requisicion()
enviar_a_aprobacion()
aprobar_requisicion()
rechazar_requisicion()
cancelar_requisicion()
vincular_cotizacion()
vincular_factura()
vincular_proyecto()
crear_orden_desde_requisicion()
recalcular_estado()
```

No poner lógica compleja en ViewSet.

---

# 19. `crear_orden_desde_requisicion()`

Esta debe convertirse en la nueva puerta principal de abastecimiento.

Pseudoflujo:

```text
resolver empresa
↓
resolver sede/area
↓
resolver requisición
↓
verificar misma empresa
↓
verificar permiso
↓
verificar estado APROBADA
↓
bloquear requisición si se requiere consistencia
↓
validar cantidades disponibles
↓
resolver proveedor
↓
crear OrdenCompra
↓
crear ItemOrdenCompra
↓
vincular OrdenCompra → Requisición
↓
actualizar estado/atención
↓
sincronizar CxP cuando corresponda
↓
commit
```

Todo el proceso debe ser atómico.

---

# 20. IDEMPOTENCIA

Crear una orden desde una requisición no puede duplicarse por doble click/reintento.

Resolver mediante combinación de:

```text
business invariant
+
database constraint cuando sea aplicable
+
transaction.atomic()
+
select_for_update()
```

No depender solo de:

```text
if exists()
```

porque eso puede sufrir race condition.

---

# 21. APROBACIÓN

No implementar un workflow RBAC nuevo.

Reutilizar el `OrganizationalContext`, permisos y roles ya existentes.

La aprobación debe vivir en Service Layer:

```text
aprobar_requisicion()
```

No:

```text
serializer.save(estado="APROBADA")
```

La modificación directa del estado desde PATCH debe estar bloqueada.

---

# 22. AUDITORÍA

Crear historial append-only:

```text
RequisicionHistorialEstado
```

Campos:

```text
uuid
requisicion
estado_anterior
estado_nuevo
usuario
fecha
comentario
```

No actualizar ni borrar eventos históricos.

Ejemplo:

```text
BORRADOR
PENDIENTE_APROBACION
APROBADA
EN_PROCESO_COMPRA
PARCIALMENTE_ATENDIDA
ATENDIDA
```

---

# 23. SEGURIDAD MULTITENANT

Toda lectura debe estar limitada a:

```text
empresa_id
```

y, cuando corresponda:

```text
OrganizationalScope
Sede
Area
```

Nunca confiar en:

```text
empresa_id
```

enviado por el frontend.

Resolverlo desde:

```text
request
tenant
organizational context
```

Aplicar el patrón DSV vigente en Compras.

---

# 24. SELECTORS

Crear:

```text
RequisicionCompraSelector
```

con métodos:

```text
get_list()
get_detail()
get_by_uuid()
get_pending_approval()
get_approved()
get_available_for_purchase()
get_with_progress()
```

Optimizar:

```text
select_related()
prefetch_related()
.only()
```

respetando la regla vigente de Compras para evitar N+1.

---

# 25. SERIALIZERS

Crear:

```text
RequisicionCompraListSerializer
RequisicionCompraDetailSerializer
RequisicionCompraCreateUpdateSerializer
RequisicionCompraItemSerializer
RequisicionCompraApprovalSerializer
```

No permitir que el serializer cambie directamente:

```text
estado
```

en PATCH genérico.

Crear endpoints explícitos:

```text
/aprobar/
/rechazar/
/enviar-aprobacion/
/cancelar/
```

---

# 26. API

Ruta base:

```text
/api/v1/compras/requisiciones/
```

Endpoints mínimos:

```text
GET     /requisiciones/
POST    /requisiciones/
GET     /requisiciones/{uuid}/
PATCH   /requisiciones/{uuid}/
DELETE  /requisiciones/{uuid}/
POST    /requisiciones/{uuid}/enviar-aprobacion/
POST    /requisiciones/{uuid}/aprobar/
POST    /requisiciones/{uuid}/rechazar/
POST    /requisiciones/{uuid}/cancelar/
POST    /requisiciones/{uuid}/crear-orden/
GET     /requisiciones/{uuid}/ordenes/
GET     /requisiciones/{uuid}/documentos/
GET     /requisiciones/{uuid}/historial/
```

Los nombres finales deben respetar los patrones ya establecidos en `apps/tenant/compras/api/`.

---

# 27. FRONTEND

No crear una aplicación frontend completamente nueva.

Integrar el submódulo dentro de:

```text
workspace/#compras
```

Estructura:

```text
Compras
├── Requisiciones
├── Ordenes de Compra
└── Recepciones
```

La documentación actual de Compras ya migró el listado visual a pestañas; reutilizar exactamente ese patrón.

No crear:

```text
workspace/#requisiciones
```

como módulo global independiente salvo que una auditoría posterior demuestre que el negocio necesita una pantalla transversal.

---

# 28. UI DE REQUISICIÓN

Listado:

```text
Número
Fecha
Solicitante
Sede
Área
Proyecto
Estado
Prioridad
Total estimado
Avance
Acciones
```

Detalle:

```text
Cabecera
Justificación
Contexto
Items
Cotizaciones
Documentos
Facturas
Órdenes generadas
Historial
```

Acciones:

```text
Editar
Enviar
Aprobar
Rechazar
Cancelar
Crear Orden
Ver documentos
Ver trazabilidad
```

Las acciones deben estar condicionadas por estado/permisos.

---

# 29. TRAZABILIDAD VISUAL

Debe existir una línea temporal:

```text
REQUISICIÓN
     │
     ├── Proyecto
     │
     ├── Cotización
     │
     ├── OrdenCompra
     │      └── Recepción
     │             └── Inventario
     │
     └── Factura
            └── CxP
```

Esto convierte a la Requisición en el verdadero expediente operativo.

---

# 30. INTEGRACIÓN CON FACTURA

No modificar la propiedad actual del dominio:

```text
Facturas = dueño fiscal
```

La Requisición solamente referencia.

Nunca duplicar:

```text
CUFE
subtotal
IVA
total
estado DIAN
```

en la Requisición.

La Requisición puede almacenar:

```text
numero_factura
```

solamente si la referencia real requiere snapshot visible, pero el SSoT debe seguir siendo Factura.

---

# 31. INTEGRACIÓN CON CXP

La lógica existente en:

```text
OrdenCompraBusinessService
```

que sincroniza Cuentas por Pagar al aprobar la orden debe permanecer en el dominio correcto.

No mover CxP a Requisición.

Regla:

```text
Requisición
= origen / justificación

OrdenCompra
= obligación de compra

CuentasPagar
= obligación financiera
```

---

# 32. INTEGRACIÓN CON INVENTARIO

La Requisición no debe modificar stock.

Inventario se mantiene como dueño del Kardex.

Flujo:

```text
Requisición
   ↓
OrdenCompra
   ↓
RecepciónCompra
   ↓
MovimientoInventario
```

La documentación actual confirma este patrón.

---

# 33. INTEGRACIÓN CON PROYECTO

Evitar reimplementar presupuestos.

Cuando exista:

```text
Proyecto
 ↓
ItemPresupuestoProyecto
```

la Requisición debe poder indicar:

```text
proyecto
```

y opcionalmente:

```text
partida / referencia presupuestal
```

solo si existe un SSoT real para esa partida.

No copiar el presupuesto completo dentro de Requisición.

---

# 34. CENTRO DE COSTO / DIMENSIÓN CONTABLE

Antes de crear cualquier modelo:

```text
CentroCosto
```

hacer auditoría real de:

```text
apps/tenant/contabilidad/
apps/tenant/gastos/
apps/tenant/proyectos/
```

Buscar:

```text
centro
costo
cost_center
cuenta
presupuesto
dimension
```

Si existe SSoT:

```text
FK/soft reference Requisición → CentroCosto
```

Si no existe:

```text
DOCUMENTAR DEFERRED
```

y no inventar infraestructura contable dentro de Compras.

---

# 35. DOCUMENTOS EXTERNOS

Una factura externa puede no existir en el modelo Factura.

Por eso `RequisicionDocumento` debe permitir:

```text
tipo = FACTURA
documento_uuid = NULL
archivo = archivo físico
numero_referencia = "FE-12345"
```

y más adelante:

```text
documento_uuid = <Factura.real>
```

sin perder el archivo ni la trazabilidad.

---

# 36. MIGRACIONES

Crear migraciones únicamente dentro de:

```text
apps/tenant/compras/requisiciones/migrations/
```

y modificar `compras` solamente cuando sea indispensable.

Antes de migrar:

```text
inspeccionar datos existentes
```

especialmente `OrdenCompra`.

No imponer inmediatamente:

```text
null=False
```

sobre `OrdenCompra.requisicion` si existen órdenes históricas sin requisición.

Estrategia:

```text
FASE A:
requisicion nullable

FASE B:
backfill de órdenes históricas cuando exista evidencia

FASE C:
bloquear nuevas órdenes sin requisición

FASE D:
NOT NULL solamente si el histórico está correctamente reconciliado
```

No inventar relaciones históricas.

---

# 37. COMPATIBILIDAD CON ÓRDENES EXISTENTES

Debe existir una regla explícita:

```text
Ordenes antiguas
= LEGACY
```

y:

```text
Ordenes nuevas
= requisicion obligatoria
```

No modificar silenciosamente el significado histórico.

Agregar, si es necesario:

```text
requisicion_legacy
```

solo si la auditoría demuestra que se necesita distinguir el origen.

---

# 38. REGLAS DE BASE DE DATOS

Usar constraints donde puedan garantizarse.

Mínimas candidatas:

```text
unique(empresa, numero_requisicion)

fecha_necesidad >= fecha_solicitud

cantidad > 0

valor_unitario_estimado >= 0

porcentaje_iva >= 0

subtotal_estimado >= 0

total_estimado >= 0
```

Y cualquier regla que dependa de otras filas debe resolverse mediante Service Layer + transacción + locking, no mediante `CHECK` que consulte otras tablas.

PostgreSQL no permite que un `CHECK` garantice correctamente reglas que dependen de otras filas/tablas.

---

# 39. PROTECCIÓN CONTRA BORRADO

No permitir DELETE físico de una requisición que tenga:

```text
OrdenCompra
Cotizacion
Factura
Recepcion
```

Regla recomendada:

```text
BORRADOR sin dependencias
    → puede eliminarse
```

```text
con dependencias
    → no DELETE
```

Usar:

```text
CANCELADA
```

cuando el expediente ya tenga trazabilidad.

No destruir historial.

---

# 40. AUDITORÍA DE DEPENDENCIAS

Antes de modificar:

```text
compras
cotizaciones
facturas
proyectos
inventario
proveedores
contabilidad
```

usar el EKG y búsqueda repo-wide para:

```text
imports
consumidores
serializers
services
ViewSets
templates
JS
tests
management commands
```

No asumir que un símbolo no se usa solamente porque no aparece en la documentación.

---

# 41. DOCUMENTACIÓN NUEVA OBLIGATORIA

Crear:

```text
docs/compras/REQUISICIONES_ARCHITECTURE.md
docs/compras/REQUISICIONES_FLOW.md
docs/compras/REQUISICIONES_RELEASE_GATE.md
docs/compras/REQUISICIONES_SSOT.md
```

Actualizar:

```text
apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md
```

y la documentación general si cambia el mapa de aplicaciones.

---

# 42. MATRIZ SSoT

Crear una tabla:

| Dato | Dueño |
|---|---|
| Necesidad | Requisición |
| Solicitante | Requisición |
| Justificación | Requisición |
| Proyecto | Proyectos |
| Cotización comercial | Cotizaciones |
| Proveedor | Proveedores |
| Orden de compra | Compras |
| Recepción | Compras |
| Stock | Inventario |
| Kardex | Inventario |
| Factura fiscal | Facturas |
| CxP | Proveedores/Contabilidad según contrato real |
| Pago | Bancos |
| Asiento | Contabilidad |
| Centro de costo | Contabilidad, si existe |

La Requisición no debe duplicar estos dominios.

---

# 43. REGLA DE NO DUPLICACIÓN

No agregar a Requisición:

```text
proveedor_nombre
cliente_nombre
factura_total
factura_cufe
stock
saldo_cxp
saldo_banco
asiento
```

como copia permanente de otros dominios salvo que exista una razón de snapshot documentada.

Preferir:

```text
referencia
+
selector
+
SSoT
```

---

# 44. CASOS DE USO OBLIGATORIOS

Implementar como mínimo estos flujos:

## Caso A

```text
Requisición
→ aprobación
→ OrdenCompra
→ recepción
```

## Caso B

```text
Requisición
→ Proyecto
→ OrdenCompra
```

## Caso C

```text
Requisición
→ Cotización/soporte
→ OrdenCompra
```

## Caso D

```text
Requisición
→ OrdenCompra
→ Factura posterior
```

## Caso E

```text
Requisición
→ factura externa existente
```

## Caso F

```text
Requisición
→ varias OrdenesCompra
```

## Caso G

```text
Requisición
→ OrdenCompra parcial
→ segunda OrdenCompra
→ ATENDIDA
```

---

# 45. CASOS DE RECHAZO OBLIGATORIOS

Debe quedar bloqueado:

```text
crear OC sin requisición
```

```text
crear OC desde requisición rechazada
```

```text
crear OC desde requisición cancelada
```

```text
ordenar más unidades que las aprobadas
```

```text
usar requisición de otro tenant
```

```text
usar proyecto de otro tenant
```

```text
usar factura de otro tenant
```

```text
usar cotización de otro tenant
```

```text
editar requisición ya aprobada
```

```text
DELETE con trazabilidad existente
```

---

# 46. EXTENSIÓN AI / TOOLING

No crear herramientas IA específicas todavía salvo que la arquitectura existente requiera registrar la nueva capacidad.

Una futura tool puede ser:

```text
buscar_requisiciones
```

pero debe permanecer:

```text
READ
tenant scoped
permission aware
```

Nunca habilitar automáticamente:

```text
crear_requisicion
aprobar_requisicion
crear_orden
```

como WRITE.

La política existente del AI Engine debe seguir bloqueando WRITE hasta existir aprobación humana real.

---

# 47. CHECKLIST DE IMPLEMENTACIÓN

## FASE 1 — AUDITORÍA PREVIA

[ ] Leer `arquitectura_general` completo en las secciones relevantes.  
[ ] Leer `AUDITORIA_FLUJO_COMPRAS.md`.  
[ ] Leer auditoría de Proyectos.  
[ ] Leer auditoría de Cotizaciones.  
[ ] Leer auditoría de Facturas.  
[ ] Leer auditoría de Inventario.  
[ ] Leer auditoría de Proveedores.  
[ ] Leer contratos cross-app relevantes.  
[ ] Inspeccionar modelos reales.  
[ ] Inspeccionar Service Layer.  
[ ] Inspeccionar API.  
[ ] Inspeccionar frontend.  
[ ] Inspeccionar migraciones.  
[ ] Inspeccionar consumidores repo-wide.  
[ ] Determinar si existe SSoT de Centro de Costo.

**Salida:**
```text
REQUISITION_BASELINE.md
```

NO ejecutar pytest.

---

# 48. FASE 2 — DISEÑO

[ ] Crear modelo conceptual.  
[ ] Definir estados.  
[ ] Definir permisos.  
[ ] Definir reglas de transición.  
[ ] Definir numeración.  
[ ] Definir items.  
[ ] Definir documentos.  
[ ] Definir vínculos transversales.  
[ ] Definir relación con Proyecto.  
[ ] Definir relación con Cotización.  
[ ] Definir relación con Factura.  
[ ] Definir relación con OrdenCompra.  
[ ] Definir atención parcial.  
[ ] Definir auditoría.  
[ ] Definir estrategia de migración de órdenes históricas.  
[ ] Definir SSoT matrix.

**Salida:**
```text
REQUISICIONES_DESIGN.md
```

NO ejecutar pytest.

---

# 49. FASE 3 — MODELOS Y MIGRACIONES

[ ] Crear app/submódulo `requisiciones`.  
[ ] Crear modelos.  
[ ] Agregar UUID.  
[ ] Agregar empresa.  
[ ] Agregar sede/area según SSoT.  
[ ] Agregar constraints.  
[ ] Agregar índices.  
[ ] Crear migraciones.  
[ ] Integrar referencia de OrdenCompra.  
[ ] Proteger compatibilidad histórica.  
[ ] No hacer migraciones destructivas.  
[ ] Verificar dependencies de migraciones.

NO ejecutar pytest.

---

# 50. FASE 4 — SERVICE LAYER

[ ] Implementar CRUD service.  
[ ] Implementar business service.  
[ ] Implementar selectors.  
[ ] Implementar transitions.  
[ ] Implementar approval service.  
[ ] Implementar creation of purchase from requisition.  
[ ] Implementar partial fulfillment.  
[ ] Implementar idempotencia.  
[ ] Implementar locking.  
[ ] Implementar audit history.  
[ ] Integrar CxP en el lugar correcto.  
[ ] No usar signals.

NO ejecutar pytest.

---

# 51. FASE 5 — API

[ ] Serializers.  
[ ] ViewSets.  
[ ] Permissions.  
[ ] Filters.  
[ ] Pagination.  
[ ] URLs.  
[ ] Actions de workflow.  
[ ] Endpoint crear-orden.  
[ ] Endpoint trazabilidad.  
[ ] OpenAPI metadata.

NO ejecutar pytest.

---

# 52. FASE 6 — FRONTEND

[ ] Integrar pestaña Requisiciones dentro de Compras.  
[ ] Crear tabla server-side reutilizando infraestructura.  
[ ] Crear editor.  
[ ] Crear detalle.  
[ ] Crear workflow buttons.  
[ ] Crear timeline.  
[ ] Crear selector de proyecto.  
[ ] Crear selector de cotizaciones/soportes.  
[ ] Crear documentos.  
[ ] Crear progreso de atención.  
[ ] Reutilizar `Sintel.Core.Http`.  
[ ] Reutilizar offcanvas helper.  
[ ] Evitar Tabulator si el patrón actual del módulo ya fue migrado a django-tables2/HTMX.  
[ ] No duplicar assets.

NO ejecutar pytest.

---

# 53. FASE 7 — INTEGRACIÓN CROSS-APP

[ ] Proyecto.  
[ ] Cotizaciones.  
[ ] Facturas.  
[ ] Proveedores.  
[ ] Inventario.  
[ ] Contabilidad.  
[ ] CxP.  
[ ] Revisar ciclos de import.  
[ ] Revisar DSV.  
[ ] Revisar OrganizationalScope.  
[ ] Revisar UUID references.  
[ ] Revisar `on_delete`.  
[ ] Confirmar que la Requisición no roba responsabilidades a otro dominio.

NO ejecutar pytest.

---

# 54. FASE 8 — HARDENING

[ ] Tenant isolation.  
[ ] Object-level authorization.  
[ ] Cross-tenant references.  
[ ] State transition guards.  
[ ] Delete protection.  
[ ] Concurrency.  
[ ] Idempotency.  
[ ] Database constraints.  
[ ] Logging seguro.  
[ ] Audit trail.  
[ ] OpenAPI.  
[ ] No debug bypass.  
[ ] No signals.  
[ ] No business logic en serializers.

NO ejecutar pytest.

---

# 55. FASE 9 — DOCUMENTACIÓN Y RELEASE GATE

[ ] Actualizar arquitectura general.  
[ ] Actualizar auditoría de Compras.  
[ ] Crear RELEASE GATE.  
[ ] Crear SSoT matrix.  
[ ] Registrar decisiones diferidas.  
[ ] Documentar compatibilidad histórica.  
[ ] Documentar reglas de negocio.  
[ ] Documentar APIs.  
[ ] Documentar UI.  
[ ] Documentar permisos.  
[ ] Documentar migraciones.

NO ejecutar pytest.

---

# 56. FASE 10 — AUTOAUDITORÍA FINAL SIN TESTS

Ejecutar únicamente revisión estática:

```text
grep repo-wide
búsqueda EKG
revisión de imports
revisión de migraciones
revisión de referencias
revisión de archivos muertos
revisión de reglas arquitectónicas
```

Verificar:

```text
[ ] no existe bypass de DEBUG
[ ] no existe signal de negocio
[ ] no existe GenericForeignKey innecesario
[ ] no existen queries sin empresa_id
[ ] no existe acceso cross-tenant
[ ] no se duplica SSoT
[ ] no se rompe OrdenCompra histórica
[ ] no se rompe CxP
[ ] no se rompe Recepción
[ ] no se rompe Inventario
[ ] no se rompe Proyecto
[ ] no se rompe Cotización
[ ] no se rompe Factura
```

Crear:

```text
docs/compras/REQUISICIONES_PRE_TEST_AUDIT.md
```

NO ejecutar pytest.

---

# 57. FASE 11 — AUTORIZACIÓN DE TESTS

Aquí la IA editora debe detenerse.

Debe responder al usuario:

```text
IMPLEMENTACIÓN DE REQUISICIONES COMPLETADA.

Todas las fases de código, arquitectura, integración y autoauditoría fueron
ejecutadas.

La fase final pendiente es TESTING.

¿AUTORIZAS EJECUTAR LA SUITE DE TESTS?
```

No ejecutar nada de la suite antes de recibir:

```text
SI
```

o autorización equivalente.

---

# 58. FASE 12 — TESTING FINAL

Después de autorización:

## 58.1 Tests específicos

```text
apps/tenant/compras/requisiciones/tests/
```

Cobertura mínima:

```text
modelos
serializers
selectors
services
permissions
state machine
idempotencia
concurrencia
multitenant isolation
cross-tenant IDOR
crear orden
atención parcial
documentos
facturas
proyecto
cotización
```

## 58.2 Regresión Compras

```text
apps/tenant/compras/tests/
```

## 58.3 Regresión cross-domain

```text
compras
proveedores
proyectos
cotizaciones
facturas
inventario
contabilidad
```

## 58.4 Checks

```text
python manage.py check
python manage.py makemigrations --check --dry-run
```

## 58.5 Suite general

Ejecutarla al final conforme al entorno de testing real del proyecto.

La documentación histórica indica que los tests Django de este proyecto pueden ser costosos y que el entorno Docker ha resultado significativamente más rápido para las suites que crean schemas tenant. Respetar la infraestructura de testing actualmente vigente en el repositorio y no inventar otro runner.

---

# 59. MATRIZ DE ACEPTACIÓN

| Requisito | Debe pasar |
|---|---|
| Requisición CRUD | ✅ |
| UUID | ✅ |
| Tenant isolation | ✅ |
| OrganizationalScope | ✅ |
| Workflow | ✅ |
| Approval | ✅ |
| Rejection | ✅ |
| Cancellation | ✅ |
| Documents | ✅ |
| Project relation | ✅ |
| Quote relation | ✅ |
| Invoice relation | ✅ |
| Multiple orders | ✅ |
| Partial fulfillment | ✅ |
| Idempotency | ✅ |
| Concurrency | ✅ |
| OC without requisition blocked | ✅ |
| Cross-tenant reference blocked | ✅ |
| Historical OC preserved | ✅ |
| CxP flow preserved | ✅ |
| Reception preserved | ✅ |
| Inventory preserved | ✅ |
| No business signals | ✅ |
| Service Layer | ✅ |
| API | ✅ |
| UI | ✅ |
| OpenAPI | ✅ |
| Migration check | ✅ |
| Full regression | ✅ |

---

# 60. CRITERIO FINAL DE TERMINACIÓN

La misión solo puede marcarse:

```text
REQUISICIONES = COMPLETED
```

cuando exista:

```text
IMPLEMENTATION
+
INTEGRATION
+
SECURITY
+
DOCUMENTATION
+
TESTS
+
REGRESSION
```

Todos los elementos que no puedan concluirse por falta de una regla de negocio real deben marcarse:

```text
DEFERRED
```

con:

```text
razón
impacto
dependencia
decisión pendiente
```

Nunca:

```text
inventar
```

ni:

```text
marcar como completado algo que solo fue diseñado.
```

---

# 61. PRINCIPIO ARQUITECTÓNICO FINAL

La Requisición debe convertirse en:

```text
DOCUMENTO ORIGEN
       +
CONTEXTO DE NEGOCIO
       +
JUSTIFICACIÓN
       +
TRAZABILIDAD
```

pero no en:

```text
ERP dentro del ERP
```

La propiedad de los datos continúa siendo:

```text
Requisición → necesidad
Proyecto    → proyecto
Cotización  → cotización
Proveedor   → proveedor
Compra      → orden
Recepción   → recepción
Inventario  → stock
Factura     → documento fiscal
CxP         → obligación financiera
Bancos      → pagos
Contabilidad→ registro contable
```

La Requisición únicamente **orquesta y conecta el expediente**, respetando cada SSoT.

---

# 62. REFERENCIAS OFICIALES Y TÉCNICAS

La implementación debe contrastarse con:

- Django 5.2 — Model field reference / relaciones.
- Django 5.2 — Model constraints (`UniqueConstraint`, `CheckConstraint`).
- Django 5.2 — Database transactions.
- PostgreSQL 16 — constraints / foreign keys / transaction integrity.
- django-tenants — tenant schemas, tenant model y tenant domain model.
- Django REST Framework — ViewSets, serializers, permissions, filtering y versionado.
- drf-spectacular — OpenAPI.
- OWASP ASVS — controles de autorización, validación, sesión y manejo seguro de datos.

No usar una fuente externa para sustituir una regla específica ya definida por la arquitectura SINTEL. La documentación propia del proyecto sigue siendo la fuente de verdad funcional cuando exista una decisión explícita.

---

# 63. REGLA DE ORO PARA LA IA EDITORA

Antes de crear cualquier campo, modelo, FK, servicio, endpoint o tabla:

```text
¿YA EXISTE?
   ↓
SI → reutilizar
NO
   ↓
¿QUIÉN ES EL SSoT?
   ↓
¿DUPLICA OTRO DOMINIO?
   ↓
¿ROMPE MULTITENANT?
   ↓
¿ROMPE SERVICE LAYER?
   ↓
¿GENERA CICLO?
   ↓
¿NECESITA MIGRACIÓN HISTÓRICA?
   ↓
IMPLEMENTAR
```

Y después:

```text
RE-AUDIT
```

Nunca asumir que la solución más grande es la mejor.

