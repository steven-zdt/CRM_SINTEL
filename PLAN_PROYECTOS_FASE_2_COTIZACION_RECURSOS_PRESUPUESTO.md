# PLAN DE ACCIÓN
# Proyecto -> Fase 2 Planeación -> Cotización Aceptada -> Recursos y Presupuesto
## SINTEL ERP / CRM_SINTEL

---

## 0. OBJETIVO

Rediseñar el flujo de:

```text
http://admin.sintel.net.co/workspace/#proyectos
    -> Editar Proyecto
    -> 2. Planeación
```

para que el encargado del proyecto pueda visualizar, asociar y utilizar una **cotización aceptada** como fuente de información de recursos y, opcionalmente, sincronizar sus costos al presupuesto planeado.

El flujo final debe permitir:

1. Vincular directamente una cotización al Proyecto.
2. Permitir únicamente cotizaciones en estado de negocio `ACEPTADA`.
3. Mostrar un resumen de la cotización por:
   - Mano de Obra
   - Materiales
   - Equipos
4. Discriminar los recursos según el cuerpo real de `CotizacionItem`.
5. Mostrar los valores **antes de IVA**.
6. Mantener la captura manual del presupuesto como primera opción.
7. Agregar un botón explícito:
   - `Sincronizar costos de cotización`
8. La sincronización debe ser opcional y no obligatoria.
9. Evitar duplicar costos manuales cuando se sincronizan los costos de la cotización.
10. Eliminar del formulario de Editar Proyecto el campo redundante:
   - `Responsable Técnico (Nómina)`
11. Mantener intacta la SSoT existente de:
   - Service Layer
   - CRUD Service
   - Selectors
   - DSV
   - OrganizationalScope
   - tenant isolation
12. No crear lógica de negocio paralela en JavaScript.

---

# 1. AUDITORÍA REAL DE `main`

Repositorio:

```text
steven-zdt/CRM_SINTEL
branch: main
```

Los puntos principales auditados son:

```text
apps/tenant/proyectos/models.py
apps/tenant/proyectos/services/business_service.py
apps/tenant/proyectos/services/presupuesto_service.py
apps/tenant/proyectos/services/selectors.py
apps/tenant/proyectos/api/serializers.py
apps/tenant/proyectos/api/viewsets.py
apps/tenant/proyectos/templates/tenant/proyectos/offcanvas_form.html
apps/tenant/proyectos/static/proyectos/js/proyectos.api.js
apps/tenant/proyectos/static/proyectos/js/features/proyectos_editor.js

apps/tenant/cotizaciones/models.py
apps/tenant/cotizaciones/services/business_service.py
apps/tenant/cotizaciones/services/item_service.py
apps/tenant/cotizaciones/services/selectors.py
apps/tenant/cotizaciones/api/serializers.py
apps/tenant/cotizaciones/api/viewsets.py
```

---

# 2. HALLAZGOS REALES

## 2.1 Estado real de Cotización

El modelo real es:

```python
class Estado(models.TextChoices):
    BORRADOR = 'BORRADOR'
    ENVIADA = 'ENVIADA'
    ACEPTADA = 'ACEPTADA'
    CANCELADA = 'CANCELADA'
```

Por tanto:

```text
ACEPTADA
```

es el estado que debe utilizar el nuevo flujo.

No se debe inventar un nuevo estado:

```text
APROBADA
```

para la Cotización.

### Regla funcional

En la interfaz puede mostrarse:

```text
Cotización aceptada
```

o, si negocio desea la terminología "aprobada":

```text
Cotización aprobada
```

pero internamente la SSoT debe seguir siendo:

```text
ACEPTADA
```

---

# 3. PROBLEMA ACTUAL DE VINCULACIÓN

Actualmente Proyecto NO posee una relación directa con `Cotizacion`.

Existe un vínculo indirecto:

```text
Proyecto
   |
   +--> Factura
           |
           +--> cotizacion_uuid
```

Además `ProyectoDetailSerializer` expone:

```text
cotizacion_numero
cotizacion_uuid
cotizacion_info
```

resolviendo la cotización mediante la factura.

Esto NO debe ser la nueva SSoT porque:

```text
Proyecto
   -> Factura
      -> Cotización
```

introduce una dependencia indirecta innecesaria.

El nuevo flujo debe pasar a ser:

```text
Proyecto
   -> Cotización
```

directamente.

El vínculo indirecto histórico por Factura debe conservarse temporalmente para compatibilidad, pero dejar de ser la fuente principal para la Planeación.

---

# 4. PROBLEMA ACTUAL DEL PRESUPUESTO

Actualmente `ItemPresupuestoProyecto` permite:

```text
MANO_OBRA
EQUIPOS
MATERIALES
```

y el usuario los ingresa manualmente desde:

```text
Desglose de Costos Planeados (Presupuesto)
```

El flujo actual es:

```text
categoría
descripción
cantidad
valor unitario
+
    ↓
POST /api/v1/proyectos/items-presupuesto/
    ↓
PresupuestoBusinessService.crear_item()
```

El servicio calcula:

```text
subtotal = cantidad x valor_unitario
```

y mantiene:

```text
costo_planeado_total
utilidad_planeada
margen_planeado
```

Esto es correcto y debe permanecer.

---

# 5. PROBLEMA ACTUAL DEL FORMULARIO

En Fase 2 se encuentra:

```text
Responsable Técnico (Nómina)
```

con:

```text
responsable_tecnico_id
responsable_tecnico_nombre
```

Este campo debe desaparecer del formulario de Editar Proyecto.

### Importante

No eliminar inmediatamente los campos históricos del modelo:

```text
responsable_tecnico_id
responsable_tecnico_nombre
```

porque existen datos existentes y lógica histórica de fase.

En esta misión:

```text
UI editable -> eliminar
Payload nuevo -> no enviar
Backend histórico -> mantener temporalmente
```

Después podrá realizarse una misión independiente para retirar completamente la estructura legacy si negocio lo autoriza.

---

# 6. MODELO FUNCIONAL FINAL

La Fase 2 debe quedar conceptualmente:

```text
2. PLANEACIÓN
│
├── Cotización aceptada
│
│   ├── Número
│   ├── Cliente
│   ├── Fecha
│   ├── Valor antes de IVA
│   └── Estado
│
├── Recursos de la cotización
│
│   ├── Mano de Obra
│   ├── Materiales
│   └── Equipos
│
├── Detalle de recursos
│
└── Presupuesto Planeado
    ├── Ingreso manual       ← opción principal
    └── Sincronizar cotización ← opción opcional
```

---

# 7. FASE 1 — MODELO DIRECTO PROYECTO ↔ COTIZACIÓN

## Objetivo

Agregar una relación directa y persistente entre Proyecto y Cotización.

### Recomendación

Agregar en `Proyecto` una relación:

```python
cotizacion = models.ForeignKey(
    'tenant_cotizaciones.Cotizacion',
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name='proyecto_asociado',
)
```

### Motivo

`PROTECT` evita que una cotización utilizada como base del Proyecto sea eliminada accidentalmente.

### Restricción funcional

Un proyecto debe tener:

```text
0 o 1 cotización principal
```

No múltiples cotizaciones simultáneas en esta primera implementación.

La estructura queda:

```text
Proyecto 1 ---- 0..1 Cotizacion
```

### Regla adicional recomendada

Una Cotización `ACEPTADA` no debe quedar asociada a varios proyectos como cotización principal.

Implementar una restricción o validación de unicidad apropiada.

---

# 8. FASE 2 — MIGRACIÓN DE DATOS HISTÓRICOS

Antes de cambiar la UI:

1. Detectar Proyectos con:
   ```text
   factura_costo_id
   ```
2. Resolver:
   ```text
   factura_costo -> cotizacion_uuid
   ```
3. Cuando la cotización exista y corresponda al mismo tenant:
   ```text
   proyecto.cotizacion = cotizacion
   ```
4. No modificar:
   ```text
   factura_costo
   ```
5. Registrar casos que no puedan migrarse automáticamente.

### Casos no migrables

```text
Factura sin cotización
Cotización inexistente
Cotización de otro tenant
cotizacion_uuid inválido
múltiples relaciones inconsistentes
```

No corregir silenciosamente estos casos.

Crear reporte de migración.

---

# 9. FASE 3 — DSV Y SEGURIDAD DE LA COTIZACIÓN

Toda vinculación debe validar:

```text
cotizacion.empresa_id == proyecto.empresa_id
```

y además:

```text
OrganizationalScope
```

cuando la Cotización tenga `sede`.

### Estado obligatorio

Solo permitir:

```text
Cotizacion.Estado.ACEPTADA
```

No permitir:

```text
BORRADOR
ENVIADA
CANCELADA
```

### Cliente

Regla recomendada:

Si el proyecto ya tiene cliente:

```text
cotizacion.cliente_id == proyecto.cliente_id
```

debe ser obligatorio.

Si el proyecto no tiene cliente:

```text
permitir vinculación
```

y posteriormente sincronizar el cliente del proyecto según las reglas existentes.

No sobrescribir automáticamente el cliente del proyecto sin una acción explícita.

---

# 10. FASE 4 — SELECTOR DE COTIZACIONES PARA PLANEACIÓN

Crear selector específico para este caso de uso.

Conceptualmente:

```text
CotizacionPlaneacionSelector
```

o extender el selector existente si la arquitectura actual lo permite sin duplicación.

Consulta:

```text
empresa_id
estado=ACEPTADA
cliente opcional
sede opcional
```

Debe utilizar:

```text
.only()
.select_related()
.prefetch_related()
```

No cargar todas las cotizaciones del tenant.

### Respuesta mínima

```json
{
  "uuid": "...",
  "numero_cotizacion": "COT-0001",
  "cliente": "...",
  "estado": "ACEPTADA",
  "fecha_emision": "...",
  "total_con_impuestos": "...",
  "subtotal_antes_iva": "..."
}
```

---

# 11. FASE 5 — RESUMEN DE RECURSOS DE COTIZACIÓN

Crear una operación de lectura dedicada:

```text
GET
/api/v1/proyectos/{uuid}/cotizacion-planeacion/
```

o equivalente dentro del ViewSet.

La respuesta debe entregar:

```text
cotizacion
resumen
items
```

Ejemplo conceptual:

```json
{
  "cotizacion": {
    "uuid": "...",
    "numero": "COT-0001",
    "estado": "ACEPTADA"
  },
  "resumen": {
    "mano_obra": 12000000,
    "materiales": 25000000,
    "equipos": 35000000,
    "total_antes_iva": 72000000
  },
  "items": []
}
```

---

# 12. FASE 6 — CLASIFICACIÓN DE RECURSOS

El cuerpo real de `CotizacionItem` tiene:

```text
PRODUCTO
MATERIAL
SERVICIO
```

y no tiene todavía:

```text
MANO_OBRA
```

Para la Planeación del Proyecto se propone este mapeo funcional:

```text
CotizacionItem.PRODUCTO
        ↓
EQUIPOS

CotizacionItem.MATERIAL
        ↓
MATERIALES

CotizacionItem.SERVICIO
        ↓
MANO_OBRA
```

### Esta regla debe centralizarse

No implementarla en:

```text
JavaScript
template
ViewSet
```

La clasificación debe vivir en una única función de dominio.

Ejemplo conceptual:

```python
mapear_tipo_item_a_recurso(tipo_item)
```

### No duplicar el mapping

Todas las siguientes operaciones deben usar la misma SSoT:

```text
resumen
sincronización
validación
reportes
```

---

# 13. FASE 7 — VALORES ANTES DE IVA

Este punto debe definirse claramente para evitar errores contables.

En `CotizacionItem` existen:

```text
cantidad
costo_unitario
porcentaje_utilidad
precio_unitario_venta
subtotal_linea
```

Para la **Planeación de Recursos / Costos**:

```text
costo_base_linea
=
cantidad x costo_unitario
```

Esto debe considerarse:

```text
COSTO PLANEADO ANTES DE IVA
```

No utilizar:

```text
total_con_impuestos
```

y no utilizar IVA.

### Además mostrar en pantalla

Separar conceptualmente:

```text
Valor comercial cotizado antes de IVA
```

y:

```text
Costo base planeable antes de IVA
```

Esto evita confundir:

```text
precio de venta
```

con:

```text
costo del recurso
```

---

# 14. FASE 8 — RESUMEN COMERCIAL + COSTO BASE

En Planeación mostrar por categoría:

| Recurso | Valor cotizado antes de IVA | Costo base antes de IVA |
|---|---:|---:|
| Mano de Obra | $ | $ |
| Materiales | $ | $ |
| Equipos | $ | $ |
| Total | $ | $ |

### Valor cotizado

Proviene del cuerpo de:

```text
cantidad x precio_unitario_venta
```

antes de IVA.

### Costo base

Proviene de:

```text
cantidad x costo_unitario
```

antes de IVA.

Esto permitirá que el encargado entienda:

```text
qué se vendió
```

y:

```text
qué costo base tiene disponible el proyecto
```

sin mezclar ambos conceptos.

---

# 15. FASE 9 — DETALLE DISCRIMINADO DE RECURSOS

Debajo del resumen:

```text
Mano de Obra
------------------------------------------------
Descripción
Cantidad
Costo unitario
Costo total
------------------------------------------------

Materiales
------------------------------------------------
...

Equipos
------------------------------------------------
...
```

Cada línea debe provenir directamente de:

```text
CotizacionItem
```

y conservar:

```text
cotizacion_item_uuid
```

como referencia de origen.

No copiar solo un total sin poder saber de dónde salió.

---

# 16. FASE 10 — PRESUPUESTO MANUAL COMO OPCIÓN PRINCIPAL

El usuario debe ver primero:

```text
Desglose de Costos Planeados
```

con la captura existente.

La opción principal debe continuar siendo:

```text
Ingresar manualmente
```

Mantener:

```text
Categoría
Descripción
Cantidad
Valor unitario
Agregar
```

No reemplazar este flujo.

---

# 17. FASE 11 — NUEVO BOTÓN

Agregar debajo del encabezado:

```text
[ + Ingresar costo manual ]
[ Sincronizar costos de cotización ]
```

La segunda acción debe ser visualmente secundaria:

```text
Sincronizar costos de cotización
```

con icono:

```text
bi-arrow-repeat
```

o equivalente visual.

### Importante

La sincronización NO se ejecuta automáticamente al vincular la cotización.

Debe existir una acción explícita del usuario.

---

# 18. FASE 12 — ORIGEN DEL PRESUPUESTO

Actualmente los items de presupuesto no tienen trazabilidad de origen.

Agregar:

```text
origen
```

con valores:

```text
MANUAL
COTIZACION
```

y una referencia:

```text
cotizacion_item_uuid
```

nullable.

Ejemplo:

```text
ItemPresupuestoProyecto
--------------------------------
categoria = EQUIPOS
descripcion = DVR 32 canales
cantidad = 2
valor_unitario = 1800000
subtotal = 3600000
origen = COTIZACION
cotizacion_item_uuid = ...
```

---

# 19. FASE 13 — SINCRONIZACIÓN IDEMPOTENTE

La acción:

```text
Sincronizar costos de cotización
```

NO debe:

```text
borrar todo el presupuesto
crear duplicados
```

### Comportamiento recomendado

1. Obtener cotización del proyecto.
2. Verificar `ACEPTADA`.
3. Leer todos sus `CotizacionItem`.
4. Mapear categorías.
5. Calcular costo base antes de IVA.
6. Buscar los items del presupuesto con:
   ```text
   origen=COTIZACION
   ```
7. Actualizar los existentes.
8. Crear los faltantes.
9. Eliminar los que ya no existan en la cotización.
10. Mantener intactos los:
   ```text
   origen=MANUAL
   ```

Resultado:

```text
PRESUPUESTO
├── Manual
│   ├── ...
│   └── ...
│
└── Cotización
    ├── ...
    ├── ...
    └── ...
```

---

# 20. FASE 14 — NO DUPLICAR LA LÓGICA DE PRESUPUESTO

La sincronización no debe crear un segundo motor.

Debe reutilizar:

```text
PresupuestoBusinessService
```

o extenderlo para agregar:

```text
sincronizar_desde_cotizacion()
```

El servicio seguirá siendo responsable de:

```text
subtotal
costo_planeado_total
utilidad_planeada
margen_planeado
```

---

# 21. FASE 15 — TRANSACCIÓN DE SINCRONIZACIÓN

La acción completa debe ser:

```python
@transaction.atomic
def sincronizar_desde_cotizacion(...):
    ...
```

Dentro de una sola transacción:

```text
validar
leer cotización
calcular
upsert items
eliminar huérfanos de origen COTIZACION
recalcular proyecto
```

Si cualquier etapa falla:

```text
ROLLBACK
```

---

# 22. FASE 16 — NUEVO ACTION ENDPOINT

Crear una acción explícita sobre Proyecto:

```text
POST /api/v1/proyectos/{uuid}/sincronizar-costos-cotizacion/
```

No usar:

```text
PATCH /proyectos/{uuid}/
```

para simular la sincronización.

Respuesta:

```json
{
  "success": true,
  "cotizacion_uuid": "...",
  "items_creados": 4,
  "items_actualizados": 3,
  "items_eliminados": 1,
  "items_manuales_preservados": 5,
  "resumen": {
    "mano_obra": "...",
    "materiales": "...",
    "equipos": "...",
    "total_costos": "..."
  }
}
```

---

# 23. FASE 17 — VINCULAR COTIZACIÓN

Crear acción explícita:

```text
POST /api/v1/proyectos/{uuid}/vincular-cotizacion/
```

Payload:

```json
{
  "cotizacion_uuid": "..."
}
```

Validaciones:

```text
proyecto existe
tenant correcto
scope correcto
cotizacion existe
tenant correcto
cotizacion.estado == ACEPTADA
cliente compatible
sede compatible cuando aplique
```

---

# 24. FASE 18 — DESVINCULAR COTIZACIÓN

Crear acción separada:

```text
POST /api/v1/proyectos/{uuid}/desvincular-cotizacion/
```

Reglas:

- no eliminar la cotización;
- no borrar presupuesto automáticamente;
- no eliminar items de origen `COTIZACION`;
- solamente retirar el vínculo.

Después de desvincular:

```text
presupuesto histórico permanece
```

y se marca como:

```text
origen=COTIZACION
```

para trazabilidad histórica.

---

# 25. FASE 19 — REEMPLAZAR COTIZACIÓN

No permitir:

```text
PATCH cotizacion=<otra>
```

silenciosamente.

Si el proyecto ya tiene cotización:

```text
Cambio de cotización
```

debe ser una acción explícita.

Ejemplo:

```text
reemplazar-cotizacion
```

Debe advertir:

```text
Este proyecto ya posee una cotización vinculada.
Los costos sincronizados actualmente pertenecen a esa cotización.
¿Desea reemplazarla?
```

La acción no debe borrar los costos manuales.

---

# 26. FASE 20 — UI FASE 2

La sección debe quedar aproximadamente:

```text
2. Planeación
────────────────────────────────────

Cotización del proyecto

[ Buscar cotización aceptada ▼ ]

COT-0042
Cliente: Empresa XYZ
Estado: ACEPTADA
Fecha: 02/10/2026

Valor cotizado antes de IVA:
$ 85.000.000

────────────────────────────────────
RECURSOS DISPONIBLES
────────────────────────────────────

Mano de Obra
Cotizado:      $ 25.000.000
Costo base:    $ 18.000.000

Materiales
Cotizado:      $ 30.000.000
Costo base:    $ 22.000.000

Equipos
Cotizado:      $ 30.000.000
Costo base:    $ 25.000.000

────────────────────────────────────

[ Ingresar costo manual ]
[ Sincronizar costos cotización ]

────────────────────────────────────
DESGLOSE DE COSTOS PLANEADOS
────────────────────────────────────

Origen       Categoría     Descripción      Cant.    Total
Manual       Materiales    ...
Cotización   Equipos       ...
Cotización   Mano Obra     ...
```

---

# 27. FASE 21 — ESTADOS DE LA UI

### Sin cotización

Mostrar:

```text
No hay cotización vinculada.
[ Vincular cotización ]
```

### Cotización inválida

Mostrar:

```text
La cotización no está aceptada.
```

### Cotización aceptada

Mostrar:

```text
Cotización aceptada
```

### Cotización sincronizada

Mostrar:

```text
Última sincronización:
02/10/2026 14:30

4 líneas sincronizadas
5 líneas manuales preservadas
```

---

# 28. FASE 22 — ELIMINAR RESPONSABLE TÉCNICO DEL FORMULARIO

En:

```text
apps/tenant/proyectos/templates/tenant/proyectos/offcanvas_form.html
```

eliminar:

```text
Responsable Técnico (Nómina)
```

y sus elementos:

```text
proyecto-responsable-tecnico-select
proyecto-responsable-tecnico-id
proyecto-responsable-tecnico-nombre
```

### También actualizar

```text
proyectos_editor.js
```

Eliminar de:

```text
recolectarDatosFormulario()
```

los campos:

```text
responsable_tecnico_id
responsable_tecnico_nombre
```

Eliminar también la lógica de limpieza específica del formulario para esos inputs.

---

# 29. FASE 23 — NO MANDAR RESPONSABLE TÉCNICO DESDE LA UI

Actualizar el cliente para que la UI ya no envíe:

```json
{
  "responsable_tecnico_id": "...",
  "responsable_tecnico_nombre": "..."
}
```

al guardar el proyecto.

El backend puede mantener esos campos para:

```text
históricos
migraciones
compatibilidad
otras integraciones
```

pero no serán editables desde este formulario.

---

# 30. FASE 24 — RESPONSABLE ACTUAL

Revisar cuidadosamente esta lógica:

```python
asignar_snapshot_responsable()
```

porque actualmente:

```text
fase PLANEACION
    -> responsable_tecnico
    -> responsable_actual
```

Al eliminar el campo del formulario, no debe producirse:

```text
responsable_actual = None
```

por efecto secundario.

La transición de fase debe seguir funcionando sin requerir:

```text
responsable_id
```

---

# 31. FASE 25 — PRESUPUESTO Y FASE DE CIERRE

La restricción actual:

```text
CIERRE
```

bloquea:

```text
crear presupuesto
actualizar presupuesto
eliminar presupuesto
```

Debe mantenerse.

La sincronización de cotización también debe quedar bloqueada en:

```text
CIERRE
```

Respuesta:

```text
No se pueden sincronizar costos de una cotización en fase Cierre.
```

---

# 32. FASE 26 — COTIZACIÓN ACEPTADA COMO FUENTE INMUTABLE

La máquina de estados actual de Cotización hace terminal:

```text
ACEPTADA
```

Esto beneficia la sincronización.

Una vez aceptada:

```text
Cotización
    ↓
Planeación
```

debe ser considerada fuente estable.

No cambiar la máquina de estados de Cotización en esta misión.

---

# 33. FASE 27 — EVITAR IVA

La sincronización debe ignorar:

```text
iva_porcentaje
```

para calcular el presupuesto.

No usar:

```text
total_con_impuestos
```

como costo planeado.

Todo resumen de recursos para Planeación debe señalar claramente:

```text
Valores antes de IVA
```

---

# 34. FASE 28 — SELECTOR DE COTIZACIÓN EN LA UI

No cargar:

```text
500 cotizaciones
```

al abrir el formulario.

Usar búsqueda:

```text
GET /api/v1/cotizaciones/
```

con:

```text
estado=ACEPTADA
search=<texto>
cliente=<cliente>
```

idealmente con límite:

```text
10-20 resultados
```

Esto evita el mismo problema de escala encontrado previamente en proveedores/proyectos de Compras.

---

# 35. FASE 29 — FRONTEND SSoT

Agregar al:

```text
proyectos.api.js
```

operaciones explícitas:

```javascript
cotizacionesPlaneacion.list(...)
cotizacionesPlaneacion.get(...)
cotizacionesPlaneacion.vincular(...)
cotizacionesPlaneacion.desvincular(...)
presupuesto.sincronizarCotizacion(...)
```

Todo mediante:

```text
Sintel.Core.Http
```

No usar:

```text
fetch()
```

directamente.

---

# 36. FASE 30 — SINCRONIZACIÓN DEL RESUMEN

Después de:

```text
vincular cotización
```

hacer:

```text
GET resumen cotización
GET presupuesto proyecto
```

y actualizar ambos paneles.

Después de:

```text
sincronizar costos
```

hacer:

```text
GET presupuesto
GET proyecto
```

para actualizar:

```text
costo_planeado_total
utilidad_planeada
margen_planeado
```

---

# 37. FASE 31 — KPI DEL PROYECTO

Después de sincronizar, el proyecto debe reflejar:

```text
valor_contrato_proyectado
costo_planeado_total
utilidad_planeada
margen_planeado
```

No recalcular estos indicadores en JavaScript como SSoT.

JavaScript solo presenta los valores retornados por backend.

---

# 38. FASE 32 — DETALLE DE ORIGEN

En la tabla del presupuesto agregar:

```text
Origen
```

con:

```text
Manual
Cotización
```

y opcionalmente:

```text
COT-0042
```

para identificar rápidamente el origen.

---

# 39. FASE 33 — EDICIÓN DE ITEMS SIN ROMPER TRAZABILIDAD

Regla recomendada:

### Item MANUAL

Puede editarse normalmente.

### Item COTIZACION

No debe editarse silenciosamente como si fuera manual.

Opciones:

```text
Editar como manual
```

o:

```text
Sobrescribir desde cotización
```

Para primera implementación:

```text
Item de cotización = solo sincronizable
```

Esto evita divergencia.

---

# 40. FASE 34 — SOBRESCRITURA CONTROLADA

Si el usuario desea modificar un costo proveniente de cotización:

```text
Convertir a Manual
```

acción:

```text
origen = MANUAL
cotizacion_item_uuid = NULL
```

y desde ahí se podrá editar manualmente.

Esto conserva la trazabilidad:

```text
Antes:
COTIZACION

Después:
MANUAL
```

---

# 41. FASE 35 — MANTENER LA LÓGICA ACTUAL DEL PRESUPUESTO

No reemplazar:

```text
PresupuestoBusinessService
```

por otro servicio.

Extenderlo.

Objetivo:

```text
PresupuestoBusinessService
├── crear_item()
├── actualizar_item()
├── eliminar_item()
├── sincronizar_desde_cotizacion()
└── recalcular_proyecto()
```

---

# 42. FASE 36 — SERVICIO DE ORQUESTACIÓN RECOMENDADO

Crear o extender una única capa para el caso de uso:

```text
ProyectoCotizacionPlaneacionService
```

Responsabilidades:

```text
vincular_cotizacion()
obtener_resumen_cotizacion()
desvincular_cotizacion()
sincronizar_costos()
```

No repartir estas reglas entre:

```text
ViewSet
Serializer
JavaScript
Template
```

---

# 43. FASE 37 — NO USAR SEÑALES

PROHIBIDO:

```text
post_save(Cotizacion)
```

para:

```text
crear presupuesto
```

PROHIBIDO:

```text
post_save(Proyecto)
```

para:

```text
sincronizar cotización
```

La acción debe ser explícita.

---

# 44. FASE 38 — EVENTOS FUNCIONALES

Después de una sincronización exitosa disparar un evento frontend:

```text
proyecto-cotizacion-updated
```

y:

```text
proyecto-presupuesto-updated
```

Esto puede refrescar:

```text
tabla
KPIs
resumen
```

sin recargar toda la página.

---

# 45. FASE 39 — MIGRACIÓN DEL SERIALIZER

`ProyectoDetailSerializer` debe exponer directamente:

```text
cotizacion
cotizacion_uuid
cotizacion_numero
cotizacion_estado
cotizacion_fecha
cotizacion_valor_antes_iva
```

y:

```text
cotizacion_recursos
```

como información calculada/read-only.

La UI no debería tener que reconstruir esto desde:

```text
Factura
```

---

# 46. FASE 40 — PRESUPUESTO COMO RECURSO DEL PROYECTO

El resultado conceptual será:

```text
Proyecto
│
├── Cotización ACEPTADA
│
├── Recursos disponibles
│   ├── Mano de Obra
│   ├── Materiales
│   └── Equipos
│
├── Presupuesto manual
│
├── Presupuesto sincronizado
│
├── Costo Planeado
│
├── Costo Real
│
└── Margen
```

Esto prepara correctamente las siguientes fases:

```text
3. Ejecución
4. Cierre
```

---

# 47. FASE 41 — IMPACTO EN EJECUCIÓN

No implementar todavía consumos reales.

La sincronización solo representa:

```text
planeado
```

No debe tocar:

```text
Inventario
Kardex
Pedidos
Recepciones
Nómina
Costos reales
```

Estos siguen perteneciendo a sus respectivos dominios.

---

# 48. FASE 42 — IMPACTO EN VENTAS

No hacer que Proyecto dependa de Venta.

La arquitectura debe continuar:

```text
Cotización
    ├── Proyecto
    └── Venta opcional
```

No:

```text
Proyecto -> Venta obligatoria
```

---

# 49. FASE 43 — PRUEBAS FUNCIONALES MANUALES

Al final de la misión realizar únicamente la validación de UI/flujo solicitada.

## Caso 1

Crear Proyecto.

Verificar:

```text
Cotización = ninguna
```

## Caso 2

Abrir Fase 2.

Verificar que NO exista:

```text
Responsable Técnico (Nómina)
```

## Caso 3

Buscar cotización:

```text
BORRADOR
```

Debe no aparecer.

## Caso 4

Buscar cotización:

```text
ENVIADA
```

Debe no aparecer.

## Caso 5

Buscar cotización:

```text
ACEPTADA
```

Debe aparecer.

## Caso 6

Vincular cotización.

Verificar:

```text
Número
Cliente
Estado
Valor antes de IVA
```

## Caso 7

Verificar resumen:

```text
Mano de Obra
Materiales
Equipos
```

## Caso 8

Agregar presupuesto manual.

Verificar:

```text
Origen = Manual
```

## Caso 9

Pulsar:

```text
Sincronizar costos de cotización
```

Verificar:

```text
Origen = Cotización
```

## Caso 10

Agregar otra línea manual.

Volver a sincronizar.

Verificar:

```text
Manual permanece
Cotización se actualiza
No hay duplicados
```

## Caso 11

Verificar IVA.

Los valores sincronizados deben mostrar:

```text
ANTES DE IVA
```

## Caso 12

Avanzar a:

```text
CIERRE
```

Verificar que sincronización quede bloqueada.

---

# 50. FASE 44 — CRITERIOS DE ACEPTACIÓN

La misión solo está terminada cuando:

```text
[ ] Proyecto tiene vínculo directo con Cotización
[ ] Solo ACEPTADA puede vincularse
[ ] Tenant isolation validado
[ ] OrganizationalScope validado
[ ] Cliente compatible
[ ] UI muestra cotización en Fase 2
[ ] Resumen Mano de Obra
[ ] Resumen Materiales
[ ] Resumen Equipos
[ ] Valores antes de IVA
[ ] Valor cotizado separado de costo base
[ ] Presupuesto manual sigue siendo primera opción
[ ] Botón Sincronizar costos de cotización
[ ] Sincronización idempotente
[ ] Items manuales preservados
[ ] Items de cotización identificables
[ ] No duplicados
[ ] Se puede desvincular sin borrar histórico
[ ] No se modifica Inventario
[ ] No se modifica Nómina
[ ] No se modifica Venta
[ ] No se altera CxP
[ ] Responsable Técnico removido del formulario
[ ] Backend histórico de Responsable Técnico no se rompe
[ ] Service Layer mantiene SSoT
[ ] No lógica en signals
[ ] Frontend usa Sintel.Core.Http
```

---

# 51. FASE 45 — ORDEN EXACTO DE IMPLEMENTACIÓN

```text
0. Baseline actual
1. Modelo Proyecto -> Cotización
2. Migración histórica
3. DSV / scope / cliente
4. Selector Cotizaciones Aceptadas
5. Resumen de recursos
6. Clasificación PRODUCTO/MATERIAL/SERVICIO
7. Valores antes de IVA
8. Origen MANUAL/COTIZACION
9. Sincronización idempotente
10. Action API vincular
11. Action API sincronizar
12. Serializer
13. UI Fase 2
14. Botón sincronización
15. Eliminar Responsable Técnico del formulario
16. Actualizar JS
17. Recalcular KPIs backend
18. Compatibilidad con histórico
19. Validación manual final
```

---

# 52. DECISIONES IMPORTANTES

## Decisión A

No utilizar:

```text
Factura -> Cotización
```

como fuente principal.

Usar:

```text
Proyecto -> Cotización
```

## Decisión B

Estado real:

```text
ACEPTADA
```

No crear:

```text
APROBADA
```

## Decisión C

Presupuesto:

```text
Manual = primera opción
Cotización = sincronización opcional
```

## Decisión D

Sincronización:

```text
solo costos
antes de IVA
```

## Decisión E

Preservar manual:

```text
MANUAL no se sobreescribe
COTIZACION sí se sincroniza
```

## Decisión F

Responsable Técnico:

```text
eliminar del formulario
mantener temporalmente en backend por compatibilidad
```

---

# 53. RESULTADO DESEADO

El encargado del proyecto debe poder abrir:

```text
/admin.sintel.net.co/workspace/#proyectos
```

editar un proyecto y llegar a:

```text
2. Planeación
```

para responder rápidamente:

```text
¿Qué cotización fue aceptada?

¿Cuánto presupuesto comercial tiene?

¿Cuánto corresponde a mano de obra?

¿Cuánto corresponde a materiales?

¿Cuánto corresponde a equipos?

¿Cuál es el costo base disponible?

¿Qué costos ya ingresé manualmente?

¿Qué costos vienen de la cotización?

¿Cuánto tengo planeado antes de IVA?

¿Cuál es mi utilidad y margen?
```

sin tener que abrir otra aplicación ni reconstruir la información manualmente.

---

# 54. REGLA FINAL DE ARQUITECTURA

El flujo debe terminar así:

```text
                    PROYECTO
                       |
                       v
             COTIZACIÓN ACEPTADA
                       |
          +------------+------------+
          |            |            |
          v            v            v
      SERVICIOS     MATERIALES    PRODUCTOS
          |            |            |
          v            v            v
     MANO DE OBRA   MATERIALES     EQUIPOS
          |            |            |
          +------------+------------+
                       |
                       v
              COSTO BASE PRE-IVA
                       |
             +---------+---------+
             |                   |
             v                   v
          MANUAL             COTIZACIÓN
        (principal)          (opcional)
             |                   |
             +---------+---------+
                       |
                       v
              PRESUPUESTO PROYECTO
                       |
             +---------+---------+
             |                   |
             v                   v
          PLANEADO              REAL
             |                   |
             +---------+---------+
                       |
                       v
                 UTILIDAD / MARGEN
```

## No modificar en esta misión

```text
Inventario
Kardex
Recepciones
Nómina
Ventas
Facturación
Contabilidad
CxP
```

La misión se limita al flujo:

```text
Cotización ACEPTADA
        ↓
Proyecto / Planeación
        ↓
Recursos
        ↓
Presupuesto Planeado
```

